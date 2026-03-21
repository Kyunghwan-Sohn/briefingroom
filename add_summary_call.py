with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

old = '''    print(f"  \u2705 WordPress \ud3ec\uc2a4\ud305 \uc644\ub8cc: {wp_count}\uac74")'''
new = '''    print(f"  \u2705 WordPress \ud3ec\uc2a4\ud305 \uc644\ub8cc: {wp_count}\uac74")

    # \uc77c\ubcc4/\uc8fc\uac04 \uc885\ud569 \uc694\uc57d \ud3ec\uc2a4\ud305
    print(f"\\n{chr(8212)*60}")
    print("[\uc885\ud569 \uc694\uc57d \ud3ec\uc2a4\ud305 \uc911...]")
    wp_post_summary(all_items, target, is_weekly)'''

if old in content:
    content = content.replace(old, new, 1)
    print('\u2705 \uc644\ub8cc')
else:
    print('\u274c \ud328\ud134 \ubbf8\ubc1c\uacac')
    idx = content.find('WordPress \ud3ec\uc2a4\ud305 \uc644\ub8cc')
    print(repr(content[idx:idx+100]))

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.write(content)
