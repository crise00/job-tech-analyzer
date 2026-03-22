import re
import pandas as pd


def load_tech_stack(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        techs = [line.strip() for line in file if line.strip()]

    techs.sort(key=len, reverse=True)
    return techs


def find_tech_in_text(text, tech_list):
    if pd.isna(text):
        return []

    text_str = str(text)
    found = []
    matched_ranges = []

    for tech in tech_list:
        pattern = re.escape(tech)
        matches = list(re.finditer(pattern, text_str, flags=re.IGNORECASE))

        for match in matches:
            start, end = match.span()

            overlap = False
            for saved_start, saved_end in matched_ranges:
                if not (end <= saved_start or start >= saved_end):
                    overlap = True
                    break

            if not overlap:
                found.append(tech)
                matched_ranges.append((start, end))
                break

    return found


def analyze_job(df, tech_list, target_job):
    job_df = df[df["job"].str.contains(target_job, case=False, na=False)].copy()

    if job_df.empty:
        return None

    total_count = len(job_df)
    required_count = {}
    preferred_count = {}

    for tech in tech_list:
        required_count[tech] = 0
        preferred_count[tech] = 0

    for _, row in job_df.iterrows():
        found_required = find_tech_in_text(row["requirements"], tech_list)
        found_preferred = find_tech_in_text(row["preferred"], tech_list)

        for tech in found_required:
            required_count[tech] += 1

        for tech in found_preferred:
            preferred_count[tech] += 1

    result = []

    for tech in tech_list:
        req_percent = (required_count[tech] / total_count) * 100
        pref_percent = (preferred_count[tech] / total_count) * 100

        if req_percent > 0 or pref_percent > 0:
            result.append({
                "job": target_job,
                "tech": tech,
                "required_percent": round(req_percent, 2),
                "preferred_percent": round(pref_percent, 2)
            })

    result_df = pd.DataFrame(result)
    result_df = result_df.sort_values(
        by=["required_percent", "preferred_percent"],
        ascending=False
    )

    return result_df


def extract_job_candidates(query, job_list):
    query = str(query).strip().lower()
    matched_jobs = []

    for job in job_list:
        job_lower = job.lower()

        if query and query in job_lower:
            matched_jobs.append(job)
            continue

        job_words = job_lower.split()
        for word in job_words:
            if word and word in query:
                matched_jobs.append(job)
                break

    return matched_jobs

def detect_question_type(query):
    query = str(query)

    if "우대" in query:
        return "preferred"
    elif "요구" in query or "필수" in query:
        return "required"
    else:
        return "all"