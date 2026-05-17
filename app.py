from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from urllib.parse import quote
from typing import Optional
import re
import html

from analyzer import (
    search_jobs,
    load_data,
    get_all_jobs,
    analyze_job,
    normalize_text,
    make_summary_message,
    compute_skill_gap,
)

app = FastAPI()

BASE_STYLE = """
font-family: 'Segoe UI', Arial, sans-serif;
max-width: 1080px;
margin: 32px auto;
line-height: 1.6;
color: #111827;
padding: 0 16px 24px 16px;
background: #f8fafc;
"""
CARD_STYLE = "background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 18px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04); margin: 16px 0;"
TABLE_STYLE = "border-collapse: collapse; width: 100%; margin-bottom: 16px; background: #fff;"
TH_STYLE = "text-align: left; padding: 10px; border-bottom: 1px solid #e5e7eb; background: #f9fafb;"
TD_STYLE = "padding: 10px; border-bottom: 1px solid #f1f5f9; vertical-align: top;"
INPUT_STYLE = "flex: 1; min-width: 260px; padding: 11px 12px; border: 1px solid #d1d5db; border-radius: 10px; font-size: 14px;"
BUTTON_STYLE = "padding: 11px 16px; border: 0; border-radius: 10px; background: #2563eb; color: #fff; font-weight: 600; cursor: pointer;"
CANDIDATE_LIST_STYLE = "list-style: none; padding-left: 0; margin: 12px 0 8px 0;"
CANDIDATE_ITEM_STYLE = "margin: 0 0 10px 0;"
CANDIDATE_LINK_STYLE = "display: block; text-decoration: none; color: #1f2937; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; font-weight: 600;"


def format_source_platform_label(platform: str) -> str:
    p = (platform or "").strip().lower()
    if p == "greenhouse":
        return "Greenhouse"
    if p == "lever":
        return "Lever"
    return (platform or "").strip() or "—"


def render_sources_section(result: dict) -> str:
    breakdown = result.get("sources_breakdown") or []
    postings = result.get("postings") or []
    truncated = result.get("postings_truncated")
    preview_limit = result.get("postings_preview_limit", 40)
    total = result.get("count", 0)

    if not breakdown and not postings:
        if total == 0:
            return ""
        return f"""
        <div style="{CARD_STYLE} background: #fafafa;">
            <h3 style="margin-top: 0;">데이터 출처</h3>
            <p style="margin: 0; color: #666;">이 데이터에는 회사·채용 플랫폼 정보가 없습니다. 수집 CSV에 company, source_platform 컬럼이 있으면 집계됩니다.</p>
        </div>
        """

    breakdown_rows = ""
    for item in breakdown:
        company = html.escape(str(item.get("company") or "—"))
        plat = html.escape(format_source_platform_label(item.get("source_platform", "")))
        cnt = item.get("count", 0)
        breakdown_rows += f"""
        <tr>
            <td style="{TD_STYLE}">{company}</td>
            <td style="{TD_STYLE}">{plat}</td>
            <td style="{TD_STYLE}">{cnt}</td>
        </tr>
        """

    posting_rows = ""
    for p in postings:
        title = html.escape(str(p.get("job_title") or ""))
        company = html.escape(str(p.get("company") or "—"))
        plat = html.escape(format_source_platform_label(p.get("source_platform", "")))
        loc = html.escape(str(p.get("location_name") or "—"))
        url = str(p.get("absolute_url") or "").strip()
        link_cell = f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer" style="color: #2563eb; font-weight: 600;">공고 보기</a>' if url else "—"
        posting_rows += f"""
        <tr>
            <td style="{TD_STYLE}">{title}</td>
            <td style="{TD_STYLE}">{company}</td>
            <td style="{TD_STYLE}">{plat}</td>
            <td style="{TD_STYLE}">{loc}</td>
            <td style="{TD_STYLE}">{link_cell}</td>
        </tr>
        """

    note = ""
    if truncated:
        note = f"""
        <p style="margin: 12px 0 0 0; color: #666; font-size: 0.95em;">
            공고 목록은 최대 {preview_limit}건만 표시합니다. (전체 {total}건)
        </p>
        """

    return f"""
    <div style="{CARD_STYLE} background: #f9fafb;">
        <h3 style="margin-top: 0;">데이터 출처</h3>
        <p style="margin-top: 0; color: #555;">아래 직무 분석에 사용된 공고의 회사 및 채용 사이트(Greenhouse, Lever 등)입니다.</p>

        <h4 style="margin-bottom: 8px;">회사·플랫폼별 공고 수</h4>
        <table style="{TABLE_STYLE}">
            <thead>
                <tr>
                    <th style="{TH_STYLE}">회사</th>
                    <th style="{TH_STYLE}">채용 플랫폼</th>
                    <th style="{TH_STYLE}">공고 수</th>
                </tr>
            </thead>
            <tbody>
                {breakdown_rows if breakdown_rows else f'<tr><td colspan="3" style="{TD_STYLE}">집계된 출처가 없습니다.</td></tr>'}
            </tbody>
        </table>

        <h4 style="margin-bottom: 8px;">공고 목록 (일부)</h4>
        <table style="{TABLE_STYLE}">
            <thead>
                <tr>
                    <th style="{TH_STYLE}">공고 제목</th>
                    <th style="{TH_STYLE}">회사</th>
                    <th style="{TH_STYLE}">플랫폼</th>
                    <th style="{TH_STYLE}">지역</th>
                    <th style="{TH_STYLE}">링크</th>
                </tr>
            </thead>
            <tbody>
                {posting_rows if posting_rows else f'<tr><td colspan="5" style="{TD_STYLE}">목록이 없습니다.</td></tr>'}
            </tbody>
        </table>
        {note}
    </div>
    """


