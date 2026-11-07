"""Cliente HTTP mínimo (stdlib): solo https, hosts permitidos, timeout y tope de tamaño."""

import urllib.request
from urllib.parse import urlsplit

USER_AGENT = "alertas-amba/0.1 (sistema civico de alertas de inundacion; sin fines de lucro)"
TIMEOUT_S = 20
MAX_BYTES = 5 * 1024 * 1024
HOSTS_PERMITIDOS = frozenset({
    "ssl.smn.gob.ar",
    "www.hidro.gob.ar",
    "snih.hidricosargentina.gob.ar",
    "alerta.ina.gob.ar",
    "aviationweather.gov",
})


def validar_url(url: str) -> None:
    partes = urlsplit(url)
    if partes.scheme != "https" or partes.hostname not in HOSTS_PERMITIDOS:
        raise ValueError(f"URL no permitida: {url}")


class _RedirectSeguro(urllib.request.HTTPRedirectHandler):
    """Valida también el destino de cada redirección (evita SSRF por redirect)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        validar_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_RedirectSeguro())


def pedir(url: str, datos: bytes | None = None, headers: dict[str, str] | None = None,
          max_bytes: int = MAX_BYTES) -> str:
    validar_url(url)
    req = urllib.request.Request(url, data=datos, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with _opener.open(req, timeout=TIMEOUT_S) as resp:
        cuerpo = resp.read(max_bytes + 1)
        if len(cuerpo) > max_bytes:
            raise ValueError(f"respuesta demasiado grande: {url}")
        charset = resp.headers.get_content_charset() or "utf-8"
        return cuerpo.decode(charset, errors="replace")
