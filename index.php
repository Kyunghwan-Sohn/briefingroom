<?php
if (is_page()) {
    $page = get_post();
    echo $page->post_content;
    exit;
}
?>
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>브리핑룸 — 27개 정부 부처 보도자료 AI 요약</title>
<meta name="description" content="대한민국 27개 정부 부처 보도자료를 매일 자동 수집하고 AI가 요약합니다. 부처별 맞춤 이메일 구독 무료.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://hotclipfolio.com/">
<meta property="og:type" content="website">
<meta property="og:title" content="브리핑룸 — 27개 정부 부처 보도자료 AI 요약">
<meta property="og:description" content="대한민국 27개 정부 부처 보도자료를 매일 자동 수집하고 AI가 요약합니다.">
<meta property="og:url" content="https://hotclipfolio.com/">
<meta property="og:site_name" content="브리핑룸">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="브리핑룸 — 정부 보도자료 AI 요약">
<meta name="twitter:description" content="27개 부처 보도자료 매일 수집 + AI 요약 + 무료 이메일 구독">
<link rel="alternate" type="application/rss+xml" title="브리핑룸 RSS" href="https://hotclipfolio.com/feed/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Pretendard:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#f5f4f0;--bg2:#eceae5;--surface:#fff;--border:#e0ddd7;--border2:#ccc9c2;--text:#1c1b18;--text2:#4a4844;--muted:#96938c;--accent:#2f54eb;--accent-l:#eef0fd;--c-fin:#2f54eb;--c-soc:#16a34a;--c-ind:#d97706;--c-dip:#dc2626;--c-adm:#7c3aed;--serif:'Noto Serif KR',serif;--sans:'Pretendard',sans-serif;--mono:'DM Mono',monospace}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;display:flex;flex-direction:column}
body::before{content:'';position:fixed;inset:0;background-image:radial-gradient(circle at 1px 1px,var(--border) 1px,transparent 0);background-size:24px 24px;opacity:.5;pointer-events:none;z-index:0}

