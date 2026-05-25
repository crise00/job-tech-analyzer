import html as _html
from urllib.parse import quote

from search_layout import render_site_footer

def _render_home_user_nav(user: dict | None) -> str:
    if user:
        uname = _html.escape(user["username"])
        return (
            f'<a class="home-nav-link" href="/mypage">마이페이지</a>'
            f'<span class="home-nav-name">{uname}</span>'
            f'<a class="home-nav-link" href="/logout">로그아웃</a>'
        )
    return (
        '<a class="home-nav-link" href="/login">로그인</a>'
        '<a class="home-nav-link home-nav-link--accent" href="/register">회원가입</a>'
    )


HOME_EXAMPLES = [
    ("백엔드 개발자", "백엔드 개발자"),
    ("프론트엔드 · 우대 기술", "프론트엔드 개발자 우대 기술 알려줘"),
    ("데이터 엔지니어", "데이터 엔지니어 필수 기술"),
    ("Senior Android Engineer", "Senior Android Engineer"),
]


def render_home_page(user: dict | None = None) -> str:
    example_chips = ""
    for label, query in HOME_EXAMPLES:
        url = f"/search?query={quote(query)}"
        example_chips += (
            f'<a class="home-chip" href="{_html.escape(url, quote=True)}">'
            f"{_html.escape(label)}</a>"
        )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Jobneuron</title>
    <style>
        * {{ box-sizing: border-box; }}
        body.home-body {{
            margin: 0;
            font-family: 'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            color: #0f172a;
            background: linear-gradient(165deg, #eff6ff 0%, #f8fafc 42%, #f1f5f9 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .home-wrap {{
            flex: 1;
            width: 100%;
            max-width: 920px;
            margin: 0 auto;
            padding: 28px 20px 24px;
        }}
        .home-hero {{ text-align: center; padding: 36px 20px 28px; }}
        .home-badge {{
            display: inline-block; padding: 6px 14px; border-radius: 999px;
            background: #dbeafe; color: #1d4ed8; font-size: 0.85rem; font-weight: 600; margin-bottom: 16px;
        }}
        .home-logo-link {{
            display: inline-block; text-decoration: none; line-height: 0;
        }}
        .home-logo-main {{
            display: block; width: min(420px, 88vw); max-height: 120px;
            object-fit: contain; margin: 0 auto 16px;
        }}
        .home-logo-link:hover .home-logo-main {{ opacity: 0.88; }}
        .home-hero p {{ margin: 0 auto; max-width: 520px; color: #475569; font-size: 1.05rem; }}
        .home-search-card {{
            background: #fff; border: 1px solid #e2e8f0; border-radius: 16px;
            padding: 22px; box-shadow: 0 10px 40px rgba(37, 99, 235, 0.08); margin-bottom: 28px;
        }}
        .home-search-form {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .home-search-form input {{
            flex: 1; min-width: 220px; padding: 14px 16px; border: 1px solid #cbd5e1;
            border-radius: 12px; font-size: 1rem; outline: none;
        }}
        .home-search-form input:focus {{
            border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
        }}
        .home-search-form button {{
            padding: 14px 22px; border: 0; border-radius: 12px;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: #fff; font-size: 1rem; font-weight: 600; cursor: pointer; white-space: nowrap;
        }}
        .home-examples-label {{
            margin: 18px 0 10px; font-size: 0.9rem; color: #64748b; font-weight: 600;
        }}
        .home-chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .home-chip {{
            display: inline-block; padding: 8px 14px; background: #f1f5f9;
            border: 1px solid #e2e8f0; border-radius: 999px; color: #334155;
            text-decoration: none; font-size: 0.9rem;
        }}
        .home-chip:hover {{ background: #eff6ff; border-color: #93c5fd; color: #1d4ed8; }}
        .home-features {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;
        }}
        .home-feature {{
            background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px;
        }}
        .home-feature-icon {{ font-size: 1.5rem; margin-bottom: 8px; }}
        .home-feature h3 {{ margin: 0 0 8px; font-size: 1.05rem; }}
        .home-feature p {{ margin: 0; color: #64748b; font-size: 0.92rem; line-height: 1.55; }}
        .site-footer {{
            margin-top: auto;
            flex-shrink: 0;
            padding: 14px 20px 18px;
            text-align: center;
            background: rgba(255, 255, 255, 0.92);
            border-top: 1px solid #e2e8f0;
        }}
        .site-footer-logo-link {{ display: inline-block; line-height: 0; text-decoration: none; }}
        .site-footer-logo {{
            display: block; width: 120px; height: auto; margin: 0 auto; opacity: 0.9; object-fit: contain;
        }}
        .site-footer-logo-link:hover .site-footer-logo {{ opacity: 0.75; }}
        .site-footer-text {{ margin: 8px 0 0; font-size: 0.8rem; color: #94a3b8; }}
        .home-nav {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 10px;
            padding: 14px 0 0;
        }}
        .home-nav-name {{
            font-weight: 600; color: #334155; font-size: 0.93rem;
        }}
        .home-nav-link {{
            text-decoration: none; color: #2563eb; font-size: 0.9rem;
            font-weight: 600; padding: 6px 14px; border-radius: 8px;
            transition: background 0.15s;
        }}
        .home-nav-link:hover {{ background: #eff6ff; }}
        .home-nav-link--accent {{
            background: #2563eb; color: #fff;
        }}
        .home-nav-link--accent:hover {{ background: #1d4ed8; }}
    </style>
</head>
<body class="home-body">
    <div class="home-wrap">
        <nav class="home-nav">
            {_render_home_user_nav(user)}
        </nav>
        <header class="home-hero">
            <a class="home-logo-link" href="/" aria-label="Jobneuron 홈으로">
                <img class="home-logo-main" src="/static/jobneuron-logo.png?v=2" alt="Jobneuron">
            </a>
            <p>직무명을 검색하면 요구 기술, 공고 출처, 스킬 갭까지 한 번에 확인할 수 있습니다.</p>
        </header>
        <section class="home-search-card">
            <form class="home-search-form" action="/search" method="get">
                <input type="text" name="query" placeholder="예: 백엔드 개발자, Senior Android Engineer" autocomplete="off">
                <button type="submit">분석 시작</button>
            </form>
            <p class="home-examples-label">바로 검색해 보기</p>
            <div class="home-chips">{example_chips}</div>
        </section>
        <section class="home-features">
            <div class="home-feature">
                <div class="home-feature-icon">📊</div>
                <h3>기술 스택 분석</h3>
                <p>공고 본문에서 요구·우대 기술을 추출해 빈도와 비율로 보여줍니다.</p>
            </div>
            <div class="home-feature">
                <div class="home-feature-icon">🔗</div>
                <h3>데이터 출처</h3>
                <p>Greenhouse·Lever 등 채용 플랫폼과 회사별 공고 수를 확인할 수 있습니다.</p>
            </div>
            <div class="home-feature">
                <div class="home-feature-icon">🎯</div>
                <h3>스킬 갭 · 학습 링크</h3>
                <p>내 스킬과 비교하고, 부족한 기술의 학습·자격 응시 페이지로 연결합니다.</p>
            </div>
        </section>
    </div>
    {render_site_footer()}
</body>
</html>"""
