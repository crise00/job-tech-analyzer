"""인증: 로그인 / 회원가입 / 로그아웃 + 세션 쿠키 관리."""

from __future__ import annotations

import html as _html
import os
from typing import Optional

from fastapi import APIRouter, Cookie, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeSerializer

from fastapi.responses import JSONResponse

from database import (
    SECURITY_QUESTIONS,
    add_bookmark,
    add_certification,
    create_user,
    delete_bookmark,
    delete_certification,
    delete_user,
    get_bookmarked_urls,
    get_bookmarks,
    get_certifications,
    get_security_question,
    get_skill_profile,
    get_user_by_id,
    reset_password,
    save_skill_profile,
    toggle_bookmark,
    username_exists,
    verify_security_answer,
    verify_user,
)
from search_layout import render_app_page, SEARCH_PAGE_CSS

router = APIRouter()

_SECRET = os.environ.get("SESSION_SECRET", "jobneuron-dev-secret-change-me")
_serializer = URLSafeSerializer(_SECRET, salt="session")
_COOKIE_NAME = "jn_session"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


# ── 세션 헬퍼 ──

def make_session_cookie(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def get_current_user(session: Optional[str] = None) -> Optional[dict]:
    if not session:
        return None
    try:
        data = _serializer.loads(session)
    except BadSignature:
        return None
    return get_user_by_id(data.get("uid", 0))


def get_current_user_from_cookie(request: Request) -> Optional[dict]:
    token = request.cookies.get(_COOKIE_NAME)
    return get_current_user(token)


# ── 공통 스타일 ──

AUTH_CARD_STYLE = """
max-width: 420px;
margin: 48px auto;
background: #fff;
border: 1px solid #e5e7eb;
border-radius: 16px;
padding: 32px 28px;
box-shadow: 0 4px 24px rgba(0,0,0,0.06);
"""

AUTH_INPUT_STYLE = """
width: 100%;
padding: 12px 14px;
border: 1px solid #d1d5db;
border-radius: 10px;
font-size: 1rem;
outline: none;
margin-bottom: 14px;
box-sizing: border-box;
"""

AUTH_BTN_STYLE = """
width: 100%;
padding: 13px;
border: 0;
border-radius: 10px;
background: linear-gradient(135deg, #2563eb, #1d4ed8);
color: #fff;
font-size: 1rem;
font-weight: 600;
cursor: pointer;
margin-top: 4px;
"""

AUTH_LINK_STYLE = "color: #2563eb; text-decoration: none; font-weight: 600;"


def _auth_page(title: str, form_html: str, error: str = "") -> str:
    error_block = ""
    if error:
        error_block = (
            f'<div style="background:#fef2f2; border:1px solid #fecaca; '
            f'border-radius:10px; padding:10px 14px; margin-bottom:16px; '
            f'color:#dc2626; font-size:0.95rem;">{_html.escape(error)}</div>'
        )
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{_html.escape(title)} · Jobneuron</title>
    <style>{SEARCH_PAGE_CSS}
    .auth-input:focus {{ border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.15); }}
    </style>
</head>
<body class="app-body">
    <header class="app-topbar">
        <div class="app-topbar-inner">
            <a class="app-logo-link" href="/" aria-label="홈">
                <img class="app-logo" src="/static/jobneuron-logo.png?v=2" alt="Jobneuron">
            </a>
        </div>
    </header>
    <main style="flex:1; padding: 20px 16px;">
        <div style="{AUTH_CARD_STYLE}">
            <h2 style="margin:0 0 20px; text-align:center; font-size:1.4rem;">{_html.escape(title)}</h2>
            {error_block}
            {form_html}
        </div>
    </main>
