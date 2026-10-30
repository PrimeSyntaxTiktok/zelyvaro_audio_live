"""Loopback-only live browser source, independent from the controls window."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hmac
import json
import secrets
import threading
import time
from urllib.parse import urlsplit, parse_qs


class LiveServer:
    def __init__(self, assets, profile):
        self.assets = Path(assets)
        profile = Path(profile)
        profile.mkdir(parents=True, exist_ok=True)
        token_file = profile / 'live-source-key.txt'
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

        for port in range(17861, 17881):
            try:
                self.http = ThreadingHTTPServer(('127.0.0.1', port), Handler)
                self.port = port
                break
            except OSError:
                continue
        else:
            raise OSError('Aucun port local disponible pour la sortie de diffusion.')
        self.http.daemon_threads = True
        self.thread = threading.Thread(target=lambda: self.http.serve_forever(poll_interval=.1), daemon=True)
        self.thread.start()

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}/live?key={self.token}#tiktok.studio'

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
