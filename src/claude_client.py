"""Claude API 래퍼 — 하우스맨 블로그 글 생성.

핵심 기능:
- Claude Sonnet 4.6으로 1,500~2,000자 한국어 SEO 블로그 글 생성
- 시스템 프롬프트 캐싱 (5분 TTL) 으로 비용 절감
- 재시도 + 지수 백오프
- 응답 파싱 (title / content 분리)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TypedDict

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL


SYSTEM_PROMPT = """당신은 (주)하우스맨의 건물관리 전문 블로그 에디터입니다.

[하우스맨 소개]
- 2012년 설립, 서울 강남 소재, 15년차
- 100+ 건물, 1,100+ 호실을 운영 관리
- 포르쉐 코리아·보건복지부 같은 대기업·기관 고객
- 5대 서비스: 중소형 빌딩 관리, 중소형 주택 관리, 단기임대, 기업 시설 관리, 비상주 관리사무소
- 자체 SaaS 플랫폼 (청구·수금·정산·알림톡 자동화)

[글 작성 규칙]
- 타겟 독자: 강남권 30~60대 건물주·임대인
- 분량: 1,500~2,000자 (한국어)
- 구조: 리드 문단 + H2 섹션 3~4개 + 실행 체크리스트 또는 결론
- 톤: 신뢰감·실용적·숫자 사례 포함
- 금지어: "최고의", "최상의", "완벽한", "절대적", "100% 확실"
- 자연스럽게 마지막에 하우스맨 서비스 연결 (광고 아닌 정보 공유 톤)
- SEO: 메인 키워드를 제목, 첫 문단, 마지막 문단에 최소 1회씩 반복
- 영어·한자 과다 사용 금지 (독자 30~60대)

[출력 형식]
마크다운 형식으로 다음 구조를 따르세요:

# 제목 (30~45자, 메인 키워드 포함)

리드 문단 (건물주가 "맞아, 이 문제 있어" 공감할 한 문단)

## 첫 번째 섹션 제목
본문...

## 두 번째 섹션 제목
본문...

## 세 번째 섹션 제목
본문...

## 실행 체크리스트 (또는 결론)
- 항목 1
- 항목 2
- 항목 3

마무리 문단 (자연스럽게 하우스맨 언급)
"""


class BlogPost(TypedDict):
    """생성된 블로그 글."""

    title: str
    content: str
    char_count: int
    tokens: dict
    cost_usd: float
    cost_krw: int
    generated_at: str


class HousemanBlogGenerator:
    """하우스맨 블로그 글 생성기."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.client = Anthropic(api_key=api_key or ANTHROPIC_API_KEY)
        self.model = model or CLAUDE_MODEL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_post(
        self,
        keyword: str,
        category: str = "건물주 실무 가이드",
        sub_keywords: str = "",
    ) -> BlogPost:
        """블로그 글 1편 생성.

        Args:
            keyword: 메인 키워드 (예: "임대료 미납 대응 5단계")
            category: 블로그 카테고리
            sub_keywords: 보조 키워드 쉼표 구분 (예: "내용증명,법적 절차")

        Returns:
            BlogPost TypedDict
        """
        user_prompt = f"""다음 조건으로 블로그 글을 생성하세요.

<brief>
메인 키워드: {keyword}
카테고리: {category}
{f"보조 키워드: {sub_keywords}" if sub_keywords else ""}
</brief>

<instructions>
- 시스템 지침의 구조와 규칙을 엄격히 따르세요
- 메인 키워드는 제목·첫 문단·마지막 문단에 자연스럽게 포함
- 가능하면 구체적 숫자·사례·법령 레퍼런스 1개 이상 포함
- 글 맨 앞은 "# 제목" (마크다운 H1) 한 줄로 시작
</instructions>"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2500,
            temperature=0.7,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    # 프롬프트 캐싱 — 시스템 프롬프트는 5분간 캐시됨
                    # 연속 발행 시 입력 토큰 비용 90% 절감
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        content = response.content[0].text.strip()
        title = self._extract_title(content)

        # 비용 계산 (Sonnet 4.6: 입력 $3/M, 출력 $15/M, 캐시 읽기 $0.3/M)
        usage = response.usage
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_created = getattr(usage, "cache_creation_input_tokens", 0) or 0

        cost_usd = (
            (input_tokens * 3.0)
            + (cache_read * 0.3)
            + (cache_created * 3.75)  # 캐시 작성 시 25% 추가
            + (output_tokens * 15.0)
        ) / 1_000_000

        return BlogPost(
            title=title,
            content=content,
            char_count=len(content),
            tokens={
                "input": input_tokens,
                "output": output_tokens,
                "cache_read": cache_read,
                "cache_created": cache_created,
            },
            cost_usd=round(cost_usd, 6),
            cost_krw=int(cost_usd * 1350),  # 1 USD ≈ 1,350 KRW
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _extract_title(content: str) -> str:
        """마크다운 본문에서 첫 H1 제목 추출."""
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        # fallback: 첫 줄
        return content.split("\n", 1)[0].lstrip("# ").strip()