</body>
</html>"""


# ── 아이디 중복 확인 API ──

@router.get("/api/check-username")
def check_username(username: str = Query("")):
    username = username.strip()
    if len(username) < 3:
        return JSONResponse({"available": False, "message": "3자 이상 입력해주세요."})
    if username_exists(username):
        return JSONResponse({"available": False, "message": "이미 사용 중인 아이디입니다."})
    return JSONResponse({"available": True, "message": "사용 가능한 아이디입니다."})


# ── 회원가입 ──

_CHECK_BTN_STYLE = (
    "padding:10px 16px; border:1px solid #2563eb; border-radius:10px; "
    "background:#fff; color:#2563eb; font-weight:600; cursor:pointer; "
    "font-size:0.9rem; white-space:nowrap; flex-shrink:0;"
)

_CHECK_JS = """
<script>
async function checkUsername() {
    const input = document.getElementById('reg-username');
    const msg = document.getElementById('username-msg');
    const val = input.value.trim();
    if (val.length < 3) {
        msg.textContent = '3자 이상 입력해주세요.';
        msg.style.color = '#dc2626';
        return;
    }
    msg.textContent = '확인 중...';
    msg.style.color = '#64748b';
    try {
        const res = await fetch('/api/check-username?username=' + encodeURIComponent(val));
        const data = await res.json();
        msg.textContent = data.message;
        msg.style.color = data.available ? '#059669' : '#dc2626';
    } catch {
        msg.textContent = '확인에 실패했습니다.';
        msg.style.color = '#dc2626';
    }
}
</script>
"""


def _register_form(error: str = "", username: str = "") -> str:
    uname = _html.escape(username)
    form = f"""
    <form method="post" action="/register">
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">아이디</label>
        <div style="display:flex; gap:8px; margin-bottom:4px;">
            <input class="auth-input" id="reg-username" name="username" value="{uname}" placeholder="영문·숫자, 3자 이상"
                   style="{AUTH_INPUT_STYLE} margin-bottom:0; flex:1;" required minlength="3" maxlength="30">
            <button type="button" onclick="checkUsername()" style="{_CHECK_BTN_STYLE}">중복확인</button>
        </div>
        <p id="username-msg" style="margin:0 0 12px; font-size:0.85rem; min-height:1.2em; color:#64748b;"></p>
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">비밀번호</label>
        <input class="auth-input" type="password" name="password" placeholder="6자 이상"
               style="{AUTH_INPUT_STYLE}" required minlength="6">
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">비밀번호 확인</label>
        <input class="auth-input" type="password" name="password2" placeholder="비밀번호를 한 번 더"
               style="{AUTH_INPUT_STYLE}" required minlength="6">
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">보안 질문 (비밀번호 찾기용)</label>
        <select name="security_question" style="{AUTH_INPUT_STYLE} appearance:auto;" required>
            {"".join(f'<option value="{_html.escape(q)}">{_html.escape(q)}</option>' for q in SECURITY_QUESTIONS)}
        </select>
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">보안 질문 답변</label>
        <input class="auth-input" name="security_answer" placeholder="답변을 입력하세요"
               style="{AUTH_INPUT_STYLE}" required>
        <button type="submit" style="{AUTH_BTN_STYLE}">회원가입</button>
    </form>
    <p style="text-align:center; margin:18px 0 0; color:#64748b; font-size:0.93rem;">
        이미 계정이 있나요? <a href="/login" style="{AUTH_LINK_STYLE}">로그인</a>
    </p>
    {_CHECK_JS}
    """
    return _auth_page("회원가입", form, error)


@router.get("/register", response_class=HTMLResponse)
def register_page():
    return _register_form()


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    username: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    security_question: str = Form(...),
    security_answer: str = Form(...),
):
    username = username.strip()
    if len(username) < 3:
        return _register_form("아이디는 3자 이상이어야 합니다.", username)
    if len(password) < 6:
        return _register_form("비밀번호는 6자 이상이어야 합니다.", username)
    if password != password2:
        return _register_form("비밀번호가 일치하지 않습니다.", username)
    if not security_answer.strip():
        return _register_form("보안 질문 답변을 입력해주세요.", username)

    user_id = create_user(username, password, security_question, security_answer)
    if user_id is None:
        return _register_form("이미 사용 중인 아이디입니다.", username)

    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(_COOKIE_NAME, make_session_cookie(user_id), max_age=_COOKIE_MAX_AGE, httponly=True, samesite="lax")
    return resp


# ── 로그인 ──

def _login_form(error: str = "", username: str = "") -> str:
    uname = _html.escape(username)
    form = f"""
    <form method="post" action="/login">
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">아이디</label>
        <input class="auth-input" name="username" value="{uname}" placeholder="아이디"
               style="{AUTH_INPUT_STYLE}" required>
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">비밀번호</label>
        <input class="auth-input" type="password" name="password" placeholder="비밀번호"
               style="{AUTH_INPUT_STYLE}" required>
        <button type="submit" style="{AUTH_BTN_STYLE}">로그인</button>
    </form>
    <p style="text-align:center; margin:14px 0 0; color:#64748b; font-size:0.93rem;">
        <a href="/forgot-password" style="color:#6b7280; text-decoration:none; font-size:0.88rem;">비밀번호를 잊으셨나요?</a>
    </p>
    <p style="text-align:center; margin:10px 0 0; color:#64748b; font-size:0.93rem;">
        계정이 없나요? <a href="/register" style="{AUTH_LINK_STYLE}">회원가입</a>
    </p>
    """
    return _auth_page("로그인", form, error)


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return _login_form()


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    username: str = Form(...),
    password: str = Form(...),
):
    user = verify_user(username, password)
    if not user:
        return _login_form("아이디 또는 비밀번호가 올바르지 않습니다.", username.strip())

    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(_COOKIE_NAME, make_session_cookie(user["id"]), max_age=_COOKIE_MAX_AGE, httponly=True, samesite="lax")
    return resp


# ── 로그아웃 ──

@router.get("/logout")
def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(_COOKIE_NAME)
    return resp


# ── 비밀번호 찾기 ──

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page():
    form = f"""
    <form method="post" action="/forgot-password">
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">아이디</label>
        <input class="auth-input" name="username" placeholder="가입한 아이디 입력"
               style="{AUTH_INPUT_STYLE}" required>
        <button type="submit" style="{AUTH_BTN_STYLE}">다음</button>
    </form>
    <p style="text-align:center; margin:18px 0 0; color:#64748b; font-size:0.93rem;">
        <a href="/login" style="{AUTH_LINK_STYLE}">로그인으로 돌아가기</a>
    </p>
    """
    return _auth_page("비밀번호 찾기", form)


@router.post("/forgot-password", response_class=HTMLResponse)
def forgot_password_submit(username: str = Form(...)):
    username = username.strip()
    question = get_security_question(username)
    if not question:
        return _auth_page("비밀번호 찾기", f"""
        <form method="post" action="/forgot-password">
            <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">아이디</label>
            <input class="auth-input" name="username" value="{_html.escape(username)}" placeholder="가입한 아이디 입력"
                   style="{AUTH_INPUT_STYLE}" required>
            <button type="submit" style="{AUTH_BTN_STYLE}">다음</button>
        </form>
        <p style="text-align:center; margin:18px 0 0; color:#64748b; font-size:0.93rem;">
            <a href="/login" style="{AUTH_LINK_STYLE}">로그인으로 돌아가기</a>
        </p>
        """, error="해당 아이디를 찾을 수 없거나 보안 질문이 설정되지 않았습니다.")

    form = f"""
    <form method="post" action="/reset-password">
        <input type="hidden" name="username" value="{_html.escape(username)}">
        <p style="margin:0 0 16px; color:#374151; font-size:0.95rem;">
            <strong>보안 질문:</strong> {_html.escape(question)}
        </p>
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">답변</label>
        <input class="auth-input" name="answer" placeholder="보안 질문의 답변을 입력하세요"
               style="{AUTH_INPUT_STYLE}" required>
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">새 비밀번호</label>
        <input class="auth-input" type="password" name="new_password" placeholder="6자 이상"
               style="{AUTH_INPUT_STYLE}" required minlength="6">
        <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">새 비밀번호 확인</label>
        <input class="auth-input" type="password" name="new_password2" placeholder="비밀번호를 한 번 더"
               style="{AUTH_INPUT_STYLE}" required minlength="6">
        <button type="submit" style="{AUTH_BTN_STYLE}">비밀번호 재설정</button>
    </form>
    <p style="text-align:center; margin:18px 0 0; color:#64748b; font-size:0.93rem;">
        <a href="/login" style="{AUTH_LINK_STYLE}">로그인으로 돌아가기</a>
    </p>
    """
    return _auth_page("비밀번호 재설정", form)


@router.post("/reset-password", response_class=HTMLResponse)
def reset_password_submit(
    username: str = Form(...),
    answer: str = Form(...),
    new_password: str = Form(...),
    new_password2: str = Form(...),
):
    username = username.strip()
    question = get_security_question(username)

    def _answer_form(err: str):
        return _auth_page("비밀번호 재설정", f"""
        <form method="post" action="/reset-password">
            <input type="hidden" name="username" value="{_html.escape(username)}">
            <p style="margin:0 0 16px; color:#374151; font-size:0.95rem;">
                <strong>보안 질문:</strong> {_html.escape(question or '')}
            </p>
            <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">답변</label>
            <input class="auth-input" name="answer" placeholder="보안 질문의 답변을 입력하세요"
                   style="{AUTH_INPUT_STYLE}" required>
            <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">새 비밀번호</label>
            <input class="auth-input" type="password" name="new_password" placeholder="6자 이상"
                   style="{AUTH_INPUT_STYLE}" required minlength="6">
            <label style="display:block; margin-bottom:4px; font-weight:600; font-size:0.9rem; color:#374151;">새 비밀번호 확인</label>
            <input class="auth-input" type="password" name="new_password2" placeholder="비밀번호를 한 번 더"
                   style="{AUTH_INPUT_STYLE}" required minlength="6">
            <button type="submit" style="{AUTH_BTN_STYLE}">비밀번호 재설정</button>
        </form>
        <p style="text-align:center; margin:18px 0 0; color:#64748b; font-size:0.93rem;">
            <a href="/login" style="{AUTH_LINK_STYLE}">로그인으로 돌아가기</a>
        </p>
        """, error=err)

    if not verify_security_answer(username, answer):
        return _answer_form("보안 질문 답변이 일치하지 않습니다.")
    if len(new_password) < 6:
        return _answer_form("비밀번호는 6자 이상이어야 합니다.")
    if new_password != new_password2:
        return _answer_form("비밀번호가 일치하지 않습니다.")

    reset_password(username, new_password)

    success_html = f"""
    <div style="text-align:center;">
        <p style="font-size:1.1rem; color:#059669; font-weight:600; margin-bottom:20px;">
            비밀번호가 성공적으로 변경되었습니다.
        </p>
        <a href="/login" style="{AUTH_BTN_STYLE} display:inline-block; text-decoration:none; padding:13px 32px;">
            로그인하러 가기
        </a>
    </div>
    """
    return _auth_page("비밀번호 변경 완료", success_html)


# ── 회원탈퇴 ──

@router.post("/profile/delete-account")
def delete_account(request: Request, password: str = Form(...)):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    verified = verify_user(user["username"], password)
    if not verified:
        return RedirectResponse("/mypage?error=wrong_password", status_code=303)

    delete_user(user["id"])
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(_COOKIE_NAME)
    return resp


# ── 스킬 프로필 저장 ──

@router.post("/profile/skills", response_class=HTMLResponse)
def save_skills(request: Request, skills: str = Form(""), redirect_to: str = Form("")):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    save_skill_profile(user["id"], skills)

    target = redirect_to.strip() or request.headers.get("referer", "/mypage")
    return RedirectResponse(target, status_code=303)


# ── 자격증 추가/삭제 ──

@router.post("/profile/cert/add")
def add_cert(
    request: Request,
    cert_name: str = Form(...),
    cert_issuer: str = Form(""),
    cert_date: str = Form(""),
):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if cert_name.strip():
        add_certification(user["id"], cert_name, cert_issuer, cert_date)
    return RedirectResponse("/mypage", status_code=303)


@router.post("/profile/cert/delete")
def delete_cert(request: Request, cert_id: int = Form(...)):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    delete_certification(user["id"], cert_id)
    return RedirectResponse("/mypage", status_code=303)


# ── 북마크 ──

@router.post("/bookmark/add")
def bookmark_add(
    request: Request,
    job_title: str = Form(...),
    company: str = Form(""),
    url: str = Form(""),
    platform: str = Form(""),
    location: str = Form(""),
):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    add_bookmark(user["id"], job_title, company, url, platform, location)
    referer = request.headers.get("referer", "/")
    return RedirectResponse(referer, status_code=303)


@router.post("/api/bookmark/toggle")
def bookmark_toggle(request: Request, body: dict):
    user = get_current_user_from_cookie(request)
    if not user:
        return JSONResponse({"error": "login_required"}, status_code=401)
    result = toggle_bookmark(
        user["id"],
        body.get("job_title", ""),
        body.get("company", ""),
        body.get("url", ""),
        body.get("platform", ""),
        body.get("location", ""),
    )
    return JSONResponse(result)


@router.post("/bookmark/delete")
def bookmark_del(request: Request, bookmark_id: int = Form(...)):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    delete_bookmark(user["id"], bookmark_id)
    return RedirectResponse("/mypage", status_code=303)


# ── 마이페이지 ──

MYPAGE_CSS = """
.mp-section {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 14px;
    padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.mp-section h3 {
    margin: 0 0 16px; font-size: 1.15rem; color: #1e293b;
    padding-bottom: 10px; border-bottom: 1px solid #f1f5f9;
}
.mp-input {
    width: 100%; padding: 11px 14px; border: 1px solid #d1d5db;
    border-radius: 10px; font-size: 0.95rem; outline: none;
    box-sizing: border-box;
}
.mp-input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.12); }
.mp-btn {
    padding: 10px 20px; border: 0; border-radius: 10px;
    background: #2563eb; color: #fff; font-weight: 600;
    cursor: pointer; font-size: 0.93rem;
}
.mp-btn:hover { background: #1d4ed8; }
.mp-btn-outline {
    padding: 6px 14px; border: 1px solid #e5e7eb; border-radius: 8px;
    background: #fff; color: #dc2626; cursor: pointer; font-size: 0.85rem;
}
.mp-btn-outline:hover { background: #fef2f2; border-color: #fca5a5; }
.mp-chip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 10px 6px 14px; margin: 3px 4px 3px 0;
    background: #eff6ff; color: #1e40af; border-radius: 999px;
    font-size: 0.9rem; font-weight: 500;
}
.mp-chip-x {
    display: inline-flex; align-items: center; justify-content: center;
    width: 20px; height: 20px; border-radius: 50%;
    border: none; background: #bfdbfe; color: #1e40af;
    font-size: 0.8rem; font-weight: 700; cursor: pointer;
    line-height: 1; padding: 0;
}
.mp-chip-x:hover { background: #93c5fd; color: #1e3a8a; }
.mp-cert-row {
    display: flex; align-items: center; gap: 12px; padding: 12px 0;
    border-bottom: 1px solid #f1f5f9;
}
.mp-cert-row:last-child { border-bottom: 0; }
.mp-cert-name { font-weight: 600; color: #1e293b; }
.mp-cert-meta { font-size: 0.88rem; color: #64748b; }
.mp-empty { color: #94a3b8; font-size: 0.93rem; padding: 8px 0; }
"""


_MYPAGE_JS = """<script>
function getSkillsFromChips() {
    return [...document.querySelectorAll('#skill-chips .mp-chip')]
        .map(function(c){ return c.dataset.skill; }).filter(Boolean);
}
function syncHidden() {
    document.getElementById('skill-hidden').value = getSkillsFromChips().join(', ');
}
function removeSkill(btn) {
    btn.closest('.mp-chip').remove();
    syncHidden();
    if (!document.querySelector('#skill-chips .mp-chip')) {
        var p = document.createElement('p');
        p.className = 'mp-empty'; p.id = 'no-skills-msg';
        p.textContent = '등록된 스킬이 없습니다.';
        document.getElementById('skill-chips').appendChild(p);
    }
}
function _doAddChip(s) {
    var container = document.getElementById('skill-chips');
    var existing = {};
    getSkillsFromChips().forEach(function(v){ existing[v.toLowerCase()] = true; });
    if (existing[s.toLowerCase()]) return;
    var noMsg = document.getElementById('no-skills-msg');
    if (noMsg) noMsg.remove();
    var span = document.createElement('span');
    span.className = 'mp-chip'; span.dataset.skill = s;
    span.innerHTML = s + '<button type="button" class="mp-chip-x" onclick="removeSkill(this)" title="\\u00d7">&times;</button>';
    container.appendChild(span);
    syncHidden();
}
function addSkills() {
    var input = document.getElementById('skill-input');
    var val = input.value.trim();
    if (!val) return;
    input.value = '';
    fetch('/api/suggest-skills?skills=' + encodeURIComponent(val))
        .then(function(r){ return r.json(); })
        .then(function(data){
            var items = val.split(',').map(function(s){ return s.trim(); }).filter(Boolean);
            var sugMap = {};
            if (data.suggestions) {
                data.suggestions.forEach(function(s){ sugMap[s.input.toLowerCase()] = s; });
            }
            var pending = [];
            items.forEach(function(s){
                var sg = sugMap[s.toLowerCase()];
                if (sg) { pending.push(sg); }
                else { _doAddChip(s); }
            });
            if (pending.length > 0) { _showSkillSuggestions(pending); }
        })
        .catch(function(){
            val.split(',').map(function(s){ return s.trim(); }).filter(Boolean).forEach(_doAddChip);
        });
}
function _showSkillSuggestions(list) {
    var box = document.getElementById('skill-suggest-box');
    if (!box) {
        box = document.createElement('div'); box.id = 'skill-suggest-box';
        box.style.cssText = 'margin-top:10px; padding:12px 14px; background:#fffbeb; border:1px solid #fde68a; border-radius:10px;';
        document.getElementById('skill-form').after(box);
    }
    window._skillPending = list;
    var html = '<p style="margin:0 0 8px; font-weight:600; color:#92400e;">\\ud639\\uc2dc \\uc774\\ub7f0 \\uae30\\uc220\\uc744 \\ub9d0\\uc500\\ud558\\uc2e0 \\uac74\\uac00\\uc694?</p>';
    list.forEach(function(s,i){
        html += '<div style="display:flex;align-items:center;gap:8px;margin:6px 0;">'
            + '<span style="color:#78350f;"><strong>' + s.input + '</strong> \\u2192 <strong>' + s.display + '</strong></span>'
            + '<button type="button" onclick="_applySkillSug('+i+')" style="padding:4px 12px;border:1px solid #059669;border-radius:8px;background:#ecfdf5;color:#059669;font-weight:600;cursor:pointer;font-size:0.85rem;">\\uc801\\uc6a9</button>'
            + '<button type="button" onclick="_skipSkillSug('+i+')" style="padding:4px 12px;border:1px solid #d1d5db;border-radius:8px;background:#fff;color:#6b7280;cursor:pointer;font-size:0.85rem;">\\ubb34\\uc2dc</button>'
            + '</div>';
    });
    box.innerHTML = html;
    box.style.display = 'block';
}
function _applySkillSug(i) {
    var s = window._skillPending[i]; if (!s) return;
    _doAddChip(s.display);
    var box = document.getElementById('skill-suggest-box');
    var rows = box.querySelectorAll('div');
    if (rows[i]) rows[i].innerHTML = '<span style="color:#059669;">\\u2713 <strong>' + s.display + '</strong> \\uc801\\uc6a9\\ub428</span>';
}
function _skipSkillSug(i) {
    var s = window._skillPending[i]; if (!s) return;
    _doAddChip(s.input);
    var box = document.getElementById('skill-suggest-box');
    var rows = box.querySelectorAll('div');
    if (rows[i]) rows[i].innerHTML = '<span style="color:#9ca3af;">\\uac74\\ub108\\ub6f0 (' + s.input + ' \\uadf8\\ub300\\ub85c \\ucd94\\uac00)</span>';
}
document.getElementById('skill-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { e.preventDefault(); addSkills(); }
});

/* \\uc790\\uaca9\\uc99d \\uc774\\ub984 \\uc81c\\uc548 */
var certForm = document.querySelector('form[action="/profile/cert/add"]');
if (certForm) {
    certForm.addEventListener('submit', function(e) {
        if (certForm.dataset.confirmed === 'yes') { certForm.dataset.confirmed = ''; return; }
        var nameInput = certForm.querySelector('input[name="cert_name"]');
        var val = nameInput.value.trim();
        if (!val) return;
        e.preventDefault();
        fetch('/api/suggest-skills?skills=' + encodeURIComponent(val))
            .then(function(r){ return r.json(); })
            .then(function(data){
                if (!data.suggestions || data.suggestions.length === 0) {
                    certForm.dataset.confirmed = 'yes'; certForm.submit(); return;
                }
                var s = data.suggestions[0];
                if (confirm('"' + s.input + '" \\u2192 "' + s.display + '"(\\uc73c)\\ub85c \\ubcc0\\uacbd\\ud560\\uae4c\\uc694?')) {
                    nameInput.value = s.display;
                }
                certForm.dataset.confirmed = 'yes'; certForm.submit();
            })
            .catch(function(){ certForm.dataset.confirmed = 'yes'; certForm.submit(); });
    });
}
</script>"""


@router.get("/mypage", response_class=HTMLResponse)
def mypage(request: Request, error: str = Query("")):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    withdraw_error = ""
    if error == "wrong_password":
        withdraw_error = (
            '<div style="background:#fef2f2; border:1px solid #fecaca; border-radius:10px; '
            'padding:10px 14px; margin-bottom:12px; color:#dc2626; font-size:0.93rem;">'
            '비밀번호가 일치하지 않습니다.</div>'
        )

    skills = get_skill_profile(user["id"])
    certs = get_certifications(user["id"])
    bookmarks = get_bookmarks(user["id"])

    skill_list = [x.strip() for x in skills.split(",") if x.strip()]
    skill_chips = ""
    if skill_list:
        for s in skill_list:
            esc = _html.escape(s)
            skill_chips += (
                f'<span class="mp-chip" data-skill="{esc}">'
                f'{esc}<button type="button" class="mp-chip-x" onclick="removeSkill(this)" title="삭제">&times;</button>'
                f'</span>'
            )
    else:
        skill_chips = '<p class="mp-empty" id="no-skills-msg">등록된 스킬이 없습니다.</p>'

    cert_rows = ""
    if certs:
        for c in certs:
            name = _html.escape(c["name"])
            issuer = _html.escape(c["issuer"]) if c["issuer"] else ""
            date = _html.escape(c["acquired_date"]) if c["acquired_date"] else ""
            meta_parts = []
            if issuer:
                meta_parts.append(issuer)
            if date:
                meta_parts.append(date)
            meta = " · ".join(meta_parts)
            meta_html = f'<span class="mp-cert-meta">{meta}</span>' if meta else ""
            cert_rows += f"""
            <div class="mp-cert-row">
                <div style="flex:1;">
                    <span class="mp-cert-name">{name}</span>
                    {meta_html}
                </div>
                <form method="post" action="/profile/cert/delete" style="margin:0;">
                    <input type="hidden" name="cert_id" value="{c['id']}">
                    <button type="submit" class="mp-btn-outline"
                            onclick="return confirm('정말 삭제할까요?')">삭제</button>
                </form>
            </div>
            """
    else:
        cert_rows = '<p class="mp-empty">등록된 자격증이 없습니다.</p>'

    bookmark_html = ""
    if bookmarks:
        bk_rows = ""
        for bk in bookmarks:
            bk_title = _html.escape(bk["job_title"])
            bk_company = _html.escape(bk["company"]) if bk["company"] else ""
            bk_plat = _html.escape(bk["platform"]) if bk["platform"] else ""
            bk_loc = _html.escape(bk["location"]) if bk["location"] else ""
            bk_url = bk["url"] or ""
            meta_parts = [x for x in [bk_company, bk_plat, bk_loc] if x]
            meta = " · ".join(meta_parts)
            meta_html = f'<span class="mp-cert-meta">{meta}</span>' if meta else ""
            link_html = ""
            if bk_url:
                link_html = (
                    f'<a href="{_html.escape(bk_url, quote=True)}" target="_blank" '
                    f'rel="noopener noreferrer" style="color:#2563eb; font-size:0.88rem; '
                    f'text-decoration:none; font-weight:600;">공고 보기</a>'
                )
            bk_rows += f"""
            <div class="mp-cert-row">
                <div style="flex:1;">
                    <span class="mp-cert-name">{bk_title}</span>
                    {meta_html}
                    <div style="margin-top:4px;">{link_html}</div>
                </div>
                <form method="post" action="/bookmark/delete" style="margin:0;">
                    <input type="hidden" name="bookmark_id" value="{bk['id']}">
                    <button type="submit" class="mp-btn-outline"
                            onclick="return confirm('저장된 공고를 삭제할까요?')">삭제</button>
                </form>
            </div>
            """
        bookmark_html = bk_rows
    else:
        bookmark_html = '<p class="mp-empty">저장한 공고가 없습니다. 분석 결과의 공고 목록에서 ☆ 버튼으로 저장할 수 있습니다.</p>'

    escaped_skills = _html.escape(skills)
    uname = _html.escape(user["username"])

    body = f"""
    <div style="max-width:680px; margin:0 auto;">
        <h2 style="margin:0 0 6px; font-size:1.4rem;">마이페이지</h2>
        <p style="margin:0 0 24px; color:#64748b;">안녕하세요, <strong>{uname}</strong>님</p>

        <!-- 스킬 -->
        <div class="mp-section">
            <h3>보유 스킬</h3>
            <div id="skill-chips" style="margin-bottom:14px;">{skill_chips}</div>
            <form method="post" action="/profile/skills" id="skill-form">
                <input type="hidden" name="redirect_to" value="/mypage">
                <input type="hidden" name="skills" id="skill-hidden" value="{escaped_skills}">
                <div style="display:flex; gap:8px;">
                    <input class="mp-input" id="skill-input"
                           placeholder="쉼표로 구분 (예: Python, SQL, Docker)" style="flex:1;">
                    <button type="button" class="mp-btn" onclick="addSkills()"
                            style="background:#059669;">추가</button>
                    <button type="submit" class="mp-btn">저장</button>
                </div>
                <p style="margin:8px 0 0; font-size:0.83rem; color:#94a3b8;">
                    스킬을 입력 후 <strong>추가</strong> → 완료되면 <strong>저장</strong>. 칩의 &times; 버튼으로 개별 삭제 가능.
                </p>
            </form>
        </div>

        <!-- 자격증 -->
        <div class="mp-section">
            <h3>자격증</h3>
            <div style="margin-bottom:16px;">{cert_rows}</div>
            <form method="post" action="/profile/cert/add">
                <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
                    <input class="mp-input" name="cert_name" placeholder="자격증 이름 (예: AWS SAA)"
                           required style="flex:2; min-width:180px;">
                    <input class="mp-input" name="cert_issuer" placeholder="발급기관 (예: Amazon)"
                           style="flex:1; min-width:120px;">
                    <input class="mp-input" name="cert_date" type="month" placeholder="취득 연월"
                           style="flex:1; min-width:130px;">
                </div>
                <button type="submit" class="mp-btn">자격증 추가</button>
            </form>
        </div>

        <!-- 저장한 공고 -->
        <div class="mp-section">
            <h3>저장한 공고</h3>
            {bookmark_html}
        </div>

        <!-- 회원탈퇴 -->
        <div class="mp-section" style="border-color:#fecaca;">
            <h3 style="color:#dc2626; border-bottom-color:#fecaca;">회원탈퇴</h3>
            {withdraw_error}
            <p style="margin:0 0 12px; color:#64748b; font-size:0.93rem;">
                탈퇴 시 모든 데이터(스킬, 자격증)가 영구 삭제됩니다. 비밀번호를 입력해 본인 확인 후 탈퇴됩니다.
            </p>
            <form method="post" action="/profile/delete-account"
                  onsubmit="return confirm('정말 탈퇴하시겠습니까? 모든 데이터가 삭제됩니다.')">
                <div style="display:flex; gap:8px;">
                    <input class="mp-input" type="password" name="password"
                           placeholder="현재 비밀번호" required style="flex:1;">
                    <button type="submit" class="mp-btn"
                            style="background:#dc2626;">회원탈퇴</button>
                </div>
            </form>
        </div>
    </div>
    """ + _MYPAGE_JS
    return render_app_page("마이페이지", body, user=user, extra_css=MYPAGE_CSS)
