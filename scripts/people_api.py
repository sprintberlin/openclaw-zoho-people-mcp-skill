#!/usr/bin/env python3
"""Direct Zoho People REST access for operations the MCP catalog does not expose.

Use this only when no MCP Action covers the operation. See references/LIMITATIONS.md.

Credentials come from environment variables, never from arguments:
    ZOHO_PEOPLE_CLIENT_ID
    ZOHO_PEOPLE_CLIENT_SECRET
    ZOHO_PEOPLE_REFRESH_TOKEN
    ZOHO_PEOPLE_DC              optional, default "eu"

Access tokens are cached in ~/.cache/zoho-people-api/tokens.json with mode 0600.
Zoho rate-limits the token endpoint, so refreshing on every call will fail.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ACCOUNTS_DC = {
    "eu": "accounts.zoho.eu",
    "com": "accounts.zoho.com",
    "in": "accounts.zoho.in",
    "com.au": "accounts.zoho.com.au",
    "jp": "accounts.zoho.jp",
    "ca": "accounts.zohocloud.ca",
    "sa": "accounts.zoho.sa",
    "com.cn": "accounts.zoho.com.cn",
}

PEOPLE_DC = {
    "eu": "people.zoho.eu",
    "com": "people.zoho.com",
    "in": "people.zoho.in",
    "com.au": "people.zoho.com.au",
    "jp": "people.zoho.jp",
    "ca": "people.zohocloud.ca",
    "sa": "people.zoho.sa",
    "com.cn": "people.zoho.com.cn",
}

TOKEN_EXPIRY_MARGIN_SECONDS = 300


class PeopleApiError(RuntimeError):
    """Raised when credentials are missing or a Zoho request fails."""


def resolve_dc(dc=None):
    value = (dc or os.environ.get("ZOHO_PEOPLE_DC") or "eu").strip().lower()
    if value not in PEOPLE_DC:
        raise PeopleApiError(f"unknown data center '{value}'; expected one of {', '.join(sorted(PEOPLE_DC))}")
    return value


def load_credentials(dc=None):
    """Read Self Client credentials from the environment. Values are never logged."""
    missing = [
        name
        for name in ("ZOHO_PEOPLE_CLIENT_ID", "ZOHO_PEOPLE_CLIENT_SECRET", "ZOHO_PEOPLE_REFRESH_TOKEN")
        if not os.environ.get(name)
    ]
    if missing:
        raise PeopleApiError("missing environment variable(s): " + ", ".join(missing))
    return {
        "client_id": os.environ["ZOHO_PEOPLE_CLIENT_ID"],
        "client_secret": os.environ["ZOHO_PEOPLE_CLIENT_SECRET"],
        "refresh_token": os.environ["ZOHO_PEOPLE_REFRESH_TOKEN"],
        "dc": resolve_dc(dc),
    }


def token_cache_path():
    override = os.environ.get("ZOHO_PEOPLE_TOKEN_CACHE")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "zoho-people-api" / "tokens.json"


def _cache_key(client_id, refresh_token, dc):
    return hashlib.sha256(f"{client_id}:{refresh_token}:{dc}".encode("utf-8")).hexdigest()


def _read_cached_token(client_id, refresh_token, dc):
    path = token_cache_path()
    if not path.is_file():
        return None
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    entry = entries.get(_cache_key(client_id, refresh_token, dc)) if isinstance(entries, dict) else None
    if not isinstance(entry, dict):
        return None
    token = entry.get("access_token")
    expires_at = entry.get("expires_at")
    if not token or not isinstance(expires_at, (int, float)) or time.time() >= float(expires_at):
        return None
    return str(token)


def _write_cached_token(client_id, refresh_token, dc, access_token, expires_in):
    path = token_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    entries = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                entries = loaded
        except (OSError, json.JSONDecodeError):
            entries = {}
    now = time.time()
    entries[_cache_key(client_id, refresh_token, dc)] = {
        "access_token": access_token,
        "expires_at": now + max(0, int(expires_in) - TOKEN_EXPIRY_MARGIN_SECONDS),
    }
    entries = {
        key: value
        for key, value in entries.items()
        if isinstance(value, dict) and isinstance(value.get("expires_at"), (int, float)) and value["expires_at"] > now
    }
    try:
        path.write_text(json.dumps(entries), encoding="utf-8")
        path.chmod(0o600)
    except OSError:
        return


def _post_form(url, payload, timeout=30):
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PeopleApiError(f"HTTP {exc.code} from Zoho: {detail}") from exc
    except urllib.error.URLError as exc:
        raise PeopleApiError(f"network error: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise PeopleApiError("Zoho returned invalid JSON") from exc


def access_token(credentials=None, use_cache=True, timeout=30):
    """Exchange the refresh token for a short-lived access token."""
    creds = credentials or load_credentials()
    if use_cache:
        cached = _read_cached_token(creds["client_id"], creds["refresh_token"], creds["dc"])
        if cached:
            return cached

    body = _post_form(
        f"https://{ACCOUNTS_DC[creds['dc']]}/oauth/v2/token",
        {
            "grant_type": "refresh_token",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
        },
        timeout=timeout,
    )
    if "error" in body:
        raise PeopleApiError(f"OAuth refresh failed: {body.get('error')}")
    token = body.get("access_token")
    if not token:
        raise PeopleApiError("OAuth refresh response contained no access_token")
    if use_cache:
        _write_cached_token(creds["client_id"], creds["refresh_token"], creds["dc"], token, body.get("expires_in", 3600))
    return token


def call(path, params=None, method="POST", credentials=None, timeout=30):
    """Call a Zoho People REST endpoint. `path` starts with /api/."""
    creds = credentials or load_credentials()
    token = access_token(creds, timeout=timeout)
    url = f"https://{PEOPLE_DC[creds['dc']]}{path}"
    query = urllib.parse.urlencode(params or {})
    data = None
    if method.upper() == "GET":
        url = f"{url}?{query}" if query else url
    else:
        data = query.encode("utf-8")

    request = urllib.request.Request(url, data=data, method=method.upper())
    request.add_header("Authorization", f"Zoho-oauthtoken {token}")
    if data is not None:
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PeopleApiError(f"HTTP {exc.code} from Zoho People: {detail}") from exc
    except urllib.error.URLError as exc:
        raise PeopleApiError(f"network error: {exc.reason}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PeopleApiError("Zoho People returned invalid JSON") from exc
