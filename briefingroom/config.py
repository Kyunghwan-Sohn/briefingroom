from pathlib import Path

API_KEY = "sk-abcd-48263410568dc65eac7c5f7290d6de506187af0a6aa1ad34"
API_URL = "https://abcllm-api.brut.bot/v1/chat/completions"
MODEL = "[MLX] Qwen3-4B"
MAX_TEXT = 6000
TIMEOUT = 20
DELAY = 1.5

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = BASE_DIR / "pdfs"
TXT_DIR = BASE_DIR / "texts"
DATA_DIR = BASE_DIR / "data"

for _dir in (PDF_DIR, TXT_DIR, DATA_DIR):
    _dir.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

SYSTEM_PROMPT = """당신은 대한민국 정부 정책 전문 분석가입니다.
보도자료 원문을 받으면 반드시 아래 형식으로만 답하세요.

요약: (3문장. 핵심 정책 내용 / 주요 수치·시행 시점 / 대상·효과 순서로)
키워드: 키워드1, 키워드2, 키워드3, 키워드4, 키워드5"""

CAT_MAP = {
    "금융위원회": "금융경제", "금융감독원": "금융경제",
    "기획재정부": "금융경제", "한국은행": "금융경제",
    "산업통상자원부": "금융경제", "공정거래위원회": "금융경제",
    "보건복지부": "사회복지", "교육부": "사회복지",
    "고용노동부": "사회복지", "성평등가족부": "사회복지",
    "국민권익위원회": "사회복지", "국가보훈부": "사회복지",
    "법무부": "사회복지",
    "과학기술정보통신부": "산업기술", "국토교통부": "산업기술",
    "해양수산부": "산업기술", "농림축산식품부": "산업기술",
    "중소벤처기업부": "산업기술", "환경부": "산업기술",
    "개인정보보호위원회": "산업기술", "문화체육관광부": "산업기술",
    "외교부": "외교안보", "통일부": "외교안보", "국방부": "외교안보",
    "행정안전부": "행정법제", "법제처": "행정법제", "인사혁신처": "행정법제",
}
