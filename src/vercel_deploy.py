"""Vercel 재빌드 훅 트리거."""
from __future__ import annotations

import requests

from src.config import VERCEL_DEPLOY_HOOK


def trigger_rebuild() -> bool:
    """발행 후 Vercel에 새 배포 트리거. 2분 내 사이트 반영."""
    if not VERCEL_DEPLOY_HOOK:
        print("[Vercel·SKIP] VERCEL_DEPLOY_HOOK 미설정 — 재빌드 건너뜀")
        return False
    try:
        response = requests.post(VERCEL_DEPLOY_HOOK, timeout=10)
        response.raise_for_status()
        print(f"[Vercel·OK] 재빌드 트리거: {response.status_code}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[Vercel·ERROR] {exc}")
        return False
