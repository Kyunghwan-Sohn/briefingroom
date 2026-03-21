<?php
get_header();
if ( have_posts() ) :
    while ( have_posts() ) : the_post();
$post_id = get_the_ID();
$source = get_post_meta($post_id, 'briefing_source', true);
$date = get_post_meta($post_id, 'briefing_date', true);
?>
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?php the_title(); ?> - 브리핑룸</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Pretendard:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#f5f4f0;--bg2:#eceae5;--surface:#fff;--border:#e0ddd7;--text:#1c1b18;--text2:#4a4844;--muted:#96938c;--accent:#2f54eb;--accent-l:#eef0fd;--serif:'Noto Serif KR',serif;--sans:'Pretendard',sans-serif;--mono:'DM Mono',monospace}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh}
body::before{content:'';position:fixed;inset:0;background-image:radial-gradient(circle at 1px 1px,var(--border) 1px,transparent 0);background-size:24px 24px;opacity:.5;pointer-events:none;z-index:0}
.wrap{max-width:720px;margin:0 auto;padding:32px 24px;position:relative;z-index:1}
.back{display:inline-flex;align-items:center;gap:6px;color:var(--muted);text-decoration:none;font-family:var(--mono);font-size:12px;margin-bottom:24px;padding:7px 14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;transition:all .15s}
.back:hover{color:var(--text);border-color:var(--border2)}
.post-badge{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:11px;padding:4px 12px;border-radius:6px;background:var(--accent-l);color:var(--accent);border:1px solid rgba(47,84,235,.2);margin-bottom:14px}
.post-title{font-family:var(--serif);font-size:26px;font-weight:700;letter-spacing:-.5px;line-height:1.35;color:var(--text);margin-bottom:20px}
.post-meta{display:flex;gap:20px;padding:14px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin-bottom:24px}
.meta-i{font-family:var(--mono);font-size:11px;color:var(--muted);display:flex;flex-direction:column;gap:3px}
.meta-i strong{color:var(--text2);font-weight:500}
.post-content{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px}
.briefing-source{font-family:var(--mono);font-size:12px;color:var(--muted)}
.briefing-date{font-family:var(--mono);font-size:12px;color:var(--muted);margin-left:12px}
.briefing-summary h3{font-family:var(--serif);font-size:16px;font-weight:600;color:var(--text);margin:16px 0 10px}
.briefing-summary p{font-size:14px;color:var(--text2);line-height:1.8;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:14px 16px}
.briefing-keywords{display:flex;flex-wrap:wrap;gap:5px;margin:16px 0}
.briefing-keywords span{font-family:var(--mono);font-size:11px;color:var(--text2);background:var(--bg2);border:1px solid var(--border);padding:3px 10px;border-radius:4px}
.briefing-links h4{font-family:var(--serif);font-size:14px;font-weight:600;color:var(--text);margin:16px 0 8px}
.briefing-links ul{list-style:none;display:flex;flex-direction:column;gap:6px}
.briefing-links a{color:var(--accent);text-decoration:none;font-size:13px;font-family:var(--mono)}
.briefing-links a:hover{text-decoration:underline}
@media(max-width:768px){.wrap{padding:20px 16px}.post-title{font-size:20px}}
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="/">&#8592; 브리핑룸으로</a>
  <div class="post-badge">📋 브리핑룸 보도자료</div>
  <h1 class="post-title"><?php the_title(); ?></h1>
  <div class="post-meta">
    <div class="meta-i"><span>날짜</span><strong><?php echo get_the_date('Y-m-d'); ?></strong></div>
    <div class="meta-i"><span>카테고리</span><strong><?php the_category(', '); ?></strong></div>
  </div>
  <div class="post-content">
    <?php the_content(); ?>
  </div>
</div>
</body>
</html>
<?php
    endwhile;
endif;
