import html

SEARCH_PAGE_CSS = """
* { box-sizing: border-box; }
body.app-body {
    margin: 0;
    font-family: 'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
    color: #0f172a;
    background: #f8fafc;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}
.app-topbar {
    background: #fff;
    border-bottom: 1px solid #e5e7eb;
    padding: 12px 20px;
}
.app-topbar-inner {
    max-width: 1080px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.app-user-nav {
    display: flex;
    align-items: center;
    gap: 12px;
}
.app-user-name {
    font-weight: 600;
    color: #334155;
    font-size: 0.93rem;
}
.app-user-link {
    text-decoration: none;
    color: #2563eb;
    font-size: 0.9rem;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 8px;
    transition: background 0.15s;
}
.app-user-link:hover { background: #eff6ff; }
.app-user-link--register {
    background: #2563eb;
    color: #fff;
}
.app-user-link--register:hover { background: #1d4ed8; }
.app-logo-link { display: inline-block; line-height: 0; text-decoration: none; }
.app-logo {
    height: 36px;
    width: auto;
    max-width: 180px;
    object-fit: contain;
}
.app-logo-link:hover .app-logo { opacity: 0.85; }
.app-search-band {
    background: #fff;
    border-bottom: 1px solid #e5e7eb;
    padding: 20px 20px 24px;
}
.app-search-band-inner {
    max-width: 720px;
    margin: 0 auto;
}
.app-search-form {
    display: flex;
    align-items: center;
    border: 2px solid #3b82f6;
    border-radius: 12px;
    background: #fff;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
}
.app-search-form:focus-within {
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}
.app-search-input {
    flex: 1;
    border: 0;
    padding: 14px 16px;
    font-size: 1rem;
    outline: none;
    min-width: 0;
}
.app-search-btn {
    border: 0;
    border-left: 1px solid #e5e7eb;
    background: #fff;
    color: #2563eb;
    padding: 0 18px;
    height: 48px;
    cursor: pointer;
    font-size: 1.1rem;
    font-weight: 600;
}
.app-search-btn:hover { background: #eff6ff; }
.app-search-hint {
    margin: 10px 0 0;
    font-size: 0.85rem;
    color: #64748b;
    text-align: center;
}
.app-main {
    flex: 1;
    width: 100%;
    max-width: 1080px;
    margin: 0 auto;
    padding: 20px 16px 24px;
}
.site-footer {
    margin-top: auto;
    flex-shrink: 0;
    padding: 14px 20px 18px;
    text-align: center;
    background: #fff;
    border-top: 1px solid #e5e7eb;
}
.site-footer-logo-link {
    display: inline-block;
    line-height: 0;
    text-decoration: none;
}
.site-footer-logo {
    display: block;
    width: 120px;
    height: auto;
    margin: 0 auto;
    opacity: 0.9;
    object-fit: contain;
}
.site-footer-logo-link:hover .site-footer-logo { opacity: 0.75; }
.site-footer-text {
    margin: 8px 0 0;
    font-size: 0.8rem;
    color: #94a3b8;
}
.app-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 18px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    margin-bottom: 16px;
}
.app-page-title {
    margin: 0 0 12px;
    font-size: 1.35rem;
    letter-spacing: -0.02em;
}
.app-meta { color: #475569; margin: 8px 0; }
.app-summary {
    background: #eff6ff;
    padding: 12px 14px;
    border-radius: 10px;
    border: 1px solid #dbeafe;
    margin: 12px 0 0;
}
.app-error { color: #dc2626; font-weight: 600; }
.app-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    background: #dbeafe;
    color: #1d4ed8;
    font-size: 0.85rem;
    font-weight: 600;
}
"""

QUESTION_TYPE_LABELS = {
    "all": "전체",
    "required": "필수 기술",
    "preferred": "우대 기술",
}


def format_question_type_label(question_type: str) -> str:
    return QUESTION_TYPE_LABELS.get((question_type or "").strip(), question_type or "—")


def render_site_footer() -> str:
    return """
    <footer class="site-footer">
        <a class="site-footer-logo-link" href="/" aria-label="Jobneuron 홈으로">
            <img class="site-footer-logo" src="/static/jobneuron-logo.png?v=2" alt="Jobneuron">
        </a>
        <p class="site-footer-text">Lever · Greenhouse 공고 데이터 기반</p>
    </footer>
    """


def render_user_nav(user: dict | None = None) -> str:
    if user:
        uname = html.escape(user["username"])
        return (
            f'<div class="app-user-nav">'
            f'<a class="app-user-link" href="/mypage">마이페이지</a>'
            f'<span class="app-user-name">{uname}</span>'
            f'<a class="app-user-link" href="/logout">로그아웃</a>'
            f'</div>'
        )
    return (
        '<div class="app-user-nav">'
        '<a class="app-user-link" href="/login">로그인</a>'
        '<a class="app-user-link app-user-link--register" href="/register">회원가입</a>'
        '</div>'
    )


def render_app_header(query: str = "", user: dict | None = None) -> str:
    escaped_query = html.escape(str(query or ""))
    return f"""
    <header class="app-topbar">
        <div class="app-topbar-inner">
            <a class="app-logo-link" href="/" aria-label="Jobneuron 홈으로">
                <img class="app-logo" src="/static/jobneuron-logo.png?v=2" alt="Jobneuron">
            </a>
            {render_user_nav(user)}
        </div>
    </header>
    <div class="app-search-band">
        <div class="app-search-band-inner">
            <form class="app-search-form" action="/search" method="get">
                <input
                    class="app-search-input"
                    type="text"
                    name="query"
                    value="{escaped_query}"
                    placeholder="직무, 기술 스택 검색 (예: 백엔드 개발자)"
                    autocomplete="off"
                >
                <button class="app-search-btn" type="submit" aria-label="검색">검색</button>
            </form>
            <p class="app-search-hint">채용공고 기반으로 요구·우대 기술과 스킬 갭을 분석합니다</p>
        </div>
    </div>
    """


def render_app_page(title: str, content: str, query: str = "", user: dict | None = None, extra_css: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)} · Jobneuron</title>
    <style>{SEARCH_PAGE_CSS}{extra_css}</style>
</head>
<body class="app-body">
    {render_app_header(query, user)}
    <main class="app-main">
        {content}
    </main>
    {render_site_footer()}
</body>
</html>"""
