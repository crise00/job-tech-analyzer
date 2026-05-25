"""직무명 표시용 한글화(영어 치환 + 외국어 기계 번역)."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

from analyzer import normalize_text

EN_REPLACEMENTS = [
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
    ("Full Stack", "풀스택"),
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
    ("Automation", "자동화"),
    ("Agents", "에이전트"),
    ("Intelligence", "인텔리전스"),
    ("Artificial", "인공"),
]

# 자주 나오는 포르투갈어·스페인어 직무 표현(번역 API 없이도 처리)
EXTRA_REPLACEMENTS = [
    ("Sênior", "시니어"),
    ("Senior", "시니어"),
    ("Júnior", "주니어"),
    ("Junior", "주니어"),
    ("Analista", "분석가"),
    ("Engenheiro", "엔지니어"),
    ("Desenvolvedor", "개발자"),
    ("Arquiteto", "아키텍트"),
    ("Automação", "자동화"),
    ("Agentes", "에이전트"),
    ("Ingeniero", "엔지니어"),
    ("Desarrollador", "개발자"),
    ("Especialista", "전문가"),
    ("Coordenador", "코디네이터"),
    ("Gerente", "매니저"),
]


def _apply_replacements(text: str, pairs: list[tuple[str, str]]) -> str:
    translated = text
    for src, dst in pairs:
        translated = re.sub(
            rf"\b{re.escape(src)}\b",
            dst,
            translated,
            flags=re.IGNORECASE,
        )
    return re.sub(r"\s+", " ", translated).strip()


def _has_hangul(text: str) -> bool:
    return bool(re.search(r"[\uac00-\ud7a3]", text))


def _needs_machine_translation(original: str) -> bool:
    if _has_hangul(original):
        return False
    if re.search(r"[^\x00-\x7f\u2013\u2014'’]", original):
        return True
    non_en_markers = (
        r"\b(analista|engenheiro|desenvolvedor|automa[cç][aã]o|agentes|"
        r"ingeniero|desarrollador|especialista|coordinador|gerente)\b"
    )
    return bool(re.search(non_en_markers, original, flags=re.IGNORECASE))


@lru_cache(maxsize=2048)
def _translate_to_ko(text: str) -> Optional[str]:
    try:
        from deep_translator import GoogleTranslator

        result = GoogleTranslator(source="auto", target="ko").translate(text)
    except Exception:
        return None
    if not result:
        return None
    cleaned = re.sub(r"\s+", " ", str(result).strip())
    if not cleaned or normalize_text(cleaned) == normalize_text(text):
        return None
    return cleaned


def localize_job_title(job_title: str) -> str:
    """UI 표시용 직무명. 한글화된 문자열과 원문을 함께 반환."""
    text = str(job_title or "").strip()
    if not text:
        return text

    if _has_hangul(text):
        return text

    if _needs_machine_translation(text):
        ko = _translate_to_ko(text)
        if ko:
            return f"{ko} ({text})"

    after_rules = _apply_replacements(text, EN_REPLACEMENTS + EXTRA_REPLACEMENTS)
    if normalize_text(after_rules) != normalize_text(text):
        return f"{after_rules} ({text})"

    return text
