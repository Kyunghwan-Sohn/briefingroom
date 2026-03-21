with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

start = content.find('def extract_hwp(path):')
end = content.find('\ndef save_text', start)
print(content[start:end])
