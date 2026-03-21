with open('index.php', encoding='utf-8') as f:
    content = f.read()

old = '''<?php
if (is_page()) {
     = get_post();
    echo ->post_content;
    exit;
}
?>'''

new = '''<?php
if (is_page()) {
     = get_post();
    echo ->post_content;
    exit;
}
?>'''

if old in content:
    content = content.replace(old, new, 1)
    print('수정 완료')
else:
    print('패턴 미발견')

with open('index.php', 'w', encoding='utf-8') as f:
    f.write(content)
