with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

# CAT_MAP부터 main 시작 전까지 전체 출력
start = content.find('\nCAT_MAP = {')
end = content.find('\ndef main():')
print(content[start:end])
