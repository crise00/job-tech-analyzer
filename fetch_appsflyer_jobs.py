import os
import re
from typing import Any, Dict, List

import pandas as pd
import requests


OUTPUT_PATH = os.path.join("data", "appsflyer_jobs.csv")
GREENHOUSE_SOURCES = {
    "appsflyer": "https://boards-api.greenhouse.io/v1/boards/appsflyer/jobs?content=true",
}
LEVER_COMPANIES = [
    "wealthfront",
    "palantir",
    "offchainlabs",
    "palantir",
    "spotify",
    "zerion",
    "modulate",
    "binance",
    "xsolla",
    "resilientco",
    "jobgether",
]


def strip_html(text: str) -> str:
    raw = str(text or "")
    if not raw.strip():
        return ""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw, "lxml")
        clean = soup.get_text(separator=" ", strip=True)
    except Exception:
        clean = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", clean).strip()


def lever_list_sections(lists: Any) -> List[str]:
    """Lever `lists[].content` is HTML string, not a list of items."""
    sections: List[str] = []
    for section in lists or []:
        content = (section or {}).get("content")
        if not content:
            continue
        if isinstance(content, list):
            for item in content:
                if item:
                    sections.append(strip_html(str(item)))
        else:
            sections.append(strip_html(str(content)))
    return sections


def collect_greenhouse_rows(company: str, api_url: str) -> List[Dict[str, Any]]:
    response = requests.get(api_url, timeout=20)
    response.raise_for_status()
    data = response.json()
    jobs = data.get("jobs", [])
    rows = []
    for job in jobs:
        rows.append(
            {
                "company": company,
                "source_platform": "greenhouse",
                "title": job.get("title", ""),
                "location_name": (job.get("location") or {}).get("name", ""),
                "absolute_url": job.get("absolute_url", ""),
                "content": strip_html(job.get("content", "")),
            }
        )
    return rows


def collect_lever_rows(company: str) -> List[Dict[str, Any]]:
    api_url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    response = requests.get(api_url, timeout=20)
    response.raise_for_status()
    postings = response.json()
    rows = []
    for posting in postings:
        categories = posting.get("categories") or {}
        description = posting.get("descriptionPlain") or posting.get("description") or ""
        list_contents = lever_list_sections(posting.get("lists"))
        full_content = " ".join([strip_html(description), *list_contents]).strip()
        rows.append(
            {
                "company": company,
                "source_platform": "lever",
                "title": posting.get("text", ""),
                "location_name": categories.get("location", ""),
                "absolute_url": posting.get("hostedUrl", ""),
                "content": full_content,
            }
        )
    return rows


def main() -> None:
    rows = []
    for company, api_url in GREENHOUSE_SOURCES.items():
        company_rows = collect_greenhouse_rows(company, api_url)
        rows.extend(company_rows)
        print(f"[greenhouse] {company}: {len(company_rows)}건 수집")

    unique_lever_companies = list(dict.fromkeys(LEVER_COMPANIES))
    for company in unique_lever_companies:
        company_rows = collect_lever_rows(company)
        rows.extend(company_rows)
        print(f"[lever] {company}: {len(company_rows)}건 수집")

    df = pd.DataFrame(
        rows,
        columns=[
            "company",
            "source_platform",
            "title",
            "location_name",
            "absolute_url",
            "content",
        ],
    )
    os.makedirs("data", exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    # 출력이 과도하게 길어지지 않도록 상위 5개만 미리보기 출력
    preview_count = min(5, len(rows))
    for row in rows[:preview_count]:
        content_preview = str(row["content"]).strip().replace("\n", " ")[:300]
        print(f"title: {row['title']}")
        print(f"location: {row['location_name']}")
        print(f"url: {row['absolute_url']}")
        print(f"content_preview: {content_preview}")
        print("-" * 40)

    if len(rows) > preview_count:
        print(f"... 생략된 공고: {len(rows) - preview_count}건")

    print(f"CSV 저장 완료: {OUTPUT_PATH}")
    print(f"저장된 행 개수: {len(df)}")


if __name__ == "__main__":
    main()
