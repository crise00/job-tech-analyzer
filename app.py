from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from analyzer import search_jobs

app = FastAPI()


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

        <form action="/search" method="get" style="margin-bottom: 20px;">
            <input type="text" name="query" placeholder="예: 백엔드 개발자 우대 기술 알려줘" style="width: 500px; padding: 10px;">
            <button type="submit" style="padding: 10px 16px;">검색</button>
        </form>

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
def search(query: str = Query(..., description="검색할 직무 또는 질문")):
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
            <p><strong>입력:</strong> {data['query']}</p>
            <p style="color: red;">{data['message']}</p>
            <a href="/">← 돌아가기</a>
        </body>
        </html>
        """

    if data["status"] == "multiple":
        candidate_links = ""
        for candidate in data["candidates"]:
            candidate_links += f"""
            <li>
                <a href="/search?query={candidate}" style="text-decoration: none;">
                    {candidate}
                </a>
            </li>
            """

        return f"""
        <html>
        <head><meta charset="utf-8"><title>직무 후보</title></head>
        <body style="{base_style}">
            <h1>직무 후보</h1>
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
        <h1>{result['job']} 분석 결과</h1>

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