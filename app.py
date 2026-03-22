from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
from analyzer import load_tech_stack, analyze_job, extract_job_candidates, detect_question_type

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <meta charset="UTF-8">
            <title>직무 기술 분석기</title>
        </head>
        <body>
            <h1>직무 기술 분석기</h1>
            <form action="/search" method="get">
                <input type="text" name="job" placeholder="질문을 입력하세요">
                <button type="submit">전송</button>
            </form>
        </body>
    </html>
    """


@app.get("/search", response_class=HTMLResponse)
def search(job: str = ""):
    tech_list = load_tech_stack("tech_stack.txt")
    df = pd.read_csv("data/job_posts.csv")

    job_list = df["job"].dropna().unique().tolist()
    job_candidates = extract_job_candidates(job, job_list)
    question_type = detect_question_type(job)

    if len(job_candidates) >= 2:
        candidate_items = ""
        for candidate in job_candidates:
            candidate_items += f"<li>{candidate}</li>"

        return f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <title>직업 후보</title>
            </head>
            <body>
                <h1>여러 직업 후보가 발견되었습니다.</h1>
                <p>입력한 질문: {job}</p>
                <p>아래 직업 중 하나를 더 구체적으로 입력해주거라.</p>
                <ul>
                    {candidate_items}
                </ul>
                <a href="/">뒤로가기</a>
            </body>
        </html>
        """

    selected_job = job_candidates[0] if len(job_candidates) == 1 else job
    result_df = analyze_job(df, tech_list, selected_job)

    matched_jobs = df[df["job"].str.contains(selected_job, case=False, na=False)]["job"].unique()
    job_count = len(df[df["job"].str.contains(selected_job, case=False, na=False)])
    matched_job_text = ", ".join(matched_jobs)

    if result_df is None:
        return f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <title>검색 결과</title>
            </head>
            <body>
                <h1>검색 결과</h1>
                <p>찾은 직업 후보: {job_candidates}</p>
                <p>'{job}' 데이터가 없습니다.</p>
                <a href="/">뒤로가기</a>
            </body>
        </html>
        """

    top_required = result_df[result_df["required_percent"] > 0]["tech"].head(3).tolist()
    top_preferred = result_df[result_df["preferred_percent"] > 0]["tech"].head(3).tolist()

    required_text = ", ".join(top_required) if top_required else "없음"
    preferred_text = ", ".join(top_preferred) if top_preferred else "없음"

    bot_answer = (
        f"'{selected_job}'와 관련된 데이터를 분석한 결과, "
        f"주요 요구 기술은 {required_text} 이고, "
        f"주요 우대 기술은 {preferred_text} 입니다."
    )

    required_rows = ""
    preferred_rows = ""

    for _, row in result_df.iterrows():
        if row["required_percent"] > 0:
            required_rows += f"""
            <tr>
                <td>{row['tech']}</td>
                <td>{row['required_percent']}%</td>
            </tr>
            """

        if row["preferred_percent"] > 0:
            preferred_rows += f"""
            <tr>
                <td>{row['tech']}</td>
                <td>{row['preferred_percent']}%</td>
            </tr>
            """

    return f"""
    <html>
        <head>
            <meta charset="UTF-8">
            <title>검색 결과</title>
        </head>
        <body>
            <h1>{selected_job} 분석 결과</h1>
            <p>{bot_answer}</p>
            <p>질문 의도: {question_type}</p>
            <p>찾은 직업 후보: {job_candidates}</p>
            <p>총 {job_count}개의 채용공고를 기준으로 분석했습니다.</p>
            <p>'{job}'로 검색한 결과이며, {matched_job_text} 관련 데이터를 보여줍니다.</p>

            <h2>요구 기술</h2>
            <table border="1" cellpadding="8">
                <tr>
                    <th>기술</th>
                    <th>요구 비율</th>
                </tr>
                {required_rows}
            </table>

            <br>

            <h2>우대 기술</h2>
            <table border="1" cellpadding="8">
                <tr>
                    <th>기술</th>
                    <th>우대 비율</th>
                </tr>
                {preferred_rows}
            </table>

            <br>
            <a href="/">뒤로가기</a>
        </body>
    </html>
    """