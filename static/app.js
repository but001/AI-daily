// 前端交互：搜索 / 来源筛选 / 日期范围 / 清空 / 复制为 Markdown 引用 / 阅读历史
// 设计原则：纯原生 JS，零依赖，静态页面也能离线运行

(function () {
  "use strict";

  var searchInput = document.getElementById("search");
  var searchBtn = document.getElementById("search-btn");
  var sourceFilter = document.getElementById("source-filter");
  var dateRange = document.querySelector(".date-range");
  var clearBtn = document.getElementById("clear-filters");
  var emptyState = document.getElementById("empty-state");
  var linkClear = document.querySelector(".link-clear");
  var hotZone = document.getElementById("hot-zone");
  var readingListEl = document.getElementById("reading-list");
  var readingEmpty = document.getElementById("reading-empty");
  var clearReadingBtn = document.getElementById("clear-reading");
  var cards = Array.prototype.slice.call(
    document.querySelectorAll("#news-container .news-card")
  );

  // 当前激活的日期范围：today / 7d / all
  var activeRange = "7d";
  // 是否首页（首页默认 7d；归档页默认 all）
  var today = (function () {
    // 取页面里任意一条卡片的 data-pub 反推"今日"不准；改用 build 时注入的 today
    var meta = document.querySelector("meta[name='today']");
    return null;
  })();

  // 从 URL 或 BODY class 判断是否归档页：归档页没有 date-range 控件
  var hasDateRange = !!dateRange;

  function todayStr() {
    // 用浏览器本地时区日期；与采集端北京时区一致即可
    var d = new Date();
    // 转换为 Asia/Shanghai 近似：东八区时间 = UTC + 8
    var utc = d.getTime() + d.getTimezoneOffset() * 60000;
    var bj = new Date(utc + 8 * 3600000);
    var m = (bj.getMonth() + 1).toString().padStart(2, "0");
    var day = bj.getDate().toString().padStart(2, "0");
    return bj.getFullYear() + "-" + m + "-" + day;
  }

  function within7d(pubDate) {
    if (!pubDate) return false;
    var today = new Date(todayStr() + "T00:00:00");
    var pub = new Date(pubDate + "T00:00:00");
    if (isNaN(pub.getTime())) return false;
    var diff = (today - pub) / 86400000;
    return diff >= 0 && diff <= 6;
  }

  function matchCard(card) {
    var q = (searchInput.value || "").trim().toLowerCase();
    var src = sourceFilter ? sourceFilter.value : "";
    var title = (card.getAttribute("data-title") || "").toLowerCase();
    var summary = (card.getAttribute("data-summary") || "").toLowerCase();
    var cardSrc = card.getAttribute("data-source") || "";
    var pub = card.getAttribute("data-pub") || "";

    if (q && title.indexOf(q) === -1 && summary.indexOf(q) === -1) return false;
    if (src && cardSrc !== src) return false;
    if (hasDateRange) {
      if (activeRange === "today" && pub !== todayStr()) return false;
      if (activeRange === "7d" && !within7d(pub)) return false;
      // 'all' 不筛选
    }
    return true;
  }

  function applyFilters() {
    var visibleCount = 0;
    // 搜索激活（输入非空）时隐藏今日热点区，避免与列表结果混淆
    var q = (searchInput && searchInput.value || "").trim();
    if (hotZone) hotZone.classList.toggle("hidden", !!q);
    cards.forEach(function (card) {
      var ok = matchCard(card);
      card.classList.toggle("hidden", !ok);
      if (ok) visibleCount++;
    });
    if (emptyState) emptyState.hidden = visibleCount !== 0;
    // 同步更新列表标题中的可见数量
    var countEl = document.getElementById("visible-count");
    if (countEl) countEl.textContent = String(visibleCount);
  }

  // 搜索：点按钮或按 Enter 才触发，避免边输入边过滤
  if (searchBtn) searchBtn.addEventListener("click", applyFilters);
  if (searchInput) {
    searchInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === "Enter ") {
        e.preventDefault();
        applyFilters();
      }
    });
  }

  // 来源筛选
  if (sourceFilter) {
    sourceFilter.addEventListener("change", applyFilters);
  }

  // 日期范围切换
  if (dateRange) {
    dateRange.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-range]");
      if (!btn) return;
      Array.prototype.forEach.call(
        dateRange.querySelectorAll("button"),
        function (b) { b.classList.remove("active"); }
      );
      btn.classList.add("active");
      activeRange = btn.getAttribute("data-range");
      applyFilters();
    });
  }

  // 清空
  function clearAll() {
    if (searchInput) searchInput.value = "";
    if (sourceFilter) sourceFilter.value = "";
    if (hotZone) hotZone.classList.remove("hidden");
    if (dateRange) {
      Array.prototype.forEach.call(
        dateRange.querySelectorAll("button"),
        function (b) { b.classList.remove("active"); }
      );
      var defaultBtn = dateRange.querySelector('button[data-range="7d"]');
      if (defaultBtn) defaultBtn.classList.add("active");
      activeRange = "7d";
    }
    applyFilters();
  }
  if (clearBtn) clearBtn.addEventListener("click", clearAll);
  if (linkClear) linkClear.addEventListener("click", clearAll);

  // 复制为 Markdown 引用
  function buildMarkdown(btn) {
    var title = btn.getAttribute("data-title") || "";
    var summary = btn.getAttribute("data-summary") || "";
    var link = btn.getAttribute("data-link") || "";
    var source = btn.getAttribute("data-source") || "";
    var time = btn.getAttribute("data-time") || "发布时间未知";

    var md = [];
    md.push("> **" + title + "**");
    md.push("> ");
    if (summary) {
      summary.split("\n").forEach(function (line) {
        md.push("> " + line);
      });
      md.push("> ");
    }
    md.push("> 来源：" + source + " · " + time);
    md.push("> 原文：" + link);
    return md.join("\n");
  }

  function showToast(msg, isError) {
    var toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.toggle("error", !!isError);
    toast.hidden = false;
    setTimeout(function () { toast.hidden = true; }, 1800);
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".copy-md");
    if (!btn) return;
    e.preventDefault();
    var text = buildMarkdown(btn);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { showToast("已复制为 Markdown 引用"); },
        function () { fallbackCopy(text); }
      );
    } else {
      fallbackCopy(text);
    }
  });

  function fallbackCopy(text) {
    // 老式 execCommand 兜底（如非 HTTPS 环境）
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      showToast(ok ? "已复制为 Markdown 引用" : "复制失败", !ok);
    } catch (err) {
      showToast("复制失败：" + err.message, true);
    }
  }

  // ── 阅读历史（localStorage） ──
  // 数据结构：[{ title, link, source, summary, pub, read_at }]
  var STORAGE_KEY = "ai_daily_reading_history";
  var MAX_RECORDS = 200;

  function loadReading() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function saveReading(list) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch (e) {
      // 容量满或无痕模式：静默失败，不阻塞用户点击
    }
  }

  function recordReading(card) {
    var link = card.getAttribute("data-link") || card.querySelector("a")?.href || "";
    if (!link) return;
    var title = card.getAttribute("data-title") || card.querySelector(".card-title a")?.textContent?.trim() || "";
    var source = card.getAttribute("data-source") || "";
    var summary = card.getAttribute("data-summary") || "";
    var pub = card.getAttribute("data-pub") || "";

    var list = loadReading();
    // 去重：同链接只保留最近一次
    list = list.filter(function (it) { return it.link !== link; });
    list.unshift({
      title: title,
      link: link,
      source: source,
      summary: summary,
      pub: pub,
      read_at: new Date().toISOString()
    });
    if (list.length > MAX_RECORDS) list = list.slice(0, MAX_RECORDS);
    saveReading(list);
  }

  // 监听卡片标题链接点击 → 记录（不影响跳转）
  document.addEventListener("click", function (e) {
    var link = e.target.closest(".news-card .card-title a");
    if (!link) return;
    var card = link.closest(".news-card");
    if (card) recordReading(card);
    // 不阻止默认跳转，让用户正常打开原文
  });

  // 在「我的阅读」页面渲染列表
  function renderReadingList() {
    if (!readingListEl) return;
    var list = loadReading();
    readingListEl.innerHTML = "";
    if (list.length === 0) {
      if (readingEmpty) readingEmpty.hidden = false;
      return;
    }
    if (readingEmpty) readingEmpty.hidden = true;
    list.forEach(function (it) {
      var article = document.createElement("article");
      article.className = "news-card";
      var head = document.createElement("div");
      head.className = "card-head";
      var src = document.createElement("span");
      src.className = "src-name";
      src.textContent = it.source || "未知来源";
      head.appendChild(src);
      var time = document.createElement("time");
      time.className = "pub-time";
      time.setAttribute("datetime", it.read_at || "");
      time.textContent = "阅读于 " + fmtReadingTime(it.read_at);
      head.appendChild(time);
      article.appendChild(head);

      var title = document.createElement("h3");
      title.className = "card-title";
      var a = document.createElement("a");
      a.href = it.link;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = it.title;
      title.appendChild(a);
      article.appendChild(title);

      if (it.summary) {
        var sum = document.createElement("p");
        sum.className = "card-summary";
        sum.textContent = it.summary;
        article.appendChild(sum);
      }
      readingListEl.appendChild(article);
    });
  }

  function fmtReadingTime(iso) {
    if (!iso) return "未知时间";
    try {
      var d = new Date(iso);
      var pad = function (n) { return n.toString().padStart(2, "0"); };
      return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate())
        + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
    } catch (e) {
      return iso;
    }
  }

  // 清空阅读历史
  if (clearReadingBtn) {
    clearReadingBtn.addEventListener("click", function () {
      if (!confirm("确定清空全部阅读历史？此操作不可撤销。")) return;
      saveReading([]);
      renderReadingList();
      showToast("已清空阅读历史");
    });
  }

  // 如果当前页是「我的阅读」页（有 reading-list 容器），初始渲染
  if (readingListEl) renderReadingList();

  // 初始：首页默认显示最近7天
  applyFilters();
})();
