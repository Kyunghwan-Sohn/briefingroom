with open('index.php', encoding='utf-8') as f:
    content = f.read()

dollar = chr(36)
old = 'if (is_page()) {\n     = get_post();\n    echo ->post_content;\n    exit;\n}'
new = f'if (is_page()) {{\n    {dollar}page = get_post();\n    echo {dollar}page->post_content;\n    exit;\n}}'

if old in content:
    content = content.replace(old, new, 1)
    print('수정 완료')
else:
    print('패턴 미발견')
    idx = content.find('is_page')
    print(repr(content[idx:idx+100]))

with open('index.php', 'w', encoding='utf-8') as f:
    f.write(content)
