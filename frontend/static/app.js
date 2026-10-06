/* CommAgent 运维台前端 */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

/* ---------- 导航 ---------- */
$$(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".nav-btn").forEach((b) => b.classList.remove("active"));
    $$(".view").forEach((v) => v.classList.remove("active"));
    btn.classList.add("active");
    $(`#view-${btn.dataset.view}`).classList.add("active");
  });
});

/* ========== 离线降级 Mock（无后端时浏览器可预览） ========== */
const MOCK_PRESETS = [
  { id: "mock", name: "本地演示引擎", mode: "mock", model: "builtin-rules", api_base: "", note: "离线确定性推理，答辩无网可用" },
  { id: "openai", name: "OpenAI", mode: "api", model: "gpt-4o-mini", api_base: "https://api.openai.com/v1", note: "GPT 系列" },
  { id: "deepseek", name: "DeepSeek", mode: "api", model: "deepseek-chat", api_base: "https://api.deepseek.com/v1", note: "性价比高，中文好" },
  { id: "moonshot", name: "Moonshot Kimi", mode: "api", model: "moonshot-v1-8k", api_base: "https://api.moonshot.cn/v1", note: "长上下文" },
  { id: "qwen", name: "通义千问 DashScope", mode: "api", model: "qwen-plus", api_base: "https://dashscope.aliyuncs.com/compatible-mode/v1", note: "阿里云兼容模式" },
  { id: "zhipu", name: "智谱 GLM", mode: "api", model: "glm-4-flash", api_base: "https://open.bigmodel.cn/api/paas/v4", note: "国产大模型" },
  { id: "custom", name: "自定义端点", mode: "api", model: "", api_base: "", note: "任意 OpenAI 兼容接口" },
];

const MOCK_CFG = {
  llm_mode: "mock",
  llm_model: "builtin-rules",
  llm_api_base: "",
  llm_api_key: "",
  llm_api_key_set: false,
  llm_timeout: 30,
  llm_temperature: 0.3,
};

function mockClassify(text) {
  const t = (text || "").toLowerCase();
  const has = (...ks) => ks.some((k) => t.includes(k));
  if (has("你好", "hello", "hi", "嗨", "在吗", "谢谢", "再见", "拜拜", "晚安", "笑话", "你是谁", "无聊", "哈哈")) return { intent: "casual", conf: 0.9 };
  if (has("可以问", "能问", "问什么", "示例", "怎么用", "怎么使用", "如何使用", "用法", "能做", "帮助", "介绍")) return { intent: "help", conf: 0.9 };
  if (has("报告", "周报")) return { intent: "report", conf: 0.9 };
  if (has("诊断", "根因", "告警", "排查")) return { intent: "diagnose", conf: 0.85 };
  if (has("优化", "功率", "调度", "吞吐", "负载")) return { intent: "optimize", conf: 0.8 };
  if (has("波束", "阵列", "天线", "mimo")) return { intent: "simulate_beam", conf: 0.85 };
  if (has("干扰", "同频", "邻区")) return { intent: "simulate_interference", conf: 0.85 };
  if (has("链路", "覆盖", "snr", "容量", "距离", "仿真")) return { intent: "simulate_link", conf: 0.85 };
  if (has("基站", "小区", "组网", "拓扑")) return { intent: "network", conf: 0.8 };
  if (has("什么是", "原理", "公式", "香农", "6g", "mimo")) return { intent: "knowledge", conf: 0.8 };
  return { intent: "casual", conf: 0.5 };
}

