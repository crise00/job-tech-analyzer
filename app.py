from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from urllib.parse import quote
from typing import Optional
import re
import html

from analyzer import search_jobs, load_data, get_all_jobs, analyze_job, normalize_text, make_summary_message

app = FastAPI()


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
            <td>{item['skill']}</td>
            <td>{item['count']}</td>
            <td>{item['percent']}%</td>
        </tr>
        """

    return f"""
    <h3>{title}</h3>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
        <thead>
            <tr>
                <th>기술</th>
                <th>등장 횟수</th>
                <th>비율</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def render_search_form(current_query: str = "") -> str:
    escaped_query = html.escape(str(current_query or ""))
    return f"""
    <form action="/search" method="get" style="margin: 16px 0 24px 0;">
        <input
            type="text"
            name="query"
            value="{escaped_query}"
            placeholder="예: 백엔드 개발자 우대 기술 알려줘"
            style="width: 500px; padding: 10px;"
        >
        <button type="submit" style="padding: 10px 16px;">검색</button>
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
    <body style="font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; line-height: 1.6;">
        <h1>채용공고 기반 직무 기술 스택 분석</h1>
        <p>직무명을 입력해보세요.</p>

        """ + render_search_form("") + """

        <h3>예시 질문</h3>
        <ul>
            <li>백엔드 개발자</li>
            <li>개발자</li>
            <li>데이터 엔지니어 필수 기술</li>
            <li>프론트엔드 개발자 우대 기술 알려줘</li>
        </ul>
    </body>
    </html>
    """


@app.get("/search", response_class=HTMLResponse)
def search(
    query: Optional[str] = Query(None, description="검색할 직무 또는 질문"),
    selected_job: Optional[str] = Query(None, description="후보에서 선택한 확정 직무"),
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

    base_style = """
    font-family: Arial, sans-serif;
    max-width: 960px;
    margin: 40px auto;
    line-height: 1.6;
    """

    if data["status"] == "not_found":
        return f"""
        <html>
        <head><meta charset="utf-8"><title>검색 결과</title></head>
        <body style="{base_style}">
            <h1>검색 결과</h1>
            {render_search_form(data['query'])}
            <p><strong>입력:</strong> {data['query']}</p>
            <p style="color: red;">{data['message']}</p>
            <a href="/">← 돌아가기</a>
        </body>
        </html>
        """

    if data["status"] == "multiple":
        candidate_links = ""
        for candidate in data["candidates"]:
            encoded_candidate = quote(candidate)
            display_candidate = localize_job_title(candidate)
            candidate_links += f"""
            <li>
                <a href="/search?selected_job={encoded_candidate}" style="text-decoration: none;">
                    {display_candidate}
                </a>
            </li>
            """

        return f"""
        <html>
        <head><meta charset="utf-8"><title>직무 후보</title></head>
        <body style="{base_style}">
            <h1>직무 후보</h1>
            {render_search_form(data['query'])}
            <p><strong>입력:</strong> {data['query']}</p>
            <p><strong>질문 의도:</strong> {data['question_type']}</p>
            <p>{data['message']}</p>

            <ul>
                {candidate_links}
            </ul>

            <a href="/">← 돌아가기</a>
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

    return f"""
    <html>
    <head><meta charset="utf-8"><title>분석 결과</title></head>
    <body style="{base_style}">
        <h1>{localize_job_title(result['job'])} 분석 결과</h1>
        {render_search_form(data['query'])}

        <p><strong>입력:</strong> {data['query']}</p>
        <p><strong>질문 의도:</strong> {question_type}</p>
        <p><strong>해당 직무 공고 수:</strong> {result['count']}</p>
        <p style="background: #f5f5f5; padding: 12px; border-radius: 8px;">
            {data['message']}
        </p>

        {required_html}
        {preferred_html}

        <a href="/">← 돌아가기</a>
    </body>
    </html>
    """