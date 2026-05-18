import re
from typing import Any, Dict, List
from urllib.parse import quote

# kind: learn=학습, cert=자격·인증, exam=응시·등록
Resource = Dict[str, str]

SKILL_RESOURCES: Dict[str, List[Resource]] = {
    "python": [
        {"title": "PCEP 응시 안내 (Python Institute)", "url": "https://pythoninstitute.org/pcep", "kind": "exam"},
        {"title": "시험 예약 (TestNow / Edube)", "url": "https://edube.org/testing-service", "kind": "exam"},
        {"title": "Python 공식 튜토리얼", "url": "https://docs.python.org/3/tutorial/", "kind": "learn"},
    ],
    "java": [
        {"title": "Oracle Java 인증", "url": "https://education.oracle.com/oracle-certification-path/pFamily_48", "kind": "cert"},
        {"title": "Java 튜토리얼 (Oracle)", "url": "https://docs.oracle.com/javase/tutorial/", "kind": "learn"},
    ],
    "kotlin": [
        {
            "title": "Associate Android Developer (Google)",
            "url": "https://developers.google.com/certification/associate-android-developer",
            "kind": "exam",
        },
        {"title": "Kotlin 공식 문서", "url": "https://kotlinlang.org/docs/home.html", "kind": "learn"},
    ],
    "javascript": [
        {"title": "MDN JavaScript 학습", "url": "https://developer.mozilla.org/ko/docs/Web/JavaScript", "kind": "learn"},
    ],
    "typescript": [
        {"title": "TypeScript 핸드북", "url": "https://www.typescriptlang.org/docs/", "kind": "learn"},
    ],
    "c++": [
        {"title": "cppreference 학습", "url": "https://en.cppreference.com/w/", "kind": "learn"},
    ],
    "c#": [
        {"title": "Microsoft C# 학습", "url": "https://learn.microsoft.com/dotnet/csharp/", "kind": "learn"},
        {"title": "Microsoft Certifications", "url": "https://learn.microsoft.com/certifications/", "kind": "cert"},
    ],
    "spring": [
        {"title": "Spring 공식 가이드", "url": "https://spring.io/guides", "kind": "learn"},
    ],
    "spring boot": [
        {"title": "Spring Boot 공식 문서", "url": "https://spring.io/projects/spring-boot", "kind": "learn"},
    ],
    "django": [
        {"title": "Django 공식 튜토리얼", "url": "https://docs.djangoproject.com/", "kind": "learn"},
    ],
    "fastapi": [
        {"title": "FastAPI 공식 문서", "url": "https://fastapi.tiangolo.com/", "kind": "learn"},
    ],
    "react": [
        {"title": "React 공식 문서", "url": "https://react.dev/learn", "kind": "learn"},
        {
            "title": "Meta Front-End 인증 (Coursera)",
            "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer",
            "kind": "cert",
        },
    ],
    "vue": [
        {"title": "Vue.js 공식 가이드", "url": "https://vuejs.org/guide/introduction.html", "kind": "learn"},
    ],
    "node.js": [
        {"title": "Node.js 공식 문서", "url": "https://nodejs.org/docs/latest/api/", "kind": "learn"},
        {"title": "OpenJS 인증 (Linux Foundation)", "url": "https://training.linuxfoundation.org/openjs/", "kind": "cert"},
    ],
    "android": [
        {"title": "Android 개발자 과정", "url": "https://developer.android.com/courses", "kind": "learn"},
        {
            "title": "Associate Android Developer (Google)",
            "url": "https://developers.google.com/certification/associate-android-developer",
            "kind": "exam",
        },
    ],
    "jetpack compose": [
        {
            "title": "Compose 공식 튜토리얼",
            "url": "https://developer.android.com/develop/ui/compose/documentation",
            "kind": "learn",
        },
        {
            "title": "Associate Android Developer (Google)",
            "url": "https://developers.google.com/certification/associate-android-developer",
            "kind": "exam",
        },
    ],
    "gradle": [
        {"title": "Gradle 공식 문서", "url": "https://docs.gradle.org/current/userguide/userguide.html", "kind": "learn"},
    ],
    "sql": [
        {"title": "SQLBolt 학습", "url": "https://sqlbolt.com/", "kind": "learn"},
        {"title": "Oracle Database 인증", "url": "https://education.oracle.com/oracle-certification-path/pFamily_48", "kind": "exam"},
    ],
    "mysql": [
        {"title": "MySQL 공식 튜토리얼", "url": "https://dev.mysql.com/doc/", "kind": "learn"},
        {"title": "Oracle 인증 (MySQL 포함)", "url": "https://education.oracle.com/oracle-certification-path/pFamily_48", "kind": "exam"},
    ],
    "postgresql": [
        {"title": "PostgreSQL 튜토리얼", "url": "https://www.postgresql.org/docs/current/tutorial.html", "kind": "learn"},
    ],
    "mongodb": [
        {"title": "MongoDB University", "url": "https://learn.mongodb.com/", "kind": "learn"},
        {"title": "MongoDB Certification", "url": "https://learn.mongodb.com/certification", "kind": "exam"},
    ],
    "oracle": [
        {"title": "Oracle 인증 로드맵", "url": "https://education.oracle.com/oracle-certification-path/pFamily_48", "kind": "cert"},
    ],
    "aws": [
        {"title": "AWS Certification", "url": "https://aws.amazon.com/certification/", "kind": "exam"},
        {"title": "AWS Skill Builder", "url": "https://skillbuilder.aws/", "kind": "learn"},
    ],
    "azure": [
        {"title": "Microsoft Certifications", "url": "https://learn.microsoft.com/certifications/", "kind": "exam"},
        {"title": "Microsoft Learn", "url": "https://learn.microsoft.com/training/", "kind": "learn"},
    ],
    "gcp": [
        {"title": "Google Cloud 인증", "url": "https://cloud.google.com/certification", "kind": "exam"},
        {"title": "Google Cloud Skills Boost", "url": "https://www.cloudskillsboost.google/", "kind": "learn"},
    ],
    "docker": [
        {"title": "Docker 공식 학습", "url": "https://docs.docker.com/get-started/", "kind": "learn"},
        {"title": "Docker Training", "url": "https://www.docker.com/training/", "kind": "cert"},
    ],
    "kubernetes": [
        {
            "title": "CKA 응시 (Linux Foundation)",
            "url": "https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/",
            "kind": "exam",
        },
        {"title": "Kubernetes 공식 문서", "url": "https://kubernetes.io/docs/home/", "kind": "learn"},
    ],
    "git": [
        {"title": "Git 공식 북", "url": "https://git-scm.com/book/ko/v2", "kind": "learn"},
    ],
    "github": [
        {"title": "GitHub Skills", "url": "https://skills.github.com/", "kind": "learn"},
        {"title": "GitHub Certifications", "url": "https://resources.github.com/learn/certifications/", "kind": "cert"},
    ],
    "linux": [
        {"title": "Linux Foundation 교육", "url": "https://training.linuxfoundation.org/", "kind": "learn"},
        {
            "title": "LFCS 응시",
            "url": "https://training.linuxfoundation.org/certification/linux-foundation-certified-sysadmin-lfcs/",
            "kind": "exam",
        },
    ],
    "tensorflow": [
        {"title": "TensorFlow Certificate 안내", "url": "https://www.tensorflow.org/certificate", "kind": "exam"},
    ],
    "pytorch": [
        {"title": "PyTorch 튜토리얼", "url": "https://pytorch.org/tutorials/", "kind": "learn"},
    ],
    "pandas": [
        {"title": "pandas 공식 문서", "url": "https://pandas.pydata.org/docs/", "kind": "learn"},
    ],
    "numpy": [
        {"title": "NumPy 공식 문서", "url": "https://numpy.org/doc/", "kind": "learn"},
    ],
    "html": [
        {"title": "MDN HTML 학습", "url": "https://developer.mozilla.org/ko/docs/Web/HTML", "kind": "learn"},
    ],
    "css": [
        {"title": "MDN CSS 학습", "url": "https://developer.mozilla.org/ko/docs/Web/CSS", "kind": "learn"},
    ],
    "swift": [
        {"title": "Swift 공식 튜토리얼", "url": "https://docs.swift.org/swift-book/", "kind": "learn"},
        {"title": "Apple Developer 학습", "url": "https://developer.apple.com/learn/", "kind": "learn"},
    ],
    "flutter": [
        {"title": "Flutter 공식 문서", "url": "https://docs.flutter.dev/", "kind": "learn"},
    ],
    "ios": [
        {"title": "Apple Developer 학습", "url": "https://developer.apple.com/learn/", "kind": "learn"},
    ],
}

KIND_LABEL = {"learn": "학습", "cert": "자격", "exam": "응시"}


def _normalize_skill_key(skill: str) -> str:
    return re.sub(r"\s+", " ", str(skill or "").strip().lower())


def get_resources_for_skill(skill: str, limit: int = 3) -> List[Resource]:
    key = _normalize_skill_key(skill)
    if key in SKILL_RESOURCES:
        return SKILL_RESOURCES[key][:limit]

    for known, resources in SKILL_RESOURCES.items():
        if key == known or key.startswith(known + " ") or known in key:
            return resources[:limit]

    query = quote(f"{skill} certification official")
    return [
        {
            "title": f"{skill} 공식 자격·학습 검색",
            "url": f"https://www.google.com/search?q={query}",
            "kind": "learn",
        },
    ]


def resources_for_missing_skills(skills: List[str], limit_per_skill: int = 2) -> Dict[str, List[Resource]]:
    return {skill: get_resources_for_skill(skill, limit=limit_per_skill) for skill in skills}