function mockChat(message) {
  const c = mockClassify(message);
  const samples = [
    "帮我做 3.5GHz 100MHz 带宽、距离 200m 的链路预算和覆盖曲线",
    "分析 16 阵元波束赋形方向图和多用户波束分配",
    "服务距离 150m，2 个同频干扰源，分析 SINR",
    "SINR 是 -2dB，BLER 0.12，帮我做根因诊断",
    "3 个基站 20 个用户组网，优化功率提升吞吐",
    "生成一份网络仿真与诊断报告",
    "什么是香农公式和它的工程意义？",
  ];
  const text = (message || "").trim();
  if (c.intent === "casual" || c.intent === "general") {
    let msg = "在的～想聊两句也行，想算网络指标也行。";
    if (/谢谢|感谢|多谢/.test(text)) msg = "不客气！还有要跑的指令随时喊我。";
    else if (/再见|拜拜|晚安/.test(text)) msg = "好嘞，先这样。有告警或覆盖问题再来找我～";
    else if (/你是谁|你叫什么|介绍/.test(text)) msg = "我是 CommAgent，通信运维搭子：链路、波束、干扰、诊断、优化、报告都能干，也接闲聊。";
    else if (/笑话/.test(text)) msg = "为什么 SINR 从不去夜店？——因为旁边全是干扰。";
    else if (/你好|hi|hello|嗨|在吗/i.test(text) || text.length <= 4) msg = "哈喽～我是 CommAgent。想算指标、查问题，或者随便聊聊都行。";
    else msg = "嗯嗯，有收到。要不要顺手来点硬活？我这边这几个很好使：\n\n" + samples.slice(0, 3).map((s) => `· ${s}`).join("\n");
    return {
      query: message,
      intent: c.intent,
      confidence: c.conf,
      entities: {},
      agent: "CasualAgent",
      success: true,
      message: msg,
      llm_note: "",
      data: { tone: "casual" },
      charts: [],
      light: true,
    };
  }
  if (c.intent === "help") {
    return {
      query: message,
      intent: "help",
      confidence: c.conf,
      entities: {},
      agent: "HelpAgent",
      success: true,
      message:
        "下面是几条你可以直接输入的运维指令：\n\n" +
        samples.map((s, i) => `${i + 1}. ${s}`).join("\n") +
        "\n\n怎么用：\n· 直接说人话下指令\n· 也可点下方快捷标签\n· 右上角「模型设置」切换引擎",
      llm_note: "",
      data: { samples },
      charts: [],
      light: true,
    };
  }
  if (c.intent === "simulate_link") {
    const pts = Array.from({ length: 12 }, (_, i) => {
      const d = 40 + i * 40;
      return {
        distance_m: d,
        snr_db: +(36 - d / 12).toFixed(2),
        capacity_mbps: +(800 - d * 1.2).toFixed(1),
      };
    });
    return {
      query: message,
      intent: "simulate_link",
      confidence: c.conf,
      entities: {},
      agent: "LinkSimulationAgent",
      success: true,
      message:
        "（预览示意）链路预算：d=200m, fc=3.5GHz, B=100MHz → 路损约 114.4 dB，SNR 约 36.7 dB，理论容量约 1218 Mbps。启动后端可得到精确结果。",
      llm_note: "离线预览，数值为示意。",
      data: { link_budget: { snr_db: 36.65, capacity_mbps: 1217.66 } },
      charts: [
        {
          type: "line",
          title: "覆盖曲线",
          x_key: "distance_m",
          series: [
            { name: "SNR (dB)", y_key: "snr_db" },
            { name: "吞吐 (Mbps)", y_key: "capacity_mbps" },
          ],
          points: pts,
        },
      ],
    };
  }
  if (c.intent === "diagnose") {
    return {
      query: message,
      intent: "diagnose",
      confidence: c.conf,
      entities: {},
      agent: "DiagnosisAgent",
      success: true,
      message: "（预览示意）诊断：SINR 低于 0 dB，链路处于干扰/噪声受限。",
      llm_note: "离线预览模式。",
      data: {
        overall: "critical",
        findings: [
          {
            level: "critical",
            signal: "SINR",
            value: "-2 dB",
            reason: "SINR 低于 0 dB，高阶调制无法工作。",
            suggestion: "检查同频邻区、启用 ICIC 或窄波束赋形。",
          },
        ],
      },
      charts: [],
    };
  }
  return {
    query: message,
    intent: c.intent,
    confidence: c.conf,
    entities: {},
    agent: "PreviewAgent",
    success: true,
    message: `（离线预览）识别意图为 ${c.intent}。启动后端（python run.py）可运行完整仿真与诊断。也可以先问：「给我几个可以问的问题」。`,
    llm_note: "当前是浏览器降级预览，未连接 CommAgent 后端。",
    data: {},
    charts: [],
  };
}

function mockHandle(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const body = options.body ? JSON.parse(options.body) : null;
  const url = new URL(path, location.href);
  const p = url.pathname;

  if (p.endsWith("/api/health")) {
    return { status: "ok", app: "CommAgent 预览", llm_mode: "preview", llm_class: "BrowserMock", llm_model: "preview", knowledge_items: 7 };
  }
  if (p.endsWith("/api/llm/presets")) return { presets: MOCK_PRESETS };
  if (p.endsWith("/api/llm/config") && method === "POST") {
    Object.assign(MOCK_CFG, body || {});
    return { ok: true, config: { ...MOCK_CFG, llm_api_key: "", llm_api_key_set: !!MOCK_CFG.llm_api_key } };
  }
  if (p.endsWith("/api/llm/config")) {
    return { ...MOCK_CFG, llm_api_key: MOCK_CFG.llm_api_key ? "已设置" : "", llm_api_key_set: !!MOCK_CFG.llm_api_key };
  }
  if (p.endsWith("/api/llm/test")) return { ok: true, detail: "预览模式连接正常", latency_ms: 1 };
  if (p.endsWith("/api/chat") && method === "POST") return mockChat(body?.message || "");
  if (p.endsWith("/api/link")) {
    const d = body?.distance_m ?? 200;
    const pts = Array.from({ length: 12 }, (_, i) => {
      const x = Math.round((d * 1.5 * (i + 1)) / 12);
      return {
        distance_m: x,
        snr_db: +(36 - x / 12).toFixed(2),
        capacity_mbps: +(800 - x * 1.2).toFixed(1),
        rx_power_dbm: +(-50 - x / 10).toFixed(2),
        path_loss_db: +(100 + x / 20).toFixed(2),
      };
    });
    return {
      link_budget: {
        path_loss_db: 114.35,
        rx_power_dbm: -50.35,
        noise_power_dbm: -87,
        snr_db: 36.65,
        capacity_mbps: 1217.66,
        spectral_efficiency_bps_hz: 12.18,
        link_quality: "优秀(256QAM)",
      },
      coverage: { points: pts, coverage_edge_m: 500, summary: "（预览）SNR≥0dB 覆盖约 500m" },
    };
  }
  if (p.endsWith("/api/beam")) {
    const pts = Array.from({ length: 37 }, (_, i) => {
      const az = -180 + i * 10;
      return { azimuth_deg: az, gain_dbi: +(18 - Math.abs(az) / 8).toFixed(2) };
    });
    return {
      pattern: { n_elements: 16, max_gain_dbi: 18, beamwidth_3db_deg: 12, points: pts, summary: "（预览）16 阵元 ULA" },
      allocation: { n_users: 4, beams: [], summary: "（预览）多用户波束分配" },
    };
  }
  if (p.endsWith("/api/interference")) {
    return {
      serving: { distance_m: 150, rx_power_dbm: -62 },
      interferers: [{ distance_m: 230, rx_power_dbm: -78 }],
      interference_dbm: -78,
      noise_dbm: -87,
      sinr_db: 8.2,
      capacity_mbps: 420,
      link_quality: "良好(64QAM)",
      summary: "（预览）2 个同频干扰源，SINR≈8.2 dB",
    };
  }
  if (p.endsWith("/api/diagnose")) {
    return mockChat("帮我做根因诊断").data;
  }
  if (p.endsWith("/api/optimize")) {
    return {
      actions: [
        { bs_id: "BS-1", action: "reduce_power", from_dbm: 40, to_dbm: 38, reason: "降低对邻区干扰" },
        { bs_id: "BS-2", action: "increase_power", from_dbm: 40, to_dbm: 44, reason: "提升覆盖" },
      ],
      before: { avg_capacity_mbps: 339 },
      after: { avg_capacity_mbps: 436 },
      delta_capacity_mbps: 97,
      scenario_after: { kpis: Array.from({ length: 12 }, (_, i) => ({ distance_m: 50 + i * 30, sinr_db: 10 + (i % 5), snr_db: 12 })) },
      summary: "（预览）功率局部搜索，平均吞吐 +97 Mbps",
    };
  }
  if (p.endsWith("/api/scenario")) {
    return {
      params: { n_bs: 3, n_ue: 20 },
      base_stations: [{ id: "BS-1", x: 0, y: 0 }, { id: "BS-2", x: 400, y: 0 }, { id: "BS-3", x: -200, y: 350 }],
      users: [],
      kpis: Array.from({ length: 12 }, (_, i) => ({
        ue_id: `UE-${i + 1}`,
        distance_m: 40 + i * 25,
        sinr_db: +(12 - i * 0.8).toFixed(2),
        snr_db: +(12 - i * 0.8).toFixed(2),
        capacity_mbps: +(300 - i * 12).toFixed(1),
      })),
      stats: { avg_sinr_db: 8.9, min_sinr_db: -0.8, avg_capacity_mbps: 339, weak_ue_count: 9 },
    };
  }
  return { ok: true };
}

