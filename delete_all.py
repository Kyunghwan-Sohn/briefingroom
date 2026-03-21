import requests
WP_URL = 'https://hotclipfolio.com'
AUTH   = ('hotclipfolio', 'qSUw w4xA ELSm w6z9 6zIU U8G8')

# 전체 포스트 가져오기
r = requests.get(f'{WP_URL}/wp-json/wp/v2/posts',
    params={'per_page': 100, '_fields': 'id,title'}, auth=AUTH, timeout=10)
posts = r.json()
print(f'총 {len(posts)}건 삭제 예정')

for p in posts:
    d = requests.delete(f'{WP_URL}/wp-json/wp/v2/posts/{p["id"]}',
        params={'force': True}, auth=AUTH, timeout=10)
    print(f'삭제: #{p["id"]} {d.status_code} {p["title"]["rendered"][:30]}')

print('완료')
