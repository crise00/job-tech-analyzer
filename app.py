import os
from collections import defaultdict
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from urllib.parse import quote
from typing import Any, Dict, List, Optional, Tuple
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
from skill_resources import get_resources_for_skill, KIND_LABEL
from home_page import render_home_page
from search_layout import render_app_page, format_question_type_label

app = FastAPI()

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

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
LOCATION_CHIP_STYLE = (
    "display: inline-block; margin: 2px 4px 2px 0; padding: 3px 10px; "
    "background: #eef2ff; color: #3730a3; border-radius: 999px; font-size: 0.85em;"
)
LOCATION_MORE_STYLE = "color: #6b7280; font-size: 0.85em; margin-left: 4px;"


def format_source_platform_label(platform: str) -> str:
    p = (platform or "").strip().lower()
    if p == "greenhouse":
        return "Greenhouse"
    if p == "lever":
        return "Lever"
    return (platform or "").strip() or "—"


def group_postings_by_role(postings: List[dict]) -> List[Tuple[Tuple[str, str, str], List[dict]]]:
    grouped: Dict[Tuple[str, str, str], List[dict]] = defaultdict(list)
    for posting in postings:
        key = (
            str(posting.get("job_title") or "").strip(),
            str(posting.get("company") or "").strip(),
            str(posting.get("source_platform") or "").strip(),
        )
        grouped[key].append(posting)
    return sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0][0]))


def render_location_chips(postings: List[dict], max_visible: int = 8) -> str:
    locations: List[str] = []
    seen = set()
    for posting in postings:
        loc = str(posting.get("location_name") or "").strip() or "—"
        if loc not in seen:
            seen.add(loc)
            locations.append(loc)

    locations.sort(key=lambda x: (x == "—", x.lower()))
    chips = "".join(
        f'<span style="{LOCATION_CHIP_STYLE}">{html.escape(loc)}</span>'
        for loc in locations[:max_visible]
    )
    extra = len(locations) - max_visible
    if extra > 0:
        chips += f'<span style="{LOCATION_MORE_STYLE}">외 {extra}곳</span>'
    return chips or f'<span style="{LOCATION_MORE_STYLE}">—</span>'