/* ---------- 工具 ---------- */
let USING_PREVIEW = false;
async function api(path, options = {}) {
  try {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  } catch (e) {
    USING_PREVIEW = true;
    return mockHandle(path, options);
  }
}

function kpis(container, items) {
  const el = typeof container === "string" ? $(container) : container;
  el.innerHTML = items
    .map(
      (it) => `
      <div class="kpi ${it.tone || ""}">
        <div class="k">${it.label}</div>
        <div class="v">${it.value}</div>
      </div>`
    )
    .join("");
}

function toast(msg, ms = 2200) {
  const el = $("#toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.hidden = true), ms);
}

/* ========== 高清 + 交互图表 ========== */
const chartTooltip = document.createElement("div");
chartTooltip.className = "chart-tip";
chartTooltip.hidden = true;
document.body.appendChild(chartTooltip);

function showTip(x, y, html) {
  chartTooltip.innerHTML = html;
  chartTooltip.hidden = false;
  const pad = 12;
  const w = chartTooltip.offsetWidth || 180;
  const h = chartTooltip.offsetHeight || 60;
  let left = x + pad;
  let top = y + pad;
  if (left + w > window.innerWidth - 8) left = x - w - pad;
  if (top + h > window.innerHeight - 8) top = y - h - pad;
  chartTooltip.style.left = `${left}px`;
  chartTooltip.style.top = `${top}px`;
}
function hideTip() {
  chartTooltip.hidden = true;
}

function setupHiDPI(canvas) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
  const rect = canvas.getBoundingClientRect();
  const cssW = rect.width || canvas.width || 640;
  const cssH = canvas.height * (cssW / (canvas.width || 640));
  canvas.style.width = cssW + "px";
  canvas.style.height = cssH + "px";
  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(cssH * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, W: cssW, H: cssH, dpr };
}

