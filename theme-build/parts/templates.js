/* ===== Red Atlas News ===== */
function ra_esc(s) {
  return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function ra_block_temp(e) {
  var lead = e.posts[0];
  var link = "/search/label/" + encodeURIComponent(e.title) + "?max-results=12";
  var blank = "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==";
  var summary = (lead.summary || "").replace(/\s+/g, " ");
  if (summary.length > 170) summary = summary.substr(0, 170).replace(/\s\S*$/, "") + "…";
  return "<section class='ra-block mb-4'>" +
    "<div class='d-flex align-items-center mb-3'><h2 class='ra-block-title mb-0'><a href='" + link + "'>" + ra_esc(e.title) + "</a></h2>" +
    "<a class='ms-auto ra-more' href='" + link + "'>More ›</a></div>" +
    "<div class='row'>" +
    "<div class='col-md-7 mb-3'><a class='ra-lead d-block' href='" + lead.url + "'>" +
    (lead.img ? "<div class='ratio ratio-16x9 jt-bg-light overflow-hidden rounded mb-2'><img alt='" + ra_esc(lead.title) + "' class='object-cover lazy-" + lead.grup_id + " lazyload' data-src='" + lead.img + "' loading='lazy' src='" + blank + "'/></div>" : "") +
    "<h3 class='ra-lead-title'>" + ra_esc(lead.title) + "</h3></a>" +
    "<p class='ra-lead-sum text-secondary mb-0'>" + ra_esc(summary) + "</p></div>" +
    "<div class='col-md-5'><ul class='ra-list list-unstyled mb-0'>" +
    e.posts.slice(1).map(function (data) {
      return "<li><a href='" + data.url + "'>" + ra_esc(data.title) + "</a><small class='d-block text-secondary mt-1'>" + data.date + "</small></li>";
    }).join("") +
    "</ul></div></div></section>";
}

function raMarkets() {
  var box = document.getElementById("ra-tv");
  if (!box) return;
  var s = document.createElement("script");
  s.src = "https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js";
  s.async = true;
  s.innerHTML = JSON.stringify({
    symbols: [
      { proName: "OANDA:XAUUSD", title: "Gold" },
      { proName: "OANDA:XAGUSD", title: "Silver" },
      { proName: "CAPITALCOM:DXY", title: "US Dollar Index" },
      { proName: "FOREXCOM:SPXUSD", title: "S&P 500" },
      { proName: "TVC:USOIL", title: "Crude Oil" },
      { proName: "FX:EURUSD", title: "EUR/USD" },
      { proName: "BITSTAMP:BTCUSD", title: "Bitcoin" }
    ],
    showSymbolLogo: true,
    isTransparent: true,
    displayMode: "regular",
    colorTheme: document.documentElement.classList.contains("dark-mode") ? "dark" : "light",
    locale: "en"
  });
  box.appendChild(s);
}

function raBreaking() {
  var bar = document.getElementById("ra-breaking");
  var items = document.getElementById("ra-breaking-items");
  if (!bar || !items || !window.fetch) return;
  fetch("/feeds/posts/summary?alt=json&max-results=8")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var entries = (data.feed && data.feed.entry) || [];
      if (!entries.length) return;
      var html = entries.map(function (en) {
        var href = "";
        (en.link || []).forEach(function (l) { if (l.rel === "alternate") href = l.href; });
        return "<a href='" + href + "'>" + ra_esc(en.title.$t) + "</a>";
      }).join("");
      items.innerHTML = html + html; /* doubled for a seamless loop */
      bar.hidden = false;
    })
    .catch(function () {});
}

function raInit() {
  if (window.raStarted) return;
  window.raStarted = true;
  var year = document.getElementById("ra-year");
  if (year) year.textContent = new Date().getFullYear();
  raBreaking();
  raMarkets();
  raGold();
}

/* JetTheme only runs jtCallback after the first scroll or tap, so start the
   tickers shortly after load instead; the delay keeps first paint fast. */
if (document.readyState === "complete") {
  setTimeout(raInit, 800);
} else {
  window.addEventListener("load", function () { setTimeout(raInit, 800); });
}
