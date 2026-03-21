import requests

WP_URL = 'https://hotclipfolio.com'
AUTH   = ('hotclipfolio', 'qSUw w4xA ELSm w6z9 6zIU U8G8')

with open('index.php', encoding='utf-8') as f:
    content = f.read()

# WordPress 테마 파일 편집 API
r = requests.put(
    f'{WP_URL}/wp-json/wp/v2/themes/briefingroom-theme/files',
    json={'file': 'index.php', 'content': content},
    auth=AUTH, timeout=30
)
print(f'상태: {r.status_code}')
print(r.text[:200])