function drawLineChart(canvas, points, series, xKey) {
  const { ctx, W, H } = setupHiDPI(canvas);
  ctx.clearRect(0, 0, W, H);
  if (!points || points.length === 0) return;

  const pad = { l: 52, r: 18, t: 28, b: 38 };
  const xs = points.map((p) => p[xKey]);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const leftKey = series[0].y_key;
  const rightKey = series[1] ? series[1].y_key : null;

  const ysLeft = points.map((p) => p[leftKey]);
  let yLMin = Math.min(...ysLeft), yLMax = Math.max(...ysLeft);
  if (yLMin === yLMax) { yLMin -= 1; yLMax += 1; }
  let yRMin = 0, yRMax = 1;
  if (rightKey) {
    const ysRight = points.map((p) => p[rightKey]);
    yRMin = Math.min(...ysRight); yRMax = Math.max(...ysRight);
    if (yRMin === yRMax) { yRMin -= 1; yRMax += 1; }
  }

  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;
  const xScale = (v) => pad.l + ((v - xMin) / (xMax - xMin || 1)) * plotW;
  const yLScale = (v) => pad.t + (1 - (v - yLMin) / (yLMax - yLMin || 1)) * plotH;
  const yRScale = (v) => pad.t + (1 - (v - yRMin) / (yRMax - yRMin || 1)) * plotH;

  ctx.strokeStyle = "rgba(255,255,255,0.07)";
  ctx.fillStyle = "#8b9bb0";
  ctx.lineWidth = 1;
  ctx.font = "11px sans-serif";
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (plotH * i) / 4;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillText((yLMax - ((yLMax - yLMin) * i) / 4).toFixed(1), 8, y + 4);
    if (rightKey) ctx.fillText((yRMax - ((yRMax - yRMin) * i) / 4).toFixed(1), W - pad.r + 2, y + 4);
  }
  for (let i = 0; i <= 5; i++) {
    const x = pad.l + (plotW * i) / 5;
    ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, H - pad.b); ctx.stroke();
    ctx.fillText((xMin + ((xMax - xMin) * i) / 5).toFixed(0), x - 10, H - pad.b + 16);
  }

  const colors = ["#3d9b8f", "#e2b15c"];
  series.forEach((s, si) => {
    const scale = si === 1 && rightKey ? yRScale : yLScale;
    ctx.strokeStyle = colors[si % colors.length];
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    points.forEach((p, i) => {
      const x = xScale(p[xKey]);
      const y = scale(p[s.y_key]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = colors[si % colors.length];
    ctx.fillRect(pad.l + si * 110, 10, 10, 10);
    ctx.fillStyle = "#d7e2ef";
    ctx.fillText(s.name, pad.l + si * 110 + 14, 19);
  });

  // 交互：悬停最近点
  canvas._chart = {
    kind: "line", points, series, xKey, xScale, yLScale, yRScale, rightKey, pad, W, H,
  };
  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    let best = null, bestD = 1e9;
    for (const p of points) {
      const d = Math.abs(xScale(p[xKey]) - mx);
      if (d < bestD) { bestD = d; best = p; }
    }
    if (!best || bestD > 40) { hideTip(); canvas._hover = null; return; }
    canvas._hover = best;
    redrawLineHover(canvas);
    const rows = series.map((s) => `<div><b style="color:#7dceb8">${s.name}</b> ${best[s.y_key]}</div>`).join("");
    showTip(e.clientX, e.clientY, `<div class="tip-t">${xKey} = ${best[xKey]}</div>${rows}`);
  };
  canvas.onmouseleave = () => { hideTip(); canvas._hover = null; redrawLineHover(canvas); };
}

function redrawLineHover(canvas) {
  const c = canvas._chart;
  if (!c) return;
  // 重绘整图（轻量）再画十字线
  drawLineChartBase(canvas);
  const p = canvas._hover;
  if (!p) return;
  const { ctx, xScale, yLScale, series } = c;
  const x = xScale(p[c.xKey]);
  ctx.strokeStyle = "rgba(226,177,92,0.55)";
  ctx.setLineDash([4, 3]);
  ctx.beginPath();
  ctx.moveTo(x, c.pad.t);
  ctx.lineTo(x, c.H - c.pad.b);
  ctx.stroke();
  ctx.setLineDash([]);
  series.forEach((s, si) => {
    const y = (si === 1 && c.rightKey ? c.yRScale : yLScale)(p[s.y_key]);
    ctx.fillStyle = "#e2b15c";
    ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#0b1220";
    ctx.beginPath(); ctx.arc(x, y, 2.2, 0, Math.PI * 2); ctx.fill();
  });
}

function drawLineChartBase(canvas) {
  const c = canvas._chart;
  if (!c) return;
  // 通过原函数重画但不绑事件 —— 复用逻辑：临时清空 _chart 防递归
  const keep = canvas._chart;
  const hover = canvas._hover;
  const onMove = canvas.onmousemove;
  const onLeave = canvas.onmouseleave;
  canvas._chart = null;
  drawLineChart(canvas, c.points, c.series, c.xKey);
  canvas._chart = keep;
  canvas._hover = hover;
  canvas.onmousemove = onMove;
  canvas.onmouseleave = onLeave;
}

function drawScatter(canvas, points, xKey, yKey) {
  const { ctx, W, H } = setupHiDPI(canvas);
  ctx.clearRect(0, 0, W, H);
  if (!points || !points.length) return;
  const pad = { l: 48, r: 18, t: 22, b: 38 };
  const xs = points.map((p) => p[xKey]);
  const ys = points.map((p) => p[yKey]);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys) - 2, yMax = Math.max(...ys) + 2;
  const plotW = W - pad.l - pad.r, plotH = H - pad.t - pad.b;
  const xScale = (v) => pad.l + ((v - xMin) / (xMax - xMin || 1)) * plotW;
  const yScale = (v) => pad.t + (1 - (v - yMin) / (yMax - yMin || 1)) * plotH;

  ctx.strokeStyle = "rgba(255,255,255,0.07)"; ctx.fillStyle = "#8b9bb0"; ctx.font = "11px sans-serif";
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (plotH * i) / 4;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillText((yMax - ((yMax - yMin) * i) / 4).toFixed(1), 8, y + 4);
  }
  if (yMin < 0 && yMax > 0) {
    ctx.strokeStyle = "#e27a5c"; ctx.setLineDash([5, 4]);
    ctx.beginPath(); ctx.moveTo(pad.l, yScale(0)); ctx.lineTo(W - pad.r, yScale(0)); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#e27a5c"; ctx.fillText("SINR = 0 dB", pad.l + 6, yScale(0) - 6);
  }

  const drawDots = (hover) => {
    points.forEach((p) => {
      const v = p[yKey];
      const on = hover === p;
      ctx.fillStyle = on ? "#f0d080" : (v < 0 ? "#e27a5c" : v < 10 ? "#e2b15c" : "#4cb89a");
      ctx.beginPath();
      ctx.arc(xScale(p[xKey]), yScale(v), on ? 7 : 5, 0, Math.PI * 2);
      ctx.fill();
      if (on) {
        ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5; ctx.stroke(); ctx.lineWidth = 1;
      }
    });
    ctx.fillStyle = "#8b9bb0";
    ctx.fillText(xKey, W / 2 - 20, H - 8);
  };
  drawDots(null);

  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    let best = null, bestD = 1e9;
    for (const p of points) {
      const d = Math.hypot(xScale(p[xKey]) - mx, yScale(p[yKey]) - my);
      if (d < bestD) { bestD = d; best = p; }
    }
    if (!best || bestD > 28) { hideTip(); drawDots(null); return; }
    drawDots(best);
    const rows = Object.entries(best)
      .slice(0, 8)
      .map(([k, v]) => `<div><b>${k}</b> ${v}</div>`)
      .join("");
    showTip(e.clientX, e.clientY, rows);
  };
  canvas.onmouseleave = () => { hideTip(); drawDots(null); };
}

