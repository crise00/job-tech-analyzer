import os
import re
from collections import Counter
from typing import List, Dict, Any

import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "job_posts.csv")
TECH_PATH = os.path.join(BASE_DIR, "tech_stack.txt")


def load_tech_stack() -> List[str]:
    if not os.path.exists(TECH_PATH):
        return []

    with open(TECH_PATH, "r", encoding="utf-8") as f:
        techs = [line.strip() for line in f if line.strip()]

    # 긴 단어 먼저 검사해서 "Spring Boot"가 "Spring"보다 먼저 잡히게 함
    techs.sort(key=len, reverse=True)
    return techs


TECH_STACK = load_tech_stack()


def normalize_text(text: str) -> str:
    if pd.isna(text):
        return ""
    return str(text).strip().lower()


def extract_technologies(text: str, tech_stack: List[str] = None) -> List[str]:
    if tech_stack is None:
        tech_stack = TECH_STACK

    text = normalize_text(text)
    found = []

    for tech in tech_stack:
        tech_lower = tech.lower()

        # 영문/숫자 포함 기술은 단어 경계로 검사
        if re.search(r"[a-z0-9]", tech_lower):
            pattern = r"(?<![a-z0-9])" + re.escape(tech_lower) + r"(?![a-z0-9])"
            if re.search(pattern, text):
                found.append(tech)
        else:
            # 한글 기술은 포함 여부로 검사
            if tech_lower in text:
                found.append(tech)

    return found


def load_data() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # 컬럼명 공백 제거
    df.columns = [col.strip() for col in df.columns]

    required_columns = ["job", "requirements", "preferred"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"CSV에 '{col}' 컬럼이 없습니다.")

    df["job"] = df["job"].fillna("").astype(str).str.strip()
    df["requirements"] = df["requirements"].fillna("").astype(str)
    df["preferred"] = df["preferred"].fillna("").astype(str)

    return df


def get_all_jobs(df: pd.DataFrame) -> List[str]:
    jobs = sorted(df["job"].dropna().astype(str).str.strip().unique().tolist())
    return [job for job in jobs if job]


def detect_question_type(query: str) -> str:
    query = normalize_text(query)

    preferred_keywords = ["우대", "preferred", "우대사항", "가산점"]
    required_keywords = ["필수", "요구", "자격", "requirements", "필요", "기본", "필수기술"]

    if any(keyword in query for keyword in preferred_keywords):
        return "preferred"

    if any(keyword in query for keyword in required_keywords):
        return "required"

    return "all"


def extract_job_candidates(query: str, jobs: List[str]) -> List[str]:
    """
    규칙:
    1. 직무명이 질문에 그대로 들어 있으면 우선 그 직무들 반환
    2. 없으면 직무명 단어 일부가 들어가는 후보들을 반환
       -> '개발자'처럼 넓은 질문에 여러 후보 보여주기 위함
    """
    query_norm = normalize_text(query)

    exact_matches = []
    partial_matches = []

    for job in jobs:
        job_norm = normalize_text(job)

        if job_norm and job_norm in query_norm:
            exact_matches.append(job)
            continue

        tokens = [token for token in re.split(r"[/\s,()\-]+", job_norm) if token]
        matched_tokens = [token for token in tokens if token in query_norm]

        if matched_tokens:
            partial_matches.append((job, len(matched_tokens), len(job_norm)))

    if exact_matches:
        # 긴 직무명 우선
        exact_matches = sorted(set(exact_matches), key=len, reverse=True)
        return exact_matches

    # 많이 맞은 후보 우선, 그 다음 직무명 긴 순
    partial_matches.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return [job for job, _, _ in partial_matches]


