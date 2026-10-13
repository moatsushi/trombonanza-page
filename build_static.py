#!/usr/bin/env python3
"""Render the Flask site to static HTML."""

import shutil
from pathlib import Path

from app import app, get_db


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "dist"


def render(client, route, destination):
    response = client.get(route)
    if response.status_code != 200:
        raise RuntimeError(f"Could not render {route}: HTTP {response.status_code}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.data)


def build():

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(
        ROOT / "static",
        OUTPUT / "static",
        ignore=shutil.ignore_patterns(".DS_Store"),
    )

    with app.app_context():
        pages = [row[0] for row in get_db().execute("SELECT page FROM stage ORDER BY id")]

    client = app.test_client()
    render(client, "/", OUTPUT / "index.html")
    render(client, "/archive", OUTPUT / "archive.html")
    for page in pages:
        render(client, f"/concert/{page}", OUTPUT / "concert" / f"{page}.html")
        # Preserve the legacy /archive/<page> URLs used by the previous site.
        render(client, f"/archive/{page}", OUTPUT / "archive" / f"{page}.html")

    (OUTPUT / "404.html").write_text(
        "<!doctype html><html lang=\"ja\"><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width\">"
        "<title>ページが見つかりません - TROMBONANZA</title>"
        "<link rel=\"stylesheet\" href=\"/static/css/styles.css\">"
        "<body><main class=\"container text-center\" style=\"padding-top:20vh\">"
        "<p class=\"eyebrow text-accent\">404</p><h1>ページが見つかりません</h1>"
        "<p><a class=\"back-link\" href=\"/\">トップページへ戻る</a></p>"
        "</main></body></html>",
        encoding="utf-8",
    )
    print(f"Generated {2 + len(pages) * 2} pages in {OUTPUT}")


if __name__ == "__main__":
    build()
