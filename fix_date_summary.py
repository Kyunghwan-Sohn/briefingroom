with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

old = '''    payload = {
        "title":      post_title,
        "content":    content_html,
        "status":     "publish",
        "categories": cat_ids,
    }'''

new = '''    payload = {
        "title":      post_title,
        "content":    content_html,
        "status":     "publish",
        "categories": cat_ids,
        "date":       f"{target.isoformat()}T08:00:00",
    }'''

if old in content:
    content = content.replace(old, new, 1)
    print('완료')
else:
    print('패턴 미발견')

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.write(content)
