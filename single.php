<?php
get_header();
if ( have_posts() ) :
    while ( have_posts() ) : the_post();
?>
<style>
.briefingroom-single{--bg:#f5f4f0;--surface:#fff;--border:#e0ddd7;--text:#1c1b18;--text2:#4a4844;--muted:#96938c;--accent:#2f54eb;--accent-l:#eef0fd;--serif:'Noto Serif KR',serif;--sans:'Pretendard',sans-serif;--mono:'DM Mono',monospace;background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;padding:32px 0}
.briefingroom-single *,.briefingroom-single *::before,.briefingroom-single *::after{box-sizing:border-box}
.briefingroom-single::before{content:'';position:fixed;inset:0;background-image:radial-gradient(circle at 1px 1px,var(--border) 1px,transparent 0);background-size:24px 24px;opacity:.5;pointer-events:none;z-index:0}
.briefingroom-single .wrap{max-width:720px;margin:0 auto;padding:0 24px;position:relative;z-index:1}
.briefingroom-single .back{display:inline-flex;align-items:center;gap:6px;color:var(--muted);text-decoration:none;font-family:var(--mono);font-size:12px;margin-bottom:24px;padding:7px 14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;transition:all .15s}
.briefingroom-single .back:hover{color:var(--text)}
.briefingroom-single .post-badge{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:11px;padding:4px 12px;border-radius:6px;background:var(--accent-l);color:var(--accent);border:1px solid rgba(47,84,235,.2);margin-bottom:14px}
.briefingroom-single .post-title{font-family:var(--serif);font-size:26px;font-weight:700;letter-spacing:-.5px;line-height:1.35;color:var(--text);margin-bottom:20px}
.briefingroom-single .post-meta{display:flex;gap:20px;padding:14px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin-bottom:24px}
.briefingroom-single .meta-i{font-family:var(--mono);font-size:11px;color:var(--muted);display:flex;flex-direction:column;gap:3px}
.briefingroom-single .meta-i strong{color:var(--text2);font-weight:500}
.briefingroom-single .post-content{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px}
@media(max-width:768px){.briefingroom-single{padding:20px 0}.briefingroom-single .wrap{padding:0 16px}.briefingroom-single .post-title{font-size:20px}}
</style>
<main class="briefingroom-single">
  <div class="wrap">
    <a class="back" href="/">&#8592; 브리핑룸으로</a>
    <div class="post-badge">📋 브리핑룸 보도자료</div>
    <h1 class="post-title"><?php the_title(); ?></h1>
    <div class="post-meta">
      <div class="meta-i"><span>날짜</span><strong><?php echo esc_html( get_the_date( 'Y-m-d' ) ); ?></strong></div>
      <div class="meta-i"><span>카테고리</span><strong><?php the_category( ', ' ); ?></strong></div>
    </div>
    <div class="post-content">
      <?php the_content(); ?>
    </div>
  </div>
</main>
<?php
    endwhile;
endif;
get_footer();
