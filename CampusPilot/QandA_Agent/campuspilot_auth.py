"""
Session login and encrypted storage of TUM web credentials (LRZ IdP / Shibboleth username+password).

Used so the backend can attach credentials to future campus-portal automation; passwords are
encrypted at rest. For production, set CAMPUSPILOT_SECRET or CAMPUSPILOT_FERNET_KEY — see ENV.example.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Annotated, Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Cookie, HTTPException, Response, status
from pydantic import BaseModel, Field

from config import settings

_DB_PATH = Path(__file__).resolve().parent / "data" / "campuspilot_auth.db"
SESSION_COOKIE_NAME = "campuspilot_session"
_SESSION_TTL_S = 7 * 24 * 60 * 60  # 7 days


def _fernet() -> Fernet:
    raw_key = os.environ.get("CAMPUSPILOT_FERNET_KEY", "").strip()
    if raw_key:
        return Fernet(raw_key.encode("ascii"))
    secret = (os.environ.get("CAMPUSPILOT_SECRET") or settings.auth_dev_fallback_secret).encode("utf-8")
    digest = hashlib.sha256(secret).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_schema_sync() -> None:
    conn = _connect()
    try:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tum_username TEXT NOT NULL UNIQUE,
                password_cipher TEXT NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            """
        )
        conn.commit()
    finally:
        conn.close()


_init_schema_sync()


def _encrypt_password(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def _decrypt_password(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise RuntimeError("password decrypt failed (wrong CAMPUSPILOT_FERNET_KEY/SECRET?)") from e


def _login_sync(username: str, password: str) -> str:
    now = time.time()
    u = username.strip().lower()
    if not u or not password:
        raise ValueError("empty credentials")
    cipher = _encrypt_password(password)
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO users (tum_username, password_cipher, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(tum_username) DO UPDATE SET
                password_cipher = excluded.password_cipher,
                updated_at = excluded.updated_at
            """,
            (u, cipher, now),
        )
        row = conn.execute("SELECT id FROM users WHERE tum_username = ?", (u,)).fetchone()
        if not row:
            raise RuntimeError("user row missing after upsert")
        user_id = int(row["id"])
        sess = secrets.token_urlsafe(32)
        exp = now + _SESSION_TTL_S
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (sess, user_id, exp),
        )
        conn.commit()
        return sess
    finally:
        conn.close()


def _logout_sync(session_token: str | None) -> None:
    if not session_token:
        return
    conn = _connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (session_token,))
        conn.commit()
    finally:
        conn.close()


def _resolve_session_sync(session_token: str | None) -> dict[str, Any] | None:
    if not session_token:
        return None
    now = time.time()
    conn = _connect()
    try:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        row = conn.execute(
            """
            SELECT s.token AS token, s.expires_at AS expires_at, u.id AS user_id, u.tum_username AS tum_username,
                   u.password_cipher AS password_cipher
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (session_token,),
        ).fetchone()
        conn.commit()
        if not row:
            return None
        if float(row["expires_at"]) < now:
            conn.execute("DELETE FROM sessions WHERE token = ?", (session_token,))
            conn.commit()
            return None
        return {
            "user_id": int(row["user_id"]),
            "tum_username": str(row["tum_username"]),
            "password_cipher": str(row["password_cipher"]),
        }
    finally:
        conn.close()


class LoginBody(BaseModel):
    tum_username: str = Field(..., min_length=1, max_length=256)
    tum_password: str = Field(..., min_length=1, max_length=4096)


class MeResponse(BaseModel):
    logged_in: bool
    tum_username: str | None = None


class AuthUser(BaseModel):
    user_id: int
    tum_username: str
    password_plain: str


async def login_user(body: LoginBody, response: Response) -> MeResponse:
    try:
        token = await asyncio.to_thread(_login_sync, body.tum_username, body.tum_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=_SESSION_TTL_S,
        httponly=True,
        samesite="lax",
        secure=False,  # localhost dev; set True behind HTTPS in production
        path="/",
    )
    return MeResponse(logged_in=True, tum_username=body.tum_username.strip().lower())


async def logout_user(response: Response, session: str | None) -> dict[str, bool]:
    await asyncio.to_thread(_logout_sync, session)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


async def me(session: str | None) -> MeResponse:
    row = await asyncio.to_thread(_resolve_session_sync, session)
    if not row:
        return MeResponse(logged_in=False, tum_username=None)
    return MeResponse(logged_in=True, tum_username=str(row["tum_username"]))


async def require_auth_user(session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None) -> AuthUser:
    row = await asyncio.to_thread(_resolve_session_sync, session)
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
    try:
        plain = await asyncio.to_thread(_decrypt_password, str(row["password_cipher"]))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
    return AuthUser(
        user_id=int(row["user_id"]),
        tum_username=str(row["tum_username"]),
        password_plain=plain,
    )
