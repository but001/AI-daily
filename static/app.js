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

  // 当前激活的日期段：null = 不筛选；[startDate, endDate] = 闭区间
  var activeDateRange = null;
  // 是否有日期段控件
  var hasDateRange = !!dateRange;
  // 当前快捷选项模式：'today' | '7d' | '30d' | 'custom'；默认 '7d'
  var activeQuick = "7d";

  // 初始化日期段下拉选项
  function initDatePickers() {
    if (!dateRange) return;
    var sy = document.getElementById("date-start-y");
    var sm = document.getElementById("date-start-m");
    var sd = document.getElementById("date-start-d");
    var ey = document.getElementById("date-end-y");
    var em = document.getElementById("date-end-m");
    var ed = document.getElementById("date-end-d");
    if (!sy || !ey) return;

    // 用页面 meta today 注入"今日"，没有则用浏览器本地日期
    var meta = document.querySelector("meta[name='today']");
    var todayStr = meta ? meta.content : (function () {
      var d = new Date();
      var utc = d.getTime() + d.getTimezoneOffset() * 60000;
      var bj = new Date(utc + 8 * 3600000);
      var p = function (n) { return n.toString().padStart(2, "0"); };
      return bj.getFullYear() + "-" + p(bj.getMonth() + 1) + "-" + p(bj.getDate());
    })();

    // 年份范围：从卡片数据最早年到今年
    var minYear = new Date().getFullYear();
    cards.forEach(function (c) {
      var p = c.getAttribute("data-pub") || "";
      if (p) {
        var y = parseInt(p.slice(0, 4), 10);
        if (!isNaN(y) && y < minYear) minYear = y;
      }
    });
    var maxYear = new Date().getFullYear();

    function fillYear(sel) {
      sel.innerHTML = "";
      for (var y = maxYear; y >= minYear; y--) {
        var o = document.createElement("option");
        o.value = y; o.textContent = y;
        sel.appendChild(o);
      }
    }
    function fillMonth(sel) {
      sel.innerHTML = "";
      for (var m = 1; m <= 12; m++) {
        var o = document.createElement("option");
        o.value = m; o.textContent = m;
        sel.appendChild(o);
      }
    }
    function fillDay(sel) {
      sel.innerHTML = "";
      for (var d = 1; d <= 31; d++) {
        var o = document.createElement("option");
        o.value = d; o.textContent = d;
        sel.appendChild(o);
      }
    }
    fillYear(sy); fillMonth(sm); fillDay(sd);
    fillYear(ey); fillMonth(em); fillDay(ed);

    // 默认：起止都是今日
    var parts = todayStr.split("-");
    sy.value = parts[0]; sm.value = parseInt(parts[1], 10); sd.value = parseInt(parts[2], 10);
    ey.value = parts[0]; em.value = parseInt(parts[1], 10); ed.value = parseInt(parts[2], 10);
  }

  // 读取当前下拉值，返回 [startDateStr, endDateStr] 或 null
  function readDateRange() {
    var sy = document.getElementById("date-start-y");
    var ey = document.getElementById("date-end-y");
    if (!sy || !ey) return null;
    var sm = document.getElementById("date-start-m");
    var sd = document.getElementById("date-start-d");
    var em = document.getElementById("date-end-m");
    var ed = document.getElementById("date-end-d");
    function p2(n) { return n.toString().padStart(2, "0"); }
    var sStr = sy.value + "-" + p2(parseInt(sm.value, 10)) + "-" + p2(parseInt(sd.value, 10));
    var eStr = ey.value + "-" + p2(parseInt(em.value, 10)) + "-" + p2(parseInt(ed.value, 10));
    return [sStr, eStr];
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
    // 日期段：闭区间 [start, end]；缺失时间不参与筛选
    if (activeDateRange) {
      if (!pub) return false;
      if (pub < activeDateRange[0] || pub > activeDateRange[1]) return false;
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

  // 主按钮组：今天 / 最近 7 天 / 最近 30 天 / 自定义…
  var customTrigger = document.getElementById("custom-trigger");
  var popover = document.getElementById("date-popover");

  function setQuickMode(mode) {
    activeQuick = mode;
    // 主按钮组高亮
    if (dateRange) {
      Array.prototype.forEach.call(
        dateRange.querySelectorAll("button[data-quick]"),
        function (b) { b.classList.remove("active"); }
      );
      var cur = dateRange.querySelector('button[data-quick="' + mode + '"]');
      if (cur) cur.classList.add("active");
    }
    // 计算对应日期段
    activeDateRange = computeQuickRange(mode);
    applyFilters();
  }

  // 把快捷模式转成 [start, end] 日期字符串
  function computeQuickRange(mode) {
    var meta = document.querySelector("meta[name='today']");
    var todayStr = meta ? meta.content : (function () {
      var d = new Date();
      var utc = d.getTime() + d.getTimezoneOffset() * 60000;
      var bj = new Date(utc + 8 * 3600000);
      var p = function (n) { return n.toString().padStart(2, "0"); };
      return bj.getFullYear() + "-" + p(bj.getMonth() + 1) + "-" + p(bj.getDate());
    })();
    var t = new Date(todayStr + "T00:00:00");
    function fmt(d) {
      var p = function (n) { return n.toString().padStart(2, "0"); };
      return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
    }
    if (mode === "today") {
      return [todayStr, todayStr];
    }
    if (mode === "yesterday") {
      var y = new Date(t.getTime() - 86400000);
      var ys = fmt(y);
      return [ys, ys];
    }
    if (mode === "7d") {
      var s = new Date(t.getTime() - 6 * 86400000);
      return [fmt(s), todayStr];
    }
    if (mode === "30d") {
      var s30 = new Date(t.getTime() - 29 * 86400000);
      return [fmt(s30), todayStr];
    }
    if (mode === "month") {
      var first = new Date(t.getFullYear(), t.getMonth(), 1);
      return [fmt(first), todayStr];
    }
    return null;
  }

  if (dateRange) {
    dateRange.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-quick]");
      if (!btn) return;
      setQuickMode(btn.getAttribute("data-quick"));
      // 切到快捷模式时关闭弹出层
      if (popover) popover.hidden = true;
    });
  }

  // 自定义触发器：开关弹出层
  if (customTrigger) {
    customTrigger.addEventListener("click", function () {
      if (!popover) return;
      popover.hidden = !popover.hidden;
    });
  }

  // 弹出层快捷选项
  var popoverEl = popover;
  if (popoverEl) {
    popoverEl.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-pop-quick]");
      if (!btn) return;
      var mode = btn.getAttribute("data-pop-quick");
      var range = computeQuickRange(mode);
      if (range) {
        // 把起止日期填入下拉
        setPickerValue("date-start", range[0]);
        setPickerValue("date-end", range[1]);
      }
    });
  }

  // 把 "YYYY-MM-DD" 填到下拉组
  function setPickerValue(prefix, dateStr) {
    var parts = dateStr.split("-");
    var y = document.getElementById(prefix + "-y");
    var m = document.getElementById(prefix + "-m");
    var d = document.getElementById(prefix + "-d");
    if (y) y.value = parseInt(parts[0], 10);
    if (m) m.value = parseInt(parts[1], 10);
    if (d) d.value = parseInt(parts[2], 10);
  }

  // 弹出层：确定 = 应用自定义日期段；清除 = 回到默认"最近 7 天"
  var dateApplyBtn = document.getElementById("date-apply");
  var dateResetBtn = document.getElementById("date-reset");
  if (dateApplyBtn) {
    dateApplyBtn.addEventListener("click", function () {
      activeDateRange = readDateRange();
      activeQuick = "custom";
      // 主按钮组取消高亮
      if (dateRange) {
        Array.prototype.forEach.call(
          dateRange.querySelectorAll("button[data-quick]"),
          function (b) { b.classList.remove("active"); }
        );
      }
      if (customTrigger) customTrigger.classList.add("active");
      if (popover) popover.hidden = true;
      applyFilters();
    });
  }
  if (dateResetBtn) {
    dateResetBtn.addEventListener("click", function () {
      if (popover) popover.hidden = true;
      setQuickMode("7d");  // 清除后回到默认"最近 7 天"
    });
  }

  // 点击弹出层外部关闭
  document.addEventListener("click", function (e) {
    if (!popover || popover.hidden) return;
    if (popover.contains(e.target)) return;
    if (customTrigger && customTrigger.contains(e.target)) return;
    popover.hidden = true;
  });

  // 清空：清除搜索词、来源筛选；日期回到默认"最近 7 天"
  function clearAll() {
    if (searchInput) searchInput.value = "";
    if (sourceFilter) sourceFilter.value = "";
    if (hotZone) hotZone.classList.remove("hidden");
    if (popover) popover.hidden = true;
    setQuickMode("7d");
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

  // 初始化日期段下拉（首页有 date-range 控件时）
  initDatePickers();

  // 初始：默认"最近 7 天"
  if (dateRange) {
    setQuickMode("7d");
  } else {
    applyFilters();
  }
})();