function drawBeamPattern(canvas, points) {
  const { ctx, W, H } = setupHiDPI(canvas);
  ctx.clearRect(0, 0, W, H);
  if (!points || !points.length) return;
  const cx = W / 2, cy = H / 2 + 8;
  const R = Math.min(W, H) * 0.38;

  const paint = (hover) => {
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = "rgba(255,255,255,0.08)"; ctx.fillStyle = "#8b9bb0"; ctx.font = "11px sans-serif";
    for (const db of [-20, -10, -3, 0]) {
      const r = R * ((db + 30) / 30);
      if (r <= 0) continue;
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
      ctx.fillText(`${db} dB`, cx + r + 4, cy + 3);
    }
    ctx.beginPath();
    points.forEach((p, i) => {
      const ang = ((p.azimuth_deg - 90) * Math.PI) / 180;
      const g = Math.max(p.gain_dbi, -30);
      const r = R * ((g + 30) / 30);
      const x = cx + r * Math.cos(ang);
      const y = cy + r * Math.sin(ang);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fillStyle = "rgba(76, 184, 154, 0.16)"; ctx.fill();
    ctx.strokeStyle = "#4cb89a"; ctx.lineWidth = 2; ctx.stroke();

    if (hover) {
      const ang = ((hover.azimuth_deg - 90) * Math.PI) / 180;
      const g = Math.max(hover.gain_dbi, -30);
      const r = R * ((g + 30) / 30);
      const x = cx + r * Math.cos(ang), y = cy + r * Math.sin(ang);
      ctx.strokeStyle = "#e2b15c"; ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(x, y); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = "#f0d080"; ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = "#d7e2ef";
    ctx.fillText("0°", cx - 8, cy - R - 8);
    ctx.fillText("90°", cx + R + 6, cy + 4);
    ctx.fillText("180°", cx - 14, cy + R + 18);
    ctx.fillText("270°", cx - R - 28, cy + 4);
  };
  paint(null);

  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const dx = mx - cx, dy = my - cy;
    const dist = Math.hypot(dx, dy);
    if (dist > R * 1.15) { hideTip(); paint(null); return; }
    // 找最近角度
    let az = (Math.atan2(dy, dx) * 180) / Math.PI + 90;
    az = ((az + 180) % 360) - 180;
    let best = null, bestD = 1e9;
    for (const p of points) {
      let d = Math.abs(p.azimuth_deg - az);
      if (d > 180) d = 360 - d;
      if (d < bestD) { bestD = d; best = p; }
    }
    paint(best);
    showTip(e.clientX, e.clientY,
      `<div class="tip-t">方向图采样</div>
       <div><b>方位角</b> ${best.azimuth_deg}°</div>
       <div><b>增益</b> ${best.gain_dbi} dBi</div>
       <div style="opacity:.7">距轴心 ${dist.toFixed(0)}px</div>`);
  };
  canvas.onmouseleave = () => { hideTip(); paint(null); };
}

/* ---------- 健康检查 ---------- */
async function refreshHealth() {
  try {
    const h = await api("/api/health");
    if (USING_PREVIEW) {
      $("#statusText").textContent = "预览模式 · 未连后端";
      $("#statusCard .dot").classList.add("ok");
      $("#llmChip").textContent = "引擎 · 浏览器预览";
    } else {
      $("#statusText").textContent = `${h.llm_mode === "mock" ? "本地演示" : h.llm_model} · 就绪`;
      $("#statusCard .dot").classList.add("ok");
      $("#llmChip").textContent =
        h.llm_mode === "mock" ? "引擎 · 本地演示" : `引擎 · ${h.llm_model}`;
    }
  } catch (e) {
    $("#statusText").textContent = "后端未连接";
  }
}
refreshHealth();

/* ========== 模型设置抽屉 ========== */
const drawer = $("#drawer");
const drawerMask = $("#drawerMask");
let currentCfg = {
  llm_mode: "mock",
  llm_model: "gpt-4o-mini",
  llm_api_base: "https://api.openai.com/v1",
  llm_api_key: "",
  llm_timeout: 30,
  llm_temperature: 0.3,
};
let presets = [];

function openDrawer() {
  drawer.hidden = false;
  drawerMask.hidden = false;
  document.body.classList.add("drawer-open");
  // 聚焦到第一个可输入，提升键盘可达性
  const first = drawer.querySelector("input, button");
  if (first) setTimeout(() => first.focus(), 50);
}
function closeDrawer() {
  document.body.classList.remove("drawer-open");
  drawer.hidden = true;
  drawerMask.hidden = true;
}

$("#btnSettings").addEventListener("click", async (e) => {
  e.stopPropagation();
  openDrawer();
  try {
    const [cfg, pre] = await Promise.all([
      api("/api/llm/config"),
      api("/api/llm/presets"),
    ]);
    currentCfg = { ...currentCfg, ...cfg };
    presets = pre.presets || [];
    fillDrawer();
  } catch (e2) {
    toast("读取模型配置失败：" + e2.message);
  }
});

// 关闭：✕ / 取消 / Esc / 左缘把手
["#drawerClose", "#btnCancel"].forEach((sel) => {
  const el = $(sel);
  if (el) el.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    closeDrawer();
  });
});
if (drawerMask) drawerMask.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeDrawer();
});

