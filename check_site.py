import requests
WP_URL = 'https://hotclipfolio.com'
AUTH   = ('hotclipfolio', 'qSUw w4xA ELSm w6z9 6zIU U8G8')
r = requests.get(WP_URL, timeout=10)
print(f'상태: {r.status_code}')
print(r.text[:500])
