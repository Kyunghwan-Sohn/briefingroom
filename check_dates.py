import requests
WP_URL = 'https://hotclipfolio.com'
AUTH   = ('hotclipfolio', 'qSUw w4xA ELSm w6z9 6zIU U8G8')
r = requests.get(f'{WP_URL}/wp-json/wp/v2/posts',
    params={'per_page':5, '_fields':'id,title,date'},
    auth=AUTH, timeout=10)
for p in r.json():
    print(f'#{p["id"]} | {p["date"]} | {p["title"]["rendered"][:40]}')
