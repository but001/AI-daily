// 前端交互：搜索 / 来源筛选 / 日期范围 / 清空 / 复制为 Markdown 引用
// 设计原则：纯原生 JS，零依赖，静态页面也能离线运行

(function () {
  "use strict";

  var searchInput = document.getElementById("search");
  var sourceFilter = document.getElementById("source-filter");
  var dateRange = document.querySelector(".date-range");
  var clearBtn = document.getElementById("clear-filters");
  var emptyState = document.getElementById("empty-state");
  var linkClear = document.querySelector(".link-clear");
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
    cards.forEach(function (card) {
      var ok = matchCard(card);
      card.classList.toggle("hidden", !ok);
      if (ok) visibleCount++;
    });
    if (emptyState) emptyState.hidden = visibleCount !== 0;
  }

  // 搜索：input 防抖
  var searchTimer = null;
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(applyFilters, 120);
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

  // 初始：首页默认显示最近7天
  applyFilters();
})();
