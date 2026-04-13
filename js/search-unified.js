/**
 * searchUnified.js — govbrief.kr 통합 검색
 * Supabase 직접 호출, 법령/조문/판례 3개 테이블 병렬 쿼리
 * 사용법: initSearch(inputEl, resultsEl, options)
 */
(function(window) {
  'use strict';

  var SB_URL = 'https://jxoghnttelexnfoeepbz.supabase.co';
  var SB_KEY = 'sb_publishable_r3eTQXF419LfIiPdE17gyw_zvAQFd5s';
  var SB_HDR = { 'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY };

  var TYPE_LABEL = { law: '법령', article: '조문', precedent: '판례' };

  function searchSupabase(query) {
    var kw = '%' + query + '%';
    var ekw = encodeURIComponent(kw);
    return Promise.all([
      fetch(SB_URL + '/rest/v1/laws?or=(name.ilike.' + ekw + ',amendment_reason.ilike.' + ekw + ')&select=law_id,name,ministry,law_type&limit=5', { headers: SB_HDR }).then(function(r) { return r.json(); }),
      fetch(SB_URL + '/rest/v1/articles?or=(article_title.ilike.' + ekw + ',content.ilike.' + ekw + ')&select=id,law_id,article_no,article_title&limit=5', { headers: SB_HDR }).then(function(r) { return r.json(); }),
      fetch(SB_URL + '/rest/v1/precedents?or=(case_name.ilike.' + ekw + ',summary.ilike.' + ekw + ')&select=prec_id,case_name,court,decision_date&limit=5', { headers: SB_HDR }).then(function(r) { return r.json(); })
    ]).then(function(res) {
      var items = [];
      (res[0] || []).forEach(function(r) {
        items.push({ type: 'law', title: r.name, subtitle: (r.ministry || '') + ' ' + (r.law_type || ''), link: '/finlaw/detail/' + r.law_id + '/' });
      });
      (res[1] || []).forEach(function(r) {
        items.push({ type: 'article', title: (r.article_no ? '제' + r.article_no + '조 ' : '') + (r.article_title || ''), subtitle: '', link: '/finlaw/detail/' + r.law_id + '/' });
      });
      (res[2] || []).forEach(function(r) {
        items.push({ type: 'precedent', title: r.case_name, subtitle: (r.court || '') + ' ' + (r.decision_date || ''), link: '/finlaw/cases/' + r.prec_id + '/' });
      });
      return items;
    });
  }

  function renderResults(container, items, query, askUrl) {
    container.textContent = '';
    var gptUrl = askUrl || '/regulation/finlaw-gpt/?q=' + encodeURIComponent(query);

    if (items.length) {
      items.forEach(function(item) {
        var link = document.createElement('a');
        link.href = item.link || gptUrl;
        link.style.cssText = 'display:block;padding:12px 16px;border-bottom:1px solid #e0e0e0;text-decoration:none;color:#222';
        var top = document.createElement('div');
        top.style.cssText = 'display:flex;align-items:center;gap:8px';
        var badge = document.createElement('span');
        badge.style.cssText = 'font-size:9px;font-weight:700;padding:2px 6px;border-radius:4px;background:rgba(217,108,44,.06);color:#d96c2c';
        badge.textContent = TYPE_LABEL[item.type] || item.type || '';
        var title = document.createElement('span');
        title.style.cssText = 'font-size:14px;font-weight:600';
        title.textContent = String(item.title || '').slice(0, 60);
        top.appendChild(badge);
        top.appendChild(title);
        var sub = document.createElement('div');
        sub.style.cssText = 'font-size:12px;color:#999;margin-top:3px';
        sub.textContent = String(item.subtitle || '').slice(0, 80);
        link.appendChild(top);
        link.appendChild(sub);
        container.appendChild(link);
      });
    } else {
      var empty = document.createElement('div');
      empty.style.cssText = 'padding:16px;text-align:center;font-size:13px;color:#999';
      empty.textContent = '검색 결과가 없습니다.';
      container.appendChild(empty);
    }

    var cta = document.createElement('a');
    cta.href = gptUrl;
    cta.style.cssText = 'display:block;padding:12px 16px;text-align:center;font-size:13px;color:#d96c2c;font-weight:600;text-decoration:none';
    cta.textContent = items.length ? 'AI에게 상세 질문 \u2192' : 'AI에게 질문하기 \u2192';
    container.appendChild(cta);
    container.style.display = 'block';
  }

  /**
   * initSearch - 검색 입력과 결과 컨테이너를 연결
   * @param {HTMLElement} inputEl - 검색 input 요소
   * @param {HTMLElement} resultsEl - 결과 드롭다운 컨테이너
   * @param {Object} options - { askUrl, minLength, debounce }
   */
  function initSearch(inputEl, resultsEl, options) {
    if (!inputEl || !resultsEl) return;
    var opts = options || {};
    var askUrl = opts.askUrl || null;
    var minLen = opts.minLength || 2;
    var debounceMs = opts.debounce || 300;
    var timer;

    inputEl.addEventListener('input', function() {
      clearTimeout(timer);
      var q = this.value.trim();
      if (q.length < minLen) { resultsEl.style.display = 'none'; return; }
      timer = setTimeout(function() {
        searchSupabase(q).then(function(items) {
          renderResults(resultsEl, items, q, askUrl);
        }).catch(function() {
          renderResults(resultsEl, [], q, askUrl);
        });
      }, debounceMs);
    });

    inputEl.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.isComposing) {
        var q = this.value.trim();
        if (q) window.location.href = (askUrl || '/regulation/finlaw-gpt/') + '?q=' + encodeURIComponent(q);
      }
    });

    document.addEventListener('click', function(e) {
      if (!e.target.closest('.search-unified-wrap')) resultsEl.style.display = 'none';
    });
  }

  // 테이블 필터 공통 함수
  function initTableFilter(inputId, tableId, countId) {
    var input = document.getElementById(inputId);
    var table = document.getElementById(tableId);
    if (!input || !table) return;
    var rows = table.querySelectorAll('tbody tr');
    var countEl = countId ? document.getElementById(countId) : null;

    function filter() {
      var terms = input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      var visible = 0;
      rows.forEach(function(row) {
        var text = row.textContent.toLowerCase();
        var match = !terms.length || terms.every(function(t) { return text.indexOf(t) >= 0; });
        row.style.display = match ? '' : 'none';
        if (match) visible++;
      });
      if (countEl) countEl.textContent = terms.length ? visible + '/' + rows.length + '건' : rows.length + '건';
    }

    input.addEventListener('input', filter);
    filter();
  }

  window.govSearch = {
    init: initSearch,
    initTableFilter: initTableFilter,
    search: searchSupabase
  };

})(window);
