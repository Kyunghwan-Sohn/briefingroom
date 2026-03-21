# Crawlers

각 부처별로 1파일씩 분리되어 있습니다.

- 파일명은 부처 코드 기준입니다. 예: `fsc.py`, `moef.py`, `msit.py`
- 수동 실행 시 특정 부처만 다시 돌리려면 환경변수 `CRAWLER_SOURCES`를 사용합니다.

예시:
- `CRAWLER_SOURCES=fsc python briefing.py`
- `CRAWLER_SOURCES=금융위원회,기획재정부 python briefing.py`
- GitHub Actions 수동 실행에서 `sources` 입력
