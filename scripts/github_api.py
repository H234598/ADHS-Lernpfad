"""Minimaler, hostgebundener JSON-Client für die GitHub REST API."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

GITHUB_API_HOST = "api.github.com"


def _validate_github_api_url(url: str) -> str:
    """Nur HTTPS-Ziele auf dem kanonischen GitHub-API-Host zulassen."""

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError(f"Ungültige GitHub-API-URL: {url!r}") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != GITHUB_API_HOST
        or port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise RuntimeError(
            "GitHub-API-Aufruf auf unerwartetes Ziel abgelehnt: "
            f"{parsed.scheme}://{parsed.netloc}"
        )
    return url


def request_json(
    url: str,
    token: str | None,
    *,
    user_agent: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> Any:
    """JSON von GitHubs REST API abrufen oder mit begrenztem Fehlertext abbrechen."""

    validated_url = _validate_github_api_url(url)
    request = Request(
        validated_url,
        data=None if data is None else json.dumps(data).encode("utf-8"),
        method=method,
    )
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", user_agent)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        # B310 ist hier bewusst lokal unterdrückt: Scheme, Host, Port und
        # Credentials wurden unmittelbar zuvor explizit allow-listed.
        with urlopen(request, timeout=30) as response:  # nosec B310
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API {exc.code} für {validated_url}: {detail[:500]}"
        ) from exc