def localize_job_title(job_title: str) -> str:
    # 간단한 사전/치환 기반 한글화(표시용)
    text = str(job_title or "").strip()
    if not text:
        return text

    replacements = [
        ("Senior", "시니어"),
        ("Junior", "주니어"),
        ("Staff", "스태프"),
        ("Lead", "리드"),
        ("Principal", "프린시펄"),
        ("Backend", "백엔드"),
        ("Back-End", "백엔드"),
        ("Frontend", "프론트엔드"),
        ("Front-End", "프론트엔드"),
        ("Fullstack", "풀스택"),
        ("Full-Stack", "풀스택"),
        ("Data", "데이터"),
        ("Software", "소프트웨어"),
        ("Application", "애플리케이션"),
        ("Security", "보안"),
        ("Support", "지원"),
        ("Engineer", "엔지니어"),
        ("Developer", "개발자"),
        ("Analyst", "분석가"),
        ("Scientist", "사이언티스트"),
        ("Architect", "아키텍트"),
        ("Manager", "매니저"),
        ("Consultant", "컨설턴트"),
        ("Group Lead", "그룹 리드"),
        ("Team Lead", "팀 리드"),
        ("Contract", "계약직"),
    ]

    translated = text
    for en, ko in replacements:
        translated = re.sub(rf"\b{re.escape(en)}\b", ko, translated, flags=re.IGNORECASE)

    translated = re.sub(r"\s+", " ", translated).strip()
    if normalize_text(translated) == normalize_text(text):
        return text
    return f"{translated} ({text})"


