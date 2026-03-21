with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

old = '    [스킵] HTML 응답\n    텍스트 저장'
# process_item에서 hwpx 처리 부분 찾기
idx = content.find('HWP 추출 오류: not an OLE2')
print(repr(content[max(0,idx-200):idx+100]))