function fillDrawer() {
  $$("#modeSeg button").forEach((b) => {
    b.classList.toggle("on", b.dataset.mode === currentCfg.llm_mode);
  });
  $("#cfgBase").value = currentCfg.llm_api_base || "";
  $("#cfgKey").value = currentCfg.llm_api_key_set
    ? currentCfg.llm_api_key || "已设置"
    : "";
  $("#cfgKey").placeholder = currentCfg.llm_api_key_set ? "已设置（留空则不修改）" : "sk-…";
  $("#cfgModel").value = currentCfg.llm_model || "";
  $("#cfgTimeout").value = currentCfg.llm_timeout ?? 30;
  $("#cfgTemp").value = currentCfg.llm_temperature ?? 0.3;
  toggleApiFields();
  renderPresets();
}

function toggleApiFields() {
  const mode = currentCfg.llm_mode;
  $$(".api-only").forEach((el) => {
    el.classList.toggle("api-hidden", mode !== "api");
  });
}

function renderPresets() {
  const grid = $("#presetGrid");
  grid.innerHTML = presets
    .map((p) => {
      const on =
        (p.mode === "mock" && currentCfg.llm_mode === "mock") ||
        (p.mode === "api" &&
          currentCfg.llm_mode === "api" &&
          (currentCfg.llm_api_base === p.api_base || (!p.api_base && p.id === "custom")));
      return `<button type="button" class="preset ${on ? "on" : ""}" data-id="${p.id}">
        <b>${p.name}</b><span>${p.note}</span>
      </button>`;
    })
    .join("");

  $$(".preset", grid).forEach((btn) => {
    btn.addEventListener("click", () => {
      const p = presets.find((x) => x.id === btn.dataset.id);
      if (!p) return;
      currentCfg.llm_mode = p.mode;
      if (p.mode === "api") {
        if (p.api_base) currentCfg.llm_api_base = p.api_base;
        if (p.model) currentCfg.llm_model = p.model;
        if (p.id === "custom") {
          currentCfg.llm_api_base = "";
          currentCfg.llm_model = "";
        }
      } else {
        currentCfg.llm_model = "builtin-rules";
      }
      fillDrawer();
    });
  });
}

$$("#modeSeg button").forEach((b) => {
  b.addEventListener("click", () => {
    currentCfg.llm_mode = b.dataset.mode;
    fillDrawer();
  });
});

