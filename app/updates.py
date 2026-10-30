"""Stable GitHub Releases and verified, private installer staging."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from packaging.version import Version, InvalidVersion
from version import APP, VERSION, REPOSITORY

API = f'https://api.github.com/repos/{REPOSITORY}'
MAX_SIZE = 1024 ** 3


@dataclass(frozen=True)
class Update:
    version: str
    name: str
    url: str
    size: int
    sha256: str


def trusted_url(url):
    p = urlsplit(url)
    return (p.scheme == 'https' and p.hostname == 'github.com' and p.port in (None, 443)
            and not p.username and not p.password
            and p.path.startswith(f'/{REPOSITORY}/releases/download/'))


def open_url(url):
    return urlopen(Request(url, headers={'User-Agent': f'ZelyvaroAudioLive/{VERSION}',
                                        'Accept': 'application/vnd.github+json'}), timeout=30)


def parse_release(info, current=VERSION):
    try:
        version = Version(info['tag_name'].removeprefix('v'))
    except (InvalidVersion, KeyError, TypeError):
        return None
    if (info.get('draft') or info.get('prerelease') or version.is_prerelease
            or version.is_devrelease or version <= Version(current)):
        return None
    name = f'ZelyvaroAudioLive-{version}-setup.exe'
    asset = next((a for a in info.get('assets', []) if a.get('name') == name), None)
    if not asset or not trusted_url(asset.get('browser_download_url', '')):
        raise ValueError('Installateur Windows absent ou URL GitHub invalide.')
    digest = asset.get('digest') or ''
    if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}', digest):
        # Older GitHub asset metadata: require the published companion checksum.
        checksum = next((a for a in info.get('assets', []) if a.get('name') == name + '.sha256'), None)
        if not checksum or not trusted_url(checksum.get('browser_download_url', '')):
            raise ValueError('Empreinte SHA-256 absente de la release.')
        with open_url(checksum['browser_download_url']) as response:
            digest = 'sha256:' + response.read(4096).decode('ascii').split()[0]
        if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}', digest):
            raise ValueError('Empreinte SHA-256 invalide.')
    size = int(asset.get('size', 0))
    if not 0 < size <= MAX_SIZE:
        raise ValueError('Taille de téléchargement invalide.')
    return Update(str(version), name, asset['browser_download_url'], size, digest[7:].lower())


def latest_update(current=VERSION):
    try:
        with open_url(API + '/releases/latest') as response:
            return parse_release(json.load(response), current)
    except HTTPError as exc:
        if exc.code == 404:
            return None  # No published stable release yet.
        raise


def download_update(update, directory, progress=lambda value: None):
    if not trusted_url(update.url) or not re.fullmatch(r'[a-f0-9]{64}', update.sha256):
        raise ValueError('Métadonnées de mise à jour invalides.')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='update-', dir=directory))
    partial = staging / 'installer.part'
    destination = staging / update.name
    count, digest = 0, hashlib.sha256()
    try:
        with open_url(update.url) as response, partial.open('xb') as out:
            while chunk := response.read(1024 * 1024):
                count += len(chunk)
                if count > update.size or count > MAX_SIZE:
                    raise ValueError('Le téléchargement dépasse la taille annoncée.')
                digest.update(chunk)
                out.write(chunk)
                progress(int(count * 100 / update.size))
        if count != update.size or digest.hexdigest() != update.sha256:
            raise ValueError('Contrôle SHA-256 ou taille incorrect : installation annulée.')
        with partial.open('rb') as file:
            if file.read(2) != b'MZ':
                raise ValueError('Le fichier reçu n’est pas un exécutable Windows.')
        partial.replace(destination)
        return destination
    except Exception:
        partial.unlink(missing_ok=True)
        raise
