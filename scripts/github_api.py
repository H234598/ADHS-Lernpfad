"""Minimaler, hostgebundener JSON-Client für die GitHub REST API."""

from __future__ import annotations

from http.client import HTTPSConnection
import json
from typing import Any
from urllib.parse import urlsplit

GITHUB_API_HOST = "api.github.com"


def _validated_path(url: str) -> str:
    """Nur HTTPS-Ziele auf dem kanonischen GitHub-API-Host zulassen."""

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError(f"Ungültige GitHub-API-URL: {url!r}") from exc

    if (parsed.scheme, parsed.hostname, port) not in {
        ("https", GITHUB_API_HOST, None),
        ("https", GITHUB_API_HOST, 443),
    }:
        raise RuntimeError(
            "GitHub-API-Aufruf auf unerwartetes Ziel abgelehnt: "
            f"{parsed.scheme}://{parsed.netloc}"
        )
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError("Credentials in GitHub-API-URLs sind unzulässig")
    if not parsed.path.startswith("/"):
        raise RuntimeError("GitHub-API-Pfad muss absolut sein")
    return parsed.path + (f"?{parsed.query}" if parsed.query else "")


def request_json(
    url: str,
    token: str | None,
    *,
    user_agent: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> Any:
    """JSON ausschließlich über eine TLS-Verbindung zu api.github.com abrufen."""

    path = _validated_path(url)
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": user_agent,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"

    connection = HTTPSConnection(GITHUB_API_HOST, 443, timeout=30)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
    finally:
        connection.close()

    text = raw.decode("utf-8", errors="replace")
    if not 200 <= response.status < 300:
        raise RuntimeError(
            f"GitHub API {response.status} für https://{GITHUB_API_HOST}{path}: "
            f"{text[:500]}"
        )
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GitHub API lieferte kein gültiges JSON") from exc