$("#btnTest").addEventListener("click", async () => {
  const result = $("#testResult");
  result.className = "test-result";
  result.textContent = "测试中…";
  try {
    const payload = {
      llm_mode: currentCfg.llm_mode,
      llm_model: $("#cfgModel").value || currentCfg.llm_model,
      llm_api_base: $("#cfgBase").value,
      llm_api_key: $("#cfgKey").value || null,
      llm_timeout: +$("#cfgTimeout").value || 15,
    };
    const r = await api("/api/llm/test", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (r.ok) {
      result.className = "test-result ok";
      result.textContent = `连接成功${r.latency_ms ? ` · ${r.latency_ms}ms` : ""} · ${r.detail.slice(0, 60)}`;
    } else {
      result.className = "test-result bad";
      result.textContent = `失败：${r.detail}`;
    }
  } catch (e) {
    result.className = "test-result bad";
    result.textContent = "请求失败：" + e.message;
  }
});

$("#btnSave").addEventListener("click", async () => {
  const payload = {
    llm_mode: currentCfg.llm_mode,
    llm_model: $("#cfgModel").value || currentCfg.llm_model,
    llm_api_base: $("#cfgBase").value,
    llm_timeout: +$("#cfgTimeout").value || 30,
    llm_temperature: +$("#cfgTemp").value || 0.3,
    llm_api_key: $("#cfgKey").value || null,
  };
  try {
    const r = await api("/api/llm/config", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    currentCfg = { ...currentCfg, ...r.config };
    await refreshHealth();
    toast("模型设置已保存并生效");
    closeDrawer();
  } catch (e) {
    toast("保存失败：" + e.message);
  }
});

/* ---------- 聊天 ---------- */
const chatHistory = []; // {role, content} 多轮上下文

function addMsg(role, html) {
  const box = $("#chatBox");
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = `
    <div class="avatar">${role === "user" ? "我" : "CA"}</div>
    <div class="bubble">${html}</div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function buildTable(points, cols) {
  if (!points || !points.length) return "";
  const head = cols.map((c) => `<th>${c.label}</th>`).join("");
  const body = points
    .slice(0, 12)
    .map(
      (p) =>
        `<tr title="悬停高亮，双击可复制行">${cols
          .map((c) => `<td>${p[c.key] ?? "—"}</td>`)
          .join("")}</tr>`
    )
    .join("");
  return `<table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderChatResult(data) {
  const panel = $("#chatResult");
  // 闲聊 / 帮助：只留在气泡里，别甩一堆调度面板
  if (data.light || data.intent === "casual" || data.intent === "help" || data.intent === "general") {
    panel.hidden = true;
    panel.innerHTML = "";
    return;
  }
  panel.hidden = false;
  const charts = (data.charts || [])
    .map((c, idx) => {
      const cols = [
        { key: c.x_key, label: c.x_key },
        ...(c.series || []).map((s) => ({ key: s.y_key, label: s.name })),
      ];
      return `<canvas id="chatChart${idx}" width="720" height="280"></canvas>${buildTable(c.points, cols)}`;
    })
    .join("");
  const findings = data.data && data.data.findings
    ? data.data.findings
        .map(
          (f) => `<div class="finding ${f.level}">
            <span class="badge ${f.level}">${f.level}</span>
            <b>${f.signal}</b> = ${f.value}<br/>${f.reason}<br/>
            <span style="color:var(--accent)">建议：${f.suggestion}</span>
          </div>`
        )
        .join("")
    : "";
  const report = data.data && data.data.report
    ? data.data.report.sections
        .map((s) => `<h3>${s.heading}</h3><p>${s.body}</p>`)
        .join("")
    : "";

  panel.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="k">意图</div><div class="v" style="font-size:14px">${data.intent}</div></div>
      <div class="kpi"><div class="k">置信度</div><div class="v" style="font-size:14px">${data.confidence}</div></div>
      <div class="kpi"><div class="k">执行 Agent</div><div class="v" style="font-size:12px">${data.agent}</div></div>
      <div class="kpi ${data.success ? "good" : "bad"}"><div class="k">状态</div><div class="v" style="font-size:14px">${data.success ? "成功" : "失败"}</div></div>
    </div>
    <pre class="code">${data.message}</pre>
    ${data.llm_note ? `<pre class="code">${data.llm_note}</pre>` : ""}
    ${findings}
    ${report ? `<div class="report-doc">${report}</div>` : ""}
    ${charts}
  `;

  (data.charts || []).forEach((c, idx) => {
    const canvas = $(`#chatChart${idx}`);
    if (!canvas) return;
    if (c.type === "scatter") drawScatter(canvas, c.points, c.x_key, c.series[0].y_key);
    else drawLineChart(canvas, c.points, c.series, c.x_key);
  });
}

async function sendChat(text) {
  const msg = text || $("#chatInput").value.trim();
  if (!msg) return;
  $("#chatInput").value = "";
  addMsg("user", msg);
  chatHistory.push({ role: "user", content: msg });
  const history = chatHistory.slice(-12, -1);
  const pending = addMsg("bot", "稍等…");
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: msg, history }),
    });
    const reply = String(data.message || "");
    chatHistory.push({ role: "assistant", content: reply });
    const bubble = pending.querySelector(".bubble");
    const body = reply.replace(/\n/g, "<br/>");
    if (data.light || data.intent === "casual" || data.intent === "help" || data.intent === "general" || data.intent === "knowledge") {
      bubble.innerHTML = body;
    } else {
      bubble.innerHTML = `
        <p style="margin:0 0 6px;opacity:.75;font-size:12px">${data.agent} · ${data.intent}</p>
        ${body}
      `;
    }
    renderChatResult(data);
  } catch (e) {
    pending.querySelector(".bubble").innerHTML = `这步没连上：${e.message}。检查一下后端是不是在跑？`;
  }
}

$("#sendBtn").addEventListener("click", () => sendChat());
$("#chatInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat();
});
$$(".qbtn").forEach((b) => b.addEventListener("click", () => sendChat(b.dataset.q)));

/* ---------- 链路 ---------- */
$("#lk_run").addEventListener("click", async () => {
  const body = {
    distance_m: +$("#lk_d").value,
    carrier_ghz: +$("#lk_fc").value,
    bandwidth_mhz: +$("#lk_bw").value,
    tx_power_dbm: +$("#lk_p").value,
    environment: $("#lk_env").value,
    interference_dbm: $("#lk_i").value === "" ? null : +$("#lk_i").value,
  };
  const data = await api("/api/link", { method: "POST", body: JSON.stringify(body) });
  const lb = data.link_budget;
  kpis("#lk_kpi", [
    { label: "路损", value: `${lb.path_loss_db} dB` },
    { label: "接收功率", value: `${lb.rx_power_dbm} dBm` },
    { label: "SNR", value: `${lb.snr_db} dB`, tone: lb.snr_db >= 10 ? "good" : lb.snr_db >= 0 ? "warn" : "bad" },
    { label: "容量", value: `${lb.capacity_mbps} Mbps`, tone: "good" },
    { label: "频谱效率", value: `${lb.spectral_efficiency_bps_hz}` },
    { label: "质量", value: lb.link_quality, tone: lb.snr_db >= 10 ? "good" : lb.snr_db >= 0 ? "warn" : "bad" },
  ]);
  drawLineChart(
    $("#lk_chart"),
    data.coverage.points,
    [
      { name: "SNR (dB)", y_key: "snr_db" },
      { name: "吞吐 (Mbps)", y_key: "capacity_mbps" },
    ],
    "distance_m"
  );
  $("#lk_detail").textContent = JSON.stringify({ link_budget: lb, coverage_summary: data.coverage.summary }, null, 2);
});

/* ---------- 波束 ---------- */
$("#bm_run").addEventListener("click", async () => {
  const data = await api(
    `/api/beam?n_elements=${+$("#bm_n").value}&n_users=${+$("#bm_u").value}`
  );
  const p = data.pattern;
  kpis("#bm_kpi", [
    { label: "阵元数", value: p.n_elements },
    { label: "峰值增益", value: `${p.max_gain_dbi} dBi`, tone: "good" },
    { label: "3dB 波束", value: `${p.beamwidth_3db_deg}°` },
    { label: "用户数", value: data.allocation.n_users },
  ]);
  drawBeamPattern($("#bm_chart"), p.points);
  $("#bm_detail").textContent = JSON.stringify({ summary: p.summary, allocation: data.allocation }, null, 2);
});

