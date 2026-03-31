import os

import pandas as pd
import requests


API_URL = "https://boards-api.greenhouse.io/v1/boards/appsflyer/jobs?content=true"
OUTPUT_PATH = os.path.join("data", "appsflyer_jobs.csv")


def main() -> None:
    response = requests.get(API_URL, timeout=15)
    response.raise_for_status()

    data = response.json()
    jobs = data.get("jobs", [])
    rows = []

    for job in jobs:
        title = job.get("title", "")
        location_name = (job.get("location") or {}).get("name", "")
        absolute_url = job.get("absolute_url", "")
        content = job.get("content", "")
        rows.append(
            {
                "title": title,
                "location_name": location_name,
                "absolute_url": absolute_url,
                "content": content,
            }
        )

    df = pd.DataFrame(rows, columns=["title", "location_name", "absolute_url", "content"])
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
