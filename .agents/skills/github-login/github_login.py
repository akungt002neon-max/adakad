#!/usr/bin/env python3
"""Log into github.com in the already-running Chrome via CDP.

Credentials are read from the environment:
  GITHUB_USERNAME  - username or email
  GITHUB_PASSWORD  - password
  _2FA_GITHUB      - optional TOTP secret (base32) for two-factor auth

Usage:
  python3 github_login.py

The session cookies stay in the browser profile afterwards, so any later
browsing (manual or scripted) is already authenticated.
"""

import os
import sys
from urllib.parse import urlparse

import pyotp
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

CDP_URL = os.environ.get("CDP_URL", "http://localhost:29229")
LOGIN_URL = "https://github.com/login"
TWO_FACTOR_URL_FRAGMENT = "two-factor"
# A rejected login re-renders the form under /session, not /login.
FAILED_LOGIN_PATHS = ("/login", "/session")


def current_user(page) -> str:
    """Return the logged-in login name, or "" when the session is anonymous.

    GitHub always renders <meta name="user-login">, but its content is empty
    for anonymous visitors.
    """
    page.goto("https://github.com/", wait_until="domcontentloaded")
    meta = page.locator("meta[name='user-login']")
    if meta.count() == 0:
        return ""
    return (meta.first.get_attribute("content") or "").strip()


def submit_credentials(page, username: str, password: str) -> None:
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.fill("#login_field", username)
    page.fill("#password", password)
    page.click("input[type='submit'][name='commit']")
    page.wait_for_load_state("domcontentloaded")


def submit_totp(page, totp_secret: str) -> None:
    code = pyotp.TOTP(totp_secret).now()
    field = page.locator("#app_totp, input[name='app_otp'], input[name='otp']").first
    field.wait_for(state="visible", timeout=15000)
    field.fill(code)
    # GitHub auto-submits once six digits are entered; press Enter as a fallback.
    if page.locator("button[type='submit']:visible").count() > 0:
        page.locator("button[type='submit']:visible").first.click()
    else:
        field.press("Enter")
    page.wait_for_load_state("domcontentloaded")


def login(page) -> None:
    username = os.environ.get("GITHUB_USERNAME")
    password = os.environ.get("GITHUB_PASSWORD")
    totp_secret = os.environ.get("_2FA_GITHUB")

    if not username or not password:
        sys.exit("GITHUB_USERNAME and GITHUB_PASSWORD must be set")

    submit_credentials(page, username, password)

    if TWO_FACTOR_URL_FRAGMENT in page.url:
        if not totp_secret:
            sys.exit(
                "Two-factor prompt shown but _2FA_GITHUB (TOTP secret) is not set"
            )
        submit_totp(page, totp_secret)

    path = urlparse(page.url).path.rstrip("/")
    if path.endswith(FAILED_LOGIN_PATHS) or TWO_FACTOR_URL_FRAGMENT in page.url:
        error = page.locator(".flash-error, [role='alert']").first
        detail = error.inner_text().strip() if error.count() else "unknown error"
        sys.exit(f"Login failed, still on {page.url}: {detail}")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(30000)

        try:
            user = current_user(page)
            if user:
                print(f"already logged in as {user}")
                return
            login(page)
        except PlaywrightTimeoutError as exc:
            sys.exit(f"timed out during login: {exc}")

        user = current_user(page)
        if not user:
            sys.exit("login appeared to succeed but session is not authenticated")
        print(f"logged in as {user}")


if __name__ == "__main__":
    main()