def analyze_job(df: pd.DataFrame, job_name: str) -> Dict[str, Any]:
    target_df = df[df["job"].str.strip() == job_name].copy()

    if target_df.empty:
        return {
            "job": job_name,
            "count": 0,
            "required_skills": [],
            "preferred_skills": [],
        }

    required_counter = Counter()
    preferred_counter = Counter()

    for _, row in target_df.iterrows():
        req_skills = extract_technologies(row["requirements"])
        pref_skills = extract_technologies(row["preferred"])

        required_counter.update(set(req_skills))
        preferred_counter.update(set(pref_skills))

    total = len(target_df)

    required_skills = []
    for skill, count in required_counter.most_common():
        required_skills.append({
            "skill": skill,
            "count": count,
            "percent": round((count / total) * 100, 1)
        })

    preferred_skills = []
    for skill, count in preferred_counter.most_common():
        preferred_skills.append({
            "skill": skill,
            "count": count,
            "percent": round((count / total) * 100, 1)
        })

    return {
        "job": job_name,
        "count": total,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
    }


def make_summary_message(result: Dict[str, Any], question_type: str) -> str:
    job = result["job"]
    count = result["count"]

    if count == 0:
        return f"{job} 직무 데이터가 없습니다."

    req_top = result["required_skills"][:3]
    pref_top = result["preferred_skills"][:3]

    if question_type == "required":
        if not req_top:
            return f"{job} 직무의 요구 기술 데이터가 부족합니다."
        top_text = ", ".join([f"{x['skill']}({x['percent']}%)" for x in req_top])
        return f"{job} 직무에서 많이 요구되는 기술은 {top_text} 입니다."

    if question_type == "preferred":
        if not pref_top:
            return f"{job} 직무의 우대 기술 데이터가 부족합니다."
        top_text = ", ".join([f"{x['skill']}({x['percent']}%)" for x in pref_top])
        return f"{job} 직무에서 자주 보이는 우대 기술은 {top_text} 입니다."

    parts = []
    if req_top:
        req_text = ", ".join([f"{x['skill']}({x['percent']}%)" for x in req_top])
        parts.append(f"요구 기술은 {req_text}")
    if pref_top:
        pref_text = ", ".join([f"{x['skill']}({x['percent']}%)" for x in pref_top])
        parts.append(f"우대 기술은 {pref_text}")

    if not parts:
        return f"{job} 직무 분석 결과를 만들었지만 기술 데이터가 부족합니다."

    return f"{job} 직무 분석 결과, " + " / ".join(parts) + " 입니다."


def search_jobs(query: str) -> Dict[str, Any]:
    df = load_data()
    jobs = get_all_jobs(df)
    question_type = detect_question_type(query)
    candidates = extract_job_candidates(query, jobs)

    if not candidates:
        return {
            "status": "not_found",
            "query": query,
            "question_type": question_type,
            "message": "해당 질문과 관련된 직무를 찾지 못했습니다."
        }

    # 정확한 직무명이 그대로 들어간 경우
    exact_candidates = [
        job for job in candidates
        if normalize_text(job) in normalize_text(query)
    ]

    # 정확 매칭이 1개면 바로 분석
    if len(exact_candidates) == 1:
        result = analyze_job(df, exact_candidates[0])
        return {
            "status": "success",
            "query": query,
            "question_type": question_type,
            "result": result,
            "message": make_summary_message(result, question_type)
        }

    # 정확 매칭이 여러 개면 후보 제시
    if len(exact_candidates) >= 2:
        return {
            "status": "multiple",
            "query": query,
            "question_type": question_type,
            "candidates": exact_candidates[:10],
            "message": "여러 직무 후보가 발견되었습니다. 하나를 선택해주세요."
        }

    # 정확 매칭은 없고 부분 매칭만 있는 경우
    # 후보가 1개면 바로 분석, 여러 개면 선택 유도
    if len(candidates) == 1:
        result = analyze_job(df, candidates[0])
        return {
            "status": "success",
            "query": query,
            "question_type": question_type,
            "result": result,
            "message": make_summary_message(result, question_type)
        }

    return {
        "status": "multiple",
        "query": query,
        "question_type": question_type,
        "candidates": candidates[:10],
        "message": "여러 직무 후보가 발견되었습니다. 하나를 선택해주세요."
    }