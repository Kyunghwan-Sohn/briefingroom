import requests
import time

CRAWLERS = {
    '금융위원회': 'https://www.fsc.go.kr/rss/rss.jsp?cate=PRESS',
    '금융감독원': 'https://www.fss.or.kr/fss/kr/rss.jsp',
    '기획재정부': 'https://www.moef.go.kr/rss/rss.jsp',
    '교육부': 'https://www.moe.go.kr/rss/rss.jsp',
    '국토교통부': 'https://www.molit.go.kr/rss/rss.jsp',
    '보건복지부': 'https://www.mohw.go.kr/rss/rss.jsp',
    '행정안전부': 'https://www.mois.go.kr/rss/rss.jsp',
    '환경부': 'https://www.me.go.kr/rss/rss.jsp',
    '고용노동부': 'https://www.moel.go.kr/rss/rss.jsp',
    '산업통상자원부': 'https://www.motie.go.kr/rss/rss.jsp',
    '외교부': 'https://www.mofa.go.kr/rss/rss.jsp',
    '국방부': 'https://www.mnd.go.kr/rss/rss.jsp',
    '과학기술정보통신부': 'https://www.msit.go.kr/rss/rss.jsp',
    '농림축산식품부': 'https://www.mafra.go.kr/rss/rss.jsp',
    '해양수산부': 'https://www.mof.go.kr/rss/rss.jsp',
    '중소벤처기업부': 'https://www.mss.go.kr/rss/rss.jsp',
    '문화체육관광부': 'https://www.mcst.go.kr/rss/rss.jsp',
    '법무부': 'https://www.moj.go.kr/rss/rss.jsp',
    '통일부': 'https://www.unikorea.go.kr/rss/rss.jsp',
    '한국은행': 'https://www.bok.or.kr/portal/cmmn/rss/selectRssList.do',
}

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

for name, url in CRAWLERS.items():
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200 and ('<rss' in r.text or '<feed' in r.text or '<?xml' in r.text):
            print(f'✅ {name}: {url}')
        else:
            print(f'❌ {name}: {r.status_code}')
    except Exception as e:
        print(f'⚠ {name}: {str(e)[:50]}')
    time.sleep(1)
