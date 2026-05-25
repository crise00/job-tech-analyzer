"""SQLite DB: 사용자 계정 + 스킬 프로필 저장."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

import bcrypt

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jobneuron.db")


def _ensure_dir():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)


@contextmanager
def get_db():
    _ensure_dir()
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password    TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_profiles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                name        TEXT NOT NULL DEFAULT '기본 프로필',
                skills      TEXT NOT NULL DEFAULT '',
                updated_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS certifications (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                name        TEXT NOT NULL,
                issuer      TEXT NOT NULL DEFAULT '',
                acquired_date TEXT NOT NULL DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                job_title   TEXT NOT NULL,
                company     TEXT NOT NULL DEFAULT '',
                url         TEXT NOT NULL DEFAULT '',
                platform    TEXT NOT NULL DEFAULT '',
                location    TEXT NOT NULL DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        for col, default in [("security_question", "''"), ("security_answer", "''")]:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT NOT NULL DEFAULT {default}")
            except sqlite3.OperationalError:
                pass


# ── 사용자 ──

SECURITY_QUESTIONS = [
    "내가 태어난 도시는?",
    "첫 번째 반려동물 이름은?",
    "어릴 때 가장 친한 친구 이름은?",
    "졸업한 초등학교 이름은?",
    "가장 좋아하는 음식은?",
]


def create_user(
    username: str,
    password: str,
    security_question: str = "",
    security_answer: str = "",
) -> Optional[int]:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password, security_question, security_answer) VALUES (?, ?, ?, ?)",
                (username.strip(), hashed, security_question.strip(), security_answer.strip()),
            )
            user_id = cur.lastrowid
            conn.execute(
                "INSERT INTO skill_profiles (user_id, name, skills) VALUES (?, '기본 프로필', '')",
                (user_id,),
            )
            return user_id
    except sqlite3.IntegrityError:
        return None


def verify_user(username: str, password: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if not row:
        return None
    if bcrypt.checkpw(password.encode("utf-8"), row["password"].encode("utf-8")):
        return {"id": row["id"], "username": row["username"]}
    return None


def username_exists(username: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
    return row is not None


def get_security_question(username: str) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT security_question FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if not row or not row["security_question"]:
        return None
    return row["security_question"]


def verify_security_answer(username: str, answer: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT security_answer FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if not row or not row["security_answer"]:
        return False
    return row["security_answer"].strip().lower() == answer.strip().lower()


def reset_password(username: str, new_password: str) -> bool:
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (hashed, username.strip()),
        )
        return cur.rowcount > 0


def delete_user(user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM bookmarks WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM certifications WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM skill_profiles WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


# ── 스킬 프로필 ──

def get_skill_profile(user_id: int) -> str:
    with get_db() as conn:
        row = conn.execute(
            "SELECT skills FROM skill_profiles WHERE user_id = ? ORDER BY id LIMIT 1",
            (user_id,),
        ).fetchone()
    return row["skills"] if row else ""


def save_skill_profile(user_id: int, skills: str):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM skill_profiles WHERE user_id = ? ORDER BY id LIMIT 1",
            (user_id,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE skill_profiles SET skills = ?, updated_at = datetime('now') WHERE id = ?",
                (skills.strip(), existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO skill_profiles (user_id, skills) VALUES (?, ?)",
                (user_id, skills.strip()),
            )


# ── 자격증 ──

def get_certifications(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, issuer, acquired_date FROM certifications WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_certification(user_id: int, name: str, issuer: str = "", acquired_date: str = "") -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO certifications (user_id, name, issuer, acquired_date) VALUES (?, ?, ?, ?)",
            (user_id, name.strip(), issuer.strip(), acquired_date.strip()),
        )
        return cur.lastrowid


def delete_certification(user_id: int, cert_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM certifications WHERE id = ? AND user_id = ?",
            (cert_id, user_id),
        )
        return cur.rowcount > 0


# ── 북마크 ──

def get_bookmarks(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, job_title, company, url, platform, location, created_at "
            "FROM bookmarks WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_bookmark(user_id: int, job_title: str, company: str = "",
                 url: str = "", platform: str = "", location: str = "") -> int:
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM bookmarks WHERE user_id = ? AND url = ? AND url != ''",
            (user_id, url.strip()),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO bookmarks (user_id, job_title, company, url, platform, location) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, job_title.strip(), company.strip(), url.strip(),
             platform.strip(), location.strip()),
        )
        return cur.lastrowid


def delete_bookmark(user_id: int, bookmark_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM bookmarks WHERE id = ? AND user_id = ?",
            (bookmark_id, user_id),
        )
        return cur.rowcount > 0


def get_bookmarked_urls(user_id: int) -> set[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT url FROM bookmarks WHERE user_id = ? AND url != ''",
            (user_id,),
        ).fetchall()
    return {r["url"] for r in rows}


def toggle_bookmark(user_id: int, job_title: str, company: str = "",
                    url: str = "", platform: str = "", location: str = "") -> dict:
    with get_db() as conn:
        if url.strip():
            existing = conn.execute(
                "SELECT id FROM bookmarks WHERE user_id = ? AND url = ?",
                (user_id, url.strip()),
            ).fetchone()
            if existing:
                conn.execute("DELETE FROM bookmarks WHERE id = ?", (existing["id"],))
                return {"bookmarked": False}
        cur = conn.execute(
            "INSERT INTO bookmarks (user_id, job_title, company, url, platform, location) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, job_title.strip(), company.strip(), url.strip(),
             platform.strip(), location.strip()),
        )
        return {"bookmarked": True, "id": cur.lastrowid}


init_db()
