import requests
r = requests.get('https://hotclipfolio.com', timeout=10)
with open('current.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
print(f'완료: {len(r.text)}')
