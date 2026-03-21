with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

idx = content.find('from datetime import timedelta')
print(repr(content[idx:idx+400]))
