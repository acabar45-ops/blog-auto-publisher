"""블로그 글 생성 테스트 스크립트.

WordPress·Google Sheets 연동 없이 Claude API로 블로그 글 1편만 생성하고
터미널에 출력 + Markdown 파일로 저장.

사용 시점:
- ANTHROPIC_API_KEY만 있고 WP 세팅 전
- 프롬프트 튜닝하면서 결과물 빠르게 확인
- CI에서 간단한 API 호출 테스트

사용법:
    cd blog-auto-publisher
    python scripts/test-generate.py "강남 단기임대 수익률 계산법"
    python scripts/test-generate.py "임대료 미납 대응 5단계" --category "건물주 실무 가이드"
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# src/ import 가능하게
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.claude_client import HousemanBlogGenerator
from src.validator import validate_post


def main() -> int:
    parser = argparse.ArgumentParser(description="블로그 글 1편 생성 + 검증 테스트")
    parser.add_argument("keyword", help="메인 키워드 (예: '단기임대 수익률')")
    parser.add_argument(
        "--category",
        default="건물주 실무 가이드",
        choices=[
            "건물주 실무 가이드",
            "단기임대 전문",
            "상업 건물 관리",
            "하우스맨 케이스",
            "하우스맨 SaaS 가이드",
        ],
    )
    parser.add_argument("--sub", default="", help="보조 키워드 (쉼표 구분)")
    parser.add_argument(
        "--output",
        default=None,
        help="출력 파일 경로 (기본: scripts/output/YYYY-MM-DD_keyword.md)",
    )
    args = parser.parse_args()

    print(f"🎯 키워드: {args.keyword}")
    print(f"📁 카테고리: {args.category}")
    if args.sub:
        print(f"🏷️  보조: {args.sub}")
    print("─" * 60)
    print("⚙️  Claude API 호출 중... (10~20초)")

    generator = HousemanBlogGenerator()
    post = generator.generate_post(
        keyword=args.keyword,
        category=args.category,
        sub_keywords=args.sub,
    )

    print(f"\n✅ 생성 완료 ({post['char_count']}자, {post['cost_krw']}원)")
    print(f"   • 입력 토큰: {post['tokens']['input']:,}")
    print(f"   • 출력 토큰: {post['tokens']['output']:,}")
    print(f"   • 캐시 읽기: {post['tokens']['cache_read']:,}")
    print(f"   • 캐시 작성: {post['tokens']['cache_created']:,}")

    # 검증
    validation = validate_post(post["content"])
    print(f"\n🔍 검증 점수: {validation.score}")
    print(f"   • 한국어 비율: {validation.korean_ratio:.1%}")
    print(f"   • 글자 수: {validation.char_count}")
    if validation.issues:
        print(f"   ⚠️ 이슈 {len(validation.issues)}건:")
        for issue in validation.issues:
            print(f"      - {issue['type']}: {issue['message']}")
    else:
        print(f"   ✅ 이슈 없음")

    # 파일 저장
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    if args.output:
        output_path = Path(args.output)
    else:
        safe_name = args.keyword.replace(" ", "-").replace("/", "-")[:40]
        output_path = output_dir / f"{datetime.now():%Y-%m-%d}_{safe_name}.md"

    output_path.write_text(
        f"""---
title: {post['title']}
category: {args.category}
keyword: {args.keyword}
generated_at: {post['generated_at']}
cost_krw: {post['cost_krw']}
validation_score: {validation.score}
---

{post['content']}
""",
        encoding="utf-8",
    )

    print(f"\n💾 저장됨: {output_path}")
    print("\n" + "─" * 60)
    print("🖨  본문 (처음 500자):")
    print(post["content"][:500])
    print("..." if len(post["content"]) > 500 else "")

    return 0 if validation.valid else 1


if __name__ == "__main__":
    sys.exit(main())
