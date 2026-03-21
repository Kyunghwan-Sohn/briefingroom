import os, shutil

src = r'C:\Users\sony0125\briefingroom'
review = r'C:\Users\sony0125\briefingroom_review'

# briefing.py, requirements.txt, workflow 복사
files_to_copy = [
    ('briefing.py', 'briefing.py'),
    ('requirements.txt', 'requirements.txt'),
    ('.github/workflows/briefing.yml', '.github/workflows/briefing.yml'),
]

for src_rel, dst_rel in files_to_copy:
    src_path = os.path.join(review, src_rel)
    dst_path = os.path.join(src, dst_rel)
    if os.path.exists(src_path):
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy2(src_path, dst_path)
        print(f'복사: {src_rel}')
    else:
        print(f'없음: {src_rel}')

# briefingroom 패키지 복사
pkg_src = os.path.join(review, 'briefingroom')
pkg_dst = os.path.join(src, 'briefingroom')
if os.path.exists(pkg_dst):
    shutil.rmtree(pkg_dst)
shutil.copytree(pkg_src, pkg_dst)
print('briefingroom 패키지 복사 완료')

# data 폴더 생성
os.makedirs(os.path.join(src, 'data'), exist_ok=True)

# .gitignore 생성
gitignore = os.path.join(src, '.gitignore')
with open(gitignore, 'w') as f:
    f.write('venv/\n__pycache__/\n*.pyc\npdfs/\ntexts/\n*.pdf\n*.hwp\n*.hwpx\n')
print('.gitignore 생성 완료')
print('배포 완료')
