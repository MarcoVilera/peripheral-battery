"""Actualizaciones via GitHub Releases.

Cada release debe tener un tag "vX.Y.Z" y como asset el instalador
"PeripheralBattery-X.Y.Z-setup.exe" (lo genera build.ps1).
"""
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from version import GITHUB_REPO, VERSION

USER_AGENT = f"PeripheralBattery/{VERSION}"


def _parse(v):
    return tuple(int(x) for x in v.lstrip("vV").split(".") if x.isdigit())


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout)


def check():
    """Devuelve (version, url_instalador) si hay una version mas nueva, si no None."""
    if not GITHUB_REPO:
        return None
    with _get(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest") as r:
        rel = json.load(r)
    latest = rel.get("tag_name", "")
    if _parse(latest) <= _parse(VERSION):
        return None
    for asset in rel.get("assets", []):
        if asset["name"].lower().endswith("-setup.exe"):
            return latest.lstrip("vV"), asset["browser_download_url"]
    return None


def download_and_install(url):
    """Descarga el instalador y lo lanza en modo silencioso.

    El instalador cierra esta app, reemplaza los archivos y la vuelve a abrir.
    El que llama debe salir de la app apenas esta funcion retorna.
    """
    dest = Path(tempfile.gettempdir()) / url.rsplit("/", 1)[-1]
    with _get(url, timeout=120) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 16):
            f.write(chunk)
    subprocess.Popen(
        [str(dest), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
        creationflags=subprocess.DETACHED_PROCESS,
    )
