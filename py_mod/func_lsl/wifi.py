import json
import time
import lib_lsl
from lib_lsl import WIFI
import lib_lsl.tl
import ws_lsl
import socket
import _thread

wifi = WIFI()

# UI网页
html = """
<!DOCTYPE html>
<html lang="zh-CN">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 网络测速 · WiFi 信号监测</title>
    <style>
        :root {
            --bg: #0b1220;
            --panel: #101a30;
            --panel2: #0d1526;
            --border: #1f2b45;
            --text: #e2e8f0;
            --muted: #94a3b8;
            --dim: #64748b;
            --accent: #38bdf8;
            --green: #22c55e;
            --red: #ef4444;
            --yellow: #eab308;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0
        }

        body {
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            font-family: "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif;
            padding: 16px;
        }

        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 16px;
            max-width: 1500px;
            margin-left: auto;
            margin-right: auto
        }

        h1 {
            font-size: 18px;
            font-weight: 600;
            color: #f1f5f9
        }

        h1 span {
            color: var(--accent)
        }

        .conn {
            display: flex;
            align-items: center;
            gap: 6px
        }

        input[type=text],
        input[type=number] {
            background: var(--panel2);
            border: 1px solid var(--border);
            color: var(--text);
            border-radius: 8px;
            padding: 8px 10px;
            font-size: 13px;
            font-family: monospace;
            outline: none;
        }

        input:focus {
            border-color: var(--accent)
        }

        .conn input {
            width: 130px
        }

        .conn input#port {
            width: 70px
        }

        button {
            background: #1e293b;
            color: var(--text);
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 13px;
            cursor: pointer;
            transition: background .15s, border-color .15s;
            white-space: nowrap;
        }

        button:hover:not(:disabled) {
            background: #2d3b55;
            border-color: var(--accent)
        }

        button:disabled {
            opacity: .4;
            cursor: not-allowed
        }

        .btn-primary {
            background: #0e7490;
            border-color: #0891b2;
            color: #fff
        }

        .btn-primary:hover:not(:disabled) {
            background: #0e7fa8;
            border-color: #22d3ee
        }

        .btn-danger {
            background: #7f1d1d;
            border-color: #b91c1c
        }

        .btn-danger:hover:not(:disabled) {
            background: #991b1b
        }

        .state {
            font-size: 12px;
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid transparent
        }

        .state.connected {
            color: var(--green);
            border-color: #22c55e55;
            background: #22c55e14
        }

        .state.connecting,
        .state.reconnecting {
            color: var(--yellow);
            border-color: #eab30855;
            background: #eab30814
        }

        .state.disconnected {
            color: var(--red);
            border-color: #ef444455;
            background: #ef444414
        }

        main {
            display: grid;
            max-width: 1500px;
            margin: 0 auto;
            gap: 14px;
            grid-template-columns: 340px 1fr;
            grid-template-areas: "controls speed" "stats rssi" "wifi wifi" "log log" "rx rx";
        }

        .panel {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            min-width: 0
        }

        .panel h2 {
            font-size: 13px;
            color: var(--muted);
            font-weight: 600;
            margin-bottom: 12px;
            letter-spacing: .3px
        }

        .controls {
            grid-area: controls
        }

        .stats {
            grid-area: stats
        }

        .speed {
            grid-area: speed
        }

        .rssi {
            grid-area: rssi
        }

        .wifi {
            grid-area: wifi
        }

        .log-panel {
            grid-area: log
        }

        .rx-panel {
            grid-area: rx
        }

        .field {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 10px
        }

        .field label {
            font-size: 13px;
            color: var(--muted);
            white-space: nowrap
        }

        .field input {
            width: 110px;
            text-align: right
        }

        .btns {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
            margin-top: 14px
        }

        .btns .row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px
        }

        .mode-hint {
            margin-top: 12px;
            font-size: 12px;
            color: var(--dim)
        }

        .comms {
            margin-top: 8px;
            font-size: 12px;
            color: var(--dim);
            font-family: monospace;
            line-height: 1.7;
            border-top: 1px solid var(--border);
            padding-top: 8px
        }

        .stat-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px
        }

        .stat {
            background: var(--panel2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px
        }

        .stat .k {
            font-size: 12px;
            color: var(--dim);
            margin-bottom: 4px
        }

        .stat .v {
            font-size: 20px;
            font-weight: 700;
            font-family: monospace;
            color: var(--accent);
            word-break: break-all
        }

        .stat .v.small {
            font-size: 15px
        }

        .chart-wrap {
            height: 250px;
            position: relative
        }

        .chart-wrap canvas {
            width: 100%;
            height: 100%;
            display: block
        }

        .legend {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
            min-height: 22px
        }

        .chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--panel2);
            border: 1px solid var(--border);
            color: #cbd5e1;
            font-size: 12px;
            border-radius: 999px;
            padding: 3px 10px 3px 6px;
            cursor: pointer;
            max-width: 220px;
        }

        .chip i {
            width: 10px;
            height: 10px;
            border-radius: 3px;
            display: inline-block;
            flex: none
        }

        .chip span {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap
        }

        .chip.off {
            opacity: .35;
            text-decoration: line-through
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px
        }

        th,
        td {
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid #1e293b;
            white-space: nowrap
        }

        th {
            color: var(--dim);
            font-weight: 600;
            font-size: 12px;
            background: var(--panel2)
        }

        tbody tr:hover {
            background: #16223c
        }

        tr.lost td {
            opacity: .45
        }

        .dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
            vertical-align: middle;
            flex: none
        }

        .ssid-cell {
            display: inline-flex;
            align-items: center;
            max-width: 260px;
            overflow: hidden;
            text-overflow: ellipsis
        }

        .mono {
            font-family: monospace;
            font-size: 12px;
            color: var(--muted)
        }

        .badge {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 999px;
            background: #ef444422;
            color: #f87171;
            border: 1px solid #ef444466;
            white-space: nowrap
        }

        #log {
            background: #0a0f1c;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px;
            height: 130px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            color: var(--muted);
            line-height: 1.7
        }

        #rxText {
            background: #0a0f1c;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px;
            height: 180px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            line-height: 1.7
        }

        .rx-item {
            color: #cbd5e1;
            word-break: break-all;
            white-space: pre-wrap;
            margin-bottom: 2px
        }

        .rx-ts {
            color: var(--dim)
        }

        .rx-src {
            display: inline-block;
            min-width: 36px;
            padding: 0 5px;
            margin: 0 6px 0 2px;
            border-radius: 4px;
            font-size: 11px;
            text-align: center
        }

        .rx-src.txt {
            background: #0e749033;
            color: #22d3ee
        }

        .rx-src.bin {
            background: #7f1d1d33;
            color: #f87171
        }

        .rx-send {
            display: flex;
            gap: 8px;
            margin-top: 10px
        }

        .rx-send input {
            flex: 1;
            font-family: monospace
        }

        .rx-send button {
            flex: none
        }

        @media(max-width:900px) {
            main {
                grid-template-columns: 1fr;
                grid-template-areas: "controls" "stats" "speed" "rssi" "wifi" "log" "rx"
            }

            .conn {
                flex-wrap: wrap
            }
        }
    </style>
</head>

<body>
    <header>
        <h1><span>ESP32</span> 网络测速 · WiFi 信号监测</h1>
        <div class="conn">
            <input type="text" id="host" value="192.168.1.188" spellcheck="false" placeholder="IP">
            <span style="color:var(--dim)">:</span>
            <input type="text" id="port" value="8000" spellcheck="false" placeholder="端口">
            <button id="btnConnect" class="btn-primary">连接</button>
            <span id="connState" class="state disconnected">未连接</span>
        </div>
    </header>
    <main>
        <section class="panel controls">
            <h2>测速参数</h2>
            <div class="field"><label>单包大小 (B)</label><input type="number" id="pktSize" value="4096" min="1"></div>
            <div class="field"><label>采样窗口 (ms)</label><input type="number" id="winMs" value="500" min="50"></div>
            <div class="btns">
                <div class="row">
                    <button id="btnEspSend" class="btn-primary">ESP32-发送测速</button>
                    <button id="btnEspRecv" class="btn-primary">ESP32-接收测速</button>
                </div>
                <div class="row">
                    <button id="btnWifi">WiFi 扫描</button>
                    <button id="btnStop" class="btn-danger">停止</button>
                </div>
            </div>
            <div class="mode-hint" id="modeHint">当前: 空闲</div>
            <div class="comms" id="commsInfo">接收: 0 帧 / 0 B · 发送: 0 B</div>
        </section>
        <section class="panel speed">
            <h2>实时速率曲线 (Mbps)</h2>
            <div class="chart-wrap"><canvas id="speedChart"></canvas></div>
            <div class="legend" id="speedLegend"></div>
        </section>
        <section class="panel stats">
            <h2>统计信息</h2>
            <div class="stat-grid">
                <div class="stat">
                    <div class="k">累计数据</div>
                    <div class="v" id="statTotal">0 B</div>
                </div>
                <div class="stat">
                    <div class="k">当前速率</div>
                    <div class="v" id="statCur">0.00 Mbps</div>
                </div>
                <div class="stat">
                    <div class="k">平均速率</div>
                    <div class="v small" id="statAvg">-- Mbps</div>
                </div>
                <div class="stat">
                    <div class="k">已测时长</div>
                    <div class="v small" id="statTime">0.0 s</div>
                </div>
            </div>
        </section>
        <section class="panel rssi">
            <h2>WiFi 信号强度 (dBm)</h2>
            <div class="chart-wrap"><canvas id="rssiChart"></canvas></div>
            <div class="legend" id="rssiLegend"></div>
        </section>
        <section class="panel wifi">
            <h2>WiFi 信号列表 <span id="wifiCount" style="color:var(--dim);font-weight:400"></span></h2>
            <div style="overflow-x:auto">
                <table>
                    <thead>
                        <tr>
                            <th>SSID</th>
                            <th>MAC</th>
                            <th>信道</th>
                            <th>信号</th>
                            <th>加密</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody id="wifiBody"></tbody>
                </table>
            </div>
        </section>
        <section class="panel log-panel">
            <h2>消息日志</h2>
            <div id="log"></div>
        </section>
        <section class="panel rx-panel">
            <h2>接收到的 txt 消息(完整显示) <span id="rxCount" style="color:var(--dim);font-weight:400"></span></h2>
            <div id="rxText"></div>
            <div class="rx-send">
                <input type="text" id="protoInput" spellcheck="false" placeholder="手动输入协议并发送, 如 q4096 / w / e / m1024">
                <button id="btnSendProto" class="btn-primary">发送</button>
            </div>
        </section>
    </main>
    <script>
        "use strict";
        /* ================= 可调参数 ================= */
        const PROTO_SPEED = "q";        // 重复发送测速协议字符(与服务器一致)
        const PROTO_WIFI = "w";        // WiFi 扫描协议字符(小写=正常, 大写如 WERROR=错误)
        const PROTO_IDLE = "e";        // 空闲/停止协议字符
        const AUTO_WIFI_SCAN = false;   // 连接成功后是否自动请求 WiFi 扫描。
        // 服务器 send_lr 是单线程, WiFi scan() 阻塞期间其他协议发送会被拖住, 默认关闭。
        const RECONNECT_DELAY = 1200;   // 断线自动重连间隔 (ms)
        const MAX_POINTS = 300;         // 每条曲线最多保留点数
        const WORST_RSSI = -100;        // 信号丢失时, 曲线用最差信号替代的数值 (dBm)
        const UPLOAD_BUFFER_LIMIT = 1 << 20; // ESP32-接收测速: 浏览器待发送缓冲上限 (字节)
        const SKIP_FIRST_POINTS = 3;  // ESP32-接收测速: 曲线剔除前几个采样点(浏览器缓冲预填导致的前段伪高速率), 统计信息不受影响
        /* ================= DOM ================= */
        const $ = (id) => document.getElementById(id);
        const el = {
            host: $("host"), port: $("port"),
            btnConnect: $("btnConnect"), connState: $("connState"),
            pktSize: $("pktSize"), winMs: $("winMs"),
            btnEspSend: $("btnEspSend"), btnEspRecv: $("btnEspRecv"),
            btnWifi: $("btnWifi"), btnStop: $("btnStop"),
            statTotal: $("statTotal"), statCur: $("statCur"), statAvg: $("statAvg"), statTime: $("statTime"),
            modeHint: $("modeHint"), commsInfo: $("commsInfo"), log: $("log"),
            rxText: $("rxText"), rxCount: $("rxCount"), protoInput: $("protoInput"), btnSendProto: $("btnSendProto"),
            wifiBody: $("wifiBody"), wifiCount: $("wifiCount"),
        };
        /* ================= 工具函数 ================= */
        function esc(s) {
            return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
        }
        function fmtTime(ts) {
            const d = new Date(ts), p = n => String(n).padStart(2, "0");
            return p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
        }
        // 自适应单位, 保留两位小数 (B / KiB / MiB / GiB / TiB ...)
        function formatBytes(bytes) {
            if (!isFinite(bytes) || bytes <= 0) return "0 B";
            const units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB"];
            const i = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
            return (bytes / Math.pow(1024, i)).toFixed(2) + " " + units[i];
        }
        const AUTH_NAMES = { 0: "开放", 1: "WEP", 2: "WPA-PSK", 3: "WPA2-PSK", 4: "WPA/WPA2", 5: "WPA2-企业", 6: "WPA3-PSK", 7: "WPA2/WPA3" };
        function authName(code) {
            return AUTH_NAMES[code] != null ? AUTH_NAMES[code] : (code != null ? "未知(" + code + ")" : "-");
        }
        const PALETTE = ["#38bdf8", "#a78bfa", "#f472b6", "#34d399", "#fbbf24", "#fb7185", "#4ade80", "#f97316", "#22d3ee", "#e879f9"];
        let colorIdx = 0;
        function nextColor() { return PALETTE[colorIdx++ % PALETTE.length]; }
        function log(msg) {
            const div = document.createElement("div");
            div.textContent = "[" + fmtTime(Date.now()) + "] " + msg;
            el.log.appendChild(div);
            while (el.log.children.length > 200) el.log.removeChild(el.log.firstChild);
            el.log.scrollTop = el.log.scrollHeight;
        }
        /* ================= 折线图 ================= */
        class LineChart {
            constructor(canvasId, legendId, opts = {}) {
                this.canvas = document.getElementById(canvasId);
                this.legendEl = document.getElementById(legendId);
                this.ctx = this.canvas.getContext("2d");
                this.series = new Map();
                this.maxPoints = opts.maxPoints || 300;
                this.fixedMin = (opts.fixedMin != null) ? opts.fixedMin : null;
                this.fixedMax = (opts.fixedMax != null) ? opts.fixedMax : null;
                this.yFmt = opts.yFmt || (v => v.toFixed(1));
                this.emptyText = opts.emptyText || "等待数据...";
                this.tick = 5;
                this._raf = false;
                this._w = 0; this._h = 0;
                this._resize();
                window.addEventListener("resize", () => this._resize());
            }
            _resize() {
                const rect = this.canvas.parentElement.getBoundingClientRect();
                const dpr = window.devicePixelRatio || 1;
                const w = Math.max(120, rect.width), h = Math.max(120, rect.height);
                this.canvas.width = Math.round(w * dpr);
                this.canvas.height = Math.round(h * dpr);
                this.canvas.style.width = w + "px";
                this.canvas.style.height = h + "px";
                this._w = w; this._h = h; this._dpr = dpr;
                this._draw();
            }
            addSeries(key, name, color) {
                if (this.series.has(key)) return;
                this.series.set(key, { name, color, pts: [], _hidden: false });
                this._renderLegend();
            }
            addPoint(key, t, v) {
                const s = this.series.get(key);
                if (!s) return;
                s.pts.push({ t, v });
                if (s.pts.length > this.maxPoints) s.pts.shift();
                this._requestDraw();
            }
            clear() {
                for (const s of this.series.values()) s.pts = [];
                this._requestDraw();
            }
            _renderLegend() {
                if (!this.legendEl) return;
                this.legendEl.innerHTML = "";
                for (const [key, s] of this.series) {
                    const chip = document.createElement("button");
                    chip.type = "button";
                    chip.className = "chip";
                    chip.innerHTML = '<i style="background:' + s.color + '"></i><span>' + esc(s.name) + '</span>';
                    chip.addEventListener("click", () => {
                        s._hidden = !s._hidden;
                        chip.classList.toggle("off", s._hidden);
                        this._requestDraw();
                    });
                    this.legendEl.appendChild(chip);
                }
            }
            _requestDraw() {
                if (this._raf) return;
                this._raf = true;
                requestAnimationFrame(() => { this._raf = false; this._draw(); });
            }
            _draw() {
                const ctx = this.ctx, w = this._w, h = this._h;
                if (!w || !h) return;
                ctx.setTransform(this._dpr, 0, 0, this._dpr, 0, 0);
                ctx.fillStyle = "#0d1526";
                ctx.fillRect(0, 0, w, h);
                const padL = 52, padR = 14, padT = 14, padB = 28;
                const pw = w - padL - padR, ph = h - padT - padB;
                let tMin = Infinity, tMax = -Infinity, vMin = Infinity, vMax = -Infinity, any = false;
                for (const s of this.series.values()) {
                    if (s._hidden) continue;
                    for (const p of s.pts) {
                        any = true;
                        if (p.t < tMin) tMin = p.t;
                        if (p.t > tMax) tMax = p.t;
                        if (p.v < vMin) vMin = p.v;
                        if (p.v > vMax) vMax = p.v;
                    }
                }
                if (!any) {
                    ctx.fillStyle = "#475569"; ctx.font = "13px monospace";
                    ctx.textAlign = "center"; ctx.textBaseline = "middle";
                    ctx.fillText(this.emptyText, w / 2, h / 2);
                    return;
                }
                let y0 = (this.fixedMin != null) ? this.fixedMin : vMin;
                let y1 = (this.fixedMax != null) ? this.fixedMax : vMax;
                if (y0 === y1) { y0 -= 1; y1 += 1; }
                const range = y1 - y0;
                if (this.fixedMin == null) y0 -= range * 0.08;
                if (this.fixedMax == null) y1 += range * 0.08;
                if (tMin === tMax) tMax = tMin + 1000;
                for (let i = 0; i <= this.tick; i++) {
                    const v = y1 - (y1 - y0) * i / this.tick;
                    const y = padT + ph * i / this.tick;
                    ctx.strokeStyle = "#1e293b";
                    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
                    ctx.fillStyle = "#64748b"; ctx.font = "11px monospace";
                    ctx.textAlign = "right"; ctx.textBaseline = "middle";
                    ctx.fillText(this.yFmt(v), padL - 6, y);
                }
                ctx.fillStyle = "#64748b"; ctx.font = "11px monospace";
                ctx.textAlign = "center"; ctx.textBaseline = "top";
                ctx.fillText(fmtTime(tMin), padL, h - padB + 6);
                ctx.fillText(fmtTime((tMin + tMax) / 2), padL + pw / 2, h - padB + 6);
                ctx.fillText(fmtTime(tMax), w - padR, h - padB + 6);
                const X = t => padL + (t - tMin) / (tMax - tMin) * pw;
                const Y = v => padT + (1 - (v - y0) / (y1 - y0)) * ph;
                for (const s of this.series.values()) {
                    if (s._hidden || s.pts.length === 0) continue;
                    ctx.strokeStyle = s.color; ctx.lineWidth = 2; ctx.lineJoin = "round";
                    ctx.beginPath();
                    let started = false;
                    for (const p of s.pts) {
                        const x = X(p.t), y = Y(p.v);
                        if (!started) { ctx.moveTo(x, y); started = true; }
                        else ctx.lineTo(x, y);
                    }
                    ctx.stroke();
                }
            }
        }
        /* ================= 图表实例 ================= */
        const speedChart = new LineChart("speedChart", "speedLegend", {
            maxPoints: MAX_POINTS, fixedMin: 0,
            yFmt: v => v.toFixed(1), emptyText: "等待测速数据..."
        });
        speedChart.addSeries("rate", "速率 (Mbps)", "#22d3ee");
        const rssiChart = new LineChart("rssiChart", "rssiLegend", {
            maxPoints: MAX_POINTS, fixedMin: -105, fixedMax: 0,
            yFmt: v => v.toFixed(0), emptyText: "等待 WiFi 扫描数据..."
        });
        /* ================= WebSocket 连接(带自动重连) ================= */
        let ws = null;
        let reconnectTimer = null;
        let manualClose = false;
        function getWsUrl() {
            let host = el.host.value.trim();
            let port = el.port.value.trim() || "8000";
            if (!host && location.hostname && location.protocol !== "file:") host = location.hostname;
            if (!host) host = "192.168.1.188";
            return "ws://" + host + ":" + port + "/";
        }
        function connect() {
            if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
            manualClose = false;
            clearTimeout(reconnectTimer);
            setState("connecting", "连接中...");
            try {
                ws = new WebSocket(getWsUrl());
            } catch (e) {
                log("连接失败: " + e.message);
                setState("reconnecting", "重连中...");
                scheduleReconnect();
                return;
            }
            ws.binaryType = "arraybuffer";
            ws.onopen = () => {
                setState("connected", "已连接");
                log("已连接 " + getWsUrl());
                if (AUTO_WIFI_SCAN) sendText(PROTO_WIFI);
                else log("提示: 点 'WiFi 扫描' 可查看周围信号");
                setBtnState();
            };
            ws.onmessage = e => handlePayload(e.data);
            ws.onerror = () => { }; // 统一由 onclose 处理
            ws.onclose = () => {
                if (mode !== "idle") { sampling.modeEnd = Date.now(); mode = "idle"; uploadBuf = null; }
                setBtnState();
                if (!manualClose) {
                    setState("reconnecting", "已断开, 重连中...");
                    log("连接断开, " + (RECONNECT_DELAY / 1000) + "s 后自动重连");
                    scheduleReconnect();
                } else {
                    setState("disconnected", "未连接");
                }
            };
        }
        function scheduleReconnect() {
            clearTimeout(reconnectTimer);
            reconnectTimer = setTimeout(connect, RECONNECT_DELAY);
        }
        function disconnect() {
            manualClose = true;
            clearTimeout(reconnectTimer);
            if (ws) { try { ws.close(); } catch (e) { } ws = null; }
            setState("disconnected", "未连接");
            setBtnState();
        }
        /* ================= 发送(带发送字节统计) ================= */
        const frameStat = { rxBin: 0, rxBinBytes: 0, rxText: 0, rxTextChars: 0, txBytes: 0 };
        function sendText(str) {  // txt 帧
            if (!ws || ws.readyState !== WebSocket.OPEN) { log("未连接, 无法发送: " + str); return false; }
            ws.send(str);
            frameStat.txBytes += new Blob([str]).size;
            return true;
        }
        function sendBinary(buf) { // bin 帧
            if (!ws || ws.readyState !== WebSocket.OPEN) return false;
            ws.send(buf);
            frameStat.txBytes += buf.byteLength;
            return true;
        }
        /* ================= 测速统计 ================= */
        let mode = "idle";          // idle | espSend | espRecv
        let uploadBuf = null;       // ESP32-接收测速时复用同一块缓冲
        let skipCurvePoints = 0;    // ESP32-接收测速: 剩余需剔除的曲线采样点(仅影响曲线, 不影响统计)
        const sampling = { start: 0, win: 500, thisLen: 0, allLen: 0, curMbps: 0, modeStart: 0, modeEnd: 0 };
        function winMs() { return Math.max(50, parseInt(el.winMs.value, 10) || 500); }
        function pktSize() { return Math.max(1, parseInt(el.pktSize.value, 10) || 1024); }
        function resetSampling() {
            sampling.start = 0;
            sampling.thisLen = 0;
            sampling.allLen = 0;
            sampling.curMbps = 0;
            sampling.modeStart = Date.now();
            sampling.modeEnd = 0;
            skipCurvePoints = 0;
            speedChart.clear();
            updateStats();
        }
        // 已测时长: 未测速为 0; 测速中实时增长; 停止/断线后冻结在结束时刻
        function elapsedSec() {
            if (!sampling.modeStart) return 0;
            const end = sampling.modeEnd || Date.now();
            return (end - sampling.modeStart) / 1000;
        }
        function avgMbps() {
            const sec = elapsedSec();
            // 前 1 秒数据不足, 不计算平均, 避免极小时间除数导致巨大尖峰
            if (sec < 1) return 0;
            return sampling.allLen * 8 / sec / 1000;
        }
        function updateStats() {
            el.statTotal.textContent = formatBytes(sampling.allLen);
            el.statCur.textContent = sampling.curMbps.toFixed(2) + " Mbps";
            const sec = elapsedSec();
            el.statAvg.textContent = sec < 1 ? "-- Mbps" : avgMbps().toFixed(2) + " Mbps";
            el.statTime.textContent = sec.toFixed(1) + " s";
        }
        // bin 测速数据: 只累加长度, 按采样窗口算一次速率
        function addBytes(len) {
            if (!(len > 0)) return;
            sampling.thisLen += len;
            sampling.allLen += len;
            const now = Date.now();
            if (!sampling.start) sampling.start = now;
            const elapsed = now - sampling.start;
            if (elapsed >= sampling.win) {
                sampling.curMbps = sampling.thisLen * 8 / elapsed / 1000; // Mbps
                sampling.start = now;
                sampling.thisLen = 0;
                if (skipCurvePoints > 0) {
                    skipCurvePoints--; // 统计照算, 仅曲线剔除该点(缓冲预填的前段伪高速率)
                } else {
                    speedChart.addPoint("rate", now, sampling.curMbps);
                }
                updateStats();
            }
        }
        function setMode(text) { el.modeHint.textContent = "当前: " + text; }
        /* ================= 测速控制 ================= */
        // ESP32-发送测速: 发 "q"+包大小(txt) → ESP32 持续回发 bin 数据, 浏览器统计接收速率
        function startEspSend() {
            if (!sendText(PROTO_SPEED + pktSize())) return;
            mode = "espSend";
            resetSampling();
            sampling.win = winMs();
            setMode("ESP32-发送测速中 (ESP32→浏览器)");
            setBtnState();
            log("开始 ESP32-发送测速: 发送 '" + PROTO_SPEED + pktSize() + "', 采样窗口 " + sampling.win + " ms");
        }
        // ESP32-接收测速: 先切空闲 + 协商接收缓冲(txt), 再持续发 bin 数据给 ESP32
        function startEspRecv() {
            if (!sendText(PROTO_IDLE)) return;       // "e": 切回空闲, 停止 ESP32 发送
            if (!sendText("m" + pktSize())) return;  // "m" + 大小: 协商 ESP32 接收缓冲
            mode = "espRecv";
            resetSampling();
            sampling.win = winMs();
            skipCurvePoints = SKIP_FIRST_POINTS; // 曲线剔除缓冲预填阶段的前几个采样点
            uploadBuf = new Uint8Array(pktSize());
            uploadBuf.fill(0x58); // 'X'
            setTimeout(uploadLoop, 0);
            setMode("ESP32-接收测速中 (浏览器→ESP32)");
            setBtnState();
            log("开始 ESP32-接收测速: 已发 'e' + 'm" + pktSize() + "', 采样窗口 " + sampling.win + " ms");
        }
        function uploadLoop() {
            if (mode !== "espRecv" || !ws || ws.readyState !== WebSocket.OPEN) return;
            const buf = uploadBuf;
            // 缓冲不超限就持续发送 bin 帧
            while (ws.bufferedAmount < UPLOAD_BUFFER_LIMIT) {
                ws.send(buf);
                frameStat.txBytes += buf.byteLength;
                addBytes(buf.byteLength);
            }
            setTimeout(uploadLoop, 0);
        }
        // 停止测速: 冻结已测时长, 切回空闲协议
        function stopTest() {
            if (mode !== "idle") sampling.modeEnd = Date.now();
            mode = "idle";
            uploadBuf = null;
            sendText(PROTO_IDLE);
            setMode("空闲");
            setBtnState();
            updateStats();
            log("已停止, 回到空闲状态");
        }
        function setBtnState() {
            const on = !!(ws && ws.readyState === WebSocket.OPEN);
            el.btnEspSend.disabled = !on || mode === "espSend";
            el.btnEspRecv.disabled = !on || mode === "espRecv";
            el.btnWifi.disabled = !on;
            el.btnStop.disabled = !on || mode === "idle";
            el.btnEspSend.textContent = mode === "espSend" ? "发送测速中..." : "ESP32-发送测速";
            el.btnEspRecv.textContent = mode === "espRecv" ? "接收测速中..." : "ESP32-接收测速";
        }
        function setState(state, text) {
            el.connState.className = "state " + state;
            el.connState.textContent = text;
            el.connState.style.color = state === "connected" ? "var(--green)"
                : (state === "connecting" || state === "reconnecting") ? "var(--yellow)" : "var(--red)";
        }
        /* ================= WiFi 信号 ================= */
        const wifiMap = new Map(); // key(ssid|mac) -> {name,mac,channel,rssi,authmode,hidden,lost,color}
        let wifiLastScan = 0;
        function handleWifi(payload) {
            let list;
            try { list = JSON.parse(payload); }
            catch (err) {
                log("WiFi 数据解析失败(可能被服务器截断): " + err.message);
                return;
            }
            if (!Array.isArray(list)) { log("WiFi 数据格式异常"); return; }
            const now = Date.now();
            wifiLastScan = now;
            const seen = new Set();
            for (const net of list) {
                const key = (net.name || "空wifi名称") + "|" + (net.mac || "");
                seen.add(key);
                let w = wifiMap.get(key);
                if (!w) {
                    w = {
                        key, name: net.name || "空wifi名称", mac: net.mac || "",
                        channel: net.channel, rssi: net.rssi, authmode: net.authmode,
                        hidden: net.hidden, lost: false, color: nextColor()
                    };
                    wifiMap.set(key, w);
                    rssiChart.addSeries(key, w.name, w.color);
                    log("发现 WiFi: " + w.name + " (" + w.mac + ")");
                } else {
                    w.channel = net.channel; w.rssi = net.rssi; w.authmode = net.authmode; w.hidden = net.hidden;
                    w.lost = false;
                }
                rssiChart.addPoint(key, now, w.rssi);
            }
            // 本次扫描缺失的信号: 标记丢失, 曲线用最差信号替代(保持列表稳定不抖动)
            for (const w of wifiMap.values()) {
                if (!seen.has(w.key)) {
                    if (!w.lost) { w.lost = true; log("信号丢失: " + w.name); }
                    rssiChart.addPoint(w.key, now, WORST_RSSI);
                }
            }
            renderWifiTable();
        }
        function renderWifiTable() {
            const rows = [...wifiMap.values()].sort((a, b) => b.rssi - a.rssi); // 信号强→弱
            el.wifiCount.textContent = "共 " + wifiMap.size + " 个" + (wifiLastScan ? " · 更新于 " + fmtTime(wifiLastScan) : "");
            el.wifiBody.innerHTML = rows.map(w => {
                const rssiCell = w.lost
                    ? '<span class="badge">信号丢失</span>'
                    : '<span class="mono" style="color:' + (w.rssi >= -60 ? "#22c55e" : w.rssi >= -80 ? "#eab308" : "#ef4444") + '">' + w.rssi + ' dBm</span>';
                return '<tr class="' + (w.lost ? "lost" : "") + '">'
                    + '<td><span class="ssid-cell"><span class="dot" style="background:' + w.color + '"></span>' + esc(w.name) + '</span></td>'
                    + '<td class="mono">' + esc(w.mac) + '</td>'
                    + '<td>' + (w.channel != null ? w.channel : "-") + '</td>'
                    + '<td>' + rssiCell + '</td>'
                    + '<td>' + authName(w.authmode) + '</td>'
                    + '<td>' + (w.hidden ? "隐藏" : "可见") + '</td>'
                    + '</tr>';
            }).join("");
        }
        /* ================= 消息分发 =================
         * 协议约定: bin(二进制帧) = 测速数据, 只取长度算速率, 不做任何解析直接丢弃;
         *           txt(文本帧)   = 其他所有消息(协议控制 / WiFi / ERROR), 完整显示到接收区。
         * WiFi 数据: 小写 "w" + JSON(字段: name/mac/channel/rssi/authmode/hidden)。
         *           大写 "WERROR:..." 是服务器错误, 不处理, 自然显示在接收区即可。 */
        function handlePayload(data) {
            // bin: 测速数据
            if (data instanceof ArrayBuffer) {
                frameStat.rxBin++; frameStat.rxBinBytes += data.byteLength;
                addBytes(data.byteLength);
                return;
            }
            // 兜底: Blob → 转 ArrayBuffer
            if (data instanceof Blob) {
                data.arrayBuffer().then(ab => handlePayload(ab));
                return;
            }
            // txt: 其余所有消息, 完整显示
            const text = data;
            frameStat.rxText++; frameStat.rxTextChars += text.length;
            pushRxText(text);
            // WiFi 控制消息(小写 "w" 开头)
            if (text[0] === PROTO_WIFI) {
                handleWifi(text.slice(1));
            }
        }
        /* 接收消息查看器: txt 消息完整显示(最多保留 100 条) */
        let rxShownCount = 0;
        function pushRxText(text) {
            rxShownCount++;
            const div = document.createElement("div");
            div.className = "rx-item";
            div.innerHTML = '<span class="rx-ts">[' + fmtTime(Date.now()) + ']</span>'
                + '<span class="rx-src txt">txt</span>'
                + '<span class="rx-body">' + esc(text) + '</span>';
            el.rxText.appendChild(div);
            while (el.rxText.children.length > 100) el.rxText.removeChild(el.rxText.firstChild);
            el.rxText.scrollTop = el.rxText.scrollHeight;
            el.rxCount.textContent = "已显示 " + rxShownCount + " 条";
        }
        /* 手动发送协议: 以 txt 帧发送输入框内容 */
        function sendManualProto() {
            const v = el.protoInput.value.trim();
            if (!v) return;
            if (!sendText(v)) return;
            log("手动发送: " + v);
            el.protoInput.value = "";
        }
        /* ================= 事件绑定 ================= */
        el.btnConnect.addEventListener("click", () => {
            if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) disconnect();
            else connect();
        });
        el.btnEspSend.addEventListener("click", startEspSend);
        el.btnEspRecv.addEventListener("click", startEspRecv);
        el.btnWifi.addEventListener("click", () => { if (sendText(PROTO_WIFI)) setMode("WiFi 扫描中"); });
        el.btnStop.addEventListener("click", stopTest);
        el.host.addEventListener("keydown", e => { if (e.key === "Enter") connect(); });
        el.port.addEventListener("keydown", e => { if (e.key === "Enter") connect(); });
        el.protoInput.addEventListener("keydown", e => { if (e.key === "Enter") sendManualProto(); });
        el.btnSendProto.addEventListener("click", sendManualProto);
        // 每秒刷新统计与通信帧计数
        setInterval(() => { updateStats(); updateComms(); }, 250);
        function updateComms() {
            const rx = frameStat.rxBin + frameStat.rxText;
            const rxBytes = frameStat.rxBinBytes + frameStat.rxTextChars;
            el.commsInfo.textContent = "接收: " + rx + " 帧 / " + formatBytes(rxBytes)
                + " · 发送: " + formatBytes(frameStat.txBytes);
        }
        // 启动: 自动连接
        setBtnState();
        updateComms();
        connect();
    </script>
</body>

</html>
""".encode()
# with open("1.html", "rb") as f:
#     html = f.read()
html = (
    b"HTTP/1.1 200 OK\r\n"
    b"Content-Type: text/html; charset=utf-8\r\n"
    b"Content-Length: " + str(len(html)).encode() + b"\r\n"
    b"Connection: close\r\n"
    b"\r\n" + html
)


