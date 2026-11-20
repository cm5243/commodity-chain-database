/* 产业链数据库 · 多品种本地静态版（布局与交互严格参考期市金研） */
(function (global) {
  "use strict";
  var DB = global.DB;
  var COMS = DB.commodities;
  var charts = [];

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function loading(t) { return '<div class="loading">' + esc(t) + "</div>"; }
  function getCom(cid) { return COMS.filter(function (c) { return c.id === cid; })[0]; }
  function findSheet(com, sid) { return com.sheets.filter(function (s) { return s.id === sid; })[0]; }
  function totals() {
    var sec = 0, ch = 0;
    COMS.forEach(function (c) { sec += c.sheets.length; ch += c.chartCount; });
    return { sec: sec, ch: ch };
  }

  /* ---------- 路由 ---------- */
  function parseRoute() {
    var h = location.hash.replace(/^#/, "") || "/";
    var qm = h.indexOf("?");
    var query = qm >= 0 ? h.slice(qm + 1) : "";
    var path = qm >= 0 ? h.slice(0, qm) : h;
    return { parts: path.split("/").filter(Boolean), query: query };
  }
  function setNav(key) {
    $$("#nav .nav-link").forEach(function (a) {
      a.classList.toggle("on", a.getAttribute("data-key") === key);
    });
  }
  function route() {
    var r = parseRoute(), p = r.parts;
    charts = [];
    if (p[0] === "data" && p[1] && p[2]) {
      setNav("data"); viewSection(p[1], p[2], r.query);
    } else if (p[0] === "data" && p[1]) {
      /* 品种页已移除：直接进该品种第一个板块 */
      var com0 = getCom(p[1]);
      if (com0 && com0.sheets[0]) { location.replace("#/data/" + com0.id + "/" + com0.sheets[0].id); return; }
      setNav("data"); viewHome();
    } else if (p[0] === "data") {
      setNav("data"); viewHome();
    } else if (p[0] === "about") {
      setNav("about"); viewAbout();
    } else {
      setNav("home"); viewHome();
    }
  }

  /* ---------- 首页：品种库 ---------- */
  function viewHome() {
    var t = totals();
    var cards = COMS.map(function (c) {
      var first = c.sheets[0];
      return '<a class="lib-card" style="--accent:' + c.color + '" href="#/data/' + c.id + "/" + (first ? first.id : "") + '">' +
        '<div class="lib-top"><span class="lib-name">' + esc(c.name) + "</span>" +
        '<span class="lib-tag">' + c.sheets.length + " 板块</span></div>" +
        '<div class="lib-desc">' + esc(first ? first.title.replace(/^\d+\s*/, "") + " 等" : "") + "</div>" +
        '<div class="lib-foot"><span>截至 ' + esc(c.updated || "—") + "</span><b>" + c.chartCount + " 图</b></div>" +
        "</a>";
    }).join("");
    $("#view").innerHTML =
      '<div class="section"><div class="section-head"><h2>品种库</h2>' +
      '<span class="hint">' + COMS.length + " 品种 / " + t.sec + " 板块 / " + t.ch + " 张图 · 分年季节性叠图</span></div>" +
      '<div class="lib-grid">' + cards + "</div></div>";
    window.scrollTo(0, 0);
  }

  /* ---------- 品种板块总览 ---------- */
  function sectionCards(com) {
    return com.sheets.map(function (s) {
      var first = s.charts[0];
      var desc = s.subtitle.split("｜")[0];
      return '<a class="lib-card" style="--accent:' + com.color + '" href="#/data/' + com.id + "/" + s.id + '">' +
        '<div class="lib-top"><span class="lib-name">' + esc(s.title.replace(/^\d+\s*/, "")) + "</span>" +
        '<span class="lib-tag">' + esc(s.title.slice(0, 2)) + "</span></div>" +
        '<div class="lib-desc">' + esc(desc) + "</div>" +
        '<div class="lib-foot"><span>' + (first ? esc(first.name) : "") + "</span><b>" + s.charts.length + " 图</b></div>" +
        "</a>";
    }).join("");
  }
  function viewCommodity(cid) {
    var com = getCom(cid);
    if (!com) { viewHome(); return; }
    $("#view").innerHTML =
      '<div class="section"><div class="section-head">' +
      '<h2><a class="crumb" href="#/">品种库</a> / ' + esc(com.name) + "</h2>" +
      '<span class="hint">' + com.sheets.length + " 板块 / " + com.chartCount + " 张图 · 截至 " + esc(com.updated || "—") + "</span></div>" +
      '<div class="lib-grid">' + sectionCards(com) + "</div></div>";
    window.scrollTo(0, 0);
  }

  /* ---------- 板块视图 ---------- */
  function switcher(cur) {
    return '<div class="side-switch"><select id="com-switch" aria-label="切换品种">' +
      COMS.map(function (c) {
        return '<option value="' + c.id + '"' + (c.id === cur ? " selected" : "") + ">" + esc(c.name) + "</option>";
      }).join("") + "</select></div>";
  }
  function viewSection(cid, sid, query) {
    var com = getCom(cid);
    if (!com) { viewHome(); return; }
    var sheet = findSheet(com, sid) || com.sheets[0];
    $("#view").innerHTML =
      '<div class="data-layout">' +
        '<aside class="sidebar">' +
          '<div class="side-head"><a class="back" href="#/">← 品种库</a>' +
            '<h2 style="--accent:' + com.color + '">' + esc(com.name) + "数据库</h2>" +
            '<div class="side-sub">' + com.sheets.length + " 板块 / " + com.chartCount + " 张图</div>" +
          "</div>" +
          switcher(com.id) +
          '<div class="side-search"><input id="side-q" placeholder="搜索全部品种图表…" autocomplete="off"></div>' +
          '<nav class="side-nav">' + com.sheets.map(function (s) {
            return '<a href="#/data/' + com.id + "/" + s.id + '" class="' + (s.id === sheet.id ? "on" : "") +
              '" data-sheet="' + s.id + '">' + esc(s.title) + "</a>";
          }).join("") + "</nav>" +
          '<div id="search-results" class="search-results"></div>' +
        "</aside>" +
        '<main class="data-main" id="data-main">' + loading("正在加载板块数据…") + "</main>" +
      "</div>";
    $("#com-switch").addEventListener("change", function () { location.hash = "#/data/" + this.value; });
    $("#side-q").addEventListener("input", function () { searchIn(this.value); });
    renderSheet(com, sheet, query);
  }

  function searchIn(kw) {
    var box = $("#search-results");
    kw = (kw || "").trim();
    if (!kw) { box.innerHTML = ""; return; }
    var hits = [];
    COMS.forEach(function (com) {
      com.sheets.forEach(function (s) {
        s.charts.forEach(function (c, i) {
          if (c.name.indexOf(kw) >= 0 || (c.note || "").indexOf(kw) >= 0) {
            hits.push({ com: com, sheet: s, idx: i, name: c.name });
          }
        });
      });
    });
    if (!hits.length) { box.innerHTML = '<div class="sr-empty">没有匹配的图表</div>'; return; }
    box.innerHTML = '<div class="sr-head">匹配 ' + hits.length + " 张图</div>" +
      hits.slice(0, 40).map(function (h) {
        return '<a class="sr-item" href="#/data/' + h.com.id + "/" + h.sheet.id + "?c=" + h.idx + '">' +
          '<span class="sr-sheet">' + esc(h.com.name) + " · " + esc(h.sheet.title.replace(/^\d+\s*/, "")) + "</span>" +
          esc(h.name) + "</a>";
      }).join("");
  }

  function renderSheet(com, sheet, query) {
    var anchor = -1;
    var m = /[?&]c=(\d+)/.exec(query || "");
    if (m) anchor = +m[1];
    $("#data-main").innerHTML =
      '<div class="sheet-head">' +
        "<div><h1>" + esc(sheet.title) + "</h1>" +
        '<p class="sheet-sub">' + esc(sheet.subtitle) + "</p></div>" +
        '<div class="sheet-tools"><span class="pill soft">' + sheet.charts.length + " 张图</span></div>" +
      "</div>" +
      '<div class="chart-grid" id="chart-grid"></div>';
    var grid = $("#chart-grid");
    sheet.charts.forEach(function (c, i) { grid.appendChild(buildChartCard(c, i)); });
    if (anchor >= 0 && grid.children[anchor]) {
      setTimeout(function () { grid.children[anchor].scrollIntoView({ behavior: "smooth", block: "center" }); }, 120);
    } else {
      window.scrollTo(0, 0);
    }
  }

  function buildChartCard(c, idx) {
    var el = document.createElement("section");
    el.className = "chart-card";
    var freqText = { day: "日度", week: "周度", month: "月度", year: "年度" }[c.freq] || c.freq;
    el.innerHTML =
      '<header class="cc-head">' +
        '<div class="cc-title"><h3>' + esc(c.name) + "</h3>" +
          (c.unit ? '<span class="unit">' + esc(c.unit) + "</span>" : "") + "</div>" +
        '<div class="cc-meta">' +
          '<span class="pill">' + freqText + "</span>" +
          (c.src ? '<span class="pill soft">' + esc(c.src) + "</span>" : "") +
          '<span class="note">' + esc(c.note || "") + "</span>" +
        "</div>" +
      "</header>" +
      '<div class="cc-body">' +
        '<div class="canvas-wrap"><canvas></canvas></div>' +
        '<div class="legend"></div>' +
      "</div>";

    var canvas = $("canvas", el);
    var chart = null;
    /* 历史年份全量保留在图例中，默认只显示最近 5 年，避免几十条线挤在一起 */
    var visible = c.years.slice(-5);

    function buildLegend() {
      var lg = $(".legend", el);
      if (c.single) {
        lg.innerHTML = '<div class="lg-years"><span class="lg-static">' +
          esc(c.unit || "年度值") + " · " + c.labels.length + " 个年度</span></div>";
        return;
      }
      lg.innerHTML =
        '<div class="lg-years">' + c.years.map(function (y, i) {
          var color = global.LineChart.color(i, c.years.length);
          return '<button class="lg-item' + (visible.indexOf(y) >= 0 ? " on" : "") +
            '" data-y="' + esc(y) + '"><span class="swatch" style="background:' + color + '"></span>' + esc(y) + "</button>";
        }).join("") + "</div>" +
        '<div class="lg-actions">' +
          '<button class="lg-btn" data-act="recent">近两年</button>' +
          '<button class="lg-btn" data-act="recent5">近五年</button>' +
          '<button class="lg-btn" data-act="all">全部</button>' +
        "</div>";
      $$(".lg-item", lg).forEach(function (b) {
        b.addEventListener("click", function () {
          var y = b.getAttribute("data-y");
          if (!chart) return;
          chart.toggle(y);
          visible = c.years.filter(function (yy) { return !chart.hidden[yy]; });
          b.classList.toggle("on", !chart.hidden[y]);
        });
      });
      $$(".lg-btn", lg).forEach(function (b) {
        b.addEventListener("click", function () {
          var act = b.getAttribute("data-act");
          visible = act === "recent" ? c.years.slice(-2)
                  : act === "recent5" ? c.years.slice(-5)
                  : c.years.slice();
          if (chart) chart.only(visible);
          $$(".lg-item", lg).forEach(function (it) {
            it.classList.toggle("on", visible.indexOf(it.getAttribute("data-y")) >= 0);
          });
        });
      });
    }
    buildLegend();
    setTimeout(function () {
      chart = global.LineChart.create(canvas, {
        labels: c.labels, years: c.years, series: c.series, unit: c.unit, freq: c.freq, height: 260,
      });
      if (visible.length < c.years.length) chart.only(visible);
      charts.push(chart);
    }, 0);
    return el;
  }

  /* ---------- 数据说明 ---------- */
  function viewAbout() {
    var t = totals();
    var freqs = [
      ["日度", "按日历日对齐，横轴为 1月1日–12月31日，各年曲线按年内日期叠放"],
      ["周度", "按 ISO 周序对齐，横轴为第1周–第53周"],
      ["月度", "按月份对齐，横轴为 1月–12月"],
      ["年度", "产能等年度指标，展示全部历史年份"],
    ];
    $("#view").innerHTML =
      '<div class="page-head"><h1>数据说明</h1><span class="hint">产业链数据库 · 多品种本地静态版</span></div>' +
      '<section class="balance-block about-block"><div class="bb-head"><h2>数据来源与更新</h2></div>' +
      '<div class="about-body">' +
      "<p>数据来源：<b>IFIND、隆众资讯、卓创资讯、百川资讯等</b>，经本地整理。共 <b>" + COMS.length + "</b> 个品种、<b>" + t.sec + "</b> 个板块、<b>" + t.ch + "</b> 张图表，各品种数据截至日期见品种卡片。</p>" +
      "<p>原始数据为源数据库各指标序列；<span class=\"pill soft\">推算数据</span> 为基于原始序列计算所得（如基差、月差、品种价差、累计值差分得到的当月值、表观消费量与产能同比等）。</p>" +
      "<p>每张图默认展示最近 5 个有数据的年份（年度图展示全部历史），点击年份标签可显示/隐藏对应曲线，「近两年」仅保留最近两年，「全部」恢复全部年份。鼠标悬停可查看各年同一期的数值。侧栏搜索框可跨全部品种检索图表。</p>" +
      "</div></section>" +
      '<section class="balance-block about-block"><div class="bb-head"><h2>频率与季节性对齐</h2></div>' +
      '<div class="about-body"><table class="dt about-table"><tbody>' +
      freqs.map(function (f) { return '<tr><th><span class="pill">' + f[0] + "</span></th><td>" + esc(f[1]) + "</td></tr>"; }).join("") +
      "</tbody></table></div></section>" +
      '<section class="balance-block about-block"><div class="bb-head"><h2>品种覆盖</h2></div>' +
      '<div class="about-body"><ol class="about-list">' +
      COMS.map(function (c) { return '<li><a href="#/data/' + c.id + "/" + (c.sheets[0] ? c.sheets[0].id : "") + '">' + esc(c.name) + "</a> · " + c.sheets.length + " 板块 / " + c.chartCount + " 图</li>"; }).join("") +
      "</ol></div></section>" +
      '<section class="balance-block about-block"><div class="bb-head"><h2>风险提示与免责声明</h2></div>' +
      '<div class="about-body legal">' +
      "<p>长江期货股份有限公司交易咨询业务资格：鄂证监期货字[2014]1号</p>" +
      "<p>潘钰烛 执业编号：F0290936 投资咨询号：Z0011442　曹雪梅 执业编号：F3051631 投资咨询号：Z0015756</p>" +
      "<p>风险提示：本数据库仅供参考之用，不构成卖出或买入期货、期权合约或其他投资标的要约或邀请。在任何情况下，本数据库中的信息和意见均不构成对任何个人的投资建议。任何形式的分享投资收益或者分担投资损失的书面或口头承诺均为无效。投资者应当充分了解数据库内容的局限性，结合自己的投资目标和财务状况自行判断是否采用本数据库所载内容和信息并自行承担风险，我公司及员工对投资者使用本数据库及其内容而造成的一切后果不承担任何法律责任。</p>" +
      "<p>免责声明：长江期货股份有限公司拥有期货投资咨询资格。长江期货系列数据库的信息均来源于公开资料，本公司对这些信息的准确性和完整性不作任何保证，也不保证所包含的信息和建议不会发生任何变更。本数据库所载资料、意见及推测仅反映在本数据库所载明日期的判断，本公司可随时修改，毋需提前通知，投资者应当自行关注相应的更新或修改。本公司已力求数据库内容的客观、公正，数据库中的信息或意见并不构成所述期货的买卖出价，投资者据此作出的任何投资决策与本公司和作者无关。本数据库版权仅为本公司所有，未经本公司书面许可，任何机构和个人不得以任何形式翻版、复制、发布、引用或再次分发他人，或投入商业使用。如征得本公司同意引用、刊发的，需在允许的范围内使用，并注明出处为“长江期货股份有限公司”，且不得对本数据库进行有悖原意的引用、删节和修改。本公司保留追究相关责任的权利。</p>" +
      "</div></section>";
    window.scrollTo(0, 0);
  }

  /* ---------- 启动 ---------- */
  var resizeTimer = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () { charts.forEach(function (c) { c.resize(); }); }, 150);
  });
  window.addEventListener("hashchange", route);
  route();
})(window);