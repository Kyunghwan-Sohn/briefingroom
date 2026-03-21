with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

old = '''def extract_hwp(path):
    """HWP(OLE2) / HWPX(ZIP) 텍스트 추출"""
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        # HWPX — ZIP 기반
        if magic[:2] == b"PK":'''

new = '''def extract_hwp(path):
    """HWP(OLE2) / HWPX(ZIP) 텍스트 추출"""
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        # HTML 응답 감지 (다운로드 실패)
        if magic[:4] in (b"<!DO", b"<htm", b"<HTM", b"<HTM") or magic[:1] == b"<":
            print(f"    [스킵] HTML 응답")
            return ""
        # HWPX — ZIP 기반
        if magic[:2] == b"PK":'''

if old in content:
    content = content.replace(old, new, 1)
    print('완료')
else:
    print('패턴 미발견')

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.write(content)