def render_skill_table(title: str, skills: list) -> str:
    if not skills:
        return f"""
        <h3>{title}</h3>
        <p>데이터가 없습니다.</p>
        """

    rows = ""
    for item in skills:
        rows += f"""
        <tr>
            <td style="{TD_STYLE}">{item['skill']}</td>
            <td style="{TD_STYLE}">{item['count']}</td>
            <td style="{TD_STYLE}">{item['percent']}%</td>
        </tr>
        """

    return f"""
    <h3>{title}</h3>
    <table style="{TABLE_STYLE}">
        <thead>
            <tr>
                <th style="{TH_STYLE}">기술</th>
                <th style="{TH_STYLE}">등장 횟수</th>
                <th style="{TH_STYLE}">비율</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def render_skill_gap_form(
    query_val: Optional[str],
    selected_job_val: Optional[str],
    my_skills: str,
) -> str:
    hidden = ""
    if selected_job_val:
        hidden += f'<input type="hidden" name="selected_job" value="{html.escape(selected_job_val)}">'
    elif query_val:
        hidden += f'<input type="hidden" name="query" value="{html.escape(query_val)}">'
    escaped_skills = html.escape(my_skills or "")
    return f"""
    <div style="{CARD_STYLE} background: #fafafa;">
        <h3>내 스킬 갭 분석</h3>
        <p style="margin-top: 0; color: #555;">보유 스킬을 입력하면 직무 요구 기술 상위 항목과 비교합니다. (쉼표로 구분)</p>
        <form method="get" action="/search" style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
            {hidden}
            <input type="text" name="my_skills" value="{escaped_skills}" placeholder="예: Python, SQL, Docker" style="{INPUT_STYLE}">
            <button type="submit" style="{BUTTON_STYLE}">갭 분석</button>
        </form>
    </div>
    """


def render_skill_gap_results(gap: dict) -> str:
    if gap["target_count"] == 0:
        return """
        <div style="margin: 16px 0; padding: 12px; background: #fff8e6; border-radius: 8px;">
            <strong>스킬 갭</strong>: 요구 기술 데이터가 없어 비교할 수 없습니다.
        </div>
        """
    matched = gap["matched_skills"]
    missing_display = gap["missing_skills"][:10]
    pct = gap["match_percent"]
    m_li = "".join(f"<li>{html.escape(str(s))}</li>" for s in matched)
    miss_li = "".join(f"<li>{html.escape(str(s))}</li>" for s in missing_display)
    return f"""
    <div style="{CARD_STYLE} background: #f0f8ff; border-color: #bfdbfe;">
        <h3 style="margin-top: 0;">스킬 갭 결과</h3>
        <p><strong>매칭률 (요구 기술 상위 {gap['target_count']}개 기준): {pct}%</strong></p>
        <p style="margin-bottom: 6px;">보유한 스킬:</p>
        <ul style="margin-top: 0;">{m_li if m_li else '<li>없음</li>'}</ul>
        <p style="margin-bottom: 6px;">부족한 스킬 (최대 10개 표시):</p>
        <ul style="margin-top: 0;">{miss_li if miss_li else '<li>없음 (요구 항목을 모두 충족)</li>'}</ul>
    </div>
    """


def render_search_form(current_query: str = "") -> str:
    escaped_query = html.escape(str(current_query or ""))
    return f"""
    <form action="/search" method="get" style="margin: 16px 0 0 0; display: flex; gap: 8px; flex-wrap: wrap;">
        <input
            type="text"
            name="query"
            value="{escaped_query}"
            placeholder="예: 백엔드 개발자 우대 기술 알려줘"
            style="{INPUT_STYLE}"
        >
        <button type="submit" style="{BUTTON_STYLE}">검색</button>
    </form>
    """


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head>
        <meta charset="utf-8">
        <title>직무 기술 분석기</title>
    </head>
    <body style=\"""" + BASE_STYLE + """\">
        <div style=\"""" + CARD_STYLE + """\">
            <h1 style="margin-top: 0;">채용공고 기반 직무 기술 스택 분석</h1>
            <p style="color: #4b5563;">직무명을 입력해 기술 스택, 출처, 스킬 갭을 한 번에 확인해보세요.</p>
            """ + render_search_form("") + """
        </div>

        <div style=\"""" + CARD_STYLE + """\">
            <h3 style="margin-top: 0;">예시 질문</h3>
            <ul style="margin-bottom: 0;">
                <li>백엔드 개발자</li>
                <li>개발자</li>
                <li>데이터 엔지니어 필수 기술</li>
                <li>프론트엔드 개발자 우대 기술 알려줘</li>
            </ul>
        </div>
    </body>
    </html>
    """


