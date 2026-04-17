"""생성된 블로그 글 품질 검증."""
from __future__ import annotations

import re
from dataclasses import dataclass


MIN_LENGTH = 1400
MAX_LENGTH = 2400
MIN_KOREAN_RATIO = 0.70  # 마크다운 기호 제외하면 85% 수준

BANNED_WORDS: list[str] = [
    "절대적",
    "100% 확실",
    "최고의",
    "최상의",
    "완벽한",
    "ChatGPT",
    "OpenAI",
    "GPT-4",
    "AI가 추천",
]

REQUIRED_BRAND = "하우스맨"


@dataclass
class ValidationResult:
    valid: bool
    score: float  # 0.0 ~ 1.0
    issues: list[dict]
    char_count: int
    korean_ratio: float


def validate_post(content: str) -> ValidationResult:
    """생성된 블로그 글 검증.

    Args:
        content: 생성된 마크다운 본문

    Returns:
        ValidationResult — valid 여부·점수·이슈 리스트
    """
    issues: list[dict] = []
    score = 1.0

    # 1) 한국어 비율
    korean_count = len(re.findall(r"[가-힣]", content))
    text_only = re.sub(r"\s", "", content)
    korean_ratio = korean_count / len(text_only) if text_only else 0.0
    if korean_ratio < MIN_KOREAN_RATIO:
        issues.append(
            {
                "type": "korean_ratio_low",
                "message": f"한국어 비율 {korean_ratio:.1%} (최소 {MIN_KOREAN_RATIO:.0%})",
                "retry": True,
            }
        )
        score -= 0.25

    # 2) 길이
    char_count = len(content)
    if char_count < MIN_LENGTH:
        issues.append(
            {
                "type": "too_short",
                "message": f"{char_count}자 (최소 {MIN_LENGTH}자)",
                "retry": True,
            }
        )
        score -= 0.30
    elif char_count > MAX_LENGTH:
        issues.append(
            {
                "type": "too_long",
                "message": f"{char_count}자 (최대 {MAX_LENGTH}자)",
                "retry": False,  # 길기만 한 건 재시도 불필요
            }
        )
        score -= 0.10

    # 3) 하우스맨 브랜드 언급
    if REQUIRED_BRAND not in content:
        issues.append(
            {
                "type": "missing_brand",
                "message": "하우스맨 언급 없음 (draft 저장 권장)",
                "retry": False,
            }
        )
        score -= 0.20

    # 4) 금지어
    for word in BANNED_WORDS:
        if word in content:
            issues.append(
                {
                    "type": "banned_word",
                    "message": f"금지어: {word!r}",
                    "retry": False,
                }
            )
            score -= 0.15

    # 5) 제목 (H1) 존재
    if not re.search(r"^#\s+.+$", content, re.MULTILINE):
        issues.append(
            {
                "type": "missing_h1",
                "message": "마크다운 H1 제목 없음",
                "retry": True,
            }
        )
        score -= 0.10

    return ValidationResult(
        valid=len(issues) == 0,
        score=max(0.0, round(score, 2)),
        issues=issues,
        char_count=char_count,
        korean_ratio=round(korean_ratio, 3),
    )
