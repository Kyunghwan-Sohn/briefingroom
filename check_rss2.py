import requests
import time

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 실제 RSS URL 후보들
candidates = {
    '금융위원회': [
        'https://www.fsc.go.kr/rss/pressRelease.xml',
        'https://www.fsc.go.kr/no010101/rss',
        'https://www.fsc.go.kr/rss.do',
    ],
    '행정안전부': [
        'https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardList.do?bbsId=BBSMSTR_000000000008&rss=Y',
        'https://www.mois.go.kr/rss/pressRelease.xml',
    ],
    '환경부': [
        'https://www.me.go.kr/home/web/rss/doRss.do?menuId=10259',
        'https://www.me.go.kr/rss/pressRelease.xml',
    ],
    '고용노동부': [
        'https://www.moel.go.kr/news/enews/report/rss.do',
        'https://www.moel.go.kr/rss/pressRelease.xml',
    ],
    '한국은행': [
        'https://www.bok.or.kr/portal/cmmn/rss/selectRssList.do?menuNo=200560',
        'https://www.bok.or.kr/rss/press.xml',
    ],
}

for name, urls in candidates.items():
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200 and ('<rss' in r.text or '<feed' in r.text):
                print(f'✅ {name}: {url}')
                break
            else:
                print(f'  ❌ {r.status_code}: {url}')
        except Exception as e:
            print(f'  ⚠ {url[:50]}: {str(e)[:40]}')
        time.sleep(1)