@app.get("/search", response_class=HTMLResponse)
def search(
    query: Optional[str] = Query(None, description="검색할 직무 또는 질문"),
    selected_job: Optional[str] = Query(None, description="후보에서 선택한 확정 직무"),
    my_skills: Optional[str] = Query(None, description="내 보유 스킬(쉼표 구분)"),
):
    if selected_job:
        # selected_job 경로는 재검색이 아니라 선택 확정: 정규화 없이 정확 직무 분석
        df = load_data()
        jobs = get_all_jobs(df)
        selected_norm = normalize_text(selected_job)
        exact_job = next((job for job in jobs if normalize_text(job) == selected_norm), None)

        if not exact_job:
            data = {
                "status": "not_found",
                "query": selected_job,
                "question_type": "all",
                "message": "선택한 직무를 데이터에서 찾지 못했습니다."
            }
        else:
            result = analyze_job(df, exact_job)
            question_type = "all"
            data = {
                "status": "success",
                "query": selected_job,
                "question_type": question_type,
                "result": result,
                "message": make_summary_message(result, question_type),
            }
    else:
        if not query:
            data = {
                "status": "not_found",
                "query": "",
                "question_type": "all",
                "message": "검색어를 입력해주세요."
            }
        else:
            data = search_jobs(query)

    if data["status"] == "not_found":
        return f"""
        <html>
        <head><meta charset="utf-8"><title>검색 결과</title></head>
        <body style="{BASE_STYLE}">
            <div style="{CARD_STYLE}">
                <h1 style="margin-top: 0;">검색 결과</h1>
                {render_search_form(data['query'])}
                <p><strong>입력:</strong> {data['query']}</p>
                <p style="color: #dc2626; font-weight: 600;">{data['message']}</p>
                <a href="/" style="color: #2563eb;">← 돌아가기</a>
            </div>
        </body>
        </html>
        """

    if data["status"] == "multiple":
        candidate_links = ""
        for idx, candidate in enumerate(data["candidates"], start=1):
            encoded_candidate = quote(candidate)
            display_candidate = localize_job_title(candidate)
            candidate_links += f"""
            <li style="{CANDIDATE_ITEM_STYLE}">
                <a href="/search?selected_job={encoded_candidate}" style="{CANDIDATE_LINK_STYLE}">
                    <span style="display: inline-block; min-width: 26px; color: #6b7280; font-weight: 700;">{idx}.</span>
                    <span>{display_candidate}</span>
                </a>
            </li>
            """

        return f"""
        <html>
        <head><meta charset="utf-8"><title>직무 후보</title></head>
        <body style="{BASE_STYLE}">
            <div style="{CARD_STYLE}">
                <h1 style="margin-top: 0;">직무 후보</h1>
                {render_search_form(data['query'])}
                <p><strong>입력:</strong> {data['query']}</p>
                <p><strong>질문 의도:</strong> {data['question_type']}</p>
                <p>{data['message']}</p>
                <p style="margin-bottom: 8px; color: #4b5563;">가장 관련도 높은 순서예요. 카드 하나를 눌러 결과를 확인해 보세요.</p>
                <ul style="{CANDIDATE_LIST_STYLE}">
                    {candidate_links}
                </ul>
                <a href="/" style="color: #2563eb;">← 돌아가기</a>
            </div>
        </body>
        </html>
        """

    result = data["result"]
    question_type = data["question_type"]

    required_html = ""
    preferred_html = ""

    if question_type == "required":
        required_html = render_skill_table("요구 기술", result["required_skills"])
    elif question_type == "preferred":
        preferred_html = render_skill_table("우대 기술", result["preferred_skills"])
    else:
        required_html = render_skill_table("요구 기술", result["required_skills"])
        preferred_html = render_skill_table("우대 기술", result["preferred_skills"])

    skill_gap_form = render_skill_gap_form(query, selected_job, my_skills or "")
    gap_results_html = ""
    if my_skills and str(my_skills).strip():
        gap = compute_skill_gap(result["required_skills"], my_skills, top_n=10)
        gap_results_html = render_skill_gap_results(gap)

    sources_html = render_sources_section(result)

    return f"""
    <html>
    <head><meta charset="utf-8"><title>분석 결과</title></head>
    <body style="{BASE_STYLE}">
        <div style="{CARD_STYLE}">
            <h1 style="margin-top: 0;">{localize_job_title(result['job'])} 분석 결과</h1>
            {render_search_form(data['query'])}

            <p><strong>입력:</strong> {data['query']}</p>
            <p><strong>질문 의도:</strong> {question_type}</p>
            <p><strong>해당 직무 공고 수:</strong> {result['count']}</p>
            <p style="background: #eff6ff; padding: 12px; border-radius: 10px; border: 1px solid #dbeafe;">
                {data['message']}
            </p>
        </div>

        {sources_html}

        {skill_gap_form}
        {gap_results_html}

        <div style="{CARD_STYLE}">
            {required_html}
            {preferred_html}
            <a href="/" style="color: #2563eb;">← 돌아가기</a>
        </div>
    </body>
    </html>
    """