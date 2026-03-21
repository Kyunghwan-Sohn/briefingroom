with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

old = '''    payload = {
        "title":      item["title"],
        "content":    content_html,
        "status":     "publish",
        "categories": cat_ids,
        "tags":       tag_ids,
    }'''

new = '''    payload = {
        "title":      item["title"],
        "content":    content_html,
        "status":     "publish",
        "categories": cat_ids,
        "tags":       tag_ids,
        "date":       f"{item['date']}T09:00:00",
    }'''

if old in content:
    content = content.replace(old, new, 1)
    print('완료')
else:
    print('패턴 미발견')

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.write(content)