# 协议类
class protocol:
    # mpy阉割了父类获取子类的能力
    # 通过装饰器保存到这里
    协议表 = {}
    默认选中 = False

    # 协议处理需要的通用数据
    def __init__(self, sock, addr, protocols, context):
        self.sock: ws_lsl.WsSocket = sock
        self.addr = addr
        # 自动匹配协议,同时让协议互相访问
        # 循环引用了,注意一下垃圾回收机制是否能正常处理
        self.protocols = protocols
        # 决定send_lr工作模式，以及提供一个锁
        self.context: lib_lsl.YZ = context

    # mpy父类无法获取子类,需要手动注册
    @classmethod
    def add(cls, child):
        cls.协议表[child.this_protocol] = child
        return child

    # 所有子协议的run共有行为
    def run(self, *args, **kwargs):
        for free in self.protocols["垃圾回收"]:
            free()

        return self._run(*args, **kwargs)

    # 执行前判断socket是否存活
    @staticmethod
    def socket_ok(func):

        def wrapper(self, *args, **kwargs):

            if self.sock.is_close:
                raise Exception("套接字以关闭")

            return func(self, *args, **kwargs)

        return wrapper

    # 被装饰的子类成员函数，会在直执行前
    # 触发所有协议的自定义free_lsl函数 释放垃圾
    @staticmethod
    def free_函数执行前触发自定义的垃圾回收(func):

        def wrapper(self, *args, **kwargs):

            for free in self.protocols["垃圾回收"]:
                free()

            return func(self, *args, **kwargs)

        return wrapper

    # 创建一份子对象返回
    @classmethod
    def new_子对象(cls, sock, addr):
        protocols = {}
        context = lib_lsl.YZ(None)
        protocols["垃圾回收"] = []
        默认 = None

        # 创建所有协议对象
        for this_protocol, protocol_cls in cls.协议表.items():
            # 创建单个协议对象
            protocols[this_protocol] = protocol_cls(sock, addr, protocols, context)

            # 判断谁是 send_lr 的默认行为
            if protocol_cls.默认选中:
                if 默认 is not None:
                    raise Exception("存在多个默认协议")
                默认 = protocols[this_protocol]

            # 如果有垃圾回收函数加入
            if hasattr(protocol_cls, "free_lsl"):
                protocols["垃圾回收"].append(protocols[this_protocol].free_lsl)

        # 没有默认send_lr行为，抛出错误
        if 默认 is None:
            raise Exception("没有默认协议")

        # 设置 send_lr 默认行为
        with context:
            context.value = 默认

        return protocols, context


