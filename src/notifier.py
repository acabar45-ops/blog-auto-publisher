"""솔라피 알림 — 카톡 알림톡 실패 시 SMS 폴백 자동.

발행 성공/실패를 사장님 휴대폰에 알림. SaaS의 솔라피 모듈과 동일 구조.
"""
from __future__ import annotations

from typing import Literal

from solapi import SolapiMessageService

from src.config import (
    NOTIFY_PHONE,
    SOLAPI_API_KEY,
    SOLAPI_API_SECRET,
    SOLAPI_SENDER,
)


class Notifier:
    def __init__(self) -> None:
        if not (SOLAPI_API_KEY and SOLAPI_API_SECRET and SOLAPI_SENDER and NOTIFY_PHONE):
            self.enabled = False
            self.service = None
        else:
            self.enabled = True
            self.service = SolapiMessageService(
                api_key=SOLAPI_API_KEY,
                api_secret=SOLAPI_API_SECRET,
            )

    def notify(
        self,
        text: str,
        kind: Literal["success", "failure"] = "success",
    ) -> dict | None:
        """메시지 발송. service 미설정 시 콘솔 출력만."""
        prefix = "✅" if kind == "success" else "⚠️"
        body = f"{prefix} [하우스맨 블로그]\n{text}"

        if not self.enabled or not self.service:
            print(f"[Notifier·DRY] {body}")
            return None

        try:
            return self.service.send(
                {
                    "to": NOTIFY_PHONE,
                    "from": SOLAPI_SENDER,
                    "text": body,
                }
            )
        except Exception as exc:  # noqa: BLE001 — 알림 실패는 전체를 막으면 안 됨
            print(f"[Notifier·ERROR] {exc}")
            return None
