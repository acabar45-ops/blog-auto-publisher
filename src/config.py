"""환경 변수 로드."""
import os
from dotenv import load_dotenv

load_dotenv()

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# WordPress
WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_APP_PW = os.getenv("WP_APP_PW")

# Google Sheets
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
GOOGLE_SHEET_WORKSHEET = os.getenv("GOOGLE_SHEET_WORKSHEET", "keywords")

# Vercel
VERCEL_DEPLOY_HOOK = os.getenv("VERCEL_DEPLOY_HOOK")

# 솔라피
SOLAPI_API_KEY = os.getenv("SOLAPI_API_KEY")
SOLAPI_API_SECRET = os.getenv("SOLAPI_API_SECRET")
SOLAPI_SENDER = os.getenv("SOLAPI_SENDER")
NOTIFY_PHONE = os.getenv("NOTIFY_PHONE")

# 플래그
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# 하우스맨 카테고리 ID 매핑 (WP 카테고리 생성 후 값 업데이트 필요)
CATEGORY_ID_MAP = {
    "건물주 실무 가이드": 1,
    "단기임대 전문": 2,
    "상업 건물 관리": 3,
    "하우스맨 케이스": 4,
    "하우스맨 SaaS 가이드": 5,
}