@protocol.add
class 重复发送测速(protocol):
    this_protocol = "q"

    def __init__(self, sock, addr, protocols, context):
        super().__init__(sock, addr, protocols, context)
        self.msg = None

    def _run(self, msg):
        lib_lsl.send("进入ESP32发送测速")
        # 测速时申请好内存，避免重复申请
        ws_msg = self.sock.get_msg(b"x" * (int(msg)))
        with self.context:
            self.msg = ws_msg
            self.context.value = self

    def run_send(self):
        self.sock.sendall(self.msg)

    # 本协议的数据如果存储在了对象中
    # 需要结束连接才会自动释放
    # 可以在本方法，手动改为，切换协议时释放
    def free_lsl(self):
        with self.context:
            self.msg = self.sock.get_msg(b"x")


@protocol.add
class 发送WIFI信号强度(protocol):
    this_protocol = "w"
    默认选中 = True

    # 协议锁
    lock = _thread.allocate_lock()

    def __init__(self, sock, addr, protocols, context):
        super().__init__(sock, addr, protocols, context)

    @protocol.free_函数执行前触发自定义的垃圾回收
    def _run(self, msg):
        lib_lsl.send("进入ESP32发送wifi信号")
        with self.context:
            self.context.value = self

    def run_send(self):

        try:
            lib_lsl.send("扫描WIFI信号。。。")
            # 获取周围wifi数据
            with self.lock:
                raw_networks = wifi.wlan.scan()

            # 解析为json数据
            clean_networks = []
            for net in raw_networks:
                ssid, bssid, channel, rssi, authmode, hidden = net

                try:
                    wifi_name = ssid.decode("utf-8") if ssid else "空wifi名称"
                except UnicodeDecodeError:
                    wifi_name = "非UTF-8 WIFI名称"

                clean_networks.append(
                    {
                        "name": wifi_name,
                        "mac": bssid.hex(),
                        "channel": channel,  # 信道
                        "rssi": rssi,  # 信号强度
                        "authmode": authmode,  # 加密认证模式
                        "hidden": hidden,  # 是否隐藏
                    }
                )

            # 转为字符串
            data = self.this_protocol + json.dumps(clean_networks)
        except Exception as e:
            data = f"{self.this_protocol.upper()}ERROR:{lib_lsl.tl.get_完整错误信息(e)}"

        self.sock.send_ws(data)


