"""Copy and normalize a user-selected raster background into the app profile."""
import base64
import json
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImageReader
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def import_background(source, directory):
    source = Path(source)
    if source.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.bmp'):
        raise ValueError('Choisissez une image PNG, JPEG, WebP ou BMP.')
    if source.stat().st_size > 50 * 1024 * 1024:
        raise ValueError('L’image doit faire moins de 50 Mo.')
    reader = QImageReader(str(source))
    reader.setDecideFormatFromContent(True)
    reader.setAutoTransform(True)
    size = reader.size()
    if not size.isValid() or max(size.width(), size.height()) > 24000:
        raise ValueError('Dimensions d’image invalides ou trop grandes.')
    if max(size.width(), size.height()) > 2560:
        reader.setScaledSize(size.scaled(2560, 2560, Qt.AspectRatioMode.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        raise ValueError('Impossible de lire cette image : ' + reader.errorString())
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    pending = directory / 'background.tmp.png'
    if not image.save(str(pending), 'PNG'):
        raise OSError('Impossible d’enregistrer l’image de fond.')
    pending.replace(directory / 'background.png')
    (directory / 'background.json').write_text(json.dumps({'name': source.name}, ensure_ascii=False), encoding='utf8')
    return state(directory)


def state(directory):
    path = Path(directory) / 'background.png'
    if not path.is_file():
        return {'url': '', 'name': ''}
    try:
        name = json.loads((Path(directory) / 'background.json').read_text(encoding='utf8'))['name']
    except (OSError, ValueError, KeyError):
        name = 'Mon image'
    # A data URI avoids local-file origin restrictions and survives install location changes.
    return {'url': 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode('ascii'), 'name': name}


def clear(directory):
    for name in ('background.png', 'background.json'):
        (Path(directory) / name).unlink(missing_ok=True)
    return {'url': '', 'name': ''}


def import_url(url, directory):
    parsed = urlsplit(url.strip())
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Utilisez un lien direct HTTP ou HTTPS vers une image.')
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / 'logo-import.png'
    try:
        with urlopen(Request(url, headers={'User-Agent': 'ZelyvaroAudioLive'}), timeout=12) as response:
            if urlsplit(response.url).scheme not in ('https', 'http'):
                raise ValueError('Redirection de lien non prise en charge.')
            data = response.read(20 * 1024 * 1024 + 1)
        if len(data) > 20 * 1024 * 1024:
            raise ValueError('Le logo doit faire moins de 20 Mo.')
        temporary.write_bytes(data)
        result = import_background(temporary, folder)
        result['name'] = Path(parsed.path).name or 'Logo importé par lien'
        (folder / 'background.json').write_text(json.dumps({'name': result['name']}), encoding='utf8')
        return result
    finally:
        temporary.unlink(missing_ok=True)
