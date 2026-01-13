from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

HTML = r"""
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Plant Plotplan (Site / Building / Road / Fence / Gate)</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background:#0b0d10; color:#e9eef5; }
    .wrap { display:flex; gap:12px; padding:12px; height: 100vh; box-sizing: border-box; }
    .panel {
      width: 340px; min-width: 320px; background:#121722; border:1px solid #263043; border-radius:14px;
      padding:14px; box-sizing:border-box; display:flex; flex-direction:column; gap:12px;
    }
    .panel h2 { font-size: 16px; margin: 0 0 4px 0; }
    .row { display:flex; gap:8px; align-items:center; }
    .row label { width: 98px; color:#b7c3d6; font-size: 13px; }
    input, select, button, textarea {
      background:#0f1420; color:#e9eef5; border:1px solid #263043; border-radius:10px; padding:9px 10px;
      outline:none; font-size: 13px;
    }
    input, select { flex:1; }
    button { cursor:pointer; }
    button:hover { border-color:#3a4a67; }
    .hint { font-size: 12px; color:#a9b6cb; line-height: 1.35; }
    .status { font-size: 12px; padding:10px; border-radius:10px; background:#0f1420; border:1px solid #263043; }
    .status b { color:#fff; }
    .canvasWrap {
      flex:1; background:#0b0d10; border-radius:14px; border:1px solid #263043; position:relative;
      display:flex; align-items:center; justify-content:center; overflow:hidden;
    }
    canvas { background:#0b0d10; }
    .badge {
      position:absolute; top:10px; right:10px; font-size:12px; padding:8px 10px;
      border:1px solid #263043; border-radius:999px; background:#0f1420; color:#b7c3d6;
    }
    .kbd { border:1px solid #3a4a67; border-bottom-width:2px; padding:2px 6px; border-radius:6px; background:#0f1420; color:#d6e2f5; }
    .small { font-size: 12px; color:#a9b6cb; }
    textarea { width:100%; height: 150px; resize: vertical; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }
    .split { display:flex; gap:8px; }
    .split button { flex:1; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <div>
        <h2>Step 1. 부지 경계</h2>
        <div class="row">
          <label>가로(m)</label>
          <input id="siteW" type="number" min="1" step="0.1" value="200">
        </div>
        <div class="row">
          <label>세로(m)</label>
          <input id="siteH" type="number" min="1" step="0.1" value="140">
        </div>
        <div class="row">
          <button id="btnSetSite" style="flex:1">부지 생성/갱신</button>
        </div>
        <div class="hint">부지를 갱신하면 기존 객체는 유지되며, 새로운 스케일로 다시 그립니다.</div>
      </div>

      <div>
        <h2>Step 2. 객체 추가</h2>
        <div class="row">
          <label>옵션</label>
          <select id="objType">
            <option value="1">1 (건물)</option>
            <option value="2">2 (도로)</option>
            <option value="3">3 (담장)</option>
            <option value="4">4 (문)</option>
          </select>
        </div>
        <div class="row">
          <label>가로(m)</label>
          <input id="objW" type="number" min="0.1" step="0.1" value="30">
        </div>
        <div class="row">
          <label>세로(m)</label>
          <input id="objH" type="number" min="0.1" step="0.1" value="18">
        </div>
        <div class="row">
          <button id="btnAdd" style="flex:1">추가 후 배치 모드</button>
        </div>
        <div class="hint">
          추가 버튼을 누르면 “배치 모드”가 됩니다. 캔버스에서 <b>좌클릭 드래그</b>로 위치를 정하고 놓으면 배치됩니다.<br/>
          배치/수정은 언제든 <b>기존 객체 좌클릭 드래그</b>로 이동 가능합니다.
        </div>
      </div>

      <div class="status" id="statusBox">
        상태: <b id="statusText">대기</b><br/>
        단축키: <span class="kbd">ESC</span> 배치 종료/모드 취소
      </div>

      <div class="split">
        <button id="btnExportJson">JSON 내보내기</button>
        <button id="btnExportPng">PNG 내보내기</button>
      </div>
      <div class="split">
        <button id="btnClear">전체 삭제</button>
        <button id="btnDeleteSel">선택 삭제</button>
      </div>

      <div>
        <div class="small">현재 레이아웃(JSON):</div>
        <textarea id="jsonOut" readonly></textarea>
      </div>
    </div>

    <div class="canvasWrap">
      <div class="badge" id="badge">Site: - × - m</div>
      <canvas id="cvs" width="1200" height="800"></canvas>
    </div>
  </div>

<script>
(() => {
  // ---------- State ----------
  const state = {
    siteW: 200,
    siteH: 140,
    objects: [],   // {id, type, w, h, x, y} x,y = left-top in meters
    selectedId: null,
    mode: "idle",  // idle | placing | finished
    placingTemplate: null, // {type,w,h}
    dragging: null, // {id, offsetX_m, offsetY_m}
    scale: 4,      // px per meter (computed)
    marginPx: 50,
    hoverMouse_m: {x: 0, y: 0}
  };

  // ---------- DOM ----------
  const cvs = document.getElementById("cvs");
  const ctx = cvs.getContext("2d");
  const elSiteW = document.getElementById("siteW");
  const elSiteH = document.getElementById("siteH");
  const elObjType = document.getElementById("objType");
  const elObjW = document.getElementById("objW");
  const elObjH = document.getElementById("objH");
  const statusText = document.getElementById("statusText");
  const badge = document.getElementById("badge");
  const jsonOut = document.getElementById("jsonOut");

  // ---------- Helpers ----------
  const typeName = (t) => ({1:"건물",2:"도로",3:"담장",4:"문"}[t] || "UNKNOWN");

  function setStatus(text) { statusText.textContent = text; }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function genId() { return Math.random().toString(16).slice(2) + Date.now().toString(16); }

  function recomputeScale() {
    // Fit site into canvas with margins
    const usableW = cvs.width - state.marginPx*2;
    const usableH = cvs.height - state.marginPx*2;
    const s1 = usableW / state.siteW;
    const s2 = usableH / state.siteH;
    state.scale = Math.max(1, Math.floor(Math.min(s1, s2)));
  }

  function mToPxX(xm) { return state.marginPx + xm * state.scale; }
  function mToPxY(ym) { return state.marginPx + ym * state.scale; }
  function pxToMX(xp) { return (xp - state.marginPx) / state.scale; }
  function pxToMY(yp) { return (yp - state.marginPx) / state.scale; }

  function pointInObj(mx, my, o) {
    return mx >= o.x && mx <= o.x + o.w && my >= o.y && my <= o.y + o.h;
  }

  function getTopmostAt(mx, my) {
    // last drawn is topmost
    for (let i = state.objects.length - 1; i >= 0; i--) {
      const o = state.objects[i];
      if (pointInObj(mx, my, o)) return o;
    }
    return null;
  }

  function sanitizeSite() {
    const w = parseFloat(elSiteW.value);
    const h = parseFloat(elSiteH.value);
    if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) {
      alert("부지 가로/세로는 0보다 커야 합니다.");
      return false;
    }
    state.siteW = w;
    state.siteH = h;
    badge.textContent = `Site: ${state.siteW} × ${state.siteH} m`;
    recomputeScale();
    draw();
    syncJson();
    return true;
  }

  function sanitizeObjInput() {
    const t = parseInt(elObjType.value, 10);
    const w = parseFloat(elObjW.value);
    const h = parseFloat(elObjH.value);
    if (![1,2,3,4].includes(t)) { alert("옵션(1~4)을 선택하세요."); return null; }
    if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) {
      alert("객체 가로/세로는 0보다 커야 합니다.");
      return null;
    }
    return {type:t, w, h};
  }

  function bringToFront(id) {
    const idx = state.objects.findIndex(o => o.id === id);
    if (idx >= 0) {
      const [o] = state.objects.splice(idx, 1);
      state.objects.push(o);
    }
  }

  function snapInsideSite(o) {
    // keep object fully inside site
    o.x = clamp(o.x, 0, Math.max(0, state.siteW - o.w));
    o.y = clamp(o.y, 0, Math.max(0, state.siteH - o.h));
  }

  function syncJson() {
    const payload = {
      site: { w_m: state.siteW, h_m: state.siteH },
      objects: state.objects.map(o => ({
        id: o.id,
        type: o.type,
        type_name: typeName(o.type),
        w_m: o.w,
        h_m: o.h,
        x_m: o.x,
        y_m: o.y
      })),
      note: "x_m,y_m are left-top position in meters within site boundary"
    };
    jsonOut.value = JSON.stringify(payload, null, 2);
  }

  // ---------- Drawing ----------
  function drawGrid() {
    const stepM = 10; // 10m grid
    ctx.save();
    ctx.globalAlpha = 0.35;
    ctx.lineWidth = 1;

    for (let x = 0; x <= state.siteW; x += stepM) {
      const px = mToPxX(x);
      ctx.beginPath();
      ctx.moveTo(px, mToPxY(0));
      ctx.lineTo(px, mToPxY(state.siteH));
      ctx.strokeStyle = "#1f2a3d";
      ctx.stroke();
    }
    for (let y = 0; y <= state.siteH; y += stepM) {
      const py = mToPxY(y);
      ctx.beginPath();
      ctx.moveTo(mToPxX(0), py);
      ctx.lineTo(mToPxX(state.siteW), py);
      ctx.strokeStyle = "#1f2a3d";
      ctx.stroke();
    }
    ctx.restore();
  }

  function colorForType(t) {
    // intentionally simple, readable on dark bg
    if (t === 1) return "#2b6cb0"; // building
    if (t === 2) return "#718096"; // road
    if (t === 3) return "#38a169"; // fence
    if (t === 4) return "#d69e2e"; // gate
    return "#a0aec0";
  }

  function drawSite() {
    ctx.save();
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#e9eef5";
    ctx.strokeRect(
      mToPxX(0), mToPxY(0),
      state.siteW * state.scale,
      state.siteH * state.scale
    );
    ctx.restore();
  }

  function drawObj(o, isGhost=false) {
    const x = mToPxX(o.x), y = mToPxY(o.y);
    const w = o.w * state.scale, h = o.h * state.scale;
    ctx.save();
    ctx.fillStyle = colorForType(o.type);
    ctx.globalAlpha = isGhost ? 0.35 : 0.75;
    ctx.fillRect(x, y, w, h);

    // border
    ctx.globalAlpha = 1.0;
    ctx.lineWidth = (o.id === state.selectedId) ? 3 : 1.5;
    ctx.strokeStyle = (o.id === state.selectedId) ? "#ffffff" : "#0b0d10";
    ctx.strokeRect(x, y, w, h);

    // label
    ctx.font = "12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillStyle = "#ffffff";
    ctx.globalAlpha = 0.95;
    const label = `${typeName(o.type)} (${o.w}×${o.h}m)`;
    ctx.fillText(label, x + 6, y + 16);

    ctx.restore();
  }

  function clearCanvas() {
    ctx.clearRect(0, 0, cvs.width, cvs.height);
    // background is via CSS canvas bg, but keep safe fill
    ctx.save();
    ctx.fillStyle = "#0b0d10";
    ctx.fillRect(0, 0, cvs.width, cvs.height);
    ctx.restore();
  }

  function draw() {
    clearCanvas();
    drawGrid();
    drawSite();

    // objects
    for (const o of state.objects) drawObj(o, false);

    // ghost (placing)
    if (state.mode === "placing" && state.placingTemplate) {
      const temp = {
        id: "__ghost__",
        type: state.placingTemplate.type,
        w: state.placingTemplate.w,
        h: state.placingTemplate.h,
        x: clamp(state.hoverMouse_m.x - state.placingTemplate.w/2, 0, Math.max(0, state.siteW - state.placingTemplate.w)),
        y: clamp(state.hoverMouse_m.y - state.placingTemplate.h/2, 0, Math.max(0, state.siteH - state.placingTemplate.h)),
      };
      drawObj(temp, true);
    }
  }

  // ---------- Events ----------
  function onSetSite() {
    if (!sanitizeSite()) return;
    if (state.mode === "finished") {
      state.mode = "idle";
      setStatus("대기");
    }
  }

  function onAdd() {
    if (!sanitizeSite()) return;
    const tpl = sanitizeObjInput();
    if (!tpl) return;

    state.mode = "placing";
    state.placingTemplate = tpl;
    state.selectedId = null;
    setStatus(`배치 모드: ${typeName(tpl.type)} (ESC로 취소)`);
    draw();
  }

  function deleteSelected() {
    if (!state.selectedId) return;
    const idx = state.objects.findIndex(o => o.id === state.selectedId);
    if (idx >= 0) state.objects.splice(idx, 1);
    state.selectedId = null;
    draw();
    syncJson();
  }

  function exportJson() {
    syncJson();
    const blob = new Blob([jsonOut.value], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "plotplan.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function exportPng() {
    const a = document.createElement("a");
    a.href = cvs.toDataURL("image/png");
    a.download = "plotplan.png";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  function clearAll() {
    if (!confirm("부지 내 모든 객체를 삭제할까요?")) return;
    state.objects = [];
    state.selectedId = null;
    state.mode = "idle";
    state.placingTemplate = null;
    setStatus("대기");
    draw();
    syncJson();
  }

  // canvas mouse helpers
  function getMouseMeters(evt) {
    const rect = cvs.getBoundingClientRect();
    const xPx = (evt.clientX - rect.left) * (cvs.width / rect.width);
    const yPx = (evt.clientY - rect.top) * (cvs.height / rect.height);
    const mx = (xPx - state.marginPx) / state.scale;
    const my = (yPx - state.marginPx) / state.scale;
    return {
      mx: clamp(mx, 0, state.siteW),
      my: clamp(my, 0, state.siteH)
    };
  }

  // mouse move
  cvs.addEventListener("mousemove", (evt) => {
    const {mx, my} = getMouseMeters(evt);
    state.hoverMouse_m = {x: mx, y: my};

    if (state.dragging) {
      const o = state.objects.find(o => o.id === state.dragging.id);
      if (o) {
        o.x = mx - state.dragging.offsetX_m;
        o.y = my - state.dragging.offsetY_m;
        snapInsideSite(o);
        draw();
      }
      return;
    }

    if (state.mode === "placing") draw();
  });

  // mousedown
  cvs.addEventListener("mousedown", (evt) => {
    if (!sanitizeSite()) return;
    const {mx, my} = getMouseMeters(evt);

    if (state.mode === "placing" && state.placingTemplate) {
      // create object on click and start dragging
      const tpl = state.placingTemplate;
      const o = {
        id: genId(),
        type: tpl.type,
        w: tpl.w,
        h: tpl.h,
        x: mx - tpl.w/2,
        y: my - tpl.h/2
      };
      snapInsideSite(o);
      state.objects.push(o);
      state.selectedId = o.id;
      bringToFront(o.id);

      state.dragging = { id: o.id, offsetX_m: mx - o.x, offsetY_m: my - o.y };
      draw();
      syncJson();
      return;
    }

    // select & drag existing
    const hit = getTopmostAt(mx, my);
    if (hit) {
      state.selectedId = hit.id;
      bringToFront(hit.id);
      state.dragging = { id: hit.id, offsetX_m: mx - hit.x, offsetY_m: my - hit.y };
      draw();
      syncJson();
    } else {
      state.selectedId = null;
      draw();
      syncJson();
    }
  });

  // mouseup: finish drag; if was placing, exit placing mode
  window.addEventListener("mouseup", () => {
    if (state.dragging) {
      state.dragging = null;
      if (state.mode === "placing") {
        state.mode = "idle";
        state.placingTemplate = null;
        setStatus("대기");
      }
      draw();
      syncJson();
    }
  });

  // keyboard
  window.addEventListener("keydown", (evt) => {
    if (evt.key === "Escape") {
      if (state.mode === "placing") {
        state.mode = "idle";
        state.placingTemplate = null;
        state.dragging = null;
        setStatus("대기");
        draw();
        syncJson();
        return;
      }
      if (state.mode !== "finished") {
        state.mode = "finished";
        setStatus("배치 완료(종료 상태)");
      } else {
        state.mode = "idle";
        setStatus("대기");
      }
      draw();
      syncJson();
    }

    if (evt.key === "Delete" || evt.key === "Backspace") {
      deleteSelected();
    }
  });

  // buttons
  document.getElementById("btnSetSite").addEventListener("click", onSetSite);
  document.getElementById("btnAdd").addEventListener("click", onAdd);
  document.getElementById("btnExportJson").addEventListener("click", exportJson);
  document.getElementById("btnExportPng").addEventListener("click", exportPng);
  document.getElementById("btnClear").addEventListener("click", clearAll);
  document.getElementById("btnDeleteSel").addEventListener("click", deleteSelected);

  // init
  badge.textContent = `Site: ${state.siteW} × ${state.siteH} m`;
  recomputeScale();
  setStatus("대기");
  draw();
  syncJson();
})();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML
