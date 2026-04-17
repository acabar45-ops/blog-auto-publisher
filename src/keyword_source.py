"""Google Sheets 기반 키워드 큐.

시트 포맷 (첫 행은 헤더):
| date | category | keyword | sub_keywords | status | url | created_at |

- status 값: "대기" / "발행중" / "완료" / "실패"
- fetch_next_pending() 은 가장 오래된 "대기" 행을 "발행중"으로 락 후 반환
- mark_completed() / mark_failed() 로 상태 갱신
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict

import gspread

from src.config import (
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_SHEET_NAME,
    GOOGLE_SHEET_WORKSHEET,
)


class KeywordRow(TypedDict):
    row_index: int  # 실제 시트 행 번호 (1-based, 헤더 포함)
    date: str
    category: str
    keyword: str
    sub_keywords: str
    status: str


class KeywordSource:
    def __init__(self) -> None:
        if not GOOGLE_SHEET_NAME:
            raise RuntimeError("GOOGLE_SHEET_NAME 환경변수가 필요합니다.")
        self.gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_PATH)
        self.sheet = self.gc.open(GOOGLE_SHEET_NAME).worksheet(GOOGLE_SHEET_WORKSHEET)
        self._header_col_cache: dict[str, int] | None = None

    def _header_col(self, name: str) -> int:
        """컬럼 이름 → 1-based 인덱스."""
        if self._header_col_cache is None:
            headers = self.sheet.row_values(1)
            self._header_col_cache = {h: i + 1 for i, h in enumerate(headers)}
        return self._header_col_cache[name]

    def fetch_next_pending(self) -> KeywordRow | None:
        """가장 오래된 '대기' 행을 '발행중'으로 락 후 반환."""
        records = self.sheet.get_all_records()
        for i, row in enumerate(records, start=2):  # row 1은 헤더
            if row.get("status") == "대기":
                # 락 — 동시 실행 방지
                self.sheet.update_cell(i, self._header_col("status"), "발행중")
                return KeywordRow(
                    row_index=i,
                    date=str(row.get("date", "")),
                    category=str(row.get("category", "")),
                    keyword=str(row.get("keyword", "")),
                    sub_keywords=str(row.get("sub_keywords", "")),
                    status="발행중",
                )
        return None

    def mark_completed(self, row_index: int, url: str) -> None:
        """발행 완료 처리."""
        now = datetime.now(timezone.utc).isoformat()
        self.sheet.update_cell(row_index, self._header_col("status"), "완료")
        self.sheet.update_cell(row_index, self._header_col("url"), url)
        self.sheet.update_cell(row_index, self._header_col("created_at"), now)

    def mark_failed(self, row_index: int, reason: str = "") -> None:
        """발행 실패 처리 (다음 날 재시도 가능하도록 '대기'로 복구할지는 선택)."""
        self.sheet.update_cell(row_index, self._header_col("status"), f"실패: {reason}"[:50])
