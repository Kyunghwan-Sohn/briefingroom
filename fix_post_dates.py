import requests
WP_URL = 'https://hotclipfolio.com'
AUTH   = ('hotclipfolio', 'qSUw w4xA ELSm w6z9 6zIU U8G8')

# 3월 21일로 저장된 포스팅을 3월 20일로 수정
r = requests.get(f'{WP_URL}/wp-json/wp/v2/posts',
    params={'per_page':100, '_fields':'id,title,date', 'after':'2026-03-21T00:00:00', 'before':'2026-03-21T23:59:59'},
    auth=AUTH, timeout=10)
posts = r.json()
print(f'총 {len(posts)}건 수정 예정')
for p in posts:
    r2 = requests.post(f'{WP_URL}/wp-json/wp/v2/posts/{p["id"]}',
        json={'date': '2026-03-20T09:00:00'},
        auth=AUTH, timeout=10)
    print(f'#{p["id"]} {r2.status_code} {p["title"]["rendered"][:30]}')
