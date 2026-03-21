with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

# HWPX 추출 함수 수정 - ZIP 기반으로 처리
old = '''def extract_hwp(path):'''

new = '''def extract_hwpx(path):
    """HWPX(ZIP 기반) 텍스트 추출"""
    import zipfile, xml.etree.ElementTree as ET
    try:
        with zipfile.ZipFile(path, 'r') as z:
            names = z.namelist()
            texts = []
            for name in names:
                if 'Contents/section' in name and name.endswith('.xml'):
                    with z.open(name) as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        ns = {'hp': 'http://www.hancom.co.kr/hwpml/2012/paragraph'}
                        for t in root.iter():
                            if t.text and t.text.strip():
                                texts.append(t.text.strip())
            return '\\n'.join(texts)
    except Exception as e:
        return ''


def extract_hwp(path):'''

if old in content:
    content = content.replace(old, new, 1)
    print('HWPX 함수 추가 완료')
else:
    print('패턴 미발견')

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.write(content)
