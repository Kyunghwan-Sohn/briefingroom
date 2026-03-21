import requests
r = requests.get('https://hotclipfolio.com', timeout=10)
content = r.text
# openDetail 함수 확인
idx = content.find('function openDetail')
print(content[idx:idx+400])