@protocol.add
class 空闲状态(protocol):
    this_protocol = "e"

    def __init__(self, sock, addr, protocols, context):
        super().__init__(sock, addr, protocols, context)
        self.num = 0

    @protocol.free_函数执行前触发自定义的垃圾回收
    def _run(self, msg):
        with self.context:
            self.context.value = self

    @protocol.socket_ok
    def run_send(self):
        time.sleep(0.1)
        self.num += 1
        if self.num >= 10000000000:
            self.num = 0

        if self.num % 20:
            return

        with lib_lsl.Thread.thread_num:
            num = lib_lsl.Thread.thread_num.value
        lib_lsl.send(f"空闲状态 --> 当前线程数量: {num}")


@ws_lsl.WsSocket.socket_close
def read_lr(sock: ws_lsl.WsSocket, addr, protocols):
    buf = bytearray(1024)

    while True:
        one_msg = sock.read_ws(buf)

        # 将byte消息接收测速,丢掉此条消息即可,浏览器可以统计速度
        if isinstance(one_msg, (bytearray, memoryview)):
            continue

        # 协商测试接收包大小
        if one_msg[0] == "m":
            buf_len = int(one_msg[1:])
            if buf_len < 1024:
                buf = bytearray(1024)
            else:
                buf = bytearray(buf_len)
            continue

        # 其他消息为协议
        protocols[one_msg[0]].run(one_msg[1:])