def render_grouped_posting_links(postings: List[dict]) -> str:
    items = []
    for posting in sorted(
        postings,
        key=lambda p: str(p.get("location_name") or "").lower(),
    ):
        loc = html.escape(str(posting.get("location_name") or "—").strip())
        url = str(posting.get("absolute_url") or "").strip()
        if url:
            link = (
                f'<a href="{html.escape(url, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer" style="color: #2563eb; font-weight: 600;">공고 보기</a>'
            )
        else:
            link = "—"
        items.append(
            f'<li style="margin: 4px 0; display: flex; justify-content: space-between; gap: 12px;">'
            f'<span>{loc}</span>{link}</li>'
        )

    count = len(postings)
    if count == 1:
        url = str(postings[0].get("absolute_url") or "").strip()
        if url:
            return (
                f'<a href="{html.escape(url, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer" style="color: #2563eb; font-weight: 600;">공고 보기</a>'
            )
        return "—"

    return f"""
    <details style="font-size: 0.95em;">
        <summary style="cursor: pointer; color: #2563eb; font-weight: 600;">{count}개 지역 공고</summary>
        <ul style="margin: 8px 0 0 0; padding-left: 18px; max-height: 220px; overflow-y: auto;">
            {"".join(items)}
        </ul>
    </details>
    """


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
    grouped_postings = group_postings_by_role(postings)
    for (_, _, _), group in grouped_postings:
        sample = group[0]
        title = html.escape(str(sample.get("job_title") or ""))
        company = html.escape(str(sample.get("company") or "—"))
        plat = html.escape(format_source_platform_label(sample.get("source_platform", "")))
        count_badge = (
            f'<span style="margin-left: 6px; color: #6b7280; font-size: 0.85em;">({len(group)}건)</span>'
            if len(group) > 1
            else ""
        )
        posting_rows += f"""
        <tr>
            <td style="{TD_STYLE}">{title}{count_badge}</td>
            <td style="{TD_STYLE}">{company}</td>
            <td style="{TD_STYLE}">{plat}</td>
            <td style="{TD_STYLE}">{render_location_chips(group)}</td>
            <td style="{TD_STYLE}">{render_grouped_posting_links(group)}</td>
        </tr>
        """

    note = ""
    if truncated:
        note = f"""
        <p style="margin: 12px 0 0 0; color: #666; font-size: 0.95em;">
            미리보기는 최대 {preview_limit}건 기준이며, 같은 직무는 한 줄로 묶어 표시합니다. (전체 {total}건)
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

        <h4 style="margin-bottom: 8px;">공고 요약 (같은 직무·회사는 지역별로 묶음)</h4>
        <table style="{TABLE_STYLE}">
            <thead>
                <tr>
                    <th style="{TH_STYLE}">공고 제목</th>
                    <th style="{TH_STYLE}">회사</th>
                    <th style="{TH_STYLE}">플랫폼</th>
                    <th style="{TH_STYLE}">채용 지역</th>
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


def render_resource_links(skill: str) -> str:
    links = []
    for res in get_resources_for_skill(skill, limit=3):
        label = html.escape(res["title"])
        url = html.escape(res["url"], quote=True)
        kind = KIND_LABEL.get(res.get("kind", ""), "링크")
        links.append(
            f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
            f'style="display: inline-block; margin: 4px 8px 4px 0; padding: 4px 10px; '
            f'background: #fff; border: 1px solid #93c5fd; border-radius: 8px; color: #1d4ed8; '
            f'font-size: 0.9em; text-decoration: none;">{label} '
            f'<span style="color: #6b7280;">({kind})</span></a>'
        )
    return "".join(links)


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
    miss_items = []
    for skill in missing_display:
        skill_esc = html.escape(str(skill))
        miss_items.append(
            f'<li style="margin-bottom: 14px;"><strong>{skill_esc}</strong>'
            f'<div style="margin-top: 6px;">{render_resource_links(skill)}</div></li>'
        )
    miss_li = "".join(miss_items)
    return f"""
    <div style="{CARD_STYLE} background: #f0f8ff; border-color: #bfdbfe;">
        <h3 style="margin-top: 0;">스킬 갭 결과</h3>
        <p><strong>매칭률 (요구 기술 상위 {gap['target_count']}개 기준): {pct}%</strong></p>
        <p style="margin-bottom: 6px;">보유한 스킬:</p>
        <ul style="margin-top: 0;">{m_li if m_li else '<li>없음</li>'}</ul>
        <p style="margin-bottom: 6px;">부족한 스킬 — 학습·자격·응시 링크 (최대 10개):</p>
        <ul style="margin-top: 0; padding-left: 20px;">{miss_li if miss_li else '<li>없음 (요구 항목을 모두 충족)</li>'}</ul>
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
    return render_home_page()


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
        q = html.escape(str(data.get("query") or ""))
        content = f"""
        <div class="app-card">
            <h1 class="app-page-title">검색 결과 없음</h1>
            {f'<p class="app-meta"><strong>입력:</strong> {q}</p>' if q else ''}
            <p class="app-error">{html.escape(data['message'])}</p>
        </div>
        """
        return render_app_page("검색 결과", content, data.get("query") or "")

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

        qtype = format_question_type_label(data["question_type"])
        content = f"""
        <div class="app-card">
            <h1 class="app-page-title">직무 후보</h1>
            <p class="app-meta"><strong>입력:</strong> {html.escape(data['query'])}</p>
            <p class="app-meta"><strong>질문 의도:</strong> <span class="app-badge">{html.escape(qtype)}</span></p>
            <p class="app-meta">{html.escape(data['message'])}</p>
            <p style="margin-bottom: 8px; color: #4b5563;">가장 관련도 높은 순서예요. 카드 하나를 눌러 결과를 확인해 보세요.</p>
            <ul style="{CANDIDATE_LIST_STYLE}">{candidate_links}</ul>
        </div>
        """
        return render_app_page("직무 후보", content, data["query"])

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

    qtype = format_question_type_label(question_type)
    job_title = html.escape(localize_job_title(result["job"]))
    content = f"""
    <div class="app-card">
        <h1 class="app-page-title">{job_title} 분석 결과</h1>
        <p class="app-meta"><strong>입력:</strong> {html.escape(data['query'])}</p>
        <p class="app-meta"><strong>질문 의도:</strong> <span class="app-badge">{html.escape(qtype)}</span></p>
        <p class="app-meta"><strong>해당 직무 공고 수:</strong> {result['count']}</p>
        <p class="app-summary">{html.escape(data['message'])}</p>
    </div>
    {sources_html}
    {skill_gap_form}
    {gap_results_html}
    <div class="app-card">
        {required_html}
        {preferred_html}
    </div>
    """
    return render_app_page("분석 결과", content, data.get("query") or selected_job or "")
