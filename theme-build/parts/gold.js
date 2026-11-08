/* ===== Red Atlas gold desk: live prices in the visitor's currency ===== */
var RA_GOLD = __RA_GOLD_CONFIG__;
var RA_GOLD_BY = {};
RA_GOLD.countries.forEach(function (c) { RA_GOLD_BY[c.code] = c; });

/* Same rules as money() in engine/gold_pages.py */
function raFmt(v, c) {
  var d = v >= 1000 ? 0 : 2;
  var indian = ["INR", "NPR", "PKR", "BDT"].indexOf(c.currency) >= 0;
  var s = v.toLocaleString(indian ? "en-IN" : "en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  return c.symbol + (c.symbol.length > 1 && /^[A-Za-z]+$/.test(c.symbol) ? " " : "") + s;
}

function raGoldData() {
  try {
    var cached = JSON.parse(sessionStorage.getItem("raGold") || "null");
    if (cached && Date.now() - cached.t < 600000) return Promise.resolve(cached);
  } catch (e) {}
  var j = function (u) { return fetch(u).then(function (r) { return r.json(); }); };
  return Promise.all([
    j("https://api.gold-api.com/price/XAU"),
    j("https://api.gold-api.com/price/XAG"),
    j("https://open.er-api.com/v6/latest/USD")
  ]).then(function (a) {
    var d = { t: Date.now(), xau: +a[0].price, xag: +a[1].price, fx: a[2].rates };
    if (!(d.xau > 100 && d.xag > 1 && d.fx && d.fx.EUR)) throw new Error("bad data");
    try { sessionStorage.setItem("raGold", JSON.stringify(d)); } catch (e) {}
    return d;
  });
}

function raDetectCountry() {
  try {
    var saved = localStorage.getItem("raGoldCountry");
    if (saved && RA_GOLD_BY[saved]) return saved;
  } catch (e) {}
  var tz = "";
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) {}
  for (var i = 0; i < RA_GOLD.countries.length; i++) {
    if (RA_GOLD.countries[i].zones.indexOf(tz) >= 0) return RA_GOLD.countries[i].code;
  }
  var m = (navigator.language || "").match(/-([A-Z]{2})$/);
  return m && RA_GOLD_BY[m[1]] ? m[1] : "US";
}

function raGoldRender(el, d) {
  var auto = el.getAttribute("data-country") === "auto";
  var c = RA_GOLD_BY[auto ? (el.getAttribute("data-current") || raDetectCountry()) : el.getAttribute("data-country")];
  var rate = d.fx[c.currency];
  if (!c || !rate) return;
  var silver = el.getAttribute("data-metal") === "XAG";
  var gram = (silver ? d.xag : d.xau) / RA_GOLD.oz * rate;
  var rows = silver ? RA_GOLD.silver : c.karats.map(function (k) { return [k, RA_GOLD.karats[k]]; });
  var units = silver ? ["gram", "ounce", "kg"] : c.units;
  var main = units[0];
  var head = units.map(function (u) { return "<th>" + RA_GOLD.units[u][0] + "</th>"; }).join("");
  var body = rows.map(function (r) {
    return "<tr><th>" + r[0] + "</th>" + units.map(function (u) {
      return "<td>" + raFmt(gram * r[1] * RA_GOLD.units[u][1], c) + "</td>";
    }).join("") + "</tr>";
  }).join("");
  var time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  var pick = "";
  if (auto) {
    var hasPage = RA_GOLD.pageFor[c.code] !== RA_GOLD.hub;
    pick = "<label class='ra-gold-pick'>Country: <select aria-label='Choose your country'>" +
      RA_GOLD.countries.map(function (x) {
        return "<option value='" + x.code + "'" + (x.code === c.code ? " selected" : "") + ">" + x.short + " (" + x.currency + ")</option>";
      }).join("") + "</select></label> <a class='ra-gold-more' href='" + RA_GOLD.pageFor[c.code] + "'>" +
      (hasPage ? "Full prices for " + c.short : "Prices by weight and calculator") + " ›</a>";
  }
  el.setAttribute("data-current", c.code);
  el.innerHTML =
    "<div class='ra-gold-head'><div><span class='ra-gold-label'>" + (silver ? "Silver" : "Gold") + " price in " + c.short + " today</span>" +
    "<strong class='ra-gold-big'>" + raFmt(gram * rows[0][1] * RA_GOLD.units[main][1], c) + "</strong>" +
    "<span class='ra-gold-sub'>" + RA_GOLD.units[main][0] + ", " + rows[0][0] + " &middot; " + c.currency + "</span></div>" +
    "<div class='ra-gold-upd'><span class='ra-live'>LIVE</span> " + time + "<br/>Spot " + (silver ? "silver" : "gold") + " $" +
    (silver ? d.xag : d.xau).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + "/oz</div></div>" +
    (auto ? "<div class='ra-gold-tools'>" + pick + "</div>" : "") +
    "<div class='ra-gold-scroll'><table class='ra-gold-table'><thead><tr><th>Purity</th>" + head + "</tr></thead><tbody>" + body + "</tbody></table></div>";
  var sel = el.querySelector("select");
  if (sel) sel.onchange = function () {
    try { localStorage.setItem("raGoldCountry", sel.value); } catch (e) {}
    el.setAttribute("data-current", sel.value);
    raGoldRender(el, d);
  };
}

/* Same markup as tiles() in engine/gold_pages.py */
function raTilesRender(el, d) {
  var c = RA_GOLD_BY[el.getAttribute("data-country")];
  var gram = d.xau / RA_GOLD.oz * d.fx[c.currency];
  var main = RA_GOLD.units[c.units[0]];
  el.innerHTML = c.karats.map(function (k) {
    var g = gram * RA_GOLD.karats[k];
    return "<div class='ra-tile'><span class='ra-tile-k'>" + k + "</span><strong>" + raFmt(g, c) + "</strong>" +
      "<small>per gram</small><em>" + raFmt(g * main[1], c) + " / " + main[0].replace("1 ", "") + "</em></div>";
  }).join("");
}

/* Same markup as weights_table() in engine/gold_pages.py */
function raWeightsRender(el, d) {
  var c = RA_GOLD_BY[el.getAttribute("data-country")];
  var silver = el.getAttribute("data-metal") === "XAG";
  var gram = (silver ? d.xag : d.xau) / RA_GOLD.oz * d.fx[c.currency];
  var cols = silver ? RA_GOLD.silver : c.karats.map(function (k) { return [k, RA_GOLD.karats[k]]; });
  el.innerHTML = "<table class='ra-gold-table'><thead><tr><th>Weight</th>" +
    cols.map(function (p) { return "<th>" + p[0] + "</th>"; }).join("") + "</tr></thead><tbody>" +
    c.weights.map(function (w) {
      return "<tr><th>" + w[0] + "</th>" + cols.map(function (p) { return "<td>" + raFmt(gram * p[1] * w[1], c) + "</td>"; }).join("") + "</tr>";
    }).join("") + "</tbody></table>";
}

function raCalcRender(el, d) {
  var c = RA_GOLD_BY[el.getAttribute("data-country")];
  var gram = d.xau / RA_GOLD.oz * d.fx[c.currency];
  var opt = function (list) { return list.map(function (x) { return "<option value='" + x[1] + "'>" + x[0] + "</option>"; }).join(""); };
  var units = [["Grams", 1]].concat(c.units.filter(function (u) { return u !== "gram"; }).map(function (u) {
    return [RA_GOLD.units[u][0].replace("1 ", "") + "s", RA_GOLD.units[u][1]];
  }));
  el.innerHTML = "<div class='ra-calc-row'><label>Weight<input type='number' min='0' step='any' value='10' inputmode='decimal'/></label>" +
    "<label>Unit<select class='ra-calc-unit'>" + opt(units) + "</select></label>" +
    "<label>Purity<select class='ra-calc-k'>" + opt(c.karats.map(function (k) { return [k, RA_GOLD.karats[k]]; })) + "</select></label></div>" +
    "<div class='ra-calc-out'><span>Estimated gold value</span><strong></strong><small>Value of the gold only, before making charges and taxes.</small></div>";
  var input = el.querySelector("input"), unit = el.querySelector(".ra-calc-unit"), k = el.querySelector(".ra-calc-k");
  var out = el.querySelector(".ra-calc-out strong");
  var update = function () {
    var w = parseFloat(input.value);
    out.textContent = w > 0 ? raFmt(gram * w * parseFloat(unit.value) * parseFloat(k.value), c) : "Enter a weight";
  };
  input.oninput = unit.onchange = k.onchange = update;
  update();
}

function raGold() {
  var els = document.querySelectorAll(".ra-gold, .ra-gold-tiles, .ra-gold-weights, .ra-gold-calc");
  if (!els.length || !window.fetch) return;
  raGoldData().then(function (d) {
    for (var i = 0; i < els.length; i++) {
      var cls = els[i].className;
      if (cls.indexOf("ra-gold-tiles") >= 0) raTilesRender(els[i], d);
      else if (cls.indexOf("ra-gold-weights") >= 0) raWeightsRender(els[i], d);
      else if (cls.indexOf("ra-gold-calc") >= 0) raCalcRender(els[i], d);
      else raGoldRender(els[i], d);
    }
  }).catch(function () { /* keep the prices already in the page */ });
}