/* ---------- 干扰 ---------- */
$("#if_run").addEventListener("click", async () => {
  const data = await api(
    `/api/interference?n_interferers=${+$("#if_n").value}&serving_distance_m=${+$("#if_d").value}`
  );
  kpis("#if_kpi", [
    { label: "SINR", value: `${data.sinr_db} dB`, tone: data.sinr_db >= 10 ? "good" : data.sinr_db >= 0 ? "warn" : "bad" },
    { label: "干扰", value: data.interference_dbm != null ? `${data.interference_dbm} dBm` : "无", tone: "warn" },
    { label: "容量", value: `${data.capacity_mbps} Mbps` },
    { label: "质量", value: data.link_quality },
  ]);
  $("#if_detail").textContent = JSON.stringify(data, null, 2);
});

/* ---------- 诊断 ---------- */
$("#dg_run").addEventListener("click", async () => {
  const body = {
    sinr_db: +$("#dg_sinr").value,
    rsrp_dbm: +$("#dg_rsrp").value,
    interference_dbm: +$("#dg_i").value,
    bler: +$("#dg_bler").value,
    prb_utilization: +$("#dg_prb").value,
    distance_m: +$("#dg_d").value,
  };
  const data = await api("/api/diagnose", { method: "POST", body: JSON.stringify(body) });
  $("#dg_out").innerHTML = `
    <div class="kpi-row">
      <div class="kpi ${data.overall === "ok" ? "good" : data.overall === "critical" ? "bad" : "warn"}">
        <div class="k">整体等级</div><div class="v">${data.overall}</div>
      </div>
      <div class="kpi"><div class="k">结论数</div><div class="v">${data.findings.length}</div></div>
    </div>
    ${data.findings
      .map(
        (f) => `<div class="finding ${f.level}">
          <span class="badge ${f.level}">${f.level}</span>
          <b>${f.signal}</b> = ${f.value}<br/>
          ${f.reason}<br/>
          <span style="color:var(--accent)">建议：${f.suggestion}</span>
        </div>`
      )
      .join("")}
  `;
});

/* ---------- 网络 ---------- */
$("#nt_run").addEventListener("click", async () => {
  const q = `n_bs=${+$("#nt_bs").value}&n_ue=${+$("#nt_ue").value}&seed=${+$("#nt_seed").value}`;
  const scenario = await api(`/api/scenario?${q}`);
  const s = scenario.stats;
  kpis("#nt_kpi", [
    { label: "平均 SINR", value: `${s.avg_sinr_db} dB`, tone: s.avg_sinr_db >= 10 ? "good" : "warn" },
    { label: "最差 SINR", value: `${s.min_sinr_db} dB`, tone: "bad" },
    { label: "平均容量", value: `${s.avg_capacity_mbps} Mbps` },
    { label: "弱覆盖 UE", value: s.weak_ue_count, tone: s.weak_ue_count > 0 ? "warn" : "good" },
  ]);
  drawScatter($("#nt_chart"), scenario.kpis, "distance_m", "sinr_db");
  $("#nt_detail").textContent = JSON.stringify(
    { params: scenario.params, base_stations: scenario.base_stations, stats: s },
    null,
    2
  );
});

$("#nt_opt").addEventListener("click", async () => {
  const body = {
    n_bs: +$("#nt_bs").value,
    n_ue: +$("#nt_ue").value,
    seed: +$("#nt_seed").value,
    area_m: 1200,
    carrier_ghz: 3.5,
    bandwidth_mhz: 100,
    tx_power_dbm: 40,
    environment: "urban",
  };
  const data = await api("/api/optimize", { method: "POST", body: JSON.stringify(body) });
  kpis("#nt_kpi", [
    { label: "优化前容量", value: `${data.before.avg_capacity_mbps ?? "-"} Mbps` },
    { label: "优化后容量", value: `${data.after.avg_capacity_mbps} Mbps`, tone: "good" },
    { label: "容量变化", value: `${data.delta_capacity_mbps} Mbps`, tone: data.delta_capacity_mbps >= 0 ? "good" : "warn" },
    { label: "动作数", value: data.actions.length },
  ]);
  $("#nt_detail").textContent = data.summary + "\n\n" + JSON.stringify(data.actions, null, 2);
  if (data.scenario_after) {
    drawScatter($("#nt_chart"), data.scenario_after.kpis, "distance_m", "sinr_db");
  }
});

/* ---------- 报告 ---------- */
async function genReport() {
  $("#rp_out").innerHTML = `<p class="muted">生成中…</p>`;
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: "生成一份网络仿真与诊断报告" }),
    });
    const report = data.data && data.data.report;
    if (!report) {
      $("#rp_out").innerHTML = `<pre class="code">${data.message}</pre>`;
      return;
    }
    $("#rp_out").innerHTML = `
      <h2 style="margin-top:0">${report.title}</h2>
      <div class="report-doc">
        ${report.sections.map((s) => `<h3>${s.heading}</h3><p>${s.body}</p>`).join("")}
      </div>
      <pre class="code">${data.message}</pre>
      <pre class="code">${data.llm_note || ""}</pre>
    `;
  } catch (e) {
    $("#rp_out").innerHTML = `<p class="muted">生成失败：${e.message}</p>`;
  }
}
$("#rp_run").addEventListener("click", genReport);

/* 默认跑一次链路 */
setTimeout(() => $("#lk_run") && $("#lk_run").click(), 300);
