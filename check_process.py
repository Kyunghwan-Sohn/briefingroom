with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

start = content.find('def process_item(item):')
end = content.find('\ndef summarize', start)
print(content[start:end])
