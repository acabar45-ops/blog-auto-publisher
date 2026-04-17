"""매일 1편 블로그 발행 엔트리 포인트.

실행 순서:
1. Google Sheet에서 오늘 발행할 키워드 1개 fetch + 락
2. Claude API로 글 생성
3. 검증 (길이·한국어·금지어)
4. 통과 → WP publish / 실패 → WP draft + 알림
5. Vercel 재빌드 트리거
6. 사장님 알림 (성공/실패)
"""
from __future__ import annotations

import sys
import traceback

from src.claude_client import HousemanBlogGenerator
from src.config import DRY_RUN
from src.keyword_source import KeywordSource
from src.notifier import Notifier
from src.validator import validate_post
from src.vercel_deploy import trigger_rebuild
from src.wp_client import WordPressClient


def run(dry_run: bool = False) -> int:
    """반환값: 0=성공, 1=실패 (GitHub Actions 종료 코드)."""
    notifier = Notifier()

    # 1. 키워드 fetch
    try:
        source = KeywordSource()
        keyword_row = source.fetch_next_pending()
    except Exception as exc:  # noqa: BLE001
        notifier.notify(f"키워드 fetch 실패: {exc}", kind="failure")
        traceback.print_exc()
        return 1

    if not keyword_row:
        print("[SKIP] 발행 대기 중인 키워드 없음")
        return 0

    keyword = keyword_row["keyword"]
    category = keyword_row["category"] or "건물주 실무 가이드"
    sub_keywords = keyword_row["sub_keywords"]
    print(f"[INFO] 발행 시작: {keyword} / {category}")

    # 2. 글 생성
    try:
        generator = HousemanBlogGenerator()
        post = generator.generate_post(
            keyword=keyword,
            category=category,
            sub_keywords=sub_keywords,
        )
        print(
            f"[OK] 생성 완료: {post['char_count']}자 / "
            f"비용 {post['cost_krw']}원 / 캐시읽기 {post['tokens']['cache_read']}토큰"
        )
    except Exception as exc:  # noqa: BLE001
        source.mark_failed(keyword_row["row_index"], f"Claude: {exc}")
        notifier.notify(f"[{keyword}] Claude 생성 실패: {exc}", kind="failure")
        traceback.print_exc()
        return 1

    # 3. 검증
    validation = validate_post(post["content"])
    print(f"[VALIDATE] 점수 {validation.score} / 이슈 {len(validation.issues)}개")
    for issue in validation.issues:
        print(f"  ⚠️ {issue['type']}: {issue['message']}")

    # 4. 발행 또는 draft
    status = "publish" if validation.valid else "draft"

    if dry_run or DRY_RUN:
        print(f"[DRY_RUN] 실제 WP 발행 생략. status={status}")
        print(f"--- 제목 ---\n{post['title']}\n--- 본문 first 300 ---\n{post['content'][:300]}")
        return 0

    try:
        wp = WordPressClient()
        wp_response = wp.create_post(
            title=post["title"],
            content=post["content"],
            category=category,
            status=status,
        )
        post_url = wp_response.get("link", "")
        print(f"[WP·{status.upper()}] {post_url}")
    except Exception as exc:  # noqa: BLE001
        source.mark_failed(keyword_row["row_index"], f"WP: {exc}")
        notifier.notify(f"[{keyword}] WP 발행 실패: {exc}", kind="failure")
        traceback.print_exc()
        return 1

    # 5. 상태 갱신
    if status == "publish":
        source.mark_completed(keyword_row["row_index"], post_url)
    else:
        source.mark_failed(
            keyword_row["row_index"],
            f"검증 실패({validation.score}) draft 저장",
        )

    # 6. Vercel 재빌드
    if status == "publish":
        trigger_rebuild()

    # 7. 사장님 알림
    if status == "publish":
        notifier.notify(
            f"[{category}]\n{post['title']}\n{post_url}\n"
            f"검증 {validation.score} · {post['char_count']}자 · {post['cost_krw']}원",
            kind="success",
        )
    else:
        notifier.notify(
            f"[{category}]\n{post['title']}\n"
            f"검증 실패 {validation.score} → draft 저장\n"
            f"이슈: {', '.join(i['type'] for i in validation.issues)}",
            kind="failure",
        )

    return 0 if status == "publish" else 1


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    sys.exit(run(dry_run=dry))
