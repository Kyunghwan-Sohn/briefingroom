with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

# 일별/주간 종합 요약 포스팅 함수 추가
new_func = '''
def wp_post_summary(all_items, target, is_weekly=False):
    """일별/주간 종합 요약 포스팅"""
    if not all_items:
        print("  요약 포스팅: 수집 건수 없음 스킵")
        return False

    from datetime import timedelta

    # 제목 설정
    if is_weekly:
        # 주차 계산
        week_num = (target.day - 1) // 7 + 1
        post_title = f"{target.year}년 {target.month}월 {week_num}주차 주간 보도자료"
        date_range = f"{(target - timedelta(days=4)).strftime('%Y.%m.%d')} ~ {target.strftime('%Y.%m.%d')}"
        period_label = f"주간 ({date_range})"
    else:
        post_title = f"{target.year}년 {target.month}월 {target.day}일 보도자료"
        period_label = target.strftime('%Y.%m.%d')

    # 중복 체크
    if wp_check_duplicate(post_title, target.isoformat()):
        return False

    # 부처별 그룹핑
    from collections import defaultdict
    by_source = defaultdict(list)
    for item in all_items:
        if item.get('summary') and not item['summary'].startswith('['):
            by_source[item['source']].append(item)

    if not by_source:
        print("  요약 포스팅: 요약된 항목 없음 스킵")
        return False

    # 분야별 색상
    CAT_COLORS = {
        '금융경제': '#2f54eb', '사회복지': '#16a34a',
        '산업기술': '#d97706', '외교안보': '#dc2626', '행정법제': '#7c3aed'
    }

    # HTML 생성
    rows = ""
    for source, items in sorted(by_source.items()):
        cat = CAT_MAP.get(source, '행정법제')
        color = CAT_COLORS.get(cat, '#2f54eb')
        for item in items:
            summary_line = ""
            for line in item["summary"].split("\\n"):
                if line.startswith("요약:"):
                    summary_line = line.replace("요약:", "").strip()
                    break
            if not summary_line:
                continue
            rows += f"""
<tr>
  <td style="padding:10px 14px;border-bottom:1px solid #e0ddd7;white-space:nowrap;vertical-align:top">
    <span style="background:{color}18;color:{color};font-size:11px;padding:2px 8px;border-radius:4px;font-family:monospace;font-weight:600">{source}</span>
  </td>
  <td style="padding:10px 14px;border-bottom:1px solid #e0ddd7;font-size:13px;line-height:1.6;color:#4a4844">
    <a href="{item['url']}" style="color:#1c1b18;text-decoration:none;font-weight:500">{item['title']}</a><br>
    <span style="color:#96938c;font-size:12px">{summary_line[:120]}{'...' if len(summary_line)>120 else ''}</span>
  </td>
</tr>"""

    total = sum(len(v) for v in by_source.values())
    content_html = f"""
<div class="briefing-post" style="font-family:'Pretendard',sans-serif">
  <div style="background:#1c1b18;padding:20px 24px;border-radius:12px 12px 0 0">
    <div style="font-family:Georgia,serif;font-size:22px;font-weight:700;color:#fff;letter-spacing:-0.5px">{post_title}</div>
    <div style="margin-top:8px;display:flex;gap:12px;align-items:center">
      <span style="background:#2f54eb;color:#fff;font-size:11px;padding:3px 12px;border-radius:20px;font-family:monospace">총 {total}건</span>
      <span style="color:rgba(255,255,255,0.5);font-size:11px;font-family:monospace">{period_label} · {len(by_source)}개 부처</span>
    </div>
  </div>
  <div style="background:#f5f4f0;padding:0">
    <table style="width:100%;border-collapse:collapse;background:#fff">
      <thead>
        <tr style="background:#f5f4f0">
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#96938c;font-family:monospace;font-weight:500;border-bottom:2px solid #e0ddd7;white-space:nowrap">부처</th>
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#96938c;font-family:monospace;font-weight:500;border-bottom:2px solid #e0ddd7">제목 / 요약</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""

    # 카테고리 설정
    cat_ids = [wp_get_or_create_category("브리핑룸")]
    if is_weekly:
        cat_ids.append(wp_get_or_create_category("주간브리핑"))
    else:
        cat_ids.append(wp_get_or_create_category("일별브리핑"))

    payload = {
        "title":      post_title,
        "content":    content_html,
        "status":     "publish",
        "categories": cat_ids,
    }
    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
                          json=payload, auth=(WP_USER, WP_PASS), timeout=30)
        if r.status_code in (200, 201):
            post_id  = r.json().get("id")
            post_url = r.json().get("link")
            print(f"    ✅ 요약 포스팅 #{post_id} {post_url}")
            return True
        else:
            print(f"    ❌ 요약 포스팅 오류: {r.status_code} {r.text[:100]}")
            return False
    except Exception as e:
        print(f"    ❌ 요약 포스팅 예외: {e}")
        return False

'''

# main() 앞에 삽입
old = '\ndef main():'
new = new_func + '\ndef main():'

if old in content:
    content = content.replace(old, new, 1)
    print('함수 추가 완료')
else:
    print('패턴 미발견')

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.write(content)
