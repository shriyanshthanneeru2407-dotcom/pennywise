"""
app/auth/oauth.py — Google OAuth 2.0 flow helper for PennyWise.

Implements standard OpenID Connect / OAuth 2.0 Authorization Code Flow:
  1. Generate cryptographically secure state token to prevent CSRF attacks.
  2. Redirect user to Google OAuth 2.0 endpoint.
  3. Exchange authorization code for tokens via Google token endpoint.
  4. Fetch and verify Google profile info (email, name, picture, sub/google_id).
"""

import os
import secrets
import urllib.parse
import json
import urllib.request
import urllib.error
from flask import current_app, url_for, session

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"


def is_google_oauth_configured() -> bool:
    """Return True if Google OAuth Client ID and Secret are configured."""
    client_id = current_app.config.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET", "").strip()
    return bool(client_id and client_secret and "your-google" not in client_id)


def get_google_auth_url(redirect_uri: str) -> str:
    """
    Generate Google OAuth 2.0 authorization URL with secure state token.
    State token is stored in Flask session to verify on callback.
    """
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    client_id = current_app.config.get("GOOGLE_CLIENT_ID", "").strip()

    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def exchange_code_for_user_info(code: str, redirect_uri: str) -> dict:
    """
    Exchange authorization code for access token, then fetch user profile from Google.
    Returns dictionary with email, name, picture, and google_id (sub).
    Raises ValueError on failure.
    """
    client_id = current_app.config.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials are not configured.")

    # 1. Exchange code for access token
    token_data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    req = urllib.request.Request(
        GOOGLE_TOKEN_ENDPOINT,
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_json = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise ValueError(f"Failed to exchange OAuth code: {error_body}")
    except Exception as e:
        raise ValueError(f"Token exchange network error: {str(e)}")

    access_token = token_json.get("access_token")
    if not access_token:
        raise ValueError("No access token returned by Google.")

    # 2. Fetch user profile with access token
    userinfo_req = urllib.request.Request(
        GOOGLE_USERINFO_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    try:
        with urllib.request.urlopen(userinfo_req, timeout=10) as resp:
            user_info = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to fetch user profile from Google: {str(e)}")

    return {
        "google_id": user_info.get("sub"),
        "email": (user_info.get("email") or "").lower().strip(),
        "name": user_info.get("name") or user_info.get("given_name") or "Google User",
        "avatar_url": user_info.get("picture"),
        "email_verified": user_info.get("email_verified", False),
    }
