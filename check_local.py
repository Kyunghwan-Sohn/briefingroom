with open('index.php', encoding='utf-8') as f:
    content = f.read()
print('mob-date-nav:', 'mob-date-nav' in content)
print('mob-cat-tabs:', 'mob-cat-tabs' in content)
print('파일 크기:', len(content))
