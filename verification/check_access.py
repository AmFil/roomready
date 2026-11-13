"""Run the Week 3 service account checks from a signed-in Google Cloud Shell."""

import argparse
from html.parser import HTMLParser
from http.client import HTTPException
from http.cookiejar import CookieJar
import json
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, HTTPCookieProcessor, Request
from uuid import uuid4


PROJECT = "roomready-team-261030"
ORIGIN = "https://roomready-et53s35jvq-uc.a.run.app"
INITIAL_RELEASE = "212d9449c2e6d4af2f33a4d9214dcfbce4f382b8"


class CheckFailed(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    # Only the original service or IAM endpoint receives a credential.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def call(opener, request):
    try:
        response = opener.open(request, timeout=20)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read(2_000_000)


def sign_account(account_name, operator_token):
    email = f"{account_name}@{PROJECT}.iam.gserviceaccount.com"
    now = int(time.time())
    claims = {"iss": email, "sub": email, "aud": ORIGIN + "/*", "iat": now, "exp": now + 600}
    endpoint = f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{email}:signJwt"
    request = Request(endpoint, data=json.dumps({"payload": json.dumps(claims)}).encode(),
                      headers={"Authorization": "Bearer " + operator_token, "Content-Type": "application/json"})
    code, _, body = call(build_opener(NoRedirect()), request)
    if code != 200:
        raise CheckFailed(f"Google could not sign for {account_name} (HTTP {code}). Check your Cloud Shell account and its Token Creator grant.")
    signed = json.loads(body).get("signedJwt", "")
    if not isinstance(signed, str) or signed.count(".") != 2:
        raise CheckFailed("Google did not return a signed test credential.")
    return signed


class Page(HTMLParser):
    def __init__(self, body):
        super().__init__()
        self.csrf = None
        self.rows = {}
        self.current = None
        self.feed(body.decode())

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if tag == "input" and fields.get("name") == "csrf_token" and not self.csrf:
            self.csrf = fields.get("value")
        if tag == "article":
            key = fields.get("data-request-id", "")
            if not re.fullmatch("[a-f0-9]{32}", key):
                raise CheckFailed("The form returned an invalid request ID.")
            self.current = key
            self.rows[key] = {"status": fields.get("data-status"), "text": ""}

    def handle_data(self, data):
        if self.current:
            self.rows[self.current]["text"] += data

    def handle_endtag(self, tag):
        if tag == "article":
            self.current = None


def app_request(opener, token, path, data=None):
    # Paths are supplied only by these checks, including validated request IDs.
    headers = {"Accept": "text/html, application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if data is not None:
        headers["Referer"] = ORIGIN + "/"
    return call(opener, Request(ORIGIN + path, headers=headers,
                                data=urlencode(data).encode() if data is not None else None))


def run_checks(release, approved_token, denied_token):
    approved = build_opener(NoRedirect(), HTTPCookieProcessor(CookieJar()))

    def checked(path, data=None):
        code, headers, body = app_request(approved, approved_token, path, data)
        expected = 200 if data is None else 303
        if code != expected or headers.get("X-RoomReady-Release") != release:
            raise CheckFailed(f"Publisher saw HTTP {code} on {path}. Check IAP access, service setup and expected release.")
        if code == 303 and urljoin(ORIGIN + path, headers.get("Location", "")) != ORIGIN + "/":
            raise CheckFailed("The saved form did not redirect to the RoomReady page.")
        return body

    health = json.loads(checked("/health"))
    if health.get("status") != "ok" or health.get("release") != release:
        raise CheckFailed("RoomReady health did not match the expected release.")

    # Prove approved access first. A service returning 403 to everybody would be a setup failure.
    anonymous = build_opener(NoRedirect())
    code, headers, _ = app_request(anonymous, "", "/")
    sign_in = code in (302, 303) and urlsplit(headers.get("Location", "")).hostname == "accounts.google.com"
    from_iap = "X-Goog-IAP-Generated-Response" in headers
    if headers.get("X-RoomReady-Release") or not (sign_in or (from_iap and code in (401, 403))):
        raise CheckFailed(f"The signed-out HTTP {code} did not establish an IAP sign-in response.")
    anonymous_status = code

    code, headers, _ = app_request(build_opener(NoRedirect()), denied_token, "/health")
    if (code != 403 or headers.get("X-RoomReady-Release") or
            "X-Goog-IAP-Generated-Response" not in headers):
        raise CheckFailed(f"Expected IAP to reject the denied test account with 403. Received HTTP {code}.")

    def read_page():
        page = Page(checked("/"))
        if not page.csrf:
            raise CheckFailed("The RoomReady form did not supply a form token.")
        return page

    page = read_page()
    marker = uuid4().hex
    checked("/requests", {"csrf_token": page.csrf, "room": "Security demo",
                          "title": "Practice projector " + marker,
                          "description": "Fictional classroom request for the Week 3 Security test."})
    page = read_page()
    matches = [key for key, row in page.rows.items() if marker in row["text"] and row["status"] == "Open"]
    if len(matches) != 1:
        raise CheckFailed("The new fictional request could not be found as Open.")
    key = matches[0]
    for status in ("Working", "Resolved"):
        checked(f"/requests/{key}/status", {"csrf_token": page.csrf, "status": status})
        page = read_page()
        if key not in page.rows or page.rows[key]["status"] != status:
            raise CheckFailed(f"The saved request did not reopen as {status}.")

    return {"release": release, "publisher_health_http": 200, "signed_out_http": anonymous_status,
            "denied_account_http": 403, "publisher_request_id": key, "final_status": "Resolved"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-release", default=INITIAL_RELEASE, help="Full commit currently serving the main URL")
    args = parser.parse_args()
    if not re.fullmatch("[a-f0-9]{40}", args.expect_release):
        parser.error("The expected release must be a full Git commit.")
    try:
        login = subprocess.run(["gcloud", "auth", "print-access-token", "--quiet"], capture_output=True,
                               text=True, timeout=45, check=True).stdout.strip()
        approved = sign_account("roomready-publisher", login)
        denied = sign_account("roomready-denied-test", login)
        result = run_checks(args.expect_release, approved, denied)
    except CheckFailed as error:
        print(str(error), file=sys.stderr)
        return 1
    except subprocess.SubprocessError:
        print("Open Cloud Shell while signed in with your approved Security account, then retry.", file=sys.stderr)
        return 1
    except (OSError, URLError, HTTPException, ValueError):
        print("Could not reach Google or read a valid response. Check the Cloud Shell session and retry.", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