@ws_lsl.WsSocket.socket_close
def send_lr(sock: ws_lsl.WsSocket, addr, context):
    while True:
        with context:
            context.run_send()


# 创建WS连接
ws = ws_lsl.Server("0.0.0.0", 8000, 0).run_thr()
conn: ws_lsl.WsSocket = None
while True:
    # http请求 回复网页
    while len(ws.http):
        lib_lsl.send("http连接处理 -> ")
        client, _ = ws.http.pop(0)
        try:
            client.settimeout(0.5)
            client.sendall(html)
            lib_lsl.send("成功!")
        except Exception as e:
            lib_lsl.send(f"失败: \n{e}")

        client.close()

    # ws请求 断开上一个连接,只向最新的连接发送
    while len(ws.ws):
        lib_lsl.send(f"新的ws请求到达{time.time()}")
        if conn is not None:
            conn.close()
        conn, addr = ws.ws.pop(0)
        pro, context = protocol.new_子对象(conn, addr)

        lib_lsl.Thread.create_thread(read_lr, (conn, addr, pro), stack_size=6144)
        lib_lsl.Thread.create_thread(send_lr, (conn, addr, context), stack_size=6144)

    time.sleep(0.1)


"""
    1、存在平均速率显示不正确问题,开始就出现一个非常大的值
    2、重启单片机这种非显式断开情况下,重连过慢,我的ws服务器没有实现ping pong
"""


"""
    给我实现一个配套的html客服端,需要3个功能
    - 单片机发
        . 这部分名字保持单片机发
        . 带宽计算要求合理,接收时判断超过N秒就已实际时间戳来计算,不要用定时器然后固定除N秒
        . 实时带宽用图形显示曲线
        . 需要可以输入每条消息大小与单片机协商

    - 单片机收
        . 这部分名字保持单片机收
        . 带宽计算要求合理
        . 实时带宽用图形显示

    - wifi信号显示
        这是默认开启的,但进入测速后就没价值了,因为单片机不会发送数据了
        显示完整数据到一行
        信号强度需要图形显示曲线
        用wifi名和mac作为ID,如果下次多出信号就实时添加,如果缺少信号就用最差信号替代


    其他
        . 带宽单位用Mbps
        . 总数据量用单位(?)iB,比如MiB
        . 使用简单的浏览器刷新来退出测速,所以刷新时需要强制断开ws连接,让单片机解除死循环
"""
