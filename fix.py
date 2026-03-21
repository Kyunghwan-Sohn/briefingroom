content = open('briefing.py', encoding='utf-8').read()
old = 'else:\n    BASE_DIR = Path.home() / "Desktop" / "briefing"'
new = 'else:\n    BASE_DIR = Path(__file__).parent'
content = content.replace(old, new, 1)
open('briefing.py', 'w', encoding='utf-8').write(content)
print('완료')
