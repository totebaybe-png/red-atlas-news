"""Publisher: talks to the Blogger API.

    python -m engine.blogger login     one-time Google sign-in (opens the browser)
    python -m engine.blogger check     shows the blog, its pages and recent posts

Credentials: client_secret.json (from Google Cloud) in the project folder; the sign-in result is
saved to data/blogger_token.json, or read from the BLOGGER_TOKEN env variable on GitHub.
"""
import json
import os
import sys
import time

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials

from . import config

SCOPES = ["https://www.googleapis.com/auth/blogger"]
API = "https://www.googleapis.com/blogger/v3"
CLIENT_FILE = config.ROOT / "client_secret.json"
TOKEN_FILE = config.DATA_DIR / "blogger_token.json"


def login():
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _creds():
    raw = os.getenv("BLOGGER_TOKEN") or (TOKEN_FILE.read_text(encoding="utf-8") if TOKEN_FILE.exists() else "")
    if not raw:
        raise RuntimeError("Not signed in to Blogger. Run: python -m engine.blogger login")
    creds = Credentials.from_authorized_user_info(json.loads(raw), SCOPES)
    if not creds.valid:
        creds.refresh(Request())
    return creds


class PublishBlocked(RuntimeError):
    """Blogger temporarily refuses to create new posts (updates still work)."""


class Blogger:
    def __init__(self):
        self.http = AuthorizedSession(_creds())
        blog = self._call("GET", "/blogs/byurl", params={"url": config.SITE_URL + "/"})
        self.blog_id = blog["id"]
        self.blog = blog

    def _call(self, method, path, **kw):
        for wait in (15, 30, 0):
            resp = self.http.request(method, API + path, timeout=60, **kw)
            is_rate_limit = resp.status_code == 429 or (
                resp.status_code == 403 and any(w in resp.text for w in ("rateLimit", "RATE_LIMIT", "quotaExceeded", "userRateLimitExceeded"))
            )
            if not is_rate_limit or not wait:
                break
            print(f"    Blogger rate-limit hit, waiting {wait}s...")
            time.sleep(wait)
        if resp.status_code == 403 and method == "POST":
            # Blogger's anti-spam brake on creating posts/pages: retrying only wastes time
            raise PublishBlocked(f"Blogger refused to create content: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise RuntimeError(f"Blogger API {method} {path}: {resp.status_code} {resp.text[:300]}")
        return resp.json() if resp.text else {}

    def publish_post(self, title, slug, html, labels, draft=False):
        """Creates the post with the slug as its first title so Blogger builds a short, clean URL
        (/2026/11/kyiv-missile-attack.html), then sets the real headline."""
        body = {"title": slug.replace("-", " "), "content": html, "labels": labels}
        post = self._call("POST", f"/blogs/{self.blog_id}/posts", params={"isDraft": str(draft).lower()}, json=body)
        post = self._call("PATCH", f"/blogs/{self.blog_id}/posts/{post['id']}", json={"title": title})
        return post

    def pages(self):
        """All live pages (the API returns them in batches)."""
        items, token = [], None
        while True:
            params = {"fetchBodies": "false", "status": "live", "maxResults": 100}
            if token:
                params["pageToken"] = token
            out = self._call("GET", f"/blogs/{self.blog_id}/pages", params=params)
            items += out.get("items", [])
            token = out.get("nextPageToken")
            if not token:
                return items

    def upsert_page(self, slug, title, html):
        """Updates /p/<slug>.html if it exists, otherwise creates it with a clean URL."""
        for page in self.pages():
            if page["url"].endswith(f"/p/{slug}.html"):
                return self._call("PATCH", f"/blogs/{self.blog_id}/pages/{page['id']}",
                                  json={"title": title, "content": html})
        page = self._call("POST", f"/blogs/{self.blog_id}/pages", json={"title": slug.replace("-", " "), "content": html})
        return self._call("PATCH", f"/blogs/{self.blog_id}/pages/{page['id']}", json={"title": title})

    def recent_posts(self, n=10):
        out = self._call("GET", f"/blogs/{self.blog_id}/posts",
                         params={"maxResults": n, "fetchBodies": "false", "status": ["live", "draft"]})
        return out.get("items", [])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "login":
        if not CLIENT_FILE.exists():
            sys.exit("client_secret.json is missing from the project folder")
        login()
        print("Signed in. Token saved to", TOKEN_FILE)
    b = Blogger()
    print(f"Blog: {b.blog['name']} | id {b.blog_id} | posts {b.blog['posts']['totalItems']} | pages {b.blog['pages']['totalItems']}")
    for p in b.pages():
        print("  page:", p["url"])
    for p in b.recent_posts(5):
        print("  post:", p.get("status"), p.get("url", "(draft)"), "|", p["title"][:70])
