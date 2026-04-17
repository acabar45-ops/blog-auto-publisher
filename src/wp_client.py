"""WordPress REST API 클라이언트 — Application Password 인증.

포스트 발행만 책임. 이미지 업로드·Featured Image는 선택.
"""
from __future__ import annotations

from typing import Literal

import requests
from requests.auth import HTTPBasicAuth

from src.config import CATEGORY_ID_MAP, WP_APP_PW, WP_URL, WP_USER


class WordPressClient:
    def __init__(self) -> None:
        if not (WP_URL and WP_USER and WP_APP_PW):
            raise RuntimeError("WP_URL / WP_USER / WP_APP_PW 환경변수가 필요합니다.")
        self.base_url = WP_URL.rstrip("/")
        self.auth = HTTPBasicAuth(WP_USER, WP_APP_PW)

    def create_post(
        self,
        title: str,
        content: str,
        category: str,
        status: Literal["publish", "draft", "future"] = "publish",
        tags: list[int] | None = None,
        featured_media: int | None = None,
        seo_meta: dict | None = None,
    ) -> dict:
        """블로그 포스트 발행.

        Args:
            title: 포스트 제목
            content: 본문 (마크다운 또는 HTML)
            category: CATEGORY_ID_MAP의 키 (한국어 카테고리명)
            status: publish / draft / future
            tags: 태그 ID 리스트
            featured_media: Featured 이미지 media ID
            seo_meta: Yoast/Rank Math 메타 필드

        Returns:
            WP 응답 JSON (id, link, status 등 포함)
        """
        category_id = CATEGORY_ID_MAP.get(category)
        if not category_id:
            raise ValueError(
                f"알 수 없는 카테고리: {category!r}. "
                f"config.py의 CATEGORY_ID_MAP에 추가 필요."
            )

        payload: dict = {
            "title": title,
            "content": content,
            "status": status,
            "categories": [category_id],
        }
        if tags:
            payload["tags"] = tags
        if featured_media:
            payload["featured_media"] = featured_media
        if seo_meta:
            payload["meta"] = seo_meta

        response = requests.post(
            f"{self.base_url}/posts",
            json=payload,
            auth=self.auth,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def upload_media(self, file_path: str, mime_type: str = "image/jpeg") -> dict:
        """Featured 이미지 업로드.

        Args:
            file_path: 로컬 이미지 파일 경로
            mime_type: MIME 타입

        Returns:
            WP 응답 JSON (id 포함 — create_post의 featured_media에 사용)
        """
        filename = file_path.split("/")[-1].split("\\")[-1]
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/media",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": mime_type,
                },
                data=f,
                auth=self.auth,
                timeout=60,
            )
        response.raise_for_status()
        return response.json()
