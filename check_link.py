import requests
r = requests.get('https://hotclipfolio.com', timeout=10)
idx = r.text.find('d-wp')
print(r.text[idx:idx+200])