/* 헤더 */
.header{position:sticky;top:0;z-index:10;background:rgba(245,244,240,.95);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:0 32px;height:56px;display:flex;align-items:center;justify-content:space-between;gap:20px}
.logo{display:flex;align-items:center;gap:9px;text-decoration:none;flex-shrink:0}
.logo-mark{width:30px;height:30px;background:var(--text);border-radius:7px;display:grid;place-items:center;font-size:14px}
.logo-text{font-family:var(--serif);font-size:16px;font-weight:700;color:var(--text);letter-spacing:-.3px}
.header-sub-area{flex:1;max-width:560px;display:flex;align-items:center;gap:10px}
.header-sub-label{font-size:12px;color:var(--text2);white-space:nowrap;font-weight:500}
.header-email{flex:1;padding:8px 14px;border:1.5px solid var(--border);border-radius:8px;font-family:var(--sans);font-size:13px;color:var(--text);outline:none;background:var(--surface);transition:all .15s}
.header-email:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(47,84,235,.1)}
.header-email::placeholder{color:var(--muted)}
.header-sub-btn{padding:8px 16px;background:var(--accent);color:#fff;border:none;border-radius:8px;font-family:var(--sans);font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap;transition:all .15s}
.header-sub-btn:hover{background:#1a3fd4}

/* 구독 팝업 오버레이 */
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);backdrop-filter:blur(4px);z-index:40;align-items:center;justify-content:center;padding:20px}
.overlay.open{display:flex}
.popup{position:relative;background:var(--surface);border-radius:18px;width:100%;max-width:540px;max-height:88vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.18)}
.popup-hdr{padding:22px 26px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:var(--surface);z-index:1}
.popup-title{font-family:var(--serif);font-size:18px;font-weight:700;color:var(--text)}
.popup-close{width:28px;height:28px;border-radius:7px;background:var(--bg2);border:1px solid var(--border);cursor:pointer;color:var(--muted);font-size:14px;display:grid;place-items:center}
.popup-close:hover{color:var(--text)}
.popup-body{padding:20px 26px 26px}
.pop-email-row{display:flex;gap:8px;margin-bottom:18px}
.pop-email{flex:1;padding:12px 16px;border:1.5px solid var(--border);border-radius:10px;font-family:var(--sans);font-size:14px;color:var(--text);outline:none;background:var(--bg);transition:all .15s}
.pop-email:focus{border-color:var(--accent);background:#fff;box-shadow:0 0 0 3px rgba(47,84,235,.1)}
.pop-email::placeholder{color:var(--muted)}
.pop-msg{padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:14px;display:none}
.pop-msg.success{background:#f0fdf4;color:#16a34a;border:1px solid #bbf7d0;display:block}
.pop-msg.error{background:#fef2f2;color:#dc2626;border:1px solid #fecaca;display:block}
.min-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.min-hdr-txt{font-size:13px;font-weight:500;color:var(--text2)}
.min-cnt{color:var(--accent);font-weight:600}
.sel-all-btn{font-family:var(--mono);font-size:10px;color:var(--accent);cursor:pointer;background:none;border:none;padding:0}
.min-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:18px}
.mc{display:flex;align-items:center;gap:6px;padding:8px 10px;border:1.5px solid var(--border);border-radius:8px;cursor:pointer;transition:all .12s;user-select:none}
.mc:hover{border-color:var(--border2);background:var(--bg2)}
.mc.on{border-color:var(--accent);background:var(--accent-l)}
.mc-dot{width:13px;height:13px;border-radius:3px;border:1.5px solid var(--border2);flex-shrink:0;display:grid;place-items:center;font-size:8px;transition:all .12s}
.mc.on .mc-dot{background:var(--accent);border-color:var(--accent);color:#fff}
.mc-name{font-size:11px;color:var(--text2)}
.mc.on .mc-name{color:var(--text);font-weight:500}
.pop-submit{width:100%;padding:13px;background:var(--text);color:#fff;border:none;border-radius:10px;font-family:var(--sans);font-size:14px;font-weight:700;cursor:pointer;transition:all .15s}
.pop-submit:hover{background:var(--accent);box-shadow:0 4px 16px rgba(47,84,235,.3)}
.pop-submit:disabled{background:var(--muted);cursor:not-allowed}

/* 메인 레이아웃 */
.body-wrap{display:flex;flex:1;position:relative;z-index:1}
.sidebar{position:fixed;top:56px;left:0;width:216px;height:calc(100vh - 56px);background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;z-index:8;overflow-y:auto}
.sb-top{padding:14px 12px;border-bottom:1px solid var(--border)}
.date-nav{display:flex;align-items:center;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:7px 10px;gap:8px}
.date-nav-label{flex:1;font-family:var(--mono);font-size:12px;color:var(--text2)}
.date-arrow{background:none;border:none;cursor:pointer;color:var(--muted);font-size:11px;padding:1px 3px;border-radius:4px;transition:all .12s}
.date-arrow:hover{color:var(--text);background:var(--bg2)}
.sb-section{padding:10px 6px;border-bottom:1px solid var(--border)}
.sb-label{font-family:var(--mono);font-size:9px;color:var(--muted);letter-spacing:1.3px;text-transform:uppercase;padding:0 6px;margin-bottom:4px}
.f-item{display:flex;align-items:center;justify-content:space-between;padding:7px 8px;border-radius:7px;cursor:pointer;transition:background .1s;user-select:none}
.f-item:hover{background:var(--bg2)}
.f-item.active{background:var(--accent-l)}
.f-left{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--text2)}
.f-item.active .f-left{color:var(--text);font-weight:500}
.f-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.f-cnt{font-family:var(--mono);font-size:10px;color:var(--muted);background:var(--bg2);padding:1px 6px;border-radius:8px}
.f-item.active .f-cnt{background:rgba(47,84,235,.12);color:var(--accent)}
.sb-min-section{padding:10px 6px;flex:1}
/* 금융 서브카테고리 */
.sb-sub{padding:0 0 0 18px;max-height:0;overflow:hidden;transition:max-height .25s ease}
.sb-sub.open{max-height:300px}
.sb-sub .f-item{padding:5px 8px}
.sb-sub .f-left{font-size:11.5px}
.sb-sub .f-dot{width:6px;height:6px}
.fin-toggle{cursor:pointer;position:relative}
.fin-toggle::after{content:'▸';position:absolute;right:8px;font-size:9px;color:var(--muted);transition:transform .2s}
.fin-toggle.expanded::after{transform:rotate(90deg)}
.main{margin-left:216px;flex:1;min-height:calc(100vh - 56px)}
.topbar{position:sticky;top:56px;z-index:5;background:rgba(245,244,240,.9);backdrop-filter:blur(10px);border-bottom:1px solid var(--border);padding:0 24px;height:46px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.search-wrap{flex:1;max-width:300px;position:relative}
.search-ico{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:12px;pointer-events:none}
.search-in{width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:6px 12px 6px 28px;font-family:var(--mono);font-size:12px;color:var(--text);outline:none;transition:all .15s}
.search-in::placeholder{color:var(--muted)}
.search-in:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(47,84,235,.1)}
.view-toggle{display:flex;background:var(--surface);border:1px solid var(--border);border-radius:7px;overflow:hidden}
.v-btn{padding:5px 9px;background:none;border:none;cursor:pointer;color:var(--muted);font-size:13px;transition:all .12s}
.v-btn.active{background:var(--text);color:#fff}
.content{padding:20px 24px}
.page-hdr{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:18px}
.page-title{font-family:var(--serif);font-size:20px;font-weight:700;letter-spacing:-.5px;color:var(--text)}
.page-sub{font-family:var(--mono);font-size:11px;color:var(--muted);margin-top:3px}
.total-badge{font-family:var(--mono);font-size:12px;color:var(--accent);background:var(--accent-l);border:1px solid rgba(47,84,235,.2);padding:4px 12px;border-radius:20px}
.loading{text-align:center;padding:60px 0;color:var(--muted)}
.loading-spinner{width:32px;height:32px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}
.cat-block{margin-bottom:24px}
.cat-divider{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.cat-divider-dot{width:9px;height:9px;border-radius:3px;flex-shrink:0}
.cat-divider-label{font-family:var(--serif);font-size:14px;font-weight:600;color:var(--text)}
.cat-divider-line{flex:1;height:1px;background:var(--border)}
.cat-divider-info{font-family:var(--mono);font-size:10px;color:var(--muted);white-space:nowrap}
.cards-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.cards-grid.list-view{grid-template-columns:1fr;gap:4px}
.more-btn{grid-column:1/-1;display:flex;align-items:center;justify-content:center;gap:6px;padding:10px;background:var(--surface);border:1px dashed var(--border2);border-radius:10px;cursor:pointer;font-family:var(--mono);font-size:11px;color:var(--muted);transition:all .15s}
.more-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-l)}
.press-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px;cursor:pointer;transition:all .15s;animation:fadeUp .3s ease both;border-left:3px solid var(--card-color,var(--accent))}
.press-card:hover{box-shadow:0 3px 16px rgba(0,0,0,.1);transform:translateY(-1px)}
.list-view .press-card{border-left:none;display:flex;align-items:center;gap:12px;padding:11px 14px;border-radius:8px}
.list-view .card-body{flex:1;min-width:0}
.list-view .card-actions{flex-shrink:0;margin-top:0}
.list-view .card-title{font-size:13px;-webkit-line-clamp:1}
.list-view .card-summary{display:none}
.list-view .card-meta{margin-top:2px}
.card-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.m-badge{font-family:var(--mono);font-size:10px;font-weight:500;padding:2px 8px;border-radius:5px}
.card-time{font-family:var(--mono);font-size:10px;color:var(--muted)}
.card-title{font-size:13px;font-weight:500;line-height:1.5;color:var(--text);margin-bottom:6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card-summary{font-size:12px;color:var(--text2);line-height:1.6;margin-bottom:8px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card-meta{display:flex;align-items:center;gap:10px;margin-top:6px}
.card-meta-i{font-family:var(--mono);font-size:10px;color:var(--muted)}
.card-actions{display:flex;gap:5px;margin-top:8px}
.c-btn{display:flex;align-items:center;gap:4px;padding:5px 10px;border-radius:6px;font-family:var(--mono);font-size:10px;cursor:pointer;transition:all .12s;text-decoration:none;border:1px solid var(--border);color:var(--muted);background:none}
.c-btn:hover{color:var(--text);border-color:var(--border2);background:var(--bg2)}
.c-btn.primary{background:var(--text);color:#fff;border-color:var(--text)}
.c-btn.primary:hover{background:var(--accent);border-color:var(--accent)}
.detail-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.25);z-index:20;backdrop-filter:blur(3px)}
.detail-overlay.open{display:block}
.detail{position:fixed;top:0;right:-500px;width:480px;height:100vh;background:var(--surface);border-left:1px solid var(--border);z-index:21;overflow-y:auto;transition:right .28s cubic-bezier(.4,0,.2,1);display:flex;flex-direction:column}
.detail.open{right:0}
.detail-hdr{position:sticky;top:0;background:var(--surface);border-bottom:1px solid var(--border);padding:14px 18px;display:flex;align-items:center;justify-content:space-between;z-index:1}
.d-close{width:28px;height:28px;border-radius:7px;background:var(--bg2);border:1px solid var(--border);cursor:pointer;color:var(--muted);font-size:14px;display:grid;place-items:center;transition:all .12s}
.d-close:hover{color:var(--text);background:var(--bg)}
.detail-body{padding:20px;flex:1}
.d-badge{display:inline-flex;align-items:center;gap:5px;font-family:var(--mono);font-size:11px;padding:4px 10px;border-radius:6px;margin-bottom:12px}
.d-title{font-family:var(--serif);font-size:18px;font-weight:700;letter-spacing:-.5px;line-height:1.4;margin-bottom:14px;color:var(--text)}
.d-meta{display:flex;flex-wrap:wrap;gap:14px;padding:12px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin-bottom:18px}
.d-meta-i{font-family:var(--mono);font-size:11px;color:var(--muted);display:flex;flex-direction:column;gap:2px}
.d-meta-i strong{color:var(--text2);font-weight:500}
.d-sec-label{font-family:var(--mono);font-size:10px;color:var(--accent);letter-spacing:1.2px;text-transform:uppercase;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.d-sec-label::before{content:'';width:12px;height:1.5px;background:var(--accent)}
.d-summary{font-size:13px;line-height:1.8;color:var(--text2);background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:14px 16px;margin-bottom:16px}
.d-kws{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:18px}
.kw{font-family:var(--mono);font-size:10px;color:var(--text2);background:var(--bg2);border:1px solid var(--border);padding:3px 9px;border-radius:4px}
.d-actions{display:flex;gap:8px}
.d-btn{flex:1;padding:10px 8px;border-radius:8px;font-family:var(--sans);font-size:13px;font-weight:500;cursor:pointer;text-align:center;text-decoration:none;transition:all .15s;display:flex;align-items:center;justify-content:center;gap:5px}
.d-btn.primary{background:var(--text);color:#fff;border:none}
.d-btn.primary:hover{background:var(--accent)}
.d-btn.sec{background:var(--bg2);color:var(--text2);border:1px solid var(--border)}
.d-btn.sec:hover{color:var(--text);border-color:var(--border2)}
/* 히어로 배너 */
.hero-banner{background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);padding:28px 24px;display:flex;align-items:center;justify-content:space-between;gap:20px;position:relative;z-index:1}
.hero-left h2{font-family:var(--serif);font-size:20px;font-weight:700;color:#fff;letter-spacing:-.5px;margin-bottom:6px}
.hero-left p{font-size:13px;color:rgba(255,255,255,.7);line-height:1.5}
.hero-stats{display:flex;gap:16px}
.hero-stat{text-align:center;padding:8px 14px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);border-radius:8px}
.hero-stat-num{font-family:var(--serif);font-size:18px;font-weight:700;color:#fff}
.hero-stat-label{font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.6);letter-spacing:.5px;margin-top:2px}
.hero-dismiss{position:absolute;top:8px;right:12px;background:none;border:none;color:rgba(255,255,255,.4);cursor:pointer;font-size:14px}
.hero-banner.hidden{display:none}
/* 구독 프리셋 */
.preset-row{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
.preset-btn{padding:6px 12px;border:1.5px solid var(--border);border-radius:20px;background:var(--surface);font-family:var(--mono);font-size:10px;color:var(--text2);cursor:pointer;transition:all .12s;white-space:nowrap}
.preset-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-l)}
@media(max-width:768px){.hero-banner{flex-direction:column;text-align:center;padding:20px 16px}.hero-left h2{font-size:17px}.hero-stats{justify-content:center}}
.empty{text-align:center;padding:50px 0;color:var(--muted);grid-column:1/-1}
.empty-icon{font-size:28px;margin-bottom:10px;opacity:.5}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px}
/* 구독 바 */
.sub-bar{background:linear-gradient(135deg,#0f172a,#2563eb);border-radius:10px;padding:10px 16px;margin-bottom:14px;display:flex;align-items:center;gap:10px}
.sub-bar-email{flex:1;padding:8px 14px;border-radius:7px;border:none;background:rgba(255,255,255,.15);color:#fff;font-family:var(--sans);font-size:13px;outline:none;transition:all .15s;min-width:0}
.sub-bar-email::placeholder{color:rgba(255,255,255,.75)}
.sub-bar-email:focus{background:rgba(255,255,255,.22)}
.sub-bar-btn{padding:8px 16px;background:rgba(255,255,255,.18);color:#fff;border:1.5px solid rgba(255,255,255,.5);border-radius:7px;font-family:var(--sans);font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap;flex-shrink:0;transition:all .15s}
.sub-bar-btn:hover{background:rgba(255,255,255,.28)}
.sub-bar-sel{padding:8px 14px;background:transparent;color:#fff;border:1.5px solid rgba(255,255,255,.4);border-radius:7px;font-family:var(--sans);font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap;flex-shrink:0;transition:all .15s}
.sub-bar-sel:hover{background:rgba(255,255,255,.1)}
.sub-bar-msg{margin-top:8px;font-size:12px;display:none}
.sub-bar-msg.success{color:#86efac;display:block}
.sub-bar-msg.error{color:#fca5a5;display:block}

.mobile-date-nav{display:none;align-items:center;justify-content:space-between;background:var(--surface);border-bottom:1px solid var(--border);padding:10px 16px;position:sticky;top:56px;z-index:7}
.mob-date-label{font-family:var(--mono);font-size:13px;color:var(--text2);font-weight:500}
.mob-date-arrow{background:var(--bg2);border:1px solid var(--border);border-radius:7px;padding:5px 14px;cursor:pointer;color:var(--text);font-size:13px}
@media(max-width:768px){
  .mobile-date-nav{display:flex}
  .sub-bar{flex-wrap:nowrap}
  .sub-bar-sel{display:none}
  .popup{max-height:80vh;overflow-y:auto;border-radius:14px 14px 0 0;position:fixed;bottom:0;left:0;right:0;width:100%;max-width:100%}
  .overlay{align-items:flex-end;padding:0}
  .min-grid{grid-template-columns:repeat(3,1fr)}
  .sidebar{display:none}.main{margin-left:0}
  .cards-grid{grid-template-columns:1fr}
  .detail{width:100%;right:-100%}
  .header-sub-area{display:none}
  .header{padding:0 16px}
  .mobile-cta{display:flex}
}
/* 모바일 하단 고정 CTA */
.mobile-cta{display:none;position:fixed;bottom:0;left:0;right:0;z-index:15;background:linear-gradient(135deg,#0f172a,#1e40af);padding:12px 16px;gap:8px;align-items:center;box-shadow:0 -4px 20px rgba(0,0,0,.15)}
.mobile-cta-text{color:rgba(255,255,255,.85);font-size:12px;white-space:nowrap}
.mobile-cta-btn{flex:1;padding:10px;background:rgba(255,255,255,.18);color:#fff;border:1.5px solid rgba(255,255,255,.5);border-radius:8px;font-family:var(--sans);font-size:13px;font-weight:700;cursor:pointer;text-align:center;transition:all .15s}
.mobile-cta-btn:hover{background:rgba(255,255,255,.28)}
</style>
</head>
<body>

<!-- 헤더 -->
<header class="header">
  <a class="logo" href="/">
    <div class="logo-mark">📋</div>
    <span class="logo-text">브리핑룸</span>
  </a>
  <div class="header-sub-area">
    <span class="header-sub-label">정부 보도자료 이메일로 받아보세요</span>
    <input class="header-email" type="email" id="header-email" placeholder="이메일 주소 입력">
    <button class="header-sub-btn" onclick="openSubPopup()">구독하기</button>
  </div>
</header>

<!-- 구독 팝업 -->
<div class="overlay" id="sub-overlay">
  <div class="popup">
    <div class="popup-hdr">
      <span class="popup-title">이메일 구독 설정</span>
      <button class="popup-close" onclick="closeSubPopup()">✕</button>
    </div>
    <div class="popup-body">
      <div class="pop-msg" id="pop-msg"></div>
      <div class="pop-email-row">
        <input class="pop-email" type="email" id="pop-email" placeholder="이메일 주소">
      </div>
      <div class="preset-row">
        <button class="preset-btn" onclick="applyPreset('journalist')">기자용 (전체)</button>
        <button class="preset-btn" onclick="applyPreset('finance')">투자자용 (금융·경제)</button>
        <button class="preset-btn" onclick="applyPreset('tech')">IT/과학 종사자</button>
        <button class="preset-btn" onclick="applyPreset('policy')">정책 연구자</button>
      </div>
      <div class="min-hdr">
        <span class="min-hdr-txt">받아볼 부처 선택 <span class="min-cnt" id="pop-cnt">0</span>개</span>
        <button class="sel-all-btn" onclick="toggleAll()">전체 선택/해제</button>
      </div>
      <div class="min-grid" id="pop-min-grid"></div>
      <button class="pop-submit" id="pop-submit" onclick="doSubscribe()">구독하기</button>
    </div>
  </div>
</div>

<!-- 히어로 배너 (첫 방문자용) -->
<div class="hero-banner" id="hero-banner">
  <div class="hero-left">
    <h2>51개 부처 + 7개 금융기관, AI가 요약합니다</h2>
    <p>정부 보도자료 + 금융 유관기관까지 매일 자동 수집 · AI 요약 · 무료 이메일 구독</p>
  </div>
  <div class="hero-stats">
    <div class="hero-stat"><div class="hero-stat-num">51+</div><div class="hero-stat-label">수집 기관</div></div>
    <div class="hero-stat"><div class="hero-stat-num">금융</div><div class="hero-stat-label">특화 분석</div></div>
    <div class="hero-stat"><div class="hero-stat-num">AI</div><div class="hero-stat-label">자동 요약</div></div>
  </div>
  <button class="hero-dismiss" onclick="dismissHero()" title="닫기">✕</button>
</div>

<!-- 본문 -->
<div class="body-wrap">
  <aside class="sidebar">
    <div class="sb-top">
      <div class="date-nav">
        <button class="date-arrow" onclick="changeDate(-1)">◀</button>
        <span class="date-nav-label" id="date-label"></span>
        <button class="date-arrow" onclick="changeDate(1)">▶</button>
      </div>
    </div>
    <div class="sb-section">
      <div class="f-item active" onclick="setFilter('all',this)">
        <div class="f-left"><div class="f-dot" style="background:var(--text)"></div>전체</div>
        <span class="f-cnt" id="cnt-all">0</span>
      </div>
    </div>
    <div class="sb-section">
      <div class="sb-label">분야</div>
      <div class="f-item fin-toggle" id="fin-toggle" onclick="toggleFinSub(this)"><div class="f-left"><div class="f-dot" style="background:var(--c-fin)"></div>금융·경제</div><span class="f-cnt" id="cnt-금융경제">0</span></div>
      <div class="sb-sub" id="fin-sub">
        <div class="f-item" onclick="setFilter('금융경제',this)"><div class="f-left"><div class="f-dot" style="background:var(--c-fin)"></div>전체</div><span class="f-cnt" id="cnt-금융경제-all">0</span></div>
        <div class="f-item" onclick="setFilter('fin-금융정책',this)"><div class="f-left"><div class="f-dot" style="background:#2f54eb"></div>금융정책</div><span class="f-cnt" id="cnt-fin-금융정책">0</span></div>
        <div class="f-item" onclick="setFilter('fin-감독규제',this)"><div class="f-left"><div class="f-dot" style="background:#dc2626"></div>감독·규제</div><span class="f-cnt" id="cnt-fin-감독규제">0</span></div>
        <div class="f-item" onclick="setFilter('fin-시장통화',this)"><div class="f-left"><div class="f-dot" style="background:#16a34a"></div>시장·통화</div><span class="f-cnt" id="cnt-fin-시장통화">0</span></div>
        <div class="f-item" onclick="setFilter('fin-금융인프라',this)"><div class="f-left"><div class="f-dot" style="background:#7c3aed"></div>금융인프라</div><span class="f-cnt" id="cnt-fin-금융인프라">0</span></div>
        <div class="f-item" onclick="setFilter('fin-정책금융',this)"><div class="f-left"><div class="f-dot" style="background:#d97706"></div>정책금융</div><span class="f-cnt" id="cnt-fin-정책금융">0</span></div>
        <div class="f-item" onclick="setFilter('fin-업계동향',this)"><div class="f-left"><div class="f-dot" style="background:#0891b2"></div>업계동향</div><span class="f-cnt" id="cnt-fin-업계동향">0</span></div>
      </div>
      <div class="f-item" onclick="setFilter('사회복지',this)"><div class="f-left"><div class="f-dot" style="background:var(--c-soc)"></div>사회·복지</div><span class="f-cnt" id="cnt-사회복지">0</span></div>
      <div class="f-item" onclick="setFilter('산업기술',this)"><div class="f-left"><div class="f-dot" style="background:var(--c-ind)"></div>산업·기술</div><span class="f-cnt" id="cnt-산업기술">0</span></div>
      <div class="f-item" onclick="setFilter('외교안보',this)"><div class="f-left"><div class="f-dot" style="background:var(--c-dip)"></div>외교·안보</div><span class="f-cnt" id="cnt-외교안보">0</span></div>
      <div class="f-item" onclick="setFilter('행정법제',this)"><div class="f-left"><div class="f-dot" style="background:var(--c-adm)"></div>행정·법제</div><span class="f-cnt" id="cnt-행정법제">0</span></div>
    </div>
    <div class="sb-min-section" id="ministry-sb"><div class="sb-label">부처별</div></div>
  </aside>

  <main class="main">
    <div class="topbar">
      <div class="search-wrap">
        <span class="search-ico">🔍</span>
        <input class="search-in" type="text" id="search-in" placeholder="보도자료 검색..." oninput="handleSearch(this.value)">
      </div>
      <div class="view-toggle">
        <button class="v-btn active" onclick="setView('grid',this)">⊞</button>
        <button class="v-btn" onclick="setView('list',this)">☰</button>
      </div>
    </div>
    <div class="content">
      <div class="page-hdr">
        <div>
          <div class="page-title" id="page-title">보도자료</div>
          <div class="page-sub" id="page-sub"></div>
        </div>
        <span class="total-badge" id="total-badge">0건</span>
      </div>
      <div id="main-content">
        <div class="loading"><div class="loading-spinner"></div><div>데이터 불러오는 중...</div></div>
      </div>


    </div>
  </main>
</div>

<!-- 상세 패널 -->
<div class="detail-overlay" id="d-overlay" onclick="closeDetail()"></div>
<div class="detail" id="detail">
  <div class="detail-hdr">
    <span id="d-hdr-min" style="font-family:var(--mono);font-size:11px;color:var(--muted)"></span>
    <button class="d-close" onclick="closeDetail()">✕</button>
  </div>
  <div class="detail-body">
    <div class="d-badge" id="d-badge"></div>
    <div class="d-title" id="d-title"></div>
    <div class="d-meta" id="d-meta"></div>
    <div class="d-sec-label">AI 요약</div>
    <div class="d-summary" id="d-summary"></div>
    <div class="d-kws" id="d-kws"></div>
    <div class="d-actions">
      <a class="d-btn primary" id="d-src" href="#" target="_blank">↗ 원문 보기</a>
      <a class="d-btn sec" id="d-wp" href="#" target="_blank">📄 상세 글</a>
    </div>
  </div>
</div>

<script>
const WP_API='https://hotclipfolio.com/wp-json/wp/v2';
const SUB_API='https://hotclipfolio.com/wp-json/briefing/v1/subscribe';
const PER_PAGE=50;
const MINS=['금융위원회','금융감독원','기획재정부','한국은행','교육부','보건복지부','고용노동부','성평등가족부','국민권익위원회','국가보훈부','법무부','과학기술정보통신부','국토교통부','해양수산부','농림축산식품부','중소벤처기업부','환경부','개인정보보호위원회','산업통상자원부','외교부','국방부','통일부','행정안전부','인사혁신처','법제처','문화체육관광부','공정거래위원회'];
const CC={'금융경제':'var(--c-fin)','사회복지':'var(--c-soc)','산업기술':'var(--c-ind)','외교안보':'var(--c-dip)','행정법제':'var(--c-adm)'};
const CB={'금융경제':'rgba(47,84,235,.08)','사회복지':'rgba(22,163,74,.08)','산업기술':'rgba(217,119,6,.08)','외교안보':'rgba(220,38,38,.08)','행정법제':'rgba(124,58,237,.08)'};
const CN={'금융경제':'금융·경제','사회복지':'사회·복지','산업기술':'산업·기술','외교안보':'외교·안보','행정법제':'행정·법제'};
const CO=['금융경제','사회복지','산업기술','외교안보','행정법제'];
let allItems=[],curFilter='all',curView='grid',curSearch='',curDate=new Date(),expanded={},catMap={},selMins=new Set();

/* 날짜 */
function fmtDate(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
function fmtDateKo(d){const days=['일','월','화','수','목','금','토'];return `${d.getFullYear()}년 ${d.getMonth()+1}월 ${d.getDate()}일 ${days[d.getDay()]}요일`}
function changeDate(dir){curDate.setDate(curDate.getDate()+dir);loadPosts()}

/* 카테고리 */
async function loadCats(){try{const r=await fetch(`${WP_API}/categories?per_page=50`);(await r.json()).forEach(c=>{catMap[c.id]=c.name})}catch(e){}}

/* 포스트 */
async function loadPosts(){
  document.getElementById('main-content').innerHTML='<div class="loading"><div class="loading-spinner"></div><div>데이터 불러오는 중...</div></div>';
  const ds=fmtDate(curDate);
  document.getElementById('date-label').textContent=ds;
  const mbl=document.getElementById('mobile-date-label');
  if(mbl) mbl.textContent=curDate.getMonth()+1+'월 '+curDate.getDate()+'일';
  document.getElementById('page-title').textContent=`${curDate.getMonth()+1}월 ${curDate.getDate()}일 보도자료`;
  const todayD=new Date();const todayWd2=todayD.getDay();
  let subText=fmtDateKo(curDate);
  // 오늘 기준 기본날짜면 요일 안내 추가
  const isFriData=(todayWd2===6||todayWd2===0||todayWd2===1);
  const isYesterday=((todayD-curDate)/(1000*60*60*24)<1.5 && curDate<todayD);
  if(isFriData&&isYesterday) subText+=' (금요일 보도자료)';
  else if(isYesterday) subText+=' 보도자료';
  document.getElementById('page-sub').textContent=subText;
  try{
    const r=await fetch(`${WP_API}/posts?per_page=${PER_PAGE}&after=${ds}T00:00:00&before=${ds}T23:59:59&_fields=id,title,content,link,categories,date`);
    if(!r.ok)throw new Error(`HTTP ${r.status}`);
    allItems=(await r.json()).map(parsePost);render();updateSidebar();
  }catch(e){document.getElementById('main-content').innerHTML=`<div class="empty"><div class="empty-icon">⚠️</div><div>로드 실패: ${e.message}</div></div>`}
}
function parsePost(p){
  const d=document.createElement('div');d.innerHTML=p.content?.rendered||'';
  const src=d.querySelector('.briefing-source')?.textContent?.replace('🏛 ','')||'';
  const sum=d.querySelector('.briefing-summary p')?.textContent||'';
  const kws=[...d.querySelectorAll('.briefing-keywords span')].map(s=>s.textContent.replace('#',''));
  const orig=d.querySelector('.briefing-links a')?.href||p.link;
  const cats=(p.categories||[]).map(id=>catMap[id]).filter(Boolean);
  const cat=CO.find(c=>cats.includes(c))||'행정법제';
  return{id:p.id,title:p.title?.rendered?.replace(/<[^>]+>/g,'')||'',src,sum,kws,orig,wp:p.link,date:p.date?.slice(0,10)||'',cat};
}
function filtered(){
  let it=allItems;
  if(curFilter!=='all'){
    if(curFilter.startsWith('fin-')){
      // 금융 서브카테고리 필터
      const sub=curFilter.slice(4);
      it=it.filter(i=>FIN_SUB_MAP[i.src]===sub);
    } else {
      it=it.filter(i=>i.cat===curFilter||i.src===curFilter);
    }
  }
  if(curSearch){const q=curSearch.toLowerCase();it=it.filter(i=>i.title.toLowerCase().includes(q)||i.src.toLowerCase().includes(q)||i.sum.toLowerCase().includes(q))}
  return it;
}
function render(){
  const items=filtered();document.getElementById('total-badge').textContent=`${items.length}건`;
  const c=document.getElementById('main-content');c.innerHTML='';
  if(!items.length){c.innerHTML='<div class="empty"><div class="empty-icon">📭</div><div>보도자료가 없습니다</div></div>';return}
  // 구독 바 삽입 (항상 맨 위)
  const sb=document.createElement('div');sb.className='sub-bar';
  sb.innerHTML=`<input class="sub-bar-email" type="email" id="sub-bar-email" placeholder="보도자료 이메일로 받아보세요"><button class="sub-bar-btn" onclick="subBarNext()">구독하기</button><button class="sub-bar-sel" onclick="subBarMinistry()">부처 선택</button><div class="sub-bar-msg" id="sub-bar-msg"></div>`;
  c.appendChild(sb);
  if(curFilter!=='all'){const g=document.createElement('div');g.className=`cards-grid${curView==='list'?' list-view':''}`;items.forEach((it,i)=>g.appendChild(mkCard(it,i)));c.appendChild(g)}
  else{const gr={};items.forEach(it=>{(gr[it.cat]=gr[it.cat]||[]).push(it)});CO.forEach(cat=>{if(!gr[cat]?.length)return;c.appendChild(mkBlock(cat,gr[cat]))})}
}
function mkBlock(cat,items){
  const SHOW=4;const isEx=expanded[cat];const shown=isEx?items:items.slice(0,SHOW);
  const b=document.createElement('div');b.className='cat-block';
  const dv=document.createElement('div');dv.className='cat-divider';
  dv.innerHTML=`<div class="cat-divider-dot" style="background:${CC[cat]}"></div><span class="cat-divider-label">${CN[cat]||cat}</span><div class="cat-divider-line"></div><span class="cat-divider-info">${items.length}건</span>`;
  b.appendChild(dv);
  const g=document.createElement('div');g.className=`cards-grid${curView==='list'?' list-view':''}`;
  shown.forEach((it,i)=>g.appendChild(mkCard(it,i)));
  const h=items.length-SHOW;
  if(!isEx&&h>0){const btn=document.createElement('button');btn.className='more-btn';btn.innerHTML=`▾ ${h}개 더보기`;btn.onclick=()=>{expanded[cat]=true;render()};g.appendChild(btn)}
  else if(isEx&&items.length>SHOW){const btn=document.createElement('button');btn.className='more-btn';btn.innerHTML='▴ 접기';btn.onclick=()=>{expanded[cat]=false;render()};g.appendChild(btn)}
  b.appendChild(g);return b;
}
function mkCard(it,idx){
  const finSub=FIN_SUB_MAP[it.src]||'';
  const col=CC[it.cat]||'var(--accent)';const bg=CB[it.cat]||'rgba(47,84,235,.08)';
  const badgeLabel=finSub?`${it.src}`:it.src;
  const c=document.createElement('div');c.className='press-card';
  c.style.cssText=`--card-color:${col};animation-delay:${Math.min(idx,8)*.04}s`;
  if(curView==='list'){
    c.innerHTML=`<div style="width:72px;flex-shrink:0;text-align:center"><span class="m-badge" style="background:${bg};color:${col}">${it.src||'정부'}</span></div><div class="card-body" style="flex:1;min-width:0"><div class="card-title" style="-webkit-line-clamp:1;margin-bottom:0">${it.title}</div><div class="card-meta"><span class="card-meta-i">📅 ${it.date}</span></div></div><div class="card-actions" style="margin-top:0"><button class="c-btn primary" onclick="event.stopPropagation();openDetail(${it.id})">보기</button></div>`;
  }else{
    c.innerHTML=`<div class="card-top"><span class="m-badge" style="background:${bg};color:${col}">${it.src||'정부'}</span><span class="card-time">${it.date}</span></div><div class="card-title">${it.title}</div><div class="card-summary">${it.sum}</div><div class="card-meta"><span class="card-meta-i">🏷 ${it.kws.slice(0,2).join(' · ')}</span></div><div class="card-actions"><button class="c-btn primary" onclick="event.stopPropagation();openDetail(${it.id})">상세보기</button><a class="c-btn" href="${it.orig}" target="_blank" onclick="event.stopPropagation()">↗ 원문</a></div>`;
  }
  c.addEventListener('click',()=>openDetail(it.id));return c;
}
function openDetail(id){
  const it=allItems.find(i=>i.id===id);if(!it)return;
  const col=CC[it.cat]||'var(--accent)';const bg=CB[it.cat]||'rgba(47,84,235,.08)';
  document.getElementById('d-hdr-min').textContent=it.src;
  const b=document.getElementById('d-badge');b.textContent=it.src;b.style.cssText=`background:${bg};color:${col};border:1px solid ${col}44`;
  document.getElementById('d-title').textContent=it.title;
  document.getElementById('d-meta').innerHTML=`<div class="d-meta-i"><span>날짜</span><strong>${it.date}</strong></div><div class="d-meta-i"><span>기관</span><strong>${it.src}</strong></div><div class="d-meta-i"><span>분야</span><strong>${CN[it.cat]||it.cat}</strong></div>`;
  document.getElementById('d-summary').textContent=it.sum||'요약 없음';
  document.getElementById('d-kws').innerHTML=it.kws.map(k=>`<span class="kw"># ${k}</span>`).join('');
  document.getElementById('d-src').href=it.orig||'#';document.getElementById('d-wp').href=it.wp||'#';
  document.getElementById('d-overlay').classList.add('open');document.getElementById('detail').classList.add('open');document.body.style.overflow='hidden';
}
function closeDetail(){document.getElementById('d-overlay').classList.remove('open');document.getElementById('detail').classList.remove('open');document.body.style.overflow=''}
function updateSidebar(){
  document.getElementById('cnt-all').textContent=allItems.length;
  CO.forEach(cat=>{const el=document.getElementById(`cnt-${cat}`);if(el)el.textContent=allItems.filter(i=>i.cat===cat).length});
  // 금융 서브카테고리 카운트
  const el0=document.getElementById('cnt-금융경제-all');if(el0)el0.textContent=allItems.filter(i=>i.cat==='금융경제').length;
  ['금융정책','감독규제','시장통화','금융인프라','정책금융','업계동향'].forEach(sub=>{
    const el=document.getElementById(`cnt-fin-${sub}`);
    if(el)el.textContent=allItems.filter(i=>FIN_SUB_MAP[i.src]===sub).length;
  });
  const sb=document.getElementById('ministry-sb');[...sb.querySelectorAll('.f-item')].forEach(e=>e.remove());
  [...new Set(allItems.map(i=>i.src))].sort((a,b)=>a.localeCompare(b,'ko')).forEach(m=>{
    const cnt=allItems.filter(i=>i.src===m).length;const cat=allItems.find(i=>i.src===m)?.cat||'행정법제';
    const el=document.createElement('div');el.className='f-item';
    el.innerHTML=`<div class="f-left"><div class="f-dot" style="background:${CC[cat]}"></div>${m}</div><span class="f-cnt">${cnt}</span>`;
    el.addEventListener('click',()=>setFilter(m,el));sb.appendChild(el);
  });
}
function setFilter(cat,el){
  curFilter=cat;
  document.querySelectorAll('.f-item').forEach(i=>i.classList.remove('active'));
  el.classList.add('active');
  expanded={};
  // 금융 서브필터 선택 시 서브메뉴 열림 유지
  if(cat.startsWith('fin-')||cat==='금융경제'){
    document.getElementById('fin-sub').classList.add('open');
    document.getElementById('fin-toggle').classList.add('expanded');
  }
  render();
  if(window.innerWidth<=768&&document.getElementById('sidebar'))toggleSidebar();
}
function setView(v,el){curView=v;document.querySelectorAll('.v-btn').forEach(b=>b.classList.remove('active'));el.classList.add('active');render()}
function handleSearch(q){curSearch=q.toLowerCase();expanded={};render()}

/* 구독 바 */
function subBarNext(){
  const email=document.getElementById('sub-bar-email').value.trim();
  const msg=document.getElementById('sub-bar-msg');
  if(!email){msg.className='sub-bar-msg error';msg.textContent='이메일을 입력해주세요.';return}
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){msg.className='sub-bar-msg error';msg.textContent='유효한 이메일 주소를 입력해주세요.';return}
  msg.className='sub-bar-msg';msg.textContent='';
  document.getElementById('pop-email').value=email;
  document.getElementById('sub-overlay').classList.add('open');
  document.body.style.overflow='hidden';
  buildPopGrid();
}
function subBarMinistry(){
  const email=document.getElementById('sub-bar-email').value.trim();
  if(email)document.getElementById('pop-email').value=email;
  document.getElementById('sub-overlay').classList.add('open');
  document.body.style.overflow='hidden';
  buildPopGrid();
}

/* 구독 팝업 */
// 히어로 배너 닫기 (localStorage로 7일간 숨김)
function dismissHero(){
  document.getElementById('hero-banner').classList.add('hidden');
  localStorage.setItem('hero_dismissed', Date.now());
}
(function(){
  const d=localStorage.getItem('hero_dismissed');
  if(d && Date.now()-Number(d)<7*86400000)
    document.getElementById('hero-banner')?.classList.add('hidden');
})();

function openSubPopup(){
  const email=document.getElementById('header-email').value.trim();
  if(email)document.getElementById('pop-email').value=email;
  document.getElementById('sub-overlay').classList.add('open');
  document.body.style.overflow='hidden';
  buildPopGrid();
}
function closeSubPopup(){document.getElementById('sub-overlay').classList.remove('open');document.body.style.overflow=''}
function buildPopGrid(){
  const g=document.getElementById('pop-min-grid');g.innerHTML='';
  MINS.forEach(m=>{
    const el=document.createElement('div');el.className='mc'+(selMins.has(m)?' on':'');
    el.innerHTML=`<div class="mc-dot">${selMins.has(m)?'✓':''}</div><span class="mc-name">${m}</span>`;
    el.onclick=()=>{
      if(selMins.has(m)){selMins.delete(m);el.classList.remove('on');el.querySelector('.mc-dot').textContent=''}
      else{selMins.add(m);el.classList.add('on');el.querySelector('.mc-dot').textContent='✓'}
      document.getElementById('pop-cnt').textContent=selMins.size;
    };
    g.appendChild(el);
  });
}
const PRESETS={
  journalist: MINS,  // 전체
  finance: ['금융위원회','금융감독원','기획재정부','재정경제부','한국은행','한국거래소','예금보험공사','은행연합회','금융결제원','금융보안원','공정거래위원회'],
  tech: ['과학기술정보통신부','산업통상자원부','산업통상부','중소벤처기업부','개인정보보호위원회'],
  policy: ['기획재정부','재정경제부','보건복지부','고용노동부','교육부','행정안전부','법제처','국토교통부','환경부','기후에너지환경부'],
};

// 금융 서브카테고리 매핑
const FIN_SUB_MAP={
  '금융위원회':'금융정책','재정경제부':'금융정책','기획재정부':'금융정책','국세청':'금융정책','관세청':'금융정책',
  '금융감독원':'감독규제','공정거래위원회':'감독규제','예금보험공사':'감독규제',
  '한국은행':'시장통화','한국거래소':'시장통화','한국예탁결제원':'시장통화','한국투자공사':'시장통화',
  '금융결제원':'금융인프라','금융보안원':'금융인프라','한국신용정보원':'금융인프라',
  '한국산업은행':'정책금융','한국수출입은행':'정책금융','한국주택금융공사':'정책금융','신용보증기금':'정책금융','기술보증기금':'정책금융','서민금융진흥원':'정책금융','한국자산관리공사':'정책금융',
  '은행연합회':'업계동향','금융투자협회':'업계동향','보험개발원':'업계동향','한국증권금융':'업계동향',
  '산업통상자원부':'금융정책','산업통상부':'금융정책','조달청':'금융정책',
};

function toggleFinSub(el){
  el.classList.toggle('expanded');
  document.getElementById('fin-sub').classList.toggle('open');
}

function applyPreset(key){
  selMins.clear();
  (PRESETS[key]||[]).forEach(m=>selMins.add(m));
  document.getElementById('pop-cnt').textContent=selMins.size;
  buildPopGrid();
}
function toggleAll(){
  if(selMins.size===MINS.length){selMins.clear()}else{MINS.forEach(m=>selMins.add(m))}
  document.getElementById('pop-cnt').textContent=selMins.size;
  buildPopGrid();
}
async function doSubscribe(){
  const email=document.getElementById('pop-email').value.trim();
  const ministries=[...selMins];
  const btn=document.getElementById('pop-submit');
  const msg=document.getElementById('pop-msg');
  if(!email){msg.className='pop-msg error';msg.textContent='이메일을 입력해주세요.';return}
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){msg.className='pop-msg error';msg.textContent='유효한 이메일 주소를 입력해주세요.';return}
  if(!ministries.length){msg.className='pop-msg error';msg.textContent='부처를 하나 이상 선택해주세요.';return}
  btn.disabled=true;btn.textContent='처리 중...';
  try{
    const r=await fetch(SUB_API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,ministries})});
    const data=await r.json();
    if(data.success){
      msg.className='pop-msg success';msg.textContent=`✅ 구독 완료! ${ministries.length}개 부처의 보도자료를 ${email}로 보내드립니다.`;
      btn.textContent='완료!';
      setTimeout(()=>{closeSubPopup();document.getElementById('header-email').value='';selMins.clear();},2500);
    }else{msg.className='pop-msg error';msg.textContent=data.message||'오류가 발생했습니다.';}
  }catch(e){msg.className='pop-msg error';msg.textContent='서버 연결 오류.';}
  btn.disabled=false;if(btn.textContent==='처리 중...')btn.textContent='구독하기';
}
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeDetail();closeSubPopup()}if(e.key==='/'&&!e.target.matches('input,textarea')){e.preventDefault();document.getElementById('search-in').focus()}});
// URL 파라미터 처리
(async()=>{
  await loadCats();

  // 요일별 기본 날짜 설정
  const today = new Date();
  const wd = today.getDay(); // 0=일, 6=토
  const defaultDate = new Date(today);
  if(wd === 6) defaultDate.setDate(today.getDate()-1);       // 토→금
  else if(wd === 0) defaultDate.setDate(today.getDate()-2);  // 일→금
  else if(wd === 1) defaultDate.setDate(today.getDate()-3);  // 월→금
  else defaultDate.setDate(today.getDate()-1);               // 화~금→전날
  curDate = defaultDate;

  // URL 파라미터 확인
  const params = new URLSearchParams(window.location.search);
  const ministry = params.get('ministry');
  const dateParam = params.get('date');

  if(dateParam){
    const parts = dateParam.split('-');
    if(parts.length===3) curDate = new Date(parts[0], parts[1]-1, parts[2]);
  }

  await loadPosts();

  // 부처 필터 적용
  if(ministry){
    const el = [...document.querySelectorAll('.f-item')].find(
      el => el.querySelector('.f-left')?.textContent?.trim() === ministry
    );
    if(el) setFilter(ministry, el);
    // 모바일 탭도 없으면 전체 유지하고 JS 필터만 적용
    curFilter = ministry;
    render();
  }
})();
</script>

<!-- 모바일 하단 고정 CTA -->
<div class="mobile-cta">
  <span class="mobile-cta-text">27개 부처 보도자료</span>
  <button class="mobile-cta-btn" onclick="openSubPopup()">무료 이메일 구독 →</button>
</div>
</body>
</html>

<!-- Dynamic page generated in 0.225 seconds. -->
<!-- Cached page generated by WP-Super-Cache on 2026-03-21 08:31:05 -->

<!-- super cache -->