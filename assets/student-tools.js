(function () {
  "use strict";
  var allJobs = [];

  var tabs = document.querySelectorAll(".st-tab");
  var panels = document.querySelectorAll(".st-panel");
  tabs.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = btn.getAttribute("data-tab");
      tabs.forEach(function (b) { b.classList.toggle("active", b === btn); });
      panels.forEach(function (p) { p.style.display = p.id === target ? "block" : "none"; });
    });
  });

  fetch("../data/public-search.json")
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (!data) return;
      var items = Array.isArray(data) ? data : (data.items || data.records || []);
      allJobs = items.filter(function (x) {
        return x && (x.category === "latest-jobs" || x.category === "upcoming-jobs" || x.type === "job");
      });
      populateCompareDropdowns();
      runEligibility();
    })
    .catch(function () {});

  function runEligibility() {
    var qualEl = document.getElementById("el-qual");
    var kwEl = document.getElementById("el-kw");
    var out = document.getElementById("el-results");
    if (!qualEl || !out) return;
    var q = (qualEl.value || "").toLowerCase();
    var kw = (kwEl ? kwEl.value : "").trim().toLowerCase();
    var matches = allJobs.filter(function (j) {
      var hay = ((j.title || "") + " " + (j.department || "") + " " + (j.qualification || "") + " " + (j.eligibility || "") + " " + (j.summary || "")).toLowerCase();
      var qOk = !q || hay.indexOf(q) !== -1;
      var kOk = !kw || hay.indexOf(kw) !== -1;
      return qOk && kOk;
    }).slice(0, 25);
    if (!matches.length) {
      out.innerHTML = "<p>कोई मेल खाती सक्रिय नौकरी नहीं मिली। कृपया दूसरा फ़िल्टर चुनें।</p>";
      return;
    }
    out.innerHTML = matches.map(function (j) {
      var url = j.url || ("../posts/" + j.id + "/");
      return '<div class="st-card"><strong><a href="' + url + '">' + (j.title || j.id) + '</a></strong>' +
        '<div class="st-meta">' + (j.department || "") + (j.lastDate ? " • Last Date: " + j.lastDate : "") + '</div></div>';
    }).join("");
  }
  var elBtn = document.getElementById("el-check-btn");
  if (elBtn) elBtn.addEventListener("click", runEligibility);

  function populateCompareDropdowns() {
    var s1 = document.getElementById("cmp-job1");
    var s2 = document.getElementById("cmp-job2");
    if (!s1 || !s2 || !allJobs.length) return;
    var opts = allJobs.slice(0, 80).map(function (j, idx) {
      return '<option value="' + idx + '">' + (j.title || j.id) + '</option>';
    }).join("");
    s1.innerHTML = opts;
    s2.innerHTML = opts;
    if (allJobs.length > 1) s2.selectedIndex = 1;
    renderCompare();
  }
  function renderCompare() {
    var s1 = document.getElementById("cmp-job1");
    var s2 = document.getElementById("cmp-job2");
    var out = document.getElementById("cmp-out");
    if (!s1 || !s2 || !out || !allJobs.length) return;
    var j1 = allJobs[parseInt(s1.value, 10) || 0];
    var j2 = allJobs[parseInt(s2.value, 10) || 0];
    if (!j1 || !j2) return;
    function row(lbl, v1, v2) {
      return "<tr><th>" + lbl + "</th><td>" + (v1 || "—") + "</td><td>" + (v2 || "—") + "</td></tr>";
    }
    out.innerHTML = '<table class="st-table"><thead><tr><th>विवरण</th><th>' + (j1.title || "") + '</th><th>' + (j2.title || "") + '</th></tr></thead><tbody>' +
      row("विभाग (Department)", j1.department, j2.department) +
      row("अंतिम तिथि (Last Date)", j1.lastDate, j2.lastDate) +
      row("योग्यता (Qualification)", j1.qualification || j1.eligibility, j2.qualification || j2.eligibility) +
      row("आवेदन स्थिति", j1.applyStatus || j1.applyLinkType, j2.applyStatus || j2.applyLinkType) +
      row("पोस्ट लिंक", '<a href="' + (j1.url || ("../posts/" + j1.id + "/")) + '">विवरण देखें</a>', '<a href="' + (j2.url || ("../posts/" + j2.id + "/")) + '">विवरण देखें</a>') +
      "</tbody></table>";
  }
  var cmpBtn = document.getElementById("cmp-btn");
  if (cmpBtn) cmpBtn.addEventListener("click", renderCompare);

  var phBtn = document.getElementById("ph-go");
  if (phBtn) {
    phBtn.addEventListener("click", function () {
      var file = document.getElementById("ph-file").files[0];
      var preset = document.getElementById("ph-preset").value.split("x");
      var maxKb = parseInt(document.getElementById("ph-kb").value, 10) || 50;
      var msg = document.getElementById("ph-msg");
      if (!file) { msg.textContent = "कृपया पहले फोटो चुनें।"; return; }
      var img = new Image();
      img.onload = function () {
        var c = document.createElement("canvas");
        c.width = parseInt(preset[0], 10);
        c.height = parseInt(preset[1], 10);
        var ctx = c.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, c.width, c.height);
        ctx.drawImage(img, 0, 0, c.width, c.height);
        var q = 0.92, dataUrl = c.toDataURL("image/jpeg", q);
        while ((dataUrl.length * 0.75) / 1024 > maxKb && q > 0.15) {
          q -= 0.07;
          dataUrl = c.toDataURL("image/jpeg", q);
        }
        var sizeKb = Math.round((dataUrl.length * 0.75) / 1024);
        var a = document.getElementById("ph-dl");
        a.href = dataUrl;
        a.download = "sarkarialert-photo-" + c.width + "x" + c.height + ".jpg";
        a.style.display = "inline-block";
        var prev = document.getElementById("ph-prev");
        prev.src = dataUrl;
        prev.style.display = "block";
        msg.textContent = "तैयार! साइज: " + c.width + "x" + c.height + " px (~" + sizeKb + " KB)";
      };
      img.src = URL.createObjectURL(file);
    });
  }

  var sigCanvas = document.getElementById("sig-canvas");
  if (sigCanvas) {
    var sctx = sigCanvas.getContext("2d");
    sctx.fillStyle = "#ffffff";
    sctx.fillRect(0, 0, sigCanvas.width, sigCanvas.height);
    sctx.strokeStyle = "#111111";
    sctx.lineWidth = 2.5;
    sctx.lineCap = "round";
    var drawing = false;
    function getPos(ev) {
      var r = sigCanvas.getBoundingClientRect();
      var t = ev.touches ? ev.touches[0] : ev;
      return { x: (t.clientX - r.left) * (sigCanvas.width / r.width), y: (t.clientY - r.top) * (sigCanvas.height / r.height) };
    }
    ["mousedown", "touchstart"].forEach(function (e) {
      sigCanvas.addEventListener(e, function (ev) {
        ev.preventDefault();
        drawing = true;
        var p = getPos(ev);
        sctx.beginPath();
        sctx.moveTo(p.x, p.y);
      });
    });
    ["mousemove", "touchmove"].forEach(function (e) {
      sigCanvas.addEventListener(e, function (ev) {
        if (!drawing) return;
        ev.preventDefault();
        var p = getPos(ev);
        sctx.lineTo(p.x, p.y);
        sctx.stroke();
      });
    });
    ["mouseup", "mouseleave", "touchend"].forEach(function (e) {
      sigCanvas.addEventListener(e, function () { drawing = false; });
    });
    document.getElementById("sig-clear").addEventListener("click", function () {
      sctx.fillStyle = "#ffffff";
      sctx.fillRect(0, 0, sigCanvas.width, sigCanvas.height);
    });
    document.getElementById("sig-dl-btn").addEventListener("click", function () {
      var outC = document.createElement("canvas");
      outC.width = 140; outC.height = 60;
      var octx = outC.getContext("2d");
      octx.fillStyle = "#ffffff";
      octx.fillRect(0, 0, 140, 60);
      octx.drawImage(sigCanvas, 0, 0, 140, 60);
      var a = document.createElement("a");
      a.href = outC.toDataURL("image/jpeg", 0.9);
      a.download = "sarkarialert-signature-140x60.jpg";
      a.click();
    });
  }

  var pdfBtn = document.getElementById("pdf-go");
  if (pdfBtn) {
    pdfBtn.addEventListener("click", function () {
      var files = document.getElementById("pdf-files").files;
      if (!files || !files.length) { alert("कृपया पहले 1 या अधिक फोटो (JPG/PNG) चुनें।"); return; }
      var w = window.open("", "_blank");
      if (!w) { alert("कृपया पॉप-अप की अनुमति दें।"); return; }
      var html = '<html><head><title>SarkariAlert PDF</title><style>body{margin:0;padding:12px;text-align:center}img{max-width:100%;max-height:95vh;page-break-after:always;margin-bottom:12px}</style></head><body>';
      for (var i = 0; i < files.length; i++) {
        html += '<img src="' + URL.createObjectURL(files[i]) + '">';
      }
      html += '<script>window.onload=function(){setTimeout(function(){window.print();},400);};<\/script></body></html>';
      w.document.write(html);
      w.document.close();
    });
  }

  var ageBtn = document.getElementById("age-go");
  if (ageBtn) {
    var asonEl = document.getElementById("age-ason");
    if (asonEl && !asonEl.value) asonEl.value = new Date().toISOString().slice(0, 10);
    ageBtn.addEventListener("click", function () {
      var dob = new Date(document.getElementById("age-dob").value);
      var ason = new Date(document.getElementById("age-ason").value);
      var out = document.getElementById("age-out");
      if (isNaN(dob.getTime()) || isNaN(ason.getTime()) || dob > ason) {
        out.textContent = "कृपया सही जन्म तिथि और गणना तिथि चुनें।";
        return;
      }
      var y = ason.getFullYear() - dob.getFullYear();
      var m = ason.getMonth() - dob.getMonth();
      var d = ason.getDate() - dob.getDate();
      if (d < 0) { m -= 1; d += new Date(ason.getFullYear(), ason.getMonth(), 0).getDate(); }
      if (m < 0) { y -= 1; m += 12; }
      out.textContent = "आपकी सटीक आयु: " + y + " वर्ष, " + m + " महीने, " + d + " दिन";
    });
  }

  var typText = "Government examinations in India such as SSC CGL, Railway RRB NTPC, UPPSC RO ARO, and Banking recruit thousands of candidates every year. Regular typing practice improves speed and accuracy for skill tests.";
  var typInput = document.getElementById("typ-input");
  var typTimer = null, typSec = 60, typStarted = false;
  if (typInput) {
    document.getElementById("typ-sample").textContent = typText;
    typInput.addEventListener("input", function () {
      if (!typStarted) {
        typStarted = true;
        typTimer = setInterval(function () {
          typSec -= 1;
          document.getElementById("typ-time").textContent = typSec + "s";
          if (typSec <= 0) { clearInterval(typTimer); typInput.disabled = true; }
        }, 1000);
      }
      var typed = typInput.value.trim();
      var words = typed ? typed.split(/\s+/).length : 0;
      var elapsed = Math.max(1, 60 - typSec);
      var wpm = Math.round((words / elapsed) * 60);
      var correct = 0;
      for (var i = 0; i < typed.length; i++) {
        if (typed[i] === typText[i]) correct++;
      }
      var acc = typed.length ? Math.round((correct / typed.length) * 100) : 100;
      document.getElementById("typ-wpm").textContent = wpm;
      document.getElementById("typ-acc").textContent = acc + "%";
    });
    document.getElementById("typ-reset").addEventListener("click", function () {
      clearInterval(typTimer);
      typSec = 60; typStarted = false;
      typInput.disabled = false; typInput.value = "";
      document.getElementById("typ-time").textContent = "60s";
      document.getElementById("typ-wpm").textContent = "0";
      document.getElementById("typ-acc").textContent = "100%";
    });
  }

  var mockBtn = document.getElementById("mock-submit");
  if (mockBtn) {
    mockBtn.addEventListener("click", function () {
      var ans = { q1: "a", q2: "b", q3: "c", q4: "a", q5: "b" };
      var right = 0, wrong = 0;
      Object.keys(ans).forEach(function (k) {
        var sel = document.querySelector('input[name="' + k + '"]:checked');
        if (!sel) return;
        if (sel.value === ans[k]) right++;
        else wrong++;
      });
      var score = (right - wrong * 0.25).toFixed(2);
      document.getElementById("mock-out").textContent = "सही: " + right + " | गलत: " + wrong + " | कुल स्कोर (-0.25 नियम): " + score + " / 5";
    });
  }
})();
