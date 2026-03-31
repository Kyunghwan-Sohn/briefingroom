"""인스타그램 캐러셀 이미지 — BCG/맥킨지 보고서 스타일

4장: 핵심요약 / 기사 / 분석 / 참여유도
1080x1350(4:5), 글자 크게, 빈 공간 없이, 인포그래픽 포함
"""
from __future__ import annotations

import json, re
from datetime import date
from pathlib import Path
from briefingroom.config import BASE_DIR, CAT_MAP, DATA_DIR

IG_OUT_DIR = BASE_DIR / "instagram"
CAT_EMOJI = {"금융경제":"💰","사회복지":"🏥","산업기술":"⚙️","외교안보":"🌏","행정법제":"📜"}
IMP = {
    "상":{"c":"#DC2626","b":"#FEE2E2","l":"HIGH"},
    "중":{"c":"#D97706","b":"#FEF3C7","l":"MID"},
    "하":{"c":"#6B7280","b":"#F3F4F6","l":"LOW"},
}

def _d(t):
    n=len(t)
    if n<20: return t
    p=t[:10]; s=t.find(p,10)
    if s>10: return t[:s].rstrip()
    h=n//2
    if h>10 and t[:h].strip()==t[h:].strip(): return t[:h].strip()
    return t

# ── 슬라이드 1: 핵심 요약 (맥킨지 Executive Summary 스타일) ──

def _s1(c):
    src=c.get("source",""); hook=_d(c.get("hook",c.get("title","")))
    sub=c.get("subtitle",""); dt=c.get("date","")
    cat=c.get("category",CAT_MAP.get(src,"")); em=CAT_EMOJI.get(cat,"📋")
    imp=IMP.get(c.get("impact","중"),IMP["중"])
    orig=_d(c.get("title",""));
    if len(orig)>45: orig=orig[:42]+"..."
    sm=c.get("summary",{}); pts=sm.get("points",c.get("points",[]))

    hs="48px" if len(hook)>14 else "56px"

    rows=""
    colors=["#2563EB","#059669","#D97706"]
    for i,pt in enumerate(pts[:3]):
        lb=pt.get("label",pt.get("title",""))
        tx=pt.get("text",pt.get("detail",""))
        st=pt.get("stat",pt.get("highlight",""))
        cl=colors[i%3]
        # 프로그레스 바 너비 (시각적 효과용)
        bw=["92%","78%","65%"][i]
        rows+=f"""
        <div class="row">
          <div class="row-left" style="border-left:5px solid {cl}">
            <div class="row-num" style="background:{cl}">{i+1}</div>
            <div class="row-label">{lb}</div>
            <div class="row-text">{tx}</div>
          </div>
          <div class="row-right">
            <div class="row-stat">{st}</div>
            <div class="bar-track"><div class="bar-fill" style="width:{bw};background:{cl}"></div></div>
          </div>
        </div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1350px;font-family:'Pretendard',sans-serif;overflow:hidden}}
    .c{{width:1080px;height:1350px;display:flex;flex-direction:column;background:#0f172a}}

    .hdr{{padding:32px 48px 0;display:flex;justify-content:space-between;align-items:center}}
    .hdr .bdg{{background:rgba(59,130,246,0.12);border:1px solid rgba(59,130,246,0.3);
      border-radius:24px;padding:7px 18px;font-size:17px;font-weight:700;color:#93c5fd}}
    .hdr .info{{font-size:14px;color:#64748b;display:flex;align-items:center;gap:8px}}
    .hdr .imp{{padding:3px 10px;border-radius:4px;font-size:12px;font-weight:800;
      background:{imp['b']};color:{imp['c']}}}

    .hero{{padding:24px 48px 16px;color:#fff}}
    .hero h1{{font-size:{hs};font-weight:900;line-height:1.18;word-break:keep-all;margin-bottom:8px}}
    .hero .sub{{font-size:22px;color:#94a3b8;margin-bottom:12px}}
    .hero .orig{{font-size:15px;color:#475569;background:rgba(255,255,255,0.05);
      border-radius:8px;padding:10px 16px;word-break:keep-all}}

    .body{{flex:1;background:#f8fafc;padding:28px 48px 48px;display:flex;flex-direction:column}}
    .body .sec-title{{font-size:15px;font-weight:800;color:#1e293b;letter-spacing:1px;
      border-bottom:3px solid #1e293b;padding-bottom:8px;margin-bottom:20px;display:flex;align-items:center;gap:8px}}
    .body .sec-title .dot{{width:8px;height:8px;border-radius:50%;background:#2563EB}}

    .row{{display:flex;gap:20px;margin-bottom:18px;min-height:0}}
    .row-left{{flex:2;padding:18px 20px 18px 24px;background:#fff;border-radius:12px;
      box-shadow:0 1px 3px rgba(0,0,0,0.05)}}
    .row-num{{display:inline-flex;width:32px;height:32px;border-radius:8px;
      color:#fff;font-size:16px;font-weight:900;align-items:center;justify-content:center;
      margin-bottom:8px}}
    .row-label{{font-size:22px;font-weight:800;color:#0f172a;margin-bottom:6px;word-break:keep-all}}
    .row-text{{font-size:18px;color:#475569;line-height:1.6;word-break:keep-all}}
    .row-right{{flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;
      background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.05)}}
    .row-stat{{font-size:36px;font-weight:900;color:#0f172a;margin-bottom:10px;text-align:center;word-break:keep-all}}
    .bar-track{{width:100%;height:8px;background:#e2e8f0;border-radius:4px}}
    .bar-fill{{height:8px;border-radius:4px}}

    .ft{{position:absolute;bottom:0;left:0;right:0;height:36px;
      background:linear-gradient(90deg,#1B2838,#2563EB);
      display:flex;align-items:center;justify-content:space-between;padding:0 24px}}
    .ft span{{font-size:11px;font-weight:700;color:#fff;letter-spacing:1px}}
    .ft .pg{{color:rgba(255,255,255,0.5);font-weight:400}}
    </style></head><body>
    <div class="c" style="position:relative">
      <div class="hdr">
        <span class="bdg">{em} {src}</span>
        <span class="info">📅 {dt} <span class="imp">{imp['l']}</span></span>
      </div>
      <div class="hero">
        <h1>{hook}</h1>
        <div class="sub">{sub}</div>
        <div class="orig">📋 {orig}</div>
      </div>
      <div class="body">
        <div class="sec-title"><span class="dot"></span> EXECUTIVE SUMMARY</div>
        {rows}
      </div>
      <div class="ft"><span>BRIEFINGROOM</span><span class="pg">1 / 4</span></div>
    </div></body></html>"""


