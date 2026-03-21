with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

# wp_post 함수 전체 출력
start = content.find('def wp_post(')
end = content.find('\ndef main()')
print(content[start:end])
