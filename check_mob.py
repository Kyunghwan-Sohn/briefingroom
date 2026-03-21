import requests
r = requests.get('https://hotclipfolio.com', timeout=10)
content = r.text
print('mob-date-nav CSS:', 'mob-date-nav' in content)
print('mob-cat-tabs:', 'mob-cat-tabs' in content)
print('mob-date-nav HTML:', 'mob-date-main' in content)
print('@media 768 count:', content.count('max-width:768px'))
# @media 내용 확인
idx = content.find('@media(max-width:768px)')
print(content[idx:idx+300])
