"""Loopback-only live browser source, independent from the controls window."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hmac
import json
import os
import secrets
import socket
import struct
import threading
import time
from stream_format import FORMATS
from urllib.parse import urlsplit, parse_qs
from urllib.request import urlopen


class LoopbackServer(ThreadingHTTPServer):
    # SO_REUSEADDR permits simultaneous listeners on Windows. Never share a live
    # source port with another instance (including an older installed version).
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def get_request(self):
        connection, address = super().get_request()
        # SSE clients reconnect to the same URL after a restart. An RST on close
        # releases the fixed Windows port without an extended TIME_WAIT delay.
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                              struct.pack('hh' if os.name == 'nt' else 'ii', 1, 0))
        return connection, address


def preserve_existing_port(profile):
    """Adopt an existing 1.2 live source when migrating its persistent identity."""
    profile = Path(profile)
    destination = profile / 'stream-port.json'
    if destination.exists():
        return
    try:
        token = (profile / 'live-source-key.txt').read_text(encoding='ascii').strip()
    except OSError:
        return
    for port in range(17861, 17881):
        try:
            with urlopen(f'http://127.0.0.1:{port}/health?key={token}', timeout=.15) as response:
                state = json.load(response)
            if 'audio_packets' in state and 'clients' in state:
                pending = profile / 'stream-port.tmp.json'
                pending.write_text(json.dumps({'port': port}), encoding='utf8')
                pending.replace(destination)
                return
        except (OSError, ValueError):
            continue


class LiveServer:
    def __init__(self, assets, profile):
        self.assets = Path(assets)
        profile = Path(profile)
        profile.mkdir(parents=True, exist_ok=True)
        token_file = profile / 'live-source-key.txt'
        previous_identity = token_file.exists()
        try:
            self.token = token_file.read_text(encoding='ascii').strip()
        except OSError:
            self.token = secrets.token_urlsafe(24)
            token_file.write_text(self.token, encoding='ascii')
        self.condition = threading.Condition()
        self.events = {}
        self.serial = 0
        self.clients = 0
        self.audio_packets = 0
        self.stopping = False
        owner = self
        port_file = profile / 'stream-port.json'
        try:
            saved_port = json.loads(port_file.read_text(encoding='utf8'))['port']
            if type(saved_port) is not int or not 17861 <= saved_port <= 17880:
                raise ValueError('Port de diffusion enregistré invalide.')
        except FileNotFoundError:
            # Windows 1.2 used 17861 before port persistence existed. Adopt a
            # running legacy listener when available; otherwise retain that URL.
            if previous_identity:
                preserve_existing_port(profile)
                saved_port = json.loads(port_file.read_text(encoding='utf8'))['port'] if port_file.exists() else 17861
            else:
                saved_port = None

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def log_message(self, *args):
                pass
            def do_GET(self):
                parsed = urlsplit(self.path)
                token = parse_qs(parsed.query).get('key', [''])[0]
                host = self.headers.get('Host', '')
                if host not in (f'127.0.0.1:{owner.port}', f'localhost:{owner.port}') or not hmac.compare_digest(token, owner.token):
                    self.send_error(403)
                    return
                output_format = parse_qs(parsed.query).get('format', [''])[0]
                if parsed.path == '/live' and output_format and output_format not in FORMATS:
                    self.send_error(400, 'Unknown output format')
                    return
                if parsed.path == '/live' and output_format and parse_qs(parsed.query).get('stage') != ['1']:
                    _, width, height, _ = FORMATS[output_format]
                    # The host owns its viewport and scene transform. Fill every pixel
                    # it supplies; a fixed contain-scaled iframe creates black bars
                    # when TikTok initializes a portrait link with a landscape viewport.
                    source = f'/live?key={owner.token}&amp;format={output_format}&amp;stage=1'
                    body = (f'<!doctype html><html lang="fr"><meta charset="utf-8"><title>ZELYVARO · {width} × {height}</title>'
                            '<meta name="viewport" content="width=device-width,initial-scale=1">'
                            '<style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:transparent}'
                            'iframe{display:block;position:fixed;inset:0;border:0;width:100%;height:100%}</style>'
                            f'<body data-format="{output_format}" data-target-width="{width}" data-target-height="{height}">'
                            f'<iframe id="stage" title="Diffusion {width} × {height}" src="{source}"></iframe></body></html>').encode('utf8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if parsed.path == '/events':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache, no-store')
                    self.send_header('Connection', 'keep-alive')
                    self.end_headers()
                    seen = {}
                    with owner.condition:
                        owner.clients += 1
                    try:
                        while not owner.stopping:
                            with owner.condition:
                                owner.condition.wait(timeout=.05)
                                changed = [(kind, seq, payload) for kind, (seq, payload) in owner.events.items()
                                           if seen.get(kind) != seq]
                            for kind, seq, payload in changed:
                                self.wfile.write(f'event: {kind}\ndata: {payload}\n\n'.encode('utf8'))
                                seen[kind] = seq
                            if changed:
                                self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        pass
                    finally:
                        with owner.condition:
                            owner.clients -= 1
                    return
                if parsed.path == '/health':
                    body = json.dumps({'audio_packets': owner.audio_packets, 'clients': owner.clients}).encode()
                    mime = 'application/json'
                elif parsed.path in ('/live', '/themes.js', '/app.js', '/overlays.js', '/logo.png', '/app.ico'):
                    name = {'/live': 'wallpaper.html', '/themes.js': 'themes.js', '/app.js': 'app.js', '/overlays.js': 'overlays.js', '/logo.png':'logo.png', '/app.ico':'app.ico'}[parsed.path]
                    body = (owner.assets / name).read_bytes()
                    mime = 'text/html; charset=utf-8' if name.endswith('.html') else 'application/javascript; charset=utf-8'
                    if name.endswith('.png'):
                        mime = 'image/png'
                    elif name.endswith('.ico'):
                        mime = 'image/x-icon'
                    if name.endswith('.html'):
                        text = body.decode('utf8').replace('<script src="qrc:///qtwebchannel/qwebchannel.js"></script>', '')
                        text = text.replace('src="themes.js"', f'src="/themes.js?key={owner.token}"')
                        text = text.replace('src="app.js"', f'src="/app.js?key={owner.token}"')
                        text = text.replace('src="overlays.js"', f'src="/overlays.js?key={owner.token}"')
                        body = text.encode('utf8')
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                self.wfile.write(body)

        for port in ([saved_port] if saved_port else range(17861, 17881)):
            try:
                self.http = LoopbackServer(('127.0.0.1', port), Handler)
                self.port = port
                break
            except OSError:
                continue
        else:
            raise OSError(f'Le port personnel de diffusion {saved_port} est occupé. Fermez la précédente instance ou le programme qui utilise ce port, puis relancez ZELYVARO. Vos liens sont conservés.' if saved_port else 'Aucun port local disponible pour la sortie de diffusion.')
        if not port_file.exists():
            pending = profile / 'stream-port.tmp.json'
            pending.write_text(json.dumps({'port': self.port}), encoding='utf8')
            pending.replace(port_file)
        self.http.daemon_threads = True
        self.thread = threading.Thread(target=lambda: self.http.serve_forever(poll_interval=.1), daemon=True)
        self.thread.start()

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}/live?key={self.token}#tiktok.studio'

    def formatted_url(self, output_format):
        if output_format not in FORMATS:
            raise ValueError('Unknown output format')
        return f'http://127.0.0.1:{self.port}/live?key={self.token}&format={output_format}#tiktok.studio'

    def publish(self, kind, payload):
        data = json.dumps(payload, ensure_ascii=True, separators=(',', ':'))
        with self.condition:
            self.serial += 1
            self.events[kind] = (self.serial, data)
            if kind == 'audio':
                self.audio_packets += 1
            self.condition.notify_all()

    def close(self):
        self.stopping = True
        with self.condition:
            self.condition.notify_all()
        self.http.shutdown()
        self.http.server_close()
