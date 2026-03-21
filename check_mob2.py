import requests
r = requests.get('https://hotclipfolio.com', timeout=10)
content = r.text
print('mob-date-nav:', 'mob-date-nav' in content)
print('mob-cat-tabs:', 'mob-cat-tabs' in content)
print('mobile-date-nav:', 'mobile-date-nav' in content)
print('파일크기:', len(content))
