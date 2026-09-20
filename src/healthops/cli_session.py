"""Interactive local API sign-in for maintenance checks; no credential files required."""

import getpass
import json
import os
from http.cookiejar import CookieJar
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener


def signed_in_opener(base_url):
    base = urlsplit(base_url)
    if base.hostname not in {"localhost", "127.0.0.1", "::1"} or base.scheme not in {
        "http",
        "https",
    }:
        raise ValueError("Maintenance sign-in requires a loopback HealthOps URL.")
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    request = Request(
        base_url.rstrip("/") + "/api/v1/auth/login",
        data=json.dumps(
            {
                "username": os.environ.get("HEALTHOPS_USERNAME") or input("HealthOps username: "),
                "password": getpass.getpass("HealthOps password: "),
            }
        ).encode(),
        headers={"Content-Type": "application/json", "X-HealthOps-Request": "1"},
    )
    with opener.open(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError("Sign-in failed.")
    return opener