# ── 슬라이드 2: 보도자료 기사 (매거진 에디토리얼) ──

def _s2(c):
    src=c.get("source",""); title=_d(c.get("title",""))
    dt=c.get("date",""); em=CAT_EMOJI.get(c.get("category",""),"📋")
    article=c.get("article","")
    if len(article)>600: article=article[:597]+"..."
    # 단락 분리
    paras=article.split("\n")
    body_html="".join(f'<p class="para">{p.strip()}</p>' for p in paras if p.strip())
    if len(title)>50: title=title[:47]+"..."

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1350px;font-family:'Pretendard',sans-serif;overflow:hidden}}
    .c{{width:1080px;height:1350px;display:flex;flex-direction:column;position:relative}}

    .hdr{{background:#0f172a;padding:36px 48px 28px;color:#fff}}
    .hdr .tag{{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;
      color:#93c5fd;letter-spacing:2px;margin-bottom:14px}}
    .hdr .tag .line{{flex:1;height:1px;background:rgba(255,255,255,0.1)}}
    .hdr h1{{font-size:34px;font-weight:900;line-height:1.3;word-break:keep-all;margin-bottom:10px}}
    .hdr .meta{{font-size:15px;color:#64748b}}

    .art{{flex:1;background:#fff;padding:36px 48px 48px;
      border-left:5px solid #2563EB;margin-left:48px;margin-right:48px;margin-top:0;
      display:flex;flex-direction:column}}
    .drop{{font-size:72px;font-weight:900;color:#2563EB;float:left;
      line-height:0.8;margin-right:12px;margin-top:8px}}
    .para{{font-size:24px;color:#1e293b;line-height:1.85;word-break:keep-all;margin-bottom:16px}}
    .src{{margin-top:auto;font-size:14px;color:#94a3b8;padding-top:12px;
      border-top:1px solid #e2e8f0}}

    .side{{background:#f1f5f9;margin:0 48px;padding:0}}

    .ft{{position:absolute;bottom:0;left:0;right:0;height:36px;
      background:linear-gradient(90deg,#1B2838,#2563EB);
      display:flex;align-items:center;justify-content:space-between;padding:0 24px}}
    .ft span{{font-size:11px;font-weight:700;color:#fff;letter-spacing:1px}}
    .ft .pg{{color:rgba(255,255,255,0.5);font-weight:400}}
    </style></head><body>
    <div class="c">
      <div class="hdr">
        <div class="tag">POLICY BRIEF <span class="line"></span></div>
        <h1>{title}</h1>
        <div class="meta">{em} {src} · {dt}</div>
      </div>
      <div class="art">
        {body_html}
        <div class="src">📋 출처: {src} 보도자료 원문 | govbrief.kr</div>
      </div>
      <div class="ft"><span>BRIEFINGROOM</span><span class="pg">2 / 4</span></div>
    </div></body></html>"""


# ── 슬라이드 3: 효과/영향 분석 (BCG 매트릭스 스타일) ──

def _s3(c):
    a=c.get("analysis",{})
    pos=a.get("positive",""); con=a.get("concern",""); out=a.get("outlook","")
    title=_d(c.get("title",""))
    if len(title)>40: title=title[:37]+"..."

    sections=[
        ("✅","긍정적 효과","POSITIVE IMPACT",pos,"#059669","#ECFDF5","#D1FAE5"),
        ("⚠️","우려 사항","RISK FACTOR",con,"#D97706","#FFFBEB","#FEF3C7"),
        ("🔭","향후 전망","FUTURE OUTLOOK",out,"#2563EB","#EFF6FF","#DBEAFE"),
    ]
    cards=""
    for icon,label,eng,text,color,bg,border_bg in sections:
        cards+=f"""
        <div class="sec" style="background:{bg};border-left:6px solid {color}">
          <div class="sec-hdr">
            <span class="sec-icon">{icon}</span>
            <div>
              <div class="sec-eng" style="color:{color}">{eng}</div>
              <div class="sec-label">{label}</div>
            </div>
          </div>
          <div class="sec-text">{text}</div>
        </div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1350px;font-family:'Pretendard',sans-serif;overflow:hidden}}
    .c{{width:1080px;height:1350px;display:flex;flex-direction:column;position:relative;background:#f8fafc}}

    .hdr{{background:#0f172a;padding:36px 48px 28px;color:#fff}}
    .hdr .tag{{font-size:13px;font-weight:700;color:#93c5fd;letter-spacing:2px;margin-bottom:10px;
      display:flex;align-items:center;gap:8px}}
    .hdr .tag .line{{flex:1;height:1px;background:rgba(255,255,255,0.1)}}
    .hdr h1{{font-size:36px;font-weight:900;line-height:1.25;margin-bottom:8px}}
    .hdr .meta{{font-size:15px;color:#64748b}}

    .body{{flex:1;padding:28px 48px 48px;display:flex;flex-direction:column;gap:18px}}

    .sec{{border-radius:16px;padding:28px 28px;flex:1;display:flex;flex-direction:column}}
    .sec-hdr{{display:flex;align-items:center;gap:14px;margin-bottom:14px}}
    .sec-icon{{font-size:32px}}
    .sec-eng{{font-size:11px;font-weight:700;letter-spacing:2px;margin-bottom:2px}}
    .sec-label{{font-size:22px;font-weight:900;color:#0f172a}}
    .sec-text{{font-size:22px;color:#334155;line-height:1.75;word-break:keep-all;flex:1}}

    .ft{{position:absolute;bottom:0;left:0;right:0;height:36px;
      background:linear-gradient(90deg,#1B2838,#2563EB);
      display:flex;align-items:center;justify-content:space-between;padding:0 24px}}
    .ft span{{font-size:11px;font-weight:700;color:#fff;letter-spacing:1px}}
    .ft .pg{{color:rgba(255,255,255,0.5);font-weight:400}}
    </style></head><body>
    <div class="c">
      <div class="hdr">
        <div class="tag">IMPACT ANALYSIS <span class="line"></span></div>
        <h1>📊 이 정책, 어떤 영향이 있을까?</h1>
        <div class="meta">{title}</div>
      </div>
      <div class="body">
        {cards}
      </div>
      <div class="ft"><span>BRIEFINGROOM</span><span class="pg">3 / 4</span></div>
    </div></body></html>"""


# ── 슬라이드 4: 참여 유도 ──

def _s4(c):
    tags="".join(f'<span class="tg">#{t}</span>' for t in c.get("hashtags",[])[:3])
    hook=_d(c.get("hook",""))

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1350px;font-family:'Pretendard',sans-serif;overflow:hidden}}
    .c{{width:1080px;height:1350px;display:flex;flex-direction:column;position:relative;background:#0f172a;color:#fff}}

    .top{{flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;
      text-align:center;padding:48px 56px}}

    .icon{{font-size:64px;margin-bottom:32px}}
    .q{{font-size:52px;font-weight:900;line-height:1.25;margin-bottom:20px}}
    .desc{{font-size:26px;color:#94a3b8;line-height:1.65;margin-bottom:40px;max-width:800px}}

    .box{{background:rgba(59,130,246,0.08);border:2px solid rgba(59,130,246,0.2);
      border-radius:20px;padding:32px 40px;margin-bottom:36px;max-width:800px;width:100%}}
    .box .t1{{font-size:26px;font-weight:800;color:#93c5fd;margin-bottom:10px}}
    .box .t2{{font-size:20px;color:#64748b;line-height:1.55}}

    .tags{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:24px}}
    .tg{{padding:10px 22px;border-radius:24px;background:rgba(255,255,255,0.06);
      border:1px solid rgba(255,255,255,0.1);font-size:18px;font-weight:600;color:#94a3b8}}

    .handle{{font-size:24px;font-weight:800;color:#3B82F6}}

    .ft{{position:absolute;bottom:0;left:0;right:0;height:36px;
      background:linear-gradient(90deg,#1B2838,#2563EB);
      display:flex;align-items:center;justify-content:space-between;padding:0 24px}}
    .ft span{{font-size:11px;font-weight:700;color:#fff;letter-spacing:1px}}
    .ft .pg{{color:rgba(255,255,255,0.5);font-weight:400}}
    </style></head><body>
    <div class="c">
      <div class="top">
        <div class="icon">💬</div>
        <div class="q">이 정책,<br>어떻게 생각하시나요?</div>
        <div class="desc">정부의 정책은 우리 모두의 삶에 영향을 줍니다.<br>관심을 갖고 함께 살펴봐요.</div>
        <div class="box">
          <div class="t1">💡 여러분의 의견을 들려주세요</div>
          <div class="t2">댓글로 생각을 남겨주시면,<br>다음 브리핑에 반영하겠습니다.</div>
        </div>
        <div class="tags">{tags}</div>
        <div class="handle">@govbrief.kr</div>
      </div>
      <div class="ft"><span>BRIEFINGROOM</span><span class="pg">4 / 4</span></div>
    </div></body></html>"""


# ── 생성 함수 ──

def generate_carousel_from_content(content, out_dir):
    from playwright.sync_api import sync_playwright
    pages=[_s1(content),_s2(content),_s3(content),_s4(content)]
    out_dir.mkdir(parents=True,exist_ok=True)
    paths=[]
    with sync_playwright() as p:
        br=p.chromium.launch()
        pg=br.new_page(viewport={"width":1080,"height":1350})
        for i,html in enumerate(pages):
            pg.set_content(html,wait_until="networkidle")
            pg.wait_for_timeout(1200)
            o=out_dir/f"slide_{i:02d}.png"
            pg.screenshot(path=str(o),type="png")
            paths.append(o)
        br.close()
    return paths

def generate_daily_carousels(target):
    from briefingroom.instagram_content import generate_carousel_content
    if isinstance(target,str): target=date.fromisoformat(target)
    jp=DATA_DIR/f"{target.isoformat()}.json"
    if not jp.exists(): return []
    data=json.loads(jp.read_text(encoding="utf-8"))
    items=data.get("items",[])
    if not items: return []
    t3=data.get("top3",[])
    if not t3:
        sc=[];
        for i,it in enumerate(items):
            s={"상":3,"중":2,"하":1}.get(it.get("impact","중"),2)
            sc.append((s,1 if it.get("summary") else 0,i))
        sc.sort(key=lambda x:(-x[0],-x[1],x[2]))
        t3=[s[2] for s in sc[:3]]
    dd=IG_OUT_DIR/target.isoformat(); res=[]
    for rank,idx in enumerate(t3):
        if idx>=len(items): continue
        item=items[idx]
        if not item.get("summary"): continue
        print(f"  [IG] #{rank+1} {item['source']} | {item['title'][:40]}")
        content=generate_carousel_content(item)
        if not content: continue
        ad=dd/f"{rank:02d}_{re.sub(r'[^w가-힣]','_',item.get('source',''))[:20]}"
        try:
            imgs=generate_carousel_from_content(content,ad)
            res.append({"content":content,"item":item,"images":imgs,"out_dir":ad})
            print(f"    → {len(imgs)}장: {ad}")
        except Exception as e: print(f"    → 실패: {e}")
    return res

if __name__=="__main__":
    import sys
    t=sys.argv[1] if len(sys.argv)>1 else date.today().isoformat()
    r=generate_daily_carousels(t)
    print(f"\n{len(r)}건 생성")
