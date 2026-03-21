import sys
sys.path.insert(0, '.')
from briefing import wp_post, make_item

test_item = {
    'source': '금융감독원',
    'title': '테스트 포스팅',
    'url': 'https://www.fss.or.kr',
    'date': '2026-03-20',
    'files': [],
    'text': '테스트',
    'summary': '요약: 테스트 요약입니다\n키워드: 테스트, 금융',
}
result = wp_post(test_item)
print(f'결과: {result}')
