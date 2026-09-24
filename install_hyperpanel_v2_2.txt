#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
#  HyperPanel — Self-Contained Installer
#  Paste this file into nano on your VPS and run:  sudo bash install.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -e

YEL='\033[0;33m'; GRN='\033[0;32m'; RED='\033[0;31m'; WHT='\033[1;37m'; NC='\033[0m'
info()  { echo -e "  ${YEL}▶${NC}  $*"; }
ok()    { echo -e "  ${GRN}✓${NC}  $*"; }
fail()  { echo -e "  ${RED}✗${NC}  $*"; exit 1; }
title() { echo -e "\n${YEL}━━  $*  ━━${NC}"; }

echo ""
echo -e "${WHT}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${WHT}║                HyperPanel  Installer                     ║${NC}"
echo -e "${WHT}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

[ "$EUID" -ne 0 ] && fail "Run as root:  sudo bash install.sh"

D=/opt/hyperpanel

# ── System packages ──────────────────────────────────────────────────────────
title "System packages"
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git curl wget lsb-release
ok "Packages ready"

# ── LXC/Incus backend ────────────────────────────────────────────────────────
title "LXC / Incus backend"
if command -v incus &>/dev/null; then
  ok "Incus found"; LXC_BACKEND="incus"
  # Ensure Incus is initialized — safe to run even if already set up
  if ! incus list &>/dev/null 2>&1; then
    info "Initializing Incus (first run)..."
    incus admin init --auto 2>/dev/null || true
  fi
elif command -v lxc &>/dev/null; then
  ok "LXC/LXD found"; LXC_BACKEND="lxc"
  # Ensure LXD is initialized — safe to run even if already set up
  if ! lxc list &>/dev/null 2>&1; then
    info "Initializing LXD (first run)..."
    lxd init --auto 2>/dev/null || true
    # Add current user/root to lxd group
    usermod -aG lxd root 2>/dev/null || true
  fi
else
  info "Installing LXD via snap..."
  apt-get install -y -qq snapd
  snap install lxd
  # Wait for snap daemon
  sleep 3
  lxd init --auto
  usermod -aG lxd root 2>/dev/null || true
  LXC_BACKEND="lxc"; ok "LXD installed and initialized"
fi

# ── Create directories ────────────────────────────────────────────────────────
title "Creating panel directory"
mkdir -p "$D/static/css" "$D/static/js" "$D/templates/admin"
ok "Directories created: $D"

# ═════════════════════════════════════════════════════════════════════════════
# FILE: requirements.txt
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/requirements.txt" << 'PYREQ'
flask>=3.0.0
flask-socketio>=5.3.6
flask-login>=0.6.3
werkzeug>=3.0.0
python-dotenv>=1.0.0
requests>=2.31.0
psutil>=5.9.8
paramiko>=3.4.0
eventlet>=0.35.2
PYREQ

# ═════════════════════════════════════════════════════════════════════════════
# FILE: static/css/hyper.css
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/static/css/hyper.css" << 'ENDCSS'
/* HyperPanel — Custom Styles */
:root {
  --accent:        #EAB308;
  --accent-dark:   #CA9B07;
  --accent-light:  #FDE047;
  --bg-900: #0a0a0a;
  --bg-800: #111111;
  --bg-700: #181818;
  --bg-600: #202020;
  --card-bg:     rgba(255,255,255,0.03);
  --card-border: rgba(255,255,255,0.07);
}
* { box-sizing: border-box; }
body { background: var(--bg-900); color: #e2e8f0; font-family: 'Inter', sans-serif; }
.hyper-bg { background: var(--bg-900); min-height: 100vh; }
.hyper-gradient        { background: linear-gradient(135deg, #EAB308, #CA9B07); }
.hyper-gradient-text   { background: linear-gradient(135deg, #EAB308, #FDE047); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.logo-square { width: 14px; height: 14px; background: #EAB308; display: inline-block; flex-shrink: 0; }
.hyper-sidebar { background: var(--bg-900); border-right: 1px solid rgba(255,255,255,0.06); }
.nav-section { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em; color: rgba(255,255,255,0.25); padding: 0 14px; margin-bottom: 2px; text-transform: uppercase; }
.nav-link { display: flex; align-items: center; gap: 10px; padding: 8px 14px; border-radius: 6px; color: rgba(255,255,255,0.45); font-size: 0.82rem; font-weight: 500; transition: all 0.12s ease; text-decoration: none; }
.nav-link:hover { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.85); }
.nav-link.active { background: rgba(234,179,8,0.1); color: #EAB308; }
.hyper-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; transition: all 0.18s ease; }
.hyper-card:hover { border-color: rgba(255,255,255,0.12); }
.stat-card { background: var(--bg-800); border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; padding: 18px 20px; }
.btn-primary { display: inline-flex; align-items: center; gap: 8px; background: #EAB308; color: #000; font-weight: 700; font-size: 0.82rem; letter-spacing: 0.02em; padding: 9px 18px; border-radius: 6px; border: none; cursor: pointer; transition: all 0.12s ease; text-decoration: none; }
.btn-primary:hover { background: #CA9B07; }
.btn-secondary { display: inline-flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.7); font-weight: 500; font-size: 0.82rem; padding: 9px 18px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); cursor: pointer; transition: all 0.12s ease; text-decoration: none; }
.btn-secondary:hover { background: rgba(255,255,255,0.08); color: white; }
.btn-danger { display: inline-flex; align-items: center; gap: 8px; background: rgba(239,68,68,0.1); color: #f87171; font-weight: 500; font-size: 0.82rem; padding: 9px 18px; border-radius: 6px; border: 1px solid rgba(239,68,68,0.2); cursor: pointer; transition: all 0.12s ease; text-decoration: none; }
.btn-danger:hover { background: rgba(239,68,68,0.2); }
.btn-sm { padding: 5px 10px; font-size: 0.75rem; }
.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-radius: 5px; color: rgba(255,255,255,0.5); cursor: pointer; transition: all 0.12s ease; text-decoration: none; font-size: 0.78rem; }
.btn-icon:hover { background: rgba(255,255,255,0.1); color: white; }
.hyper-input { width: 100%; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 10px 14px; color: white; font-size: 0.875rem; outline: none; transition: all 0.12s ease; }
.hyper-input:focus { border-color: rgba(234,179,8,0.5); background: rgba(255,255,255,0.06); box-shadow: 0 0 0 3px rgba(234,179,8,0.08); }
.hyper-input::placeholder { color: rgba(255,255,255,0.2); }
select.hyper-input option { background: #181818; color: white; }
.hyper-label { display: block; font-size: 0.72rem; font-weight: 600; color: rgba(255,255,255,0.45); margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.07em; }
.status-badge { display: inline-flex; align-items: center; gap: 5px; font-size: 0.68rem; font-weight: 700; padding: 3px 8px; border-radius: 4px; letter-spacing: 0.05em; text-transform: uppercase; }
.status-running  { background: rgba(34,197,94,0.12);  color: #4ade80; border: 1px solid rgba(34,197,94,0.2);  }
.status-stopped  { background: rgba(239,68,68,0.12);  color: #f87171; border: 1px solid rgba(239,68,68,0.2);  }
.status-frozen   { background: rgba(234,179,8,0.12);  color: #FDE047; border: 1px solid rgba(234,179,8,0.2);  }
.status-unknown  { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.4); border: 1px solid rgba(255,255,255,0.08); }
.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.dot-running { background: #4ade80; animation: pulse 2s infinite; }
.dot-stopped { background: #f87171; }
.dot-frozen  { background: #FDE047; }
.dot-unknown { background: rgba(255,255,255,0.3); }
@keyframes pulse { 0%, 100% { opacity: 1; box-shadow: 0 0 4px #4ade80; } 50% { opacity: 0.5; box-shadow: none; } }
.progress-bar { height: 4px; background: rgba(255,255,255,0.06); border-radius: 999px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 999px; transition: width 0.5s ease; }
.progress-yellow { background: #EAB308; }
.progress-orange { background: #F97316; }
.progress-red    { background: #EF4444; }
.progress-green  { background: #22c55e; }
.progress-cyan   { background: #06b6d4; }
.hyper-table { width: 100%; border-collapse: collapse; }
.hyper-table th { text-align: left; font-size: 0.68rem; font-weight: 600; color: rgba(255,255,255,0.3); text-transform: uppercase; letter-spacing: 0.08em; padding: 9px 14px; border-bottom: 1px solid rgba(255,255,255,0.05); }
.hyper-table td { padding: 12px 14px; font-size: 0.84rem; border-bottom: 1px solid rgba(255,255,255,0.04); color: rgba(255,255,255,0.75); }
.hyper-table tr:hover td { background: rgba(255,255,255,0.02); }
.hyper-table tr:last-child td { border-bottom: none; }
.instance-row { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.04); transition: background 0.12s; }
.instance-row:hover { background: rgba(255,255,255,0.02); }
.instance-row:last-child { border-bottom: none; }
.hyper-modal-backdrop { position: fixed; inset: 0; z-index: 100; background: rgba(0,0,0,0.8); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; }
.hyper-modal { background: #161616; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 28px; width: 100%; max-width: 440px; box-shadow: 0 40px 80px rgba(0,0,0,0.6); }
.wizard-step { display: flex; flex-direction: column; align-items: center; gap: 4px; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.07em; color: rgba(255,255,255,0.3); }
.wizard-step-num { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.82rem; border: 1px solid rgba(255,255,255,0.15); color: rgba(255,255,255,0.3); }
.wizard-step.active .wizard-step-num  { background: #EAB308; border-color: #EAB308; color: #000; }
.wizard-step.active   { color: #EAB308; }
.wizard-step.done .wizard-step-num    { background: rgba(234,179,8,0.15); border-color: rgba(234,179,8,0.4); color: #EAB308; }
.wizard-step.done     { color: rgba(255,255,255,0.5); }
.wizard-connector { flex: 1; height: 1px; background: rgba(255,255,255,0.1); margin-top: -14px; }
.wizard-connector.done { background: rgba(234,179,8,0.3); }
.vtype-card { border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 20px; cursor: pointer; transition: all 0.15s ease; background: rgba(255,255,255,0.02); }
.vtype-card:hover  { border-color: rgba(234,179,8,0.3); background: rgba(234,179,8,0.03); }
.vtype-card.selected { border-color: #EAB308; background: rgba(234,179,8,0.06); }
.os-card { border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 14px; cursor: pointer; transition: all 0.12s ease; text-align: center; background: rgba(255,255,255,0.02); }
.os-card:hover   { border-color: rgba(234,179,8,0.3); }
.os-card.selected { border-color: #EAB308; background: rgba(234,179,8,0.06); }
.terminal-container { background: #0a0a0f; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; overflow: hidden; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
.page-header { margin-bottom: 28px; }
.page-title  { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; }
.divider { height: 1px; background: rgba(255,255,255,0.06); margin: 20px 0; }
.metric-label { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: rgba(255,255,255,0.35); margin-bottom: 6px; }
.fade-in { animation: fadeIn 0.25s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
.count-card { flex: 1; background: var(--bg-800); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 14px 18px; text-align: center; }
.count-card .count-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.3); margin-bottom: 6px; }
.count-card .count-val { font-size: 1.6rem; font-weight: 700; }
.search-input { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 8px 14px 8px 36px; color: rgba(255,255,255,0.7); font-size: 0.84rem; outline: none; width: 100%; transition: all 0.12s ease; }
.search-input:focus { border-color: rgba(234,179,8,0.3); }
.search-input::placeholder { color: rgba(255,255,255,0.2); }
ENDCSS

# ═════════════════════════════════════════════════════════════════════════════
# FILE: static/js/console.js
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/static/js/console.js" << 'ENDJS'
function initConsole(iid, name) {
  const term = new Terminal({
    cursorBlink: true, fontSize: 14,
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    theme: {
      background: '#0a0a0f', foreground: '#e2e8f0', cursor: window._HP_ACCENT||'#EAB308',
      cursorAccent: '#0a0a0f', black: '#1a1a2e', red: '#f87171',
      green: '#4ade80', yellow: '#fbbf24', blue: '#60a5fa',
      magenta: '#a78bfa', cyan: '#22d3ee', white: '#e2e8f0',
      brightBlack: '#374151', brightRed: '#ef4444', brightGreen: '#22c55e',
      brightYellow: '#f59e0b', brightBlue: '#3b82f6',
      brightMagenta: '#8b5cf6', brightCyan: '#06b6d4', brightWhite: '#f1f5f9',
    },
    allowTransparency: true, scrollback: 5000,
  });
  const fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  const container = document.getElementById('terminal');
  term.open(container);
  fitAddon.fit();
  new ResizeObserver(() => { try { fitAddon.fit(); } catch(e) {} }).observe(container);
  const socket = io('/console', { transports: ['websocket'], reconnectionAttempts: 5, reconnectionDelay: 2000 });
  let connected = false;
  function setStatus(text, color) {
    const dot = document.getElementById('conn-dot');
    const lbl = document.getElementById('conn-status');
    if (dot) dot.style.background = color;
    if (lbl) lbl.textContent = text;
  }
  socket.on('connect', () => {
    setStatus('Connecting to instance…', '#fbbf24');
    term.writeln('\x1b[33m╔══════════════════════════════════╗\x1b[0m');
    term.writeln('\x1b[33m║       HyperPanel  Console         ║\x1b[0m');
    term.writeln('\x1b[33m╚══════════════════════════════════╝\x1b[0m');
    term.writeln(`\x1b[90mConnecting to \x1b[37m${name}\x1b[90m...\x1b[0m`);
    socket.emit('start_ssh', { iid: iid });
  });
  socket.on('connected', (data) => {
    connected = true;
    setStatus('Connected', '#4ade80');
    term.writeln(`\x1b[32m✓ ${data.msg || 'Connected'}\x1b[0m\r\n`);
  });
  socket.on('output', (data) => { term.write(data.data || ''); });
  socket.on('error', (data) => {
    setStatus('Error', '#f87171');
    term.writeln(`\r\n\x1b[31m✗ ${data.msg || 'Connection error'}\x1b[0m`);
    term.writeln('\x1b[90mTip: Make sure the instance is running.\x1b[0m');
  });
  socket.on('disconnected', () => {
    connected = false;
    setStatus('Disconnected', '#6b7280');
    term.writeln('\r\n\x1b[90m[Session ended. Click Reconnect to restart.]\x1b[0m');
  });
  socket.on('disconnect', () => { setStatus('Disconnected', '#6b7280'); });
  term.onData((data) => { if (connected) socket.emit('input', { data }); });
  term.onResize(({ cols, rows }) => { socket.emit('resize', { cols, rows }); });
  window.clearTerminal = () => term.clear();
  window.reconnect = () => {
    connected = false;
    term.writeln('\r\n\x1b[90mReconnecting…\x1b[0m');
    socket.emit('start_ssh', { iid });
  };
  window.addEventListener('resize', () => { try { fitAddon.fit(); } catch(e) {} });
}
ENDJS

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/base.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/base.html" << 'ENDBASE'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ panel_name }} · {% block title %}{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.min.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/css/hyper.css">
  <style>
    :root{--accent:{{ accent_color }};--accent-dark:{{ accent_dark }};--accent-light:{{ accent_light }};}
    .nav-link.active{color:var(--accent);}
    .btn-primary{background:var(--accent) !important;}
    .btn-primary:hover{background:var(--accent-dark) !important;}
    .logo-square{background:var(--accent);}
    .hyper-gradient{background:linear-gradient(135deg,var(--accent),var(--accent-dark));}
    .hyper-gradient-text{background:linear-gradient(135deg,var(--accent),var(--accent-light));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
    .hyper-input:focus{border-color:var(--accent);}
    .wizard-step.active .wizard-step-num{background:var(--accent);border-color:var(--accent);}
    .wizard-step.active{color:var(--accent);}
    .wizard-step.done .wizard-step-num{color:var(--accent);}
    .vtype-card.selected{border-color:var(--accent);}
    .os-card.selected{border-color:var(--accent);}
    .progress-yellow{background:var(--accent);}
  </style>
  <script>window._HP_ACCENT="{{ accent_color }}";</script>
  {% block head %}{% endblock %}
</head>
<body class="hyper-bg text-white min-h-screen" style="font-family:'Inter',sans-serif;">

{% with messages = get_flashed_messages(with_categories=true) %}
{% if messages %}
<div id="flash-container" class="fixed top-4 right-4 z-50 flex flex-col gap-2" style="max-width:360px;">
  {% for cat, msg in messages %}
  <div class="flash-msg flex items-start gap-3 px-4 py-3 rounded-lg border text-sm
    {% if cat=='success' %}bg-emerald-950 border-emerald-800/50 text-emerald-300
    {% elif cat=='error' %}bg-red-950 border-red-800/50 text-red-300
    {% else %}bg-yellow-950 border-yellow-800/50 text-yellow-300{% endif %} shadow-xl">
    <i class="fa-solid {% if cat=='success' %}fa-circle-check text-emerald-400{% elif cat=='error' %}fa-circle-exclamation text-red-400{% else %}fa-circle-info text-yellow-400{% endif %} mt-0.5 flex-shrink-0"></i>
    <span>{{ msg }}</span>
    <button onclick="this.parentElement.remove()" class="ml-auto opacity-50 hover:opacity-100"><i class="fa-solid fa-xmark"></i></button>
  </div>
  {% endfor %}
</div>
<script>setTimeout(()=>{document.querySelectorAll('.flash-msg').forEach(el=>el.remove())},5000)</script>
{% endif %}
{% endwith %}

<div class="flex min-h-screen">
  <aside class="hyper-sidebar w-52 flex-shrink-0 flex flex-col fixed top-0 left-0 h-full z-40 hidden lg:flex">
    <div class="px-4 py-4 border-b border-white/5">
      <a href="/dashboard" class="flex items-center gap-2">
        <span class="logo-square"></span>
        <span class="font-bold text-sm tracking-wider text-white uppercase">{{ panel_name }}</span>
      </a>
    </div>
    <nav class="flex-1 px-3 py-4 overflow-y-auto space-y-0.5">
      <p class="nav-section mb-2">System</p>
      <a href="/dashboard" class="nav-link {% if request.path=='/dashboard' %}active{% endif %}">
        <i class="fa-solid fa-gauge w-4 text-xs"></i> Dashboard
      </a>
      <a href="/instances" class="nav-link {% if request.path.startswith('/instances') and 'create' not in request.path %}active{% endif %}">
        <i class="fa-solid fa-server w-4 text-xs"></i> Instances
      </a>
      {% if current_user.is_admin %}
      <p class="nav-section mt-5 mb-2">Administration</p>
      <a href="/admin" class="nav-link {% if request.path=='/admin' %}active{% endif %}">
        <i class="fa-solid fa-circle-nodes w-4 text-xs"></i> Overview
      </a>
      <a href="/admin/users" class="nav-link {% if request.path=='/admin/users' %}active{% endif %}">
        <i class="fa-solid fa-users w-4 text-xs"></i> Users
      </a>
      <a href="/admin/instances" class="nav-link {% if request.path=='/admin/instances' %}active{% endif %}">
        <i class="fa-solid fa-layer-group w-4 text-xs"></i> All Instances
      </a>
      <a href="/admin/nodes" class="nav-link {% if request.path=='/admin/nodes' %}active{% endif %}">
        <i class="fa-solid fa-network-wired w-4 text-xs"></i> Nodes
      </a>
      <a href="/admin/settings" class="nav-link {% if request.path=='/admin/settings' %}active{% endif %}">
        <i class="fa-solid fa-sliders w-4 text-xs"></i> Settings
      </a>
      {% endif %}
    </nav>
    <div class="px-3 py-3 border-t border-white/5">
      <div class="flex items-center gap-2 px-2 py-2">
        <div class="w-7 h-7 rounded flex items-center justify-center text-xs font-bold text-black flex-shrink-0" style="background:var(--accent);">
          {{ current_user.username[0].upper() }}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-medium text-white truncate">{{ current_user.username }}</p>
        </div>
        <a href="/logout" class="text-white/25 hover:text-red-400 transition-colors text-xs" title="Logout">
          <i class="fa-solid fa-arrow-right-from-bracket"></i>
        </a>
      </div>
      <p class="text-center text-white/10 text-[9px] leading-snug mt-1 pb-1">Made by Indian_Pvper<br>Owned by GunpointNodes</p>
    </div>
  </aside>

  <div class="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3 border-b border-white/5" style="background:rgba(10,10,10,0.98);">
    <a href="/dashboard" class="flex items-center gap-2">
      <span class="logo-square"></span>
      <span class="font-bold text-xs tracking-wider text-white uppercase">{{ panel_name }}</span>
    </a>
    <button id="mobile-menu-btn" class="text-white/50 hover:text-white p-1"><i class="fa-solid fa-bars"></i></button>
  </div>

  <div id="mobile-menu" class="lg:hidden hidden fixed inset-0 z-40">
    <div class="absolute inset-0 bg-black/70" onclick="closeMobileMenu()"></div>
    <aside class="absolute left-0 top-0 h-full w-52 hyper-sidebar flex flex-col">
      <div class="px-4 py-4 border-b border-white/5 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="logo-square"></span>
          <span class="font-bold text-xs tracking-wider uppercase">{{ panel_name }}</span>
        </div>
        <button onclick="closeMobileMenu()" class="text-white/30 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <nav class="flex-1 px-3 py-4 space-y-0.5">
        <p class="nav-section mb-2">System</p>
        <a href="/dashboard" class="nav-link">Dashboard</a>
        <a href="/instances" class="nav-link">Instances</a>
        {% if current_user.is_admin %}
        <p class="nav-section mt-4 mb-2">Administration</p>
        <a href="/admin" class="nav-link">Overview</a>
        <a href="/admin/users" class="nav-link">Users</a>
        <a href="/admin/instances" class="nav-link">All Instances</a>
        <a href="/admin/nodes" class="nav-link">Nodes</a>
        <a href="/admin/settings" class="nav-link">Settings</a>
        {% endif %}
        <div class="mt-4 pt-4 border-t border-white/5">
          <a href="/logout" class="nav-link text-red-400"><i class="fa-solid fa-arrow-right-from-bracket w-4 text-xs"></i> Logout</a>
        </div>
      </nav>
    </aside>
  </div>

  <main class="flex-1 lg:ml-52 flex flex-col min-h-screen">
    <div class="flex-1 px-4 lg:px-7 pt-16 lg:pt-7 pb-10">
      {% block content %}{% endblock %}
    </div>
  </main>
</div>

<script>
function closeMobileMenu() { document.getElementById('mobile-menu').classList.add('hidden'); }
document.getElementById('mobile-menu-btn')?.addEventListener('click', () => {
  document.getElementById('mobile-menu').classList.remove('hidden');
});
</script>
{% block scripts %}{% endblock %}
</body>
</html>
ENDBASE

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/index.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/index.html" << 'ENDINDEX'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{{ panel_name }}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body { background: #080808; color: #d4d4d4; font-family: 'Inter', sans-serif; -webkit-font-smoothing: antialiased; }

    /* NAV */
    nav { position: fixed; top: 0; left: 0; right: 0; z-index: 100; display: flex; align-items: center; justify-content: space-between; padding: 0 40px; height: 60px; background: rgba(8,8,8,0.85); backdrop-filter: blur(20px); border-bottom: 1px solid rgba(255,255,255,0.05); }
    .nav-logo { display: flex; align-items: center; gap: 10px; text-decoration: none; }
    .nav-logo-sq { width: 12px; height: 12px; background: #EAB308; flex-shrink: 0; }
    .nav-logo-text { font-size: 0.78rem; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: #fff; }
    .nav-links { display: flex; align-items: center; gap: 6px; }
    .nav-login { color: rgba(255,255,255,0.45); font-size: 0.84rem; font-weight: 500; padding: 7px 16px; border-radius: 5px; text-decoration: none; transition: color .15s; }
    .nav-login:hover { color: rgba(255,255,255,0.85); }
    .nav-cta { background: #EAB308; color: #000; font-size: 0.82rem; font-weight: 700; padding: 8px 18px; border-radius: 5px; text-decoration: none; transition: background .12s; letter-spacing: 0.01em; }
    .nav-cta:hover { background: #d4a008; }

    /* HERO */
    .hero { padding: 160px 40px 100px; max-width: 920px; margin: 0 auto; }
    .hero-eyebrow { display: inline-flex; align-items: center; gap: 8px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #EAB308; margin-bottom: 28px; }
    .hero-eyebrow::before { content: ''; display: block; width: 20px; height: 1px; background: #EAB308; }
    .hero h1 { font-size: clamp(2.8rem, 7vw, 5.5rem); font-weight: 900; letter-spacing: -0.04em; line-height: 1.0; color: #fff; margin-bottom: 24px; }
    .hero h1 em { font-style: normal; color: #EAB308; }
    .hero-sub { font-size: 1.05rem; color: rgba(255,255,255,0.38); line-height: 1.7; max-width: 520px; margin-bottom: 40px; }
    .hero-actions { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-bottom: 64px; }
    .btn-hero-p { display: inline-flex; align-items: center; gap: 8px; background: #EAB308; color: #000; font-weight: 800; font-size: 0.88rem; letter-spacing: 0.01em; padding: 13px 28px; border-radius: 5px; text-decoration: none; transition: background .12s; }
    .btn-hero-p:hover { background: #d4a008; }
    .btn-hero-s { display: inline-flex; align-items: center; gap: 8px; background: transparent; color: rgba(255,255,255,0.5); font-weight: 500; font-size: 0.88rem; padding: 13px 24px; border-radius: 5px; border: 1px solid rgba(255,255,255,0.1); text-decoration: none; transition: all .12s; }
    .btn-hero-s:hover { border-color: rgba(255,255,255,0.25); color: rgba(255,255,255,0.8); }

    /* TERMINAL */
    .terminal-wrap { border-radius: 10px; overflow: hidden; border: 1px solid rgba(255,255,255,0.07); box-shadow: 0 40px 80px rgba(0,0,0,0.6); max-width: 640px; }
    .tbar { background: #141414; padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; gap: 6px; }
    .tdot { width: 11px; height: 11px; border-radius: 50%; }
    .ttitle { margin-left: 8px; font-size: 0.72rem; color: rgba(255,255,255,0.2); font-family: 'JetBrains Mono', monospace; }
    .tbody { background: #0c0c0c; padding: 22px 24px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; line-height: 1.85; }
    .tp { color: rgba(255,255,255,0.85); }
    .tc { color: #EAB308; }
    .tm { color: rgba(255,255,255,0.25); }
    .tg { color: #4ade80; }
    .ty { color: #fbbf24; }
    .cursor { display: inline-block; width: 7px; height: 13px; background: #EAB308; vertical-align: middle; animation: blink 1.1s step-end infinite; }
    @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

    /* STATS ROW */
    .stats-row { display: flex; gap: 0; border-top: 1px solid rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.05); }
    .stat-item { flex: 1; padding: 28px 32px; border-right: 1px solid rgba(255,255,255,0.05); }
    .stat-item:last-child { border-right: none; }
    .stat-num { font-size: 2rem; font-weight: 800; color: #fff; letter-spacing: -0.03em; margin-bottom: 4px; }
    .stat-num span { color: #EAB308; }
    .stat-label { font-size: 0.78rem; color: rgba(255,255,255,0.3); font-weight: 500; }

    /* FEATURES */
    .features { padding: 100px 40px; max-width: 920px; margin: 0 auto; }
    .section-label { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(255,255,255,0.25); margin-bottom: 48px; display: flex; align-items: center; gap: 12px; }
    .section-label::after { content: ''; flex: 1; height: 1px; background: rgba(255,255,255,0.06); }
    .feat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; overflow: hidden; }
    .feat-card { background: #0d0d0d; padding: 32px 28px; transition: background .15s; }
    .feat-card:hover { background: #111; }
    .feat-icon { font-size: 1rem; color: #EAB308; margin-bottom: 18px; }
    .feat-title { font-size: 0.92rem; font-weight: 700; color: #fff; margin-bottom: 10px; letter-spacing: -0.01em; }
    .feat-desc { font-size: 0.82rem; color: rgba(255,255,255,0.3); line-height: 1.65; }

    /* FOOTER */
    footer { padding: 32px 40px; border-top: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: space-between; }
    .foot-logo { display: flex; align-items: center; gap: 8px; }
    .foot-sq { width: 10px; height: 10px; background: #EAB308; }
    .foot-name { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: rgba(255,255,255,0.3); }
    footer p { font-size: 0.75rem; color: rgba(255,255,255,0.15); }

    @media(max-width: 640px) {
      nav { padding: 0 20px; }
      .hero { padding: 120px 20px 80px; }
      .stats-row { flex-wrap: wrap; }
      .stat-item { min-width: 50%; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.05); }
      .features { padding: 60px 20px; }
      footer { flex-direction: column; gap: 12px; padding: 24px 20px; text-align: center; }
    }
  </style>
</head>
<body>
  <nav>
    <a href="/" class="nav-logo">
      <span class="nav-logo-sq"></span>
      <span class="nav-logo-text">{{ panel_name }}</span>
    </a>
    <div class="nav-links">
      <a href="/login" class="nav-login">Sign in</a>
      <a href="/register" class="nav-cta">Get access</a>
    </div>
  </nav>

  <section class="hero">
    <p class="hero-eyebrow">LXC / Incus Virtualization</p>
    <h1>Your infrastructure,<br><em>fully controlled.</em></h1>
    <p class="hero-sub">Hard CPU limits, dedicated RAM, isolated storage. A management panel built for operators who don't compromise.</p>
    <div class="hero-actions">
      <a href="/register" class="btn-hero-p"><i class="fa-solid fa-bolt" style="font-size:0.75rem;"></i> Start deploying</a>
      <a href="/login" class="btn-hero-s">Sign in to console</a>
    </div>
    <div class="terminal-wrap">
      <div class="tbar">
        <div class="tdot" style="background:#ff5f57;"></div>
        <div class="tdot" style="background:#febc2e;"></div>
        <div class="tdot" style="background:#28c840;"></div>
        <span class="ttitle">root@{{ panel_name | lower }}:~</span>
      </div>
      <div class="tbody">
        <div><span class="tp">$ </span><span class="tc">incus launch ubuntu:22.04 web-01 -c limits.cpu=4 -c limits.memory=8GiB</span></div>
        <div class="tm">Creating web-01</div>
        <div class="tm">Starting web-01</div>
        <div class="tg">✓ Instance web-01 started successfully</div>
        <div class="ty" style="margin-top:2px;">10.84.116.42  &nbsp;web-01  &nbsp;RUNNING  &nbsp;4 CPU  &nbsp;8 GiB</div>
        <div style="margin-top:4px;"><span class="tp">$ </span><span class="cursor"></span></div>
      </div>
    </div>
  </section>

  <div class="stats-row">
    <div class="stat-item">
      <div class="stat-num"><span>∞</span></div>
      <div class="stat-label">Instances per node</div>
    </div>
    <div class="stat-item">
      <div class="stat-num">100<span>%</span></div>
      <div class="stat-label">Dedicated CPU &amp; RAM</div>
    </div>
    <div class="stat-item">
      <div class="stat-num"><span>&lt;</span>50ms</div>
      <div class="stat-label">Web console latency</div>
    </div>
    <div class="stat-item">
      <div class="stat-num">0<span>$</span></div>
      <div class="stat-label">Licence cost</div>
    </div>
  </div>

  <section class="features">
    <p class="section-label">Capabilities</p>
    <div class="feat-grid">
      <div class="feat-card">
        <div class="feat-icon"><i class="fa-solid fa-microchip"></i></div>
        <div class="feat-title">Hard resource limits</div>
        <div class="feat-desc">True CPU pinning and non-overcommitted RAM per container — not soft quotas that neighbours can steal.</div>
      </div>
      <div class="feat-card">
        <div class="feat-icon"><i class="fa-solid fa-terminal"></i></div>
        <div class="feat-title">In-browser console</div>
        <div class="feat-desc">Full xterm.js WebSocket terminal into any instance. No SSH key setup needed — just click.</div>
      </div>
      <div class="feat-card">
        <div class="feat-icon"><i class="fa-solid fa-users"></i></div>
        <div class="feat-title">Multi-user RBAC</div>
        <div class="feat-desc">Admin and user roles with per-user instance quotas, ban controls, and a full audit log.</div>
      </div>
      <div class="feat-card">
        <div class="feat-icon"><i class="fa-solid fa-network-wired"></i></div>
        <div class="feat-title">Multi-node support</div>
        <div class="feat-desc">Attach remote nodes via the node agent. Deploy instances to any node from one dashboard.</div>
      </div>
    </div>
  </section>

  <footer>
    <div class="foot-logo">
      <span class="foot-sq"></span>
      <span class="foot-name">{{ panel_name }}</span>
    </div>
    <p>Self-hosted infrastructure panel</p>
  </footer>
</body>
</html>
ENDINDEX

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/login.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/login.html" << 'ENDLOGIN'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Sign in — {{ panel_name }}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #080808;
      min-height: 100vh;
      display: flex;
      font-family: 'Inter', sans-serif;
      -webkit-font-smoothing: antialiased;
      color: #d4d4d4;
    }

    /* LEFT PANEL */
    .left-panel {
      width: 380px;
      flex-shrink: 0;
      background: #0d0d0d;
      border-right: 1px solid rgba(255,255,255,0.05);
      display: flex;
      flex-direction: column;
      padding: 40px;
    }
    .lp-logo { display: flex; align-items: center; gap: 10px; margin-bottom: auto; }
    .lp-sq { width: 11px; height: 11px; background: #EAB308; flex-shrink: 0; }
    .lp-name { font-size: 0.75rem; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: rgba(255,255,255,0.6); }

    .lp-content { flex: 1; display: flex; flex-direction: column; justify-content: center; }
    .lp-heading { font-size: 1.75rem; font-weight: 800; color: #fff; letter-spacing: -0.03em; line-height: 1.15; margin-bottom: 10px; }
    .lp-heading em { font-style: normal; color: #EAB308; }
    .lp-sub { font-size: 0.82rem; color: rgba(255,255,255,0.3); line-height: 1.6; margin-bottom: 40px; }

    .lp-feature { display: flex; align-items: center; gap: 12px; padding: 11px 0; border-top: 1px solid rgba(255,255,255,0.04); }
    .lp-feature:last-child { border-bottom: 1px solid rgba(255,255,255,0.04); }
    .lp-feat-icon { width: 28px; height: 28px; border-radius: 5px; background: rgba(234,179,8,0.08); border: 1px solid rgba(234,179,8,0.15); display: flex; align-items: center; justify-content: center; color: #EAB308; font-size: 0.7rem; flex-shrink: 0; }
    .lp-feat-text { font-size: 0.8rem; color: rgba(255,255,255,0.4); }

    .lp-footer { font-size: 0.7rem; color: rgba(255,255,255,0.15); margin-top: 40px; }

    /* RIGHT / FORM */
    .right-panel {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 40px 24px;
    }
    .form-wrap { width: 100%; max-width: 340px; }

    .form-eyebrow { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(255,255,255,0.2); margin-bottom: 28px; }
    .form-title { font-size: 1.35rem; font-weight: 800; color: #fff; letter-spacing: -0.02em; margin-bottom: 6px; }
    .form-subtitle { font-size: 0.82rem; color: rgba(255,255,255,0.3); margin-bottom: 36px; }

    .field { margin-bottom: 16px; }
    .field-label { display: block; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.35); margin-bottom: 7px; }
    .field-input {
      width: 100%;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.09);
      border-radius: 6px;
      padding: 11px 14px;
      color: #fff;
      font-size: 0.875rem;
      outline: none;
      transition: border-color .15s, background .15s;
      font-family: 'Inter', sans-serif;
      -webkit-font-smoothing: antialiased;
    }
    .field-input:focus { border-color: rgba(234,179,8,0.45); background: rgba(255,255,255,0.04); box-shadow: 0 0 0 3px rgba(234,179,8,0.06); }
    .field-input::placeholder { color: rgba(255,255,255,0.15); }

    .error-box {
      display: flex; align-items: center; gap: 10px;
      background: rgba(239,68,68,0.07);
      border: 1px solid rgba(239,68,68,0.18);
      border-radius: 6px;
      padding: 11px 14px;
      margin-bottom: 20px;
      font-size: 0.82rem;
      color: #fca5a5;
    }
    .error-box i { flex-shrink: 0; font-size: 0.8rem; }

    .btn-submit {
      width: 100%;
      background: #EAB308;
      color: #000;
      font-weight: 800;
      font-size: 0.82rem;
      letter-spacing: 0.05em;
      padding: 13px;
      border-radius: 6px;
      border: none;
      cursor: pointer;
      transition: background .12s;
      margin-top: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .btn-submit:hover { background: #d4a008; }

    .form-footer { text-align: center; margin-top: 24px; font-size: 0.8rem; color: rgba(255,255,255,0.25); }
    .form-footer a { color: #EAB308; text-decoration: none; }
    .form-footer a:hover { text-decoration: underline; }

    @media (max-width: 720px) {
      .left-panel { display: none; }
      body { align-items: center; justify-content: center; }
    }
  </style>
</head>
<body>
  <div class="left-panel">
    <div class="lp-logo">
      <span class="lp-sq"></span>
      <span class="lp-name">{{ panel_name }}</span>
    </div>

    <div class="lp-content">
      <h2 class="lp-heading">Infrastructure<br>you <em>control.</em></h2>
      <p class="lp-sub">Deploy and manage LXC containers and VMs from a single dark, fast panel.</p>

      <div class="lp-feature">
        <div class="lp-feat-icon"><i class="fa-solid fa-microchip"></i></div>
        <span class="lp-feat-text">Hard CPU &amp; RAM limits — no overcommit</span>
      </div>
      <div class="lp-feature">
        <div class="lp-feat-icon"><i class="fa-solid fa-terminal"></i></div>
        <span class="lp-feat-text">Live WebSocket console in browser</span>
      </div>
      <div class="lp-feature">
        <div class="lp-feat-icon"><i class="fa-solid fa-network-wired"></i></div>
        <span class="lp-feat-text">Multi-node, multi-user with RBAC</span>
      </div>
    </div>

    <p class="lp-footer">Self-hosted. No licence fees.</p>
  </div>

  <div class="right-panel">
    <div class="form-wrap">
      <p class="form-eyebrow">{{ panel_name }}</p>
      <h1 class="form-title">Welcome back</h1>
      <p class="form-subtitle">Sign in to your account to continue.</p>

      {% if error %}
      <div class="error-box">
        <i class="fa-solid fa-circle-exclamation"></i>
        <span>{{ error }}</span>
      </div>
      {% endif %}

      <form method="POST" action="/login">
        <div class="field">
          <label class="field-label" for="username">Username</label>
          <input id="username" type="text" name="username" class="field-input" placeholder="admin" autocomplete="username" required autofocus>
        </div>
        <div class="field">
          <label class="field-label" for="password">Password</label>
          <input id="password" type="password" name="password" class="field-input" placeholder="••••••••" autocomplete="current-password" required>
        </div>
        <button type="submit" class="btn-submit">
          <i class="fa-solid fa-arrow-right-to-bracket" style="font-size:0.8rem;"></i>
          Sign in
        </button>
      </form>

      <p class="form-footer">No account? <a href="/register">Request access</a></p>
    </div>
  </div>
</body>
</html>
ENDLOGIN

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/register.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/register.html" << 'ENDREG'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Register — {{ panel_name }}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/css/hyper.css">
  <style>
    body{background:#0a0a0a;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;}
    .wrap{width:100%;max-width:380px;}
    .field-label{font-size:0.7rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:rgba(255,255,255,0.4);margin-bottom:6px;display:block;}
    .field-input{width:100%;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.12);border-radius:5px;padding:10px 14px;color:white;font-size:0.875rem;outline:none;transition:border-color .12s;font-family:'Inter',sans-serif;}
    .field-input:focus{border-color:#EAB308;} .field-input::placeholder{color:rgba(255,255,255,0.2);}
    .btn-auth{width:100%;background:#EAB308;color:#000;font-weight:800;font-size:0.8rem;letter-spacing:0.12em;text-transform:uppercase;padding:12px;border-radius:5px;border:none;cursor:pointer;transition:background .12s;}
    .btn-auth:hover{background:#CA9B07;}
  </style>
</head>
<body>
  <div class="wrap fade-in">
    <div class="text-center mb-10">
      <div class="flex items-center justify-center gap-2 mb-6">
        <span style="width:14px;height:14px;background:#EAB308;display:inline-block;"></span>
        <span class="font-bold text-sm tracking-widest text-white uppercase">{{ panel_name }}</span>
      </div>
      <h1 class="text-2xl font-bold text-white mb-2">Request Access</h1>
      <p class="text-white/35 text-sm">Create your panel account.</p>
    </div>
    {% if registration == 'disabled' %}
    <div class="text-center p-6 border border-white/10 rounded-lg">
      <p class="text-white/50 text-sm">Registration is currently disabled. Contact an administrator.</p>
      <a href="/login" style="color:#EAB308;" class="text-sm mt-3 inline-block">← Back to Login</a>
    </div>
    {% else %}
    {% if error %}
    <div class="flex items-center gap-3 bg-red-950 border border-red-800/40 text-red-300 text-sm px-4 py-3 rounded-md mb-5">
      <i class="fa-solid fa-circle-exclamation flex-shrink-0"></i>{{ error }}
    </div>
    {% endif %}
    <form method="POST" action="/register">
      <div class="space-y-4">
        <div><label class="field-label">Username</label><input type="text" name="username" class="field-input" placeholder="yourname" required minlength="3" autofocus></div>
        <div><label class="field-label">Email</label><input type="email" name="email" class="field-input" placeholder="you@example.com" required></div>
        <div><label class="field-label">Password</label><input type="password" name="password" class="field-input" placeholder="Min 8 characters" required minlength="8"></div>
        <div><label class="field-label">Confirm Password</label><input type="password" name="confirm" class="field-input" placeholder="Repeat password" required></div>
      </div>
      <button type="submit" class="btn-auth mt-6">Create Account</button>
    </form>
    <p class="text-center text-sm text-white/30 mt-6">Already have an account? <a href="/login" style="color:#EAB308;">Sign in</a></p>
    {% endif %}
  </div>
</body>
</html>
ENDREG

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/error.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/error.html" << 'ENDERR'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Error {{ code }} — {{ panel_name }}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/css/hyper.css">
  <style>body{background:#0a0a0a;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;}</style>
</head>
<body>
  <div class="text-center">
    <p class="text-6xl font-black text-white/10 mb-4">{{ code }}</p>
    <h1 class="text-xl font-bold text-white mb-2">{{ error }}</h1>
    <a href="/dashboard" style="color:#EAB308;" class="text-sm transition-colors">← Back to Dashboard</a>
  </div>
</body>
</html>
ENDERR

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/dashboard.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/dashboard.html" << 'ENDDASH'
{% extends "base.html" %}
{% block title %}Instances{% endblock %}
{% block content %}
<div class="max-w-5xl mx-auto fade-in">
  <div class="page-header flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
    <div>
      <h1 class="page-title">Instances</h1>
      <p class="text-white/35 mt-1 text-sm">Manage your containers and virtual machines</p>
    </div>
    {% if current_user.is_admin %}
    <a href="/instances/create" class="btn-primary" style="flex-shrink:0;">
      <i class="fa-solid fa-plus text-xs"></i> Deploy Instance
    </a>
    {% endif %}
  </div>
  <div class="relative mb-5">
    <i class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-white/25 text-xs"></i>
    <input type="text" id="search-box" class="search-input" placeholder="Search instances...">
  </div>
  {% if instances %}
  <div class="hyper-card overflow-hidden" id="instance-list">
    {% for inst in instances %}
    <div class="instance-row" data-name="{{ inst.name|lower }}">
      <span class="status-badge status-{{ inst.status }} flex-shrink-0">
        <span class="status-dot dot-{{ inst.status }}"></span>{{ inst.status|upper }}
      </span>
      <div class="flex-1 min-w-0">
        <a href="/instances/{{ inst.id }}" class="text-sm font-semibold text-white hover:text-yellow-300 transition-colors truncate block">{{ inst.name }}</a>
        <p class="text-xs text-white/30 mt-0.5">{{ inst.os_image }} · {{ inst.type or 'container' }}{% if current_user.is_admin and inst.get('username') %} · <span class="text-white/40">{{ inst.username }}</span>{% endif %}</p>
      </div>
      <div class="hidden sm:flex items-center gap-5 text-xs text-white/40 flex-shrink-0">
        <div><span class="text-xs uppercase tracking-wide text-white/20 mr-1">CPU</span><span class="text-white/70 font-medium">{{ inst.cpu }}</span></div>
        <div><span class="text-xs uppercase tracking-wide text-white/20 mr-1">RAM</span><span class="text-white/70 font-medium">{{ inst.ram }}M</span></div>
        <div><span class="text-xs uppercase tracking-wide text-white/20 mr-1">DISK</span><span class="text-white/70 font-medium">{{ inst.disk }}G</span></div>
        <div><span class="text-white/40 font-mono text-xs">{{ inst.ip_address or 'No IP' }}</span></div>
      </div>
      <div class="flex items-center gap-1 flex-shrink-0">
        {% if inst.status != 'running' %}
        <form method="POST" action="/instances/{{ inst.id }}/start" style="display:inline;">
          <button type="submit" class="btn-icon" title="Start"><i class="fa-solid fa-play text-green-400"></i></button>
        </form>
        {% else %}
        <form method="POST" action="/instances/{{ inst.id }}/stop" style="display:inline;">
          <button type="submit" class="btn-icon" title="Stop"><i class="fa-solid fa-stop text-red-400"></i></button>
        </form>
        {% endif %}
        <form method="POST" action="/instances/{{ inst.id }}/restart" style="display:inline;">
          <button type="submit" class="btn-icon" title="Restart"><i class="fa-solid fa-rotate-right text-yellow-400"></i></button>
        </form>
        <a href="/instances/{{ inst.id }}/console" class="btn-icon" title="Console"><i class="fa-solid fa-terminal text-yellow-300"></i></a>
        <a href="/instances/{{ inst.id }}" class="btn-icon" title="Details"><i class="fa-solid fa-arrow-right text-white/40"></i></a>
      </div>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <div class="hyper-card p-16 text-center">
    <i class="fa-solid fa-server text-white/10 text-4xl mb-5 block"></i>
    <h3 class="text-base font-semibold text-white/70">No instances yet</h3>
    {% if current_user.is_admin %}
    <p class="text-white/30 text-sm mt-2 mb-6">Deploy your first container or VM to get started.</p>
    <a href="/instances/create" class="btn-primary"><i class="fa-solid fa-plus text-xs"></i> Deploy Instance</a>
    {% else %}
    <p class="text-white/30 text-sm mt-2">No instances have been assigned to your account yet. Contact an administrator.</p>
    {% endif %}
  </div>
  {% endif %}
</div>
{% endblock %}
{% block scripts %}
<script>
document.getElementById('search-box')?.addEventListener('input', function() {
  const q = this.value.toLowerCase().trim();
  document.querySelectorAll('.instance-row').forEach(row => {
    row.style.display = (row.dataset.name||'').includes(q) ? '' : 'none';
  });
});
</script>
{% endblock %}
ENDDASH

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/profile.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/profile.html" << 'ENDPROFILE'
{% extends "base.html" %}
{% block title %}Profile{% endblock %}
{% block content %}
<div class="max-w-xl mx-auto fade-in">
  <div class="page-header"><h1 class="page-title">Profile</h1><p class="text-white/35 mt-1 text-sm">Manage your account</p></div>
  <div class="hyper-card p-6 mb-5">
    <div class="flex items-center gap-4 mb-5">
      <div class="w-12 h-12 rounded-lg flex items-center justify-center text-xl font-bold text-black" style="background:#EAB308;">{{ current_user.username[0].upper() }}</div>
      <div><p class="font-semibold text-white">{{ current_user.username }}</p><p class="text-sm text-white/35">{{ 'Administrator' if current_user.is_admin else 'User' }}</p></div>
    </div>
    <div class="space-y-3 text-sm border-t border-white/5 pt-4">
      <div class="flex justify-between"><span class="text-white/35">Email</span><span class="text-white">{{ current_user.email or '—' }}</span></div>
      <div class="flex justify-between"><span class="text-white/35">Instance Quota</span><span class="text-white">{{ instances|length }} / {{ current_user.max_instances }}</span></div>
      <div class="flex justify-between"><span class="text-white/35">Role</span><span class="text-yellow-400">{{ current_user.role }}</span></div>
    </div>
  </div>
  <div class="hyper-card p-6">
    <h2 class="font-semibold text-white mb-4 text-sm">Change Password</h2>
    <form method="POST" action="/profile">
      <div class="space-y-4">
        <div><label class="hyper-label">Current Password</label><input type="password" name="current_password" class="hyper-input" required></div>
        <div><label class="hyper-label">New Password</label><input type="password" name="new_password" class="hyper-input" required minlength="8"></div>
        <div><label class="hyper-label">Confirm New Password</label><input type="password" name="confirm_password" class="hyper-input" required></div>
      </div>
      <button type="submit" class="btn-primary mt-5"><i class="fa-solid fa-key text-xs"></i> Update Password</button>
    </form>
  </div>
</div>
{% endblock %}
ENDPROFILE

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/console.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/console.html" << 'ENDCON'
{% extends "base.html" %}
{% block title %}Console — {{ inst.name }}{% endblock %}
{% block head %}
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css">
<script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
<style>
  .xterm-viewport::-webkit-scrollbar{width:4px;}
  .xterm-viewport::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.12);border-radius:2px;}
  #terminal-wrapper{height:calc(100vh - 220px);min-height:400px;}
</style>
{% endblock %}
{% block content %}
<div class="max-w-6xl mx-auto fade-in">
  <div class="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
    <div>
      <a href="/instances/{{ inst.id }}" class="text-white/25 hover:text-white text-xs flex items-center gap-2 mb-3 w-fit uppercase tracking-wider">
        <i class="fa-solid fa-arrow-left text-xs"></i> Back to Instance
      </a>
      <h1 class="page-title text-xl flex items-center gap-3">
        <i class="fa-solid fa-terminal text-yellow-400 text-base"></i>{{ inst.name }}
      </h1>
    </div>
    <div class="flex items-center gap-3">
      <span class="status-badge status-{{ inst.status }}"><span class="status-dot dot-{{ inst.status }}"></span>{{ inst.status|upper }}</span>
      <div class="flex items-center gap-2 text-xs text-white/25">
        <span class="w-2 h-2 rounded-full bg-gray-700" id="conn-dot"></span>
        <span id="conn-status">Connecting…</span>
      </div>
    </div>
  </div>
  <div class="terminal-container" id="terminal-wrapper">
    <div class="flex items-center gap-3 px-4 py-3 border-b border-white/5">
      <div class="flex gap-1.5">
        <div class="w-3 h-3 rounded-full" style="background:rgba(255,95,87,0.7);"></div>
        <div class="w-3 h-3 rounded-full" style="background:rgba(254,188,46,0.7);"></div>
        <div class="w-3 h-3 rounded-full" style="background:rgba(40,200,64,0.7);"></div>
      </div>
      <span class="text-xs text-white/25 font-mono">root@{{ inst.name }}</span>
      <div class="ml-auto flex gap-2">
        <button onclick="clearTerminal()" class="text-xs text-white/25 hover:text-white/60 transition-colors px-2 py-1 rounded">Clear</button>
        <button onclick="reconnect()" class="text-xs text-white/25 hover:text-white/60 transition-colors px-2 py-1 rounded">Reconnect</button>
      </div>
    </div>
    <div id="terminal" style="padding:8px;height:calc(100% - 48px);"></div>
  </div>
  <div class="mt-3 flex flex-wrap gap-4 text-xs text-white/20">
    <span><i class="fa-solid fa-circle-info mr-1"></i> Ctrl+C to interrupt · Ctrl+L to clear</span>
    <span class="ml-auto">{{ inst.ip_address or 'No IP assigned' }}</span>
  </div>
</div>
{% endblock %}
{% block scripts %}
<script src="/static/js/console.js"></script>
<script>initConsole('{{ inst.id }}', '{{ inst.name }}');</script>
{% endblock %}
ENDCON

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/create_instance.html  (wizard)
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/create_instance.html" << 'ENDCREATE'
{% extends "base.html" %}
{% block title %}Deploy Instance{% endblock %}
{% block content %}
<div class="max-w-2xl mx-auto fade-in">
  <div class="page-header">
    <a href="/instances" class="text-white/30 hover:text-white text-xs flex items-center gap-2 mb-4 w-fit uppercase tracking-wider"><i class="fa-solid fa-arrow-left text-xs"></i> Back</a>
    <h1 class="page-title">Deploy Instance</h1>
    <p class="text-white/35 mt-1 text-sm">Configure your new consequential infrastructure</p>
  </div>
  {% if error %}
  <div class="flex items-center gap-3 bg-red-950 border border-red-800/40 text-red-300 text-sm px-4 py-3 rounded-md mb-6">
    <i class="fa-solid fa-circle-exclamation flex-shrink-0"></i> {{ error }}
  </div>
  {% endif %}
  <div class="flex items-center mb-8">
    <div class="wizard-step" id="step-1-indicator"><div class="wizard-step-num">1</div><div>TYPE</div></div>
    <div class="wizard-connector" id="conn-1"></div>
    <div class="wizard-step" id="step-2-indicator"><div class="wizard-step-num">2</div><div>IMAGE</div></div>
    <div class="wizard-connector" id="conn-2"></div>
    <div class="wizard-step" id="step-3-indicator"><div class="wizard-step-num">3</div><div>SPECS</div></div>
    <div class="wizard-connector" id="conn-3"></div>
    <div class="wizard-step" id="step-4-indicator"><div class="wizard-step-num">4</div><div>CONFIRM</div></div>
  </div>
  <form method="POST" action="/instances/create" id="deploy-form">
    <div id="step-1" class="wizard-pane">
      <div class="hyper-card p-6 mb-4">
        <h2 class="font-semibold text-white mb-5 text-base">Select Virtualization Type</h2>
        <div class="grid grid-cols-2 gap-4">
          <label class="vtype-card selected" id="lxc-card" onclick="selectType('lxc')">
            <input type="radio" name="vtype" value="lxc" class="hidden" checked>
            <div class="text-yellow-400 text-xl mb-3"><i class="fa-solid fa-box"></i></div>
            <div class="font-semibold text-white text-sm mb-1">System Container<br>(LXC)</div>
            <p class="text-white/30 text-xs leading-relaxed mt-2">High performance, lightweight isolation sharing the host kernel.</p>
          </label>
          <label class="vtype-card" id="kvm-card" onclick="selectType('kvm')">
            <input type="radio" name="vtype" value="kvm" class="hidden">
            <div class="text-white/40 text-xl mb-3"><i class="fa-solid fa-server"></i></div>
            <div class="font-semibold text-white text-sm mb-1">Virtual Machine<br>(KVM)</div>
            <p class="text-white/30 text-xs leading-relaxed mt-2">Full hardware virtualization with dedicated kernel.</p>
          </label>
        </div>
      </div>
    </div>
    <div id="step-2" class="wizard-pane hidden">
      <div class="hyper-card p-6 mb-4">
        <h2 class="font-semibold text-white mb-5 text-base">Select Operating System</h2>
        {% set os_icons = {'ubuntu':('fa-ubuntu','#e95420','Ubuntu'),'debian':('fa-debian','#d70751','Debian'),'alpine':('fa-mountain','#0d597f','Alpine'),'centos':('fa-centos','#932279','CentOS'),'fedora':('fa-fedora','#51a2da','Fedora'),'almalinux':('fa-linux','#0f4266','AlmaLinux'),'rocky':('fa-linux','#10B981','Rocky')} %}
        <div class="grid grid-cols-3 gap-3" id="os-grid">
          {% for img in images %}
          {% set parts = img.split(':') %}
          {% set distro = parts[0] %}
          {% set ver = parts[1] if parts|length > 1 else '' %}
          {% set ico = os_icons.get(distro, ('fa-linux','#EAB308',distro|capitalize)) %}
          <label class="os-card {% if loop.first %}selected{% endif %}" onclick="selectOs(this)">
            <input type="radio" name="os_image" value="{{ img }}" class="hidden os-radio" {% if loop.first %}checked{% endif %}>
            <i class="fa-brands {{ ico[0] }} text-2xl mb-2 block" style="color:{{ ico[1] }};"></i>
            <div class="text-sm font-semibold text-white">{{ ico[2] }}</div>
            {% if ver %}<div class="text-xs text-white/30 mt-0.5">{{ ver }}</div>{% endif %}
          </label>
          {% endfor %}
        </div>
        <div class="mt-4 pt-4 border-t border-white/5">
          <label class="hyper-label">Or enter custom image</label>
          <input type="text" name="custom_image" class="hyper-input" placeholder="e.g. ubuntu:24.04">
          <p class="text-xs text-white/20 mt-1">Override the selection above with any valid Incus/LXC image name</p>
        </div>
      </div>
    </div>
    <div id="step-3" class="wizard-pane hidden">
      <div class="hyper-card p-6 mb-4">
        <h2 class="font-semibold text-white mb-1 text-base">Configure Resources</h2>
        <p class="text-xs text-white/30 mb-5">Hard limits — not shared, not overcommitted.</p>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div><label class="hyper-label">CPU Cores</label><div class="relative"><input type="number" name="cpu" id="cpu-input" class="hyper-input pr-16" value="1" min="1" max="64" required><span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-white/25">vCores</span></div></div>
          <div><label class="hyper-label">RAM</label><div class="flex gap-2"><input type="number" name="ram" id="ram-input" class="hyper-input flex-1" value="1024" min="128" max="131072" required><select id="ram-unit" class="hyper-input" style="width:64px;flex-shrink:0;" onchange="convertRam()"><option value="mb" selected>MB</option><option value="gb">GB</option></select></div><p class="text-xs text-white/20 mt-1" id="ram-hint">= 1 GB</p></div>
          <div><label class="hyper-label">Disk</label><div class="relative"><input type="number" name="disk" id="disk-input" class="hyper-input pr-10" value="20" min="5" max="2000" required><span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-white/25">GB</span></div></div>
        </div>
      </div>
      <div class="hyper-card p-6 mb-4">
        <h2 class="font-semibold text-white mb-4 text-base">Instance Details</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div><label class="hyper-label">Instance Name</label><input type="text" name="name" class="hyper-input" placeholder="e.g. web-01" pattern="[a-zA-Z0-9\-]+"><p class="text-xs text-white/20 mt-1">Leave blank for auto-name</p></div>
          <div><label class="hyper-label">Owner</label><select name="user_id" class="hyper-input">{% for u in users %}<option value="{{ u.id }}" {% if u.id == current_user.id %}selected{% endif %}>{{ u.username }}{% if u.id == current_user.id %} (you){% endif %}</option>{% endfor %}</select></div>
          <div><label class="hyper-label">Expiry Date <span class="text-white/25 font-normal">(optional)</span></label><input type="datetime-local" name="expires_at" class="hyper-input"><p class="text-xs text-white/20 mt-1">Instance will auto-stop at this date/time (UTC). Leave blank for no expiry.</p></div>
        </div>
      </div>
      {% if current_user.is_admin and nodes %}
      <div class="hyper-card p-6 mb-4">
        <h2 class="font-semibold text-white mb-3 text-base">Deployment Node</h2>
        <select name="node_id" class="hyper-input"><option value="0">Auto (best available)</option>{% for node in nodes %}<option value="{{ node.id }}">{{ node.name }} — {{ node.location }}{% if node.is_main %} (Main){% endif %}</option>{% endfor %}</select>
      </div>
      {% endif %}
    </div>
    <div id="step-4" class="wizard-pane hidden">
      <div class="hyper-card p-6 mb-4">
        <h2 class="font-semibold text-white mb-5 text-base">Review & Deploy</h2>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between py-2 border-b border-white/5"><span class="text-white/40">Type</span><span class="text-white font-medium capitalize" id="confirm-type">—</span></div>
          <div class="flex justify-between py-2 border-b border-white/5"><span class="text-white/40">OS Image</span><span class="text-white font-medium" id="confirm-image">—</span></div>
          <div class="flex justify-between py-2 border-b border-white/5"><span class="text-white/40">CPU</span><span class="text-white font-medium" id="confirm-cpu">—</span></div>
          <div class="flex justify-between py-2 border-b border-white/5"><span class="text-white/40">RAM</span><span class="text-white font-medium" id="confirm-ram">—</span></div>
          <div class="flex justify-between py-2 border-b border-white/5"><span class="text-white/40">Disk</span><span class="text-white font-medium" id="confirm-disk">—</span></div>
          <div class="flex justify-between py-2"><span class="text-white/40">Name</span><span class="text-white font-medium" id="confirm-name">Auto-generated</span></div>
        </div>
        <div class="mt-5 p-4 rounded-md" style="background:rgba(234,179,8,0.06);border:1px solid rgba(234,179,8,0.15);">
          <p class="text-yellow-300/70 text-xs">Deployment takes 30–120 seconds depending on image size.</p>
        </div>
      </div>
    </div>
    <div class="flex items-center justify-between mt-2">
      <button type="button" id="back-btn" onclick="prevStep()" class="btn-secondary" style="display:none;"><i class="fa-solid fa-arrow-left text-xs"></i> Back</button>
      <div></div>
      <button type="button" id="next-btn" onclick="nextStep()" class="btn-primary">Continue <i class="fa-solid fa-arrow-right text-xs"></i></button>
      <button type="submit" id="deploy-btn" class="btn-primary" style="display:none;"><i class="fa-solid fa-rocket text-xs"></i> <span id="deploy-text">Deploy Instance</span></button>
    </div>
  </form>
</div>
{% endblock %}
{% block scripts %}
<script>
let currentStep = 1; const totalSteps = 4;
function updateStepUI() {
  for (let i = 1; i <= totalSteps; i++) {
    const pane = document.getElementById(`step-${i}`);
    const ind  = document.getElementById(`step-${i}-indicator`);
    if (!pane||!ind) continue;
    pane.classList.toggle('hidden', i !== currentStep);
    ind.classList.remove('active','done');
    if (i === currentStep) ind.classList.add('active');
    else if (i < currentStep) ind.classList.add('done');
    const conn = document.getElementById(`conn-${i}`);
    if (conn) conn.classList.toggle('done', i < currentStep);
  }
  document.getElementById('back-btn').style.display = currentStep > 1 ? '' : 'none';
  document.getElementById('next-btn').style.display = currentStep < totalSteps ? '' : 'none';
  document.getElementById('deploy-btn').style.display = currentStep === totalSteps ? '' : 'none';
  if (currentStep === totalSteps) populateConfirm();
}
function nextStep() { if (currentStep < totalSteps) { currentStep++; updateStepUI(); } }
function prevStep() { if (currentStep > 1) { currentStep--; updateStepUI(); } }
function selectType(type) {
  document.getElementById('lxc-card').classList.toggle('selected', type==='lxc');
  document.getElementById('kvm-card').classList.toggle('selected', type==='kvm');
  document.querySelector(`input[value="${type}"]`).checked = true;
}
function selectOs(el) {
  document.querySelectorAll('.os-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected'); el.querySelector('.os-radio').checked = true;
}
function populateConfirm() {
  const type = document.querySelector('input[name="vtype"]:checked')?.value || '—';
  const customImg = document.querySelector('input[name="custom_image"]')?.value?.trim();
  const selectedOs = document.querySelector('.os-radio:checked')?.value || '—';
  document.getElementById('confirm-type').textContent = type === 'lxc' ? 'System Container (LXC)' : 'Virtual Machine (KVM)';
  document.getElementById('confirm-image').textContent = customImg || selectedOs;
  document.getElementById('confirm-cpu').textContent = document.getElementById('cpu-input')?.value + ' vCore(s)';
  const ramVal = document.getElementById('ram-input')?.value;
  const ramUnit = document.getElementById('ram-unit')?.value;
  document.getElementById('confirm-ram').textContent = ramUnit === 'gb' ? ramVal + ' GB' : ramVal + ' MB';
  document.getElementById('confirm-disk').textContent = document.getElementById('disk-input')?.value + ' GB';
  const name = document.querySelector('input[name="name"]')?.value?.trim();
  document.getElementById('confirm-name').textContent = name || 'Auto-generated';
}
const ramInput = document.getElementById('ram-input');
const ramHint  = document.getElementById('ram-hint');
const ramUnit  = document.getElementById('ram-unit');
function updateRamHint() {
  const v = parseInt(ramInput.value)||0, u = ramUnit.value;
  if (u==='mb') ramHint.textContent = v>=1024 ? `= ${(v/1024).toFixed(1).replace(/\.0$/,'')} GB` : `= ${v} MB`;
  else ramHint.textContent = `= ${v*1024} MB`;
}
function convertRam() {
  const v = parseInt(ramInput.value)||1;
  if (ramUnit.value==='gb') { ramInput.min=1; ramInput.max=128; ramInput.value=Math.max(1,Math.round(v/1024))||1; }
  else { ramInput.min=128; ramInput.max=131072; ramInput.value=Math.max(128,v*1024); }
  updateRamHint();
}
ramInput?.addEventListener('input', updateRamHint); updateRamHint();
document.getElementById('deploy-form').addEventListener('submit', e => {
  if (ramUnit.value==='gb') ramInput.value = parseInt(ramInput.value)*1024;
  const btn = document.getElementById('deploy-btn');
  btn.disabled = true; document.getElementById('deploy-text').textContent = 'Deploying…'; btn.style.opacity = '0.6';
});
updateStepUI();
</script>
{% endblock %}
ENDCREATE

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/instance_detail.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/instance_detail.html" << 'ENDDETAIL'
{% extends "base.html" %}
{% block title %}{{ inst.name }}{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto fade-in">
  <div class="page-header">
    <a href="/instances" class="text-white/30 hover:text-white text-xs flex items-center gap-2 mb-4 w-fit uppercase tracking-wider"><i class="fa-solid fa-arrow-left text-xs"></i> Back</a>
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <div class="flex items-center gap-3 mb-2">
          <span class="status-badge status-{{ inst.status }}" id="status-badge">
            <span class="status-dot dot-{{ inst.status }}" id="status-dot"></span>
            <span id="status-text">{{ inst.status|upper }}</span>
          </span>
        </div>
        <h1 class="page-title text-2xl">{{ inst.name }}</h1>
        <p class="text-white/30 text-sm mt-1">{{ inst.os_image }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        {% if inst.status != 'running' %}
        <button onclick="doAction('start')" class="btn-secondary btn-sm"><i class="fa-solid fa-play text-green-400 text-xs"></i> Start</button>
        {% else %}
        <button onclick="doAction('stop')" class="btn-secondary btn-sm"><i class="fa-solid fa-stop text-red-400 text-xs"></i> Stop</button>
        <button onclick="doAction('restart')" class="btn-secondary btn-sm"><i class="fa-solid fa-rotate-right text-yellow-400 text-xs"></i> Restart</button>
        {% endif %}
        <a href="/instances/{{ inst.id }}/console" class="btn-secondary btn-sm"><i class="fa-solid fa-terminal text-yellow-300 text-xs"></i> Console</a>
        <button onclick="showReinstall()" class="btn-secondary btn-sm"><i class="fa-solid fa-rotate text-white/40 text-xs"></i> Reinstall</button>
        <button onclick="showDelete()" class="btn-danger btn-sm"><i class="fa-solid fa-trash text-xs"></i> Delete</button>
      </div>
    </div>
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
    <div class="hyper-card p-5">
      <h2 class="text-xs font-bold text-white/25 uppercase tracking-widest mb-4">Specs</h2>
      <div class="space-y-3">
        <div class="flex items-center justify-between"><span class="text-sm text-white/40 flex items-center gap-2"><i class="fa-solid fa-microchip w-4 text-yellow-400 text-xs"></i> CPU</span><span class="text-sm font-semibold text-white">{{ inst.cpu }} vCore{{ 's' if inst.cpu > 1 }}</span></div>
        <div class="flex items-center justify-between"><span class="text-sm text-white/40 flex items-center gap-2"><i class="fa-solid fa-memory w-4 text-blue-400 text-xs"></i> RAM</span><span class="text-sm font-semibold text-white">{% if inst.ram >= 1024 %}{{ (inst.ram / 1024)|round(1) }} GB{% else %}{{ inst.ram }} MB{% endif %}</span></div>
        <div class="flex items-center justify-between"><span class="text-sm text-white/40 flex items-center gap-2"><i class="fa-solid fa-hdd w-4 text-green-400 text-xs"></i> Disk</span><span class="text-sm font-semibold text-white">{{ inst.disk }} GB</span></div>
        <div class="flex items-center justify-between"><span class="text-sm text-white/40 flex items-center gap-2"><i class="fa-solid fa-network-wired w-4 text-white/30 text-xs"></i> Node</span><span class="text-sm font-semibold text-white">{{ node.name if node else 'Local' }}</span></div>
      </div>
    </div>
    <div class="hyper-card p-5">
      <h2 class="text-xs font-bold text-white/25 uppercase tracking-widest mb-3">Console Access</h2>
      <p class="text-xs text-white/35 leading-relaxed mb-4">Access your instance directly through the in-browser terminal — no SSH key or public IP required.</p>
      <a href="/instances/{{ inst.id }}/console" class="btn-secondary w-full justify-center"><i class="fa-solid fa-terminal text-xs"></i> Open Terminal</a>
    </div>
    <div class="hyper-card p-5">
      <h2 class="text-xs font-bold text-white/25 uppercase tracking-widest mb-4">Live Stats</h2>
      {% if inst.status == 'running' %}
      <div class="space-y-4">
        <div>
          <div class="flex justify-between text-xs mb-1.5"><span class="text-white/40">CPU</span><span class="text-white font-semibold" id="live-cpu">–</span></div>
          <div class="progress-bar"><div class="progress-fill progress-yellow" id="cpu-bar" style="width:0%"></div></div>
        </div>
        <div>
          <div class="flex justify-between text-xs mb-1.5"><span class="text-white/40">RAM</span><span class="text-white font-semibold" id="live-ram">–</span></div>
          <div class="progress-bar"><div class="progress-fill progress-cyan" id="ram-bar" style="width:0%"></div></div>
        </div>
        <div>
          <div class="flex justify-between text-xs mb-1.5"><span class="text-white/40">Disk</span><span class="text-white font-semibold" id="live-disk">–</span></div>
          <div class="progress-bar"><div class="progress-fill progress-green" id="disk-bar" style="width:0%"></div></div>
        </div>
        <div class="grid grid-cols-2 gap-3 mt-1">
          <div class="rounded-md p-3 text-center" style="background:rgba(255,255,255,0.04);"><div class="text-xs text-white/25 mb-1">Net In</div><div class="text-sm font-semibold text-white" id="live-net-in">–</div></div>
          <div class="rounded-md p-3 text-center" style="background:rgba(255,255,255,0.04);"><div class="text-xs text-white/25 mb-1">Net Out</div><div class="text-sm font-semibold text-white" id="live-net-out">–</div></div>
        </div>
      </div>
      {% else %}
      <div class="text-center py-10 text-white/15"><i class="fa-solid fa-power-off text-3xl mb-2 block"></i><p class="text-sm">Instance is stopped</p></div>
      {% endif %}
    </div>
  </div>
  <div class="hyper-card p-5">
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
      <div><p class="text-xs text-white/25 mb-1">Created</p><p class="text-sm text-white">{{ inst.created_at[:10] if inst.created_at else '—' }}</p></div>
      <div><p class="text-xs text-white/25 mb-1">Instance ID</p><p class="text-xs font-mono text-white/70">{{ inst.id }}</p></div>
      <div><p class="text-xs text-white/25 mb-1">OS Image</p><p class="text-sm text-white">{{ inst.os_image }}</p></div>
      <div>
        <p class="text-xs text-white/25 mb-1">Expires</p>
        {% if inst.expires_at %}
        <p class="text-sm text-yellow-400">{{ inst.expires_at[:10] }}</p>
        {% else %}
        <p class="text-sm text-white/40">Never</p>
        {% endif %}
      </div>
    </div>
  </div>
</div>
{% if pf_enabled %}
<div class="hyper-card p-5 mt-4">
  <div class="flex items-center justify-between mb-4">
    <div>
      <h2 class="text-sm font-semibold text-white">Port Forwarding</h2>
      <p class="text-xs text-white/30 mt-0.5">Route public ports on your VPS into this container</p>
    </div>
    {% if inst.status == 'running' %}
    <button onclick="document.getElementById('pf-modal').classList.remove('hidden')" class="btn-secondary btn-sm"><i class="fa-solid fa-plus text-xs"></i> Add Rule</button>
    {% endif %}
  </div>
  {% if port_forwards %}
  <table class="hyper-table">
    <thead><tr><th>Protocol</th><th>Public Port</th><th></th><th>Container Port</th><th>Note</th><th></th></tr></thead>
    <tbody>
      {% for pf in port_forwards %}
      <tr>
        <td><span class="status-badge status-unknown text-[10px]">{{ pf.protocol|upper }}</span></td>
        <td class="font-mono font-semibold text-white">{{ pf.public_port }}</td>
        <td class="text-white/20 text-xs px-1"><i class="fa-solid fa-arrow-right"></i></td>
        <td class="font-mono text-white/60">{{ pf.private_port }}</td>
        <td class="text-white/40 text-xs">{{ pf.note or '—' }}</td>
        <td><button onclick="deletePf({{ pf.id }})" class="text-red-400/50 hover:text-red-400 transition-colors" title="Remove rule"><i class="fa-solid fa-trash text-xs"></i></button></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="text-center py-8 text-white/20">
    <i class="fa-solid fa-arrow-right-arrow-left text-2xl mb-2 block opacity-30"></i>
    <p class="text-xs">No forwarding rules yet.</p>
    {% if inst.status != 'running' %}<p class="text-xs mt-1 text-white/15">Start the instance first to add rules.</p>{% endif %}
  </div>
  {% endif %}
</div>
<div id="pf-modal" class="hyper-modal-backdrop hidden">
  <div class="hyper-modal">
    <h3 class="font-semibold text-white mb-1">Add Port Forward Rule</h3>
    <p class="text-xs text-white/35 mb-5">Traffic arriving on the public port of your VPS will be forwarded to the container.</p>
    <div class="space-y-4">
      <div class="grid grid-cols-2 gap-3">
        <div><label class="hyper-label">Public Port (VPS)</label><input type="number" id="pf-pub" class="hyper-input" placeholder="e.g. 8080" min="1" max="65535"></div>
        <div><label class="hyper-label">Container Port</label><input type="number" id="pf-priv" class="hyper-input" placeholder="e.g. 80" min="1" max="65535"></div>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="hyper-label">Protocol</label><select id="pf-proto" class="hyper-input"><option value="tcp">TCP</option><option value="udp">UDP</option></select></div>
        <div><label class="hyper-label">Note (optional)</label><input type="text" id="pf-note" class="hyper-input" placeholder="e.g. Web server" maxlength="64"></div>
      </div>
      <p id="pf-err" class="text-red-400 text-xs hidden"></p>
    </div>
    <div class="flex gap-3 mt-6">
      <button onclick="submitPf()" class="btn-primary flex-1 justify-center"><i class="fa-solid fa-plus text-xs"></i> Add Rule</button>
      <button onclick="document.getElementById('pf-modal').classList.add('hidden')" class="btn-secondary flex-1 justify-center">Cancel</button>
    </div>
  </div>
</div>
{% endif %}
<div id="delete-modal" class="hyper-modal-backdrop hidden">
  <div class="hyper-modal">
    <div class="flex items-center gap-3 mb-5">
      <div class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0" style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);"><i class="fa-solid fa-trash text-red-400 text-sm"></i></div>
      <div><h3 class="font-semibold text-white">Delete Instance</h3><p class="text-xs text-white/35">This cannot be undone</p></div>
    </div>
    <p class="text-sm text-white/55 mb-6">Delete <strong class="text-white">{{ inst.name }}</strong>? All data will be permanently lost.</p>
    <div class="flex gap-3">
      <button onclick="doDelete()" class="btn-danger flex-1 justify-center"><i class="fa-solid fa-trash text-xs"></i> Delete</button>
      <button onclick="closeModals()" class="btn-secondary flex-1 justify-center">Cancel</button>
    </div>
  </div>
</div>
<div id="reinstall-modal" class="hyper-modal-backdrop hidden">
  <div class="hyper-modal">
    <h3 class="font-semibold text-white mb-1">Reinstall Instance</h3>
    <p class="text-xs text-white/40 mb-5">Wipes the container and reinstalls the OS. All data will be lost.</p>
    <div class="mb-5">
      <label class="hyper-label">OS Image</label>
      <select id="reinstall-image" class="hyper-input">
        {% for img in images %}<option value="{{ img }}" {% if img == inst.os_image %}selected{% endif %}>{{ img }}</option>{% endfor %}
      </select>
    </div>
    <div class="flex gap-3">
      <button onclick="doReinstall()" class="btn-primary flex-1 justify-center"><i class="fa-solid fa-rotate text-xs"></i> Reinstall</button>
      <button onclick="closeModals()" class="btn-secondary flex-1 justify-center">Cancel</button>
    </div>
  </div>
</div>
{% endblock %}
{% block scripts %}
<script>
const iid = '{{ inst.id }}';
async function doAction(action) {
  const r = await fetch(`/instances/${iid}/${action}`, {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  const d = await r.json();
  if (d.ok !== false) location.reload(); else alert(d.error||'Action failed');
}
function showDelete()    { document.getElementById('delete-modal').classList.remove('hidden'); }
function showReinstall() { document.getElementById('reinstall-modal').classList.remove('hidden'); }
function closeModals() {
  document.getElementById('delete-modal').classList.add('hidden');
  document.getElementById('reinstall-modal').classList.add('hidden');
}
async function doDelete() {
  const r = await fetch(`/instances/${iid}/delete`, {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  const d = await r.json(); location.href = d.redirect||'/instances';
}
async function doReinstall() {
  const image = document.getElementById('reinstall-image').value;
  await fetch(`/instances/${iid}/reinstall`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image})});
  closeModals(); location.reload();
}
{% if inst.status == 'running' %}
async function refreshStats() {
  try {
    const r = await fetch(`/api/stats/instance/${iid}`); const d = await r.json();
    document.getElementById('live-cpu').textContent = (d.cpu_percent||0).toFixed(1)+'%';
    document.getElementById('cpu-bar').style.width = Math.min(100,d.cpu_percent||0)+'%';
    document.getElementById('live-ram').textContent = `${d.ram_used_mb||0} / ${d.ram_total_mb||0} MB`;
    document.getElementById('ram-bar').style.width = Math.min(100,d.ram_percent||0)+'%';
    document.getElementById('live-disk').textContent = `${d.disk_used_mb||0} / ${d.disk_total_mb||0} MB`;
    document.getElementById('disk-bar').style.width = Math.min(100,d.disk_percent||0)+'%';
    document.getElementById('live-net-in').textContent = (d.net_in_mb||0).toFixed(2)+' MB';
    document.getElementById('live-net-out').textContent = (d.net_out_mb||0).toFixed(2)+' MB';
  } catch(e) {}
}
refreshStats(); setInterval(refreshStats, 4000);
{% endif %}
document.querySelectorAll('.hyper-modal-backdrop').forEach(m => {
  m.addEventListener('click', e => { if (e.target===m) { closeModals(); m.classList.add('hidden'); } });
});
{% if pf_enabled %}
async function submitPf() {
  const pub = parseInt(document.getElementById('pf-pub').value)||0;
  const priv = parseInt(document.getElementById('pf-priv').value)||0;
  const proto = document.getElementById('pf-proto').value;
  const note = document.getElementById('pf-note').value;
  const err = document.getElementById('pf-err');
  err.classList.add('hidden');
  try {
    const r = await fetch(`/instances/${iid}/port-forwards/add`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({public_port:pub, private_port:priv, protocol:proto, note})
    });
    const d = await r.json();
    if (d.ok) { location.reload(); }
    else { err.textContent = d.error||'Failed to add rule'; err.classList.remove('hidden'); }
  } catch(e) { err.textContent = 'Request failed'; err.classList.remove('hidden'); }
}
async function deletePf(fid) {
  if (!confirm('Remove this port forward rule?')) return;
  await fetch(`/instances/${iid}/port-forwards/${fid}/delete`, {method:'POST'});
  location.reload();
}
{% endif %}
</script>
{% endblock %}
ENDDETAIL

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/admin/dashboard.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/admin/dashboard.html" << 'ENDADMIN'
{% extends "base.html" %}
{% block title %}Overview{% endblock %}
{% block content %}
<div class="max-w-5xl mx-auto fade-in">
  <div class="page-header"><p class="text-xs text-white/30 uppercase tracking-widest mb-1">System status & overview</p></div>
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
    <div class="stat-card">
      <div class="flex items-center justify-between mb-3"><p class="metric-label">Host CPU</p><div class="w-7 h-7 rounded flex items-center justify-center" style="background:rgba(234,179,8,0.1);"><i class="fa-solid fa-microchip text-yellow-400 text-xs"></i></div></div>
      <div class="text-2xl font-bold text-white mb-2" id="sys-cpu">{{ stats.cpu_percent }}%</div>
      <div class="progress-bar"><div class="progress-fill {% if stats.cpu_percent > 80 %}progress-red{% elif stats.cpu_percent > 60 %}progress-orange{% else %}progress-yellow{% endif %}" id="sys-cpu-bar" style="width:{{ stats.cpu_percent }}%"></div></div>
    </div>
    <div class="stat-card">
      <div class="flex items-center justify-between mb-3"><p class="metric-label">Host Memory</p><div class="w-7 h-7 rounded flex items-center justify-center" style="background:rgba(234,179,8,0.1);"><i class="fa-solid fa-memory text-yellow-400 text-xs"></i></div></div>
      <div class="text-2xl font-bold text-white mb-2" id="sys-ram">{{ stats.ram_percent }}%</div>
      <div class="progress-bar"><div class="progress-fill {% if stats.ram_percent > 80 %}progress-red{% elif stats.ram_percent > 60 %}progress-orange{% else %}progress-cyan{% endif %}" id="sys-ram-bar" style="width:{{ stats.ram_percent }}%"></div></div>
    </div>
    <div class="stat-card">
      <div class="flex items-center justify-between mb-3"><p class="metric-label">Host Storage</p><div class="w-7 h-7 rounded flex items-center justify-center" style="background:rgba(234,179,8,0.1);"><i class="fa-solid fa-database text-yellow-400 text-xs"></i></div></div>
      <div class="text-2xl font-bold text-white mb-2">{{ stats.disk_percent }}%</div>
      <div class="progress-bar"><div class="progress-fill {% if stats.disk_percent > 80 %}progress-red{% elif stats.disk_percent > 60 %}progress-orange{% else %}progress-green{% endif %}" style="width:{{ stats.disk_percent }}%"></div></div>
    </div>
  </div>
  <div class="flex gap-3 mb-6">
    <div class="count-card"><div class="count-label">Total</div><div class="count-val text-white">{{ total_instances }}</div></div>
    <div class="count-card"><div class="count-label" style="color:rgba(74,222,128,0.6);">⬤ Running</div><div class="count-val" style="color:#4ade80;">{{ running_instances }}</div></div>
    <div class="count-card"><div class="count-label" style="color:rgba(248,113,113,0.6);">⬤ Stopped</div><div class="count-val" style="color:#f87171;">{{ stopped_instances }}</div></div>
    <div class="count-card"><div class="count-label">Panel Users</div><div class="count-val text-white">{{ total_users }}</div></div>
  </div>
  <div class="hyper-card overflow-hidden">
    <div class="flex items-center justify-between px-5 py-4 border-b border-white/5">
      <h2 class="font-semibold text-white text-sm">Recent Instances</h2>
      <a href="/admin/instances" class="text-xs text-yellow-400 hover:text-yellow-300 transition-colors">View All</a>
    </div>
    {% if instances %}
    <table class="hyper-table">
      <thead><tr><th>Status</th><th>Name</th><th>Owner</th><th>CPU</th><th>RAM</th><th>IP</th><th></th></tr></thead>
      <tbody>
        {% for inst in instances %}
        <tr>
          <td><span class="status-badge status-{{ inst.status }}"><span class="status-dot dot-{{ inst.status }}"></span>{{ inst.status|upper }}</span></td>
          <td><a href="/instances/{{ inst.id }}" class="text-white hover:text-yellow-300 font-mono text-sm transition-colors">{{ inst.name }}</a></td>
          <td class="text-white/40 text-xs">{{ inst.get('username','—') }}</td>
          <td class="text-white/60 text-xs">{{ inst.cpu }} Cores</td>
          <td class="text-white/60 text-xs">{{ inst.ram }} MB</td>
          <td class="text-white/40 text-xs font-mono">{{ inst.ip_address or 'Unassigned' }}</td>
          <td><a href="/instances/{{ inst.id }}/console" class="text-xs text-yellow-400/70 hover:text-yellow-300">Console</a></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p class="text-white/25 text-sm text-center py-10">No instances yet</p>
    {% endif %}
  </div>
</div>
{% endblock %}
{% block scripts %}
<script>
async function refreshSysStats() {
  try {
    const r = await fetch('/api/stats/system'); const d = await r.json();
    const cpuEl=document.getElementById('sys-cpu'), cpuBar=document.getElementById('sys-cpu-bar');
    const ramEl=document.getElementById('sys-ram'), ramBar=document.getElementById('sys-ram-bar');
    if(cpuEl) cpuEl.textContent=d.cpu_percent+'%';
    if(cpuBar) cpuBar.style.width=d.cpu_percent+'%';
    if(ramEl) ramEl.textContent=d.ram_percent+'%';
    if(ramBar) ramBar.style.width=d.ram_percent+'%';
  } catch(e) {}
}
setInterval(refreshSysStats, 5000);
</script>
{% endblock %}
ENDADMIN

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/admin/users.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/admin/users.html" << 'ENDUSERS'
{% extends "base.html" %}
{% block title %}Users{% endblock %}
{% block content %}
<div class="max-w-5xl mx-auto fade-in">
  <div class="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
    <div><h1 class="page-title">Users</h1><p class="text-white/35 mt-1 text-sm">{{ users|length }} registered accounts</p></div>
    <button onclick="document.getElementById('create-user-modal').classList.remove('hidden')" class="btn-primary" style="flex-shrink:0;"><i class="fa-solid fa-user-plus text-xs"></i> Add User</button>
  </div>
  <div class="hyper-card overflow-hidden">
    <table class="hyper-table">
      <thead><tr><th>User</th><th>Role</th><th>Instances</th><th>Limit</th><th>Status</th><th>Joined</th><th>Actions</th></tr></thead>
      <tbody>
        {% for u in users %}
        <tr>
          <td>
            <div class="flex items-center gap-3">
              <div class="w-7 h-7 rounded flex items-center justify-center text-xs font-bold text-black flex-shrink-0" style="background:#EAB308;">{{ u.username[0].upper() }}</div>
              <div><p class="text-sm font-medium text-white">{{ u.username }}</p><p class="text-xs text-white/25">{{ u.email or '—' }}</p></div>
            </div>
          </td>
          <td><span class="text-xs font-medium px-2 py-1 rounded {% if u.role=='admin' %}text-yellow-300{% else %}text-white/40{% endif %}" style="{% if u.role=='admin' %}background:rgba(234,179,8,0.1);border:1px solid rgba(234,179,8,0.2);{% else %}background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);{% endif %}">{{ u.role }}</span></td>
          <td class="font-semibold text-white">{{ u.instance_count }}</td>
          <td class="text-white/40">{{ u.max_instances }}</td>
          <td>{% if u.banned %}<span class="status-badge status-stopped">Banned</span>{% else %}<span class="status-badge status-running">Active</span>{% endif %}</td>
          <td class="text-white/30 text-xs">{{ u.created_at[:10] if u.created_at else '—' }}</td>
          <td>
            {% if u.id != current_user.id %}
            <div class="flex items-center gap-1 flex-wrap">
              {% if u.banned %}<form method="POST" action="/admin/users/{{ u.id }}/action" class="inline"><input type="hidden" name="action" value="unban"><button type="submit" class="text-xs px-2 py-1 rounded text-green-400" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">Unban</button></form>
              {% else %}<form method="POST" action="/admin/users/{{ u.id }}/action" class="inline"><input type="hidden" name="action" value="ban"><button type="submit" class="text-xs px-2 py-1 rounded text-yellow-400" style="background:rgba(234,179,8,0.08);border:1px solid rgba(234,179,8,0.2);">Ban</button></form>{% endif %}
              {% if u.role != 'admin' %}<form method="POST" action="/admin/users/{{ u.id }}/action" class="inline"><input type="hidden" name="action" value="make_admin"><button type="submit" class="text-xs px-2 py-1 rounded text-yellow-400" style="background:rgba(234,179,8,0.08);border:1px solid rgba(234,179,8,0.2);">Promote</button></form>
              {% else %}<form method="POST" action="/admin/users/{{ u.id }}/action" class="inline"><input type="hidden" name="action" value="remove_admin"><button type="submit" class="text-xs px-2 py-1 rounded text-white/40" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);">Demote</button></form>{% endif %}
              <form method="POST" action="/admin/users/{{ u.id }}/action" class="inline flex items-center gap-1"><input type="hidden" name="action" value="set_limit"><input type="number" name="max_instances" value="{{ u.max_instances }}" min="0" max="999" class="w-12 text-xs px-1 py-1 rounded text-center" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);color:white;"><button type="submit" class="text-xs px-2 py-1 rounded text-white/40" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);">Set</button></form>
              <form method="POST" action="/admin/users/{{ u.id }}/action" class="inline" onsubmit="return confirm('Delete user and all their instances?')"><input type="hidden" name="action" value="delete"><button type="submit" class="text-xs px-2 py-1 rounded text-red-400" style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);">Delete</button></form>
            </div>
            {% else %}<span class="text-xs text-white/15">You</span>{% endif %}
          </td>
        </tr>
        {% else %}<tr><td colspan="7" class="text-center text-white/25 py-10">No users found</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
<div id="create-user-modal" class="hyper-modal-backdrop hidden">
  <div class="hyper-modal">
    <h3 class="font-semibold text-white mb-5">Add User</h3>
    <form method="POST" action="/admin/users/create">
      <div class="space-y-4">
        <div><label class="hyper-label">Username</label><input type="text" name="username" class="hyper-input" required minlength="3" placeholder="username"></div>
        <div><label class="hyper-label">Email</label><input type="email" name="email" class="hyper-input" placeholder="email@example.com"></div>
        <div><label class="hyper-label">Password</label><input type="password" name="password" class="hyper-input" required minlength="8" placeholder="Min 8 characters"></div>
        <div><label class="hyper-label">Role</label><select name="role" class="hyper-input"><option value="user">User</option><option value="admin">Admin</option></select></div>
      </div>
      <div class="flex gap-3 mt-6">
        <button type="submit" class="btn-primary flex-1 justify-center">Create</button>
        <button type="button" onclick="document.getElementById('create-user-modal').classList.add('hidden')" class="btn-secondary flex-1 justify-center">Cancel</button>
      </div>
    </form>
  </div>
</div>
{% block scripts %}
<script>document.getElementById('create-user-modal').addEventListener('click', e => { if(e.target.id==='create-user-modal') e.target.classList.add('hidden'); });</script>
{% endblock %}
{% endblock %}
ENDUSERS

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/admin/instances.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/admin/instances.html" << 'ENDAINST'
{% extends "base.html" %}
{% block title %}All Instances{% endblock %}
{% block content %}
<div class="max-w-5xl mx-auto fade-in">
  <div class="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
    <div><h1 class="page-title">All Instances</h1><p class="text-white/35 mt-1 text-sm">{{ instances|length }} total instances across all users</p></div>
    <a href="/instances/create" class="btn-primary" style="flex-shrink:0;"><i class="fa-solid fa-plus text-xs"></i> Deploy Instance</a>
  </div>
  <div class="hyper-card overflow-hidden">
    <table class="hyper-table">
      <thead><tr><th>Status</th><th>Name</th><th>Owner</th><th>OS</th><th>Specs</th><th>IP</th><th>Actions</th></tr></thead>
      <tbody>
        {% for inst in instances %}
        <tr>
          <td><span class="status-badge status-{{ inst.status }}"><span class="status-dot dot-{{ inst.status }}"></span>{{ inst.status|upper }}</span></td>
          <td><a href="/instances/{{ inst.id }}" class="font-mono text-sm text-white hover:text-yellow-300 transition-colors">{{ inst.name }}</a></td>
          <td class="text-white/40 text-xs">{{ inst.get('username','—') }}</td>
          <td class="text-white/40 text-xs">{{ inst.os_image }}</td>
          <td class="text-white/40 text-xs">{{ inst.cpu }}C · {{ inst.ram }}M · {{ inst.disk }}G</td>
          <td class="font-mono text-xs text-white/40">{{ inst.ip_address or '—' }}</td>
          <td>
            <div class="flex items-center gap-1">
              <a href="/instances/{{ inst.id }}/console" class="btn-icon" title="Console"><i class="fa-solid fa-terminal text-yellow-300 text-xs"></i></a>
              {% if inst.status == 'running' %}
              <form method="POST" action="/admin/instances/{{ inst.id }}/suspend" class="inline"><button type="submit" class="btn-icon" title="Suspend"><i class="fa-solid fa-pause text-yellow-400 text-xs"></i></button></form>
              {% else %}
              <form method="POST" action="/admin/instances/{{ inst.id }}/unsuspend" class="inline"><button type="submit" class="btn-icon" title="Unsuspend"><i class="fa-solid fa-play text-green-400 text-xs"></i></button></form>
              {% endif %}
            </div>
          </td>
        </tr>
        {% else %}<tr><td colspan="7" class="text-center text-white/25 py-10">No instances found</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
ENDAINST

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/admin/nodes.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/admin/nodes.html" << 'ENDNODES'
{% extends "base.html" %}
{% block title %}Nodes{% endblock %}
{% block content %}
<div class="max-w-5xl mx-auto fade-in">
  <div class="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
    <div><h1 class="page-title">Nodes</h1><p class="text-white/35 mt-1 text-sm">{{ nodes|length }} registered node(s)</p></div>
    <button onclick="document.getElementById('add-node-modal').classList.remove('hidden')" class="btn-primary" style="flex-shrink:0;"><i class="fa-solid fa-plus text-xs"></i> Add Node</button>
  </div>
  <div class="hyper-card overflow-hidden mb-4">
    <table class="hyper-table">
      <thead><tr><th>Status</th><th>Name</th><th>Host</th><th>Location</th><th>CPU</th><th>RAM</th><th>Actions</th></tr></thead>
      <tbody>
        {% for node in nodes %}
        {% set ns = node_stats.get(node.id, {}) %}
        <tr>
          <td>{% if ns.get('online') %}<span class="status-badge status-running"><span class="status-dot dot-running"></span>ONLINE</span>{% else %}<span class="status-badge status-stopped"><span class="status-dot dot-stopped"></span>OFFLINE</span>{% endif %}</td>
          <td class="font-semibold text-white text-sm">{{ node.name }}{% if node.is_main %}<span class="ml-2 text-xs text-yellow-400/60 font-normal">(main)</span>{% endif %}</td>
          <td class="font-mono text-xs text-white/40">{{ node.host }}:{{ node.port }}</td>
          <td class="text-white/40 text-xs">{{ node.location }}</td>
          <td class="text-white/40 text-xs">{{ ns.get('cpu_percent','—') }}{% if ns.get('cpu_percent') is not none %}%{% endif %}</td>
          <td class="text-white/40 text-xs">{{ ns.get('ram_percent','—') }}{% if ns.get('ram_percent') is not none %}%{% endif %}</td>
          <td>{% if not node.is_main %}<div class="flex gap-1"><form method="POST" action="/admin/nodes/{{ node.id }}/toggle" class="inline"><button type="submit" class="text-xs px-2 py-1 rounded text-white/40" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);">{{ 'Disable' if node.active else 'Enable' }}</button></form><form method="POST" action="/admin/nodes/{{ node.id }}/delete" class="inline" onsubmit="return confirm('Remove this node?')"><button type="submit" class="text-xs px-2 py-1 rounded text-red-400" style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);">Remove</button></form></div>{% endif %}</td>
        </tr>
        {% else %}<tr><td colspan="7" class="text-center text-white/25 py-10">No nodes registered</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="hyper-card p-5">
    <h2 class="font-semibold text-white mb-2 text-sm">Node Secret</h2>
    <p class="text-xs text-white/35 mb-3">Use this secret when connecting remote nodes via the node agent.</p>
    <div class="flex items-center gap-3 rounded-md px-4 py-3" style="background:#0d0d0d;border:1px solid rgba(255,255,255,0.08);">
      <code class="font-mono text-sm text-yellow-300 flex-1 break-all" id="node-secret-val">{{ node_secret }}</code>
      <button onclick="copySecret()" class="text-white/25 hover:text-white transition-colors text-xs" title="Copy"><i class="fa-solid fa-copy" id="ns-copy-icon"></i></button>
    </div>
  </div>
</div>
<div id="add-node-modal" class="hyper-modal-backdrop hidden">
  <div class="hyper-modal">
    <h3 class="font-semibold text-white mb-5">Add Remote Node</h3>
    <form method="POST" action="/admin/nodes/add">
      <div class="space-y-4">
        <div><label class="hyper-label">Node Name</label><input type="text" name="name" class="hyper-input" required placeholder="e.g. eu-node-1"></div>
        <div class="grid grid-cols-2 gap-3"><div><label class="hyper-label">Host (IP or Tailscale)</label><input type="text" name="host" class="hyper-input" required placeholder="100.x.x.x"></div><div><label class="hyper-label">Port</label><input type="number" name="port" class="hyper-input" value="4567" required></div></div>
        <div><label class="hyper-label">API Key</label><input type="text" name="api_key" class="hyper-input" required placeholder="Node secret"></div>
        <div><label class="hyper-label">Location</label><input type="text" name="location" class="hyper-input" placeholder="e.g. Frankfurt, DE"></div>
      </div>
      <div class="flex gap-3 mt-6"><button type="submit" class="btn-primary flex-1 justify-center">Add Node</button><button type="button" onclick="document.getElementById('add-node-modal').classList.add('hidden')" class="btn-secondary flex-1 justify-center">Cancel</button></div>
    </form>
  </div>
</div>
{% block scripts %}
<script>
function copySecret() {
  const val = document.getElementById('node-secret-val').textContent;
  navigator.clipboard.writeText(val.trim()).catch(()=>{});
  const icon = document.getElementById('ns-copy-icon');
  icon.className = 'fa-solid fa-check text-green-400';
  setTimeout(()=>{ icon.className='fa-solid fa-copy'; }, 2000);
}
document.getElementById('add-node-modal').addEventListener('click', e => { if(e.target.id==='add-node-modal') e.target.classList.add('hidden'); });
</script>
{% endblock %}
{% endblock %}
ENDNODES

# ═════════════════════════════════════════════════════════════════════════════
# FILE: templates/admin/settings.html
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/templates/admin/settings.html" << 'ENDSETTINGS'
{% extends "base.html" %}
{% block title %}Settings{% endblock %}
{% block content %}
<div class="max-w-2xl mx-auto fade-in">
  <div class="page-header"><h1 class="page-title">Settings</h1><p class="text-white/35 mt-1 text-sm">Panel-wide configuration</p></div>
  {% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for cat, msg in messages %}
  <div class="flex items-center gap-3 mb-5 px-4 py-3 rounded-md text-sm {% if cat=='success' %}bg-emerald-950 border border-emerald-800/40 text-emerald-300{% else %}bg-red-950 border border-red-800/40 text-red-300{% endif %}">
    <i class="fa-solid {% if cat=='success' %}fa-check{% else %}fa-circle-exclamation{% endif %} flex-shrink-0"></i>{{ msg }}
  </div>
  {% endfor %}{% endif %}{% endwith %}
  <form method="POST" action="/admin/settings">
    <div class="hyper-card p-6 mb-4 space-y-5">
      <h3 class="text-xs font-bold text-white/25 uppercase tracking-widest pb-3 border-b border-white/5">General</h3>
      <div><label class="hyper-label">Panel Name</label><input type="text" name="panel_name" class="hyper-input" value="{{ settings.panel_name }}"></div>
      <div><label class="hyper-label">Registration</label><select name="registration" class="hyper-input"><option value="open" {% if settings.registration=='open' %}selected{% endif %}>Open (anyone can register)</option><option value="disabled" {% if settings.registration=='disabled' %}selected{% endif %}>Disabled (admin only)</option></select></div>
      <div><label class="hyper-label">Default Instance Limit (per user)</label><input type="number" name="max_instances" class="hyper-input" value="{{ settings.max_instances }}" min="0" max="999"></div>
      <div><label class="hyper-label">Welcome Message</label><input type="text" name="welcome_msg" class="hyper-input" value="{{ settings.welcome_msg }}"></div>
    </div>
    <div class="hyper-card p-6 mb-4 space-y-5">
      <h3 class="text-xs font-bold text-white/25 uppercase tracking-widest pb-3 border-b border-white/5">Appearance</h3>
      <div>
        <label class="hyper-label">Accent Colour</label>
        <p class="text-xs text-white/25 mb-3 mt-1">Sets the highlight colour used across the entire panel UI.</p>
        <div class="flex items-center gap-3">
          <span id="accent-preview" class="w-9 h-9 rounded-full flex-shrink-0 border border-white/10 transition-all" style="background:{{ settings.accent_color or '#EAB308' }};"></span>
          <select name="accent_color" class="hyper-input" onchange="document.getElementById('accent-preview').style.background=this.value">
            <option value="#EAB308" {% if not settings.accent_color or settings.accent_color=='#EAB308' %}selected{% endif %}>Yellow (default)</option>
            <option value="#3B82F6" {% if settings.accent_color=='#3B82F6' %}selected{% endif %}>Blue</option>
            <option value="#8B5CF6" {% if settings.accent_color=='#8B5CF6' %}selected{% endif %}>Purple</option>
            <option value="#22C55E" {% if settings.accent_color=='#22C55E' %}selected{% endif %}>Green</option>
            <option value="#EF4444" {% if settings.accent_color=='#EF4444' %}selected{% endif %}>Red</option>
            <option value="#06B6D4" {% if settings.accent_color=='#06B6D4' %}selected{% endif %}>Cyan</option>
            <option value="#F97316" {% if settings.accent_color=='#F97316' %}selected{% endif %}>Orange</option>
            <option value="#EC4899" {% if settings.accent_color=='#EC4899' %}selected{% endif %}>Pink</option>
          </select>
        </div>
        <p class="text-xs text-white/20 mt-2">Preview updates instantly. Save then hard-refresh (Ctrl+Shift+R) to apply panel-wide.</p>
      </div>
    </div>
    <div class="hyper-card p-6 mb-5 space-y-5">
      <h3 class="text-xs font-bold text-white/25 uppercase tracking-widest pb-3 border-b border-white/5">Features</h3>
      <div>
        <label class="hyper-label">Port Forwarding</label>
        <select name="port_forwarding_enabled" class="hyper-input mt-1">
          <option value="0" {% if settings.port_forwarding_enabled!='1' %}selected{% endif %}>Disabled — feature hidden from all users</option>
          <option value="1" {% if settings.port_forwarding_enabled=='1' %}selected{% endif %}>Enabled — users can add port forward rules to their instances</option>
        </select>
        <p class="text-xs text-white/20 mt-1">Uses iptables DNAT on the host. Only enable when a node with a public IPv4 is connected.</p>
      </div>
    </div>
    <button type="submit" class="btn-primary"><i class="fa-solid fa-floppy-disk text-xs"></i> Save Settings</button>
  </form>
</div>
{% endblock %}
ENDSETTINGS

# ═════════════════════════════════════════════════════════════════════════════
# FILE: panel.py  (written in chunks to avoid huge heredoc)
# ═════════════════════════════════════════════════════════════════════════════
cat > "$D/panel.py" << 'ENDPANEL'
#!/usr/bin/env python3
"""HyperPanel — Multi-Node LXC/Incus VPS Management Panel"""
import os, sys, json, time, uuid, random, string, threading, subprocess, logging, sqlite3, socket, select, struct, fcntl, signal
import traceback
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response, stream_with_context
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect as socketio_disconnect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import requests
import psutil
import paramiko
load_dotenv()

SECRET_KEY     = os.getenv('SECRET_KEY', 'hyperpanel-dev-key-change-me')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123456')
ADMIN_EMAIL    = os.getenv('ADMIN_EMAIL', 'admin@hyperpanel.local')
PANEL_NAME     = os.getenv('PANEL_NAME', 'HyperPanel')
PANEL_HOST     = os.getenv('PANEL_HOST', '0.0.0.0')
PANEL_PORT     = int(os.getenv('PANEL_PORT', 5000))
NODE_SECRET    = os.getenv('NODE_SECRET', 'node-secret-change-me')
LXC_BACKEND    = os.getenv('LXC_BACKEND', 'auto')
DB_FILE        = os.getenv('DB_FILE', 'hyperpanel.db')
REGISTRATION   = os.getenv('REGISTRATION', 'open')
MAX_INSTANCES  = int(os.getenv('MAX_INSTANCES_PER_USER', 3))
DEFAULT_IMAGES = os.getenv('DEFAULT_IMAGES', 'ubuntu:22.04,ubuntu:20.04,debian:12,almalinux:9,alpine:3.19').split(',')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('hyperpanel.log')])
logger = logging.getLogger('HyperPanel')

def detect_backend():
    if LXC_BACKEND in ('incus','lxc'):
        # Verify it actually works (daemon must be initialized)
        try:
            r = subprocess.run([LXC_BACKEND,'list','--format','json'], capture_output=True, timeout=10)
            if r.returncode == 0: return LXC_BACKEND
            logger.warning(f"{LXC_BACKEND} found but not initialized: {r.stderr.decode().strip()}")
        except (FileNotFoundError, subprocess.TimeoutExpired): pass
        return None
    for cmd in ['incus','lxc']:
        try:
            r = subprocess.run([cmd,'list','--format','json'], capture_output=True, timeout=10)
            if r.returncode == 0: return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired): pass
    return None

BACKEND = detect_backend()
logger.info(f"LXC backend: {BACKEND or 'NOT FOUND — demo mode'}")

def run_lxc(*args, timeout=30):
    if not BACKEND: return '','LXC backend not found',1
    try:
        r = subprocess.run([BACKEND]+list(args), capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired: return '','Command timed out',1
    except Exception as e: return '',str(e),1

class Database:
    _local = threading.local()
    def __init__(self, db_file):
        self.db_file = db_file; self._init_db()
    def _conn(self):
        if not hasattr(self._local,'conn') or self._local.conn is None:
            conn = sqlite3.connect(self.db_file, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL"); conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn
    def _exec(self, sql, params=()):
        conn = self._conn(); cur = conn.execute(sql, params); conn.commit(); return cur
    def _query(self, sql, params=()): return self._conn().execute(sql, params).fetchall()
    def _init_db(self):
        conn = sqlite3.connect(self.db_file); conn.row_factory = sqlite3.Row
        stmts = [
            """CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE, password TEXT NOT NULL, role TEXT DEFAULT 'user', banned INTEGER DEFAULT 0,
                max_instances INTEGER DEFAULT 3, created_at TEXT DEFAULT (datetime('now')))""",
            """CREATE TABLE IF NOT EXISTS instances (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, node_id INTEGER,
                name TEXT UNIQUE NOT NULL, os_image TEXT NOT NULL, type TEXT DEFAULT 'container', cpu INTEGER DEFAULT 1,
                ram INTEGER DEFAULT 512, disk INTEGER DEFAULT 10, ip_address TEXT, ssh_port INTEGER, ssh_password TEXT,
                status TEXT DEFAULT 'creating', suspended INTEGER DEFAULT 0, expires_at TEXT DEFAULT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id))""",
            """CREATE TABLE IF NOT EXISTS nodes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                host TEXT NOT NULL, port INTEGER DEFAULT 4567, api_key TEXT NOT NULL, location TEXT DEFAULT 'Unknown',
                is_main INTEGER DEFAULT 0, active INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now')))""",
            """CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""",
            """CREATE TABLE IF NOT EXISTS activity_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                action TEXT NOT NULL, detail TEXT, ip TEXT, created_at TEXT DEFAULT (datetime('now')))""",
        ]
        for s in stmts: conn.execute(s)
        conn.commit()
        # Migrations for existing databases
        try: conn.execute("ALTER TABLE instances ADD COLUMN expires_at TEXT DEFAULT NULL"); conn.commit()
        except: pass
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS port_forwards (
                id INTEGER PRIMARY KEY AUTOINCREMENT, instance_id TEXT NOT NULL,
                protocol TEXT DEFAULT 'tcp', public_port INTEGER NOT NULL,
                private_port INTEGER NOT NULL, note TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE)""")
            conn.commit()
        except: pass
        if not conn.execute("SELECT id FROM users WHERE username=?", (ADMIN_USERNAME,)).fetchone():
            conn.execute("INSERT INTO users (username,email,password,role,max_instances) VALUES (?,?,?,?,?)",
                (ADMIN_USERNAME, ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD), 'admin', 9999))
            conn.commit(); logger.info(f"Admin user '{ADMIN_USERNAME}' created.")
        conn.close()
    def get_user(self, username):
        r = self._conn().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(r) if r else None
    def get_user_by_id(self, uid):
        r = self._conn().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(r) if r else None
    def get_all_users(self):
        return [dict(r) for r in self._conn().execute("SELECT * FROM users ORDER BY created_at DESC")]
    def create_user(self, username, email, password, role='user'):
        try:
            self._exec("INSERT INTO users (username,email,password,role,max_instances) VALUES (?,?,?,?,?)",
                (username, email, generate_password_hash(password), role, MAX_INSTANCES))
            return True, None
        except sqlite3.IntegrityError as e: return False, str(e)
    def update_user(self, uid, **kwargs):
        sets = ', '.join(f"{k}=?" for k in kwargs)
        self._exec(f"UPDATE users SET {sets} WHERE id=?", (*kwargs.values(), uid))
    def delete_user(self, uid):
        self._exec("DELETE FROM instances WHERE user_id=?", (uid,))
        self._exec("DELETE FROM users WHERE id=?", (uid,))
    def count_user_instances(self, uid):
        r = self._conn().execute("SELECT COUNT(*) FROM instances WHERE user_id=?", (uid,)).fetchone()
        return r[0] if r else 0
    def create_instance(self, iid, user_id, node_id, name, os_image, itype, cpu, ram, disk, ssh_port, ssh_password, expires_at=None):
        self._exec("INSERT INTO instances (id,user_id,node_id,name,os_image,type,cpu,ram,disk,ssh_port,ssh_password,expires_at,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'creating')",
            (iid, user_id, node_id, name, os_image, itype, cpu, ram, disk, ssh_port, ssh_password, expires_at))
    def get_instance(self, iid):
        r = self._conn().execute("SELECT i.*, u.username FROM instances i LEFT JOIN users u ON i.user_id=u.id WHERE i.id=?", (iid,)).fetchone()
        return dict(r) if r else None
    def get_instances(self, user_id=None, node_id=None):
        sql = "SELECT i.*, u.username FROM instances i LEFT JOIN users u ON i.user_id=u.id"
        params=[]; clauses=[]
        if user_id is not None: clauses.append("i.user_id=?"); params.append(user_id)
        if node_id is not None: clauses.append("i.node_id=?"); params.append(node_id)
        if clauses: sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY i.created_at DESC"
        return [dict(r) for r in self._conn().execute(sql, params)]
    def update_instance(self, iid, **kwargs):
        sets = ', '.join(f"{k}=?" for k in kwargs)
        self._exec(f"UPDATE instances SET {sets} WHERE id=?", (*kwargs.values(), iid))
    def delete_instance(self, iid): self._exec("DELETE FROM instances WHERE id=?", (iid,))
    def add_node(self, name, host, port, api_key, location, is_main, active):
        cur = self._exec("INSERT INTO nodes (name,host,port,api_key,location,is_main,active) VALUES (?,?,?,?,?,?,?)",
            (name,host,port,api_key,location,is_main,active))
        return cur.lastrowid
    def get_main_node(self):
        r = self._conn().execute("SELECT * FROM nodes WHERE is_main=1 LIMIT 1").fetchone()
        return dict(r) if r else None
    def get_node(self, nid):
        r = self._conn().execute("SELECT * FROM nodes WHERE id=?", (nid,)).fetchone()
        return dict(r) if r else None
    def get_nodes(self):
        return [dict(r) for r in self._conn().execute("SELECT * FROM nodes ORDER BY is_main DESC, id ASC")]
    def update_node(self, nid, **kwargs):
        sets = ', '.join(f"{k}=?" for k in kwargs)
        self._exec(f"UPDATE nodes SET {sets} WHERE id=?", (*kwargs.values(), nid))
    def delete_node(self, nid): self._exec("DELETE FROM nodes WHERE id=?", (nid,))
    def get_setting(self, key, default=''):
        r = self._conn().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r[0] if r else default
    def set_setting(self, key, value):
        self._exec("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))
    def log(self, user_id, action, detail='', ip=''):
        self._exec("INSERT INTO activity_log (user_id,action,detail,ip) VALUES (?,?,?,?)", (user_id,action,detail,ip))
    def get_activity(self, limit=20):
        return [dict(r) for r in self._conn().execute(
            "SELECT a.*, u.username FROM activity_log a LEFT JOIN users u ON a.user_id=u.id ORDER BY a.created_at DESC LIMIT ?", (limit,))]
    def get_port_forwards(self, instance_id):
        return [dict(r) for r in self._conn().execute("SELECT * FROM port_forwards WHERE instance_id=? ORDER BY id", (instance_id,))]
    def get_port_forward(self, fid):
        r = self._conn().execute("SELECT * FROM port_forwards WHERE id=?", (fid,)).fetchone()
        return dict(r) if r else None
    def add_port_forward(self, instance_id, protocol, public_port, private_port, note=""):
        cur = self._exec("INSERT INTO port_forwards (instance_id,protocol,public_port,private_port,note) VALUES (?,?,?,?,?)",
            (instance_id, protocol, public_port, private_port, note))
        return cur.lastrowid
    def delete_port_forward(self, fid): self._exec("DELETE FROM port_forwards WHERE id=?", (fid,))

db = Database(DB_FILE)

def gen_name(): return 'hp-'+''.join(random.choices(string.ascii_lowercase+string.digits,k=6))
def gen_password(length=16):
    return ''.join(random.choices(string.ascii_letters+string.digits+'!@#$%',k=length))
def find_free_port(start=10000, end=20000):
    for _ in range(200):
        p = random.randint(start,end)
        try: s=socket.socket(); s.bind(('',p)); s.close(); return p
        except OSError: pass
    return random.randint(start,end)
_lxc_list_cache={'data':[],'ts':0.0}
_LXC_CACHE_TTL=5
def lxc_list(force=False):
    now=time.time()
    if not force and now-_lxc_list_cache['ts']<_LXC_CACHE_TTL: return _lxc_list_cache['data']
    stdout,_,rc=run_lxc('list','--format','json')
    if rc!=0: return _lxc_list_cache['data']
    try:
        result=json.loads(stdout); _lxc_list_cache['data']=result; _lxc_list_cache['ts']=now; return result
    except: return _lxc_list_cache['data']
def lxc_container_stats(name):
    stdout,_,rc = run_lxc('query',f'/1.0/instances/{name}/state')
    if rc!=0: return None
    try: return json.loads(stdout)
    except: return None

def lxc_container_exists(name):
    """Return True if a container with this name exists in LXC (any state)."""
    return any(c.get('name')==name for c in lxc_list())

def setup_container_cpu_info(name):
    """Bind-mount host /proc/cpuinfo so neofetch/screenfetch can see CPU model."""
    run_lxc('config','set',name,'security.nesting','true',timeout=10)
    run_lxc('config','set',name,'raw.lxc',
            'lxc.mount.entry = /proc/cpuinfo proc/cpuinfo none bind,ro 0 0',timeout=10)
    run_lxc('restart',name,timeout=60)

def setup_container_ssh(name,ssh_pass):
    script=(
        f'echo "root:{ssh_pass}" | chpasswd 2>/dev/null || true; '
        'if command -v apt-get >/dev/null 2>&1; then '
        '  DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server >/dev/null 2>&1 || true; '
        'elif command -v apk >/dev/null 2>&1; then '
        '  apk add --no-cache openssh >/dev/null 2>&1 || true; '
        'elif command -v dnf >/dev/null 2>&1; then '
        '  dnf install -y openssh-server >/dev/null 2>&1 || true; '
        'elif command -v yum >/dev/null 2>&1; then '
        '  yum install -y openssh-server >/dev/null 2>&1 || true; '
        'fi; '
        'ssh-keygen -A >/dev/null 2>&1 || true; '
        'printf "\\nPermitRootLogin yes\\nPasswordAuthentication yes\\n" >> /etc/ssh/sshd_config 2>/dev/null || true; '
        'systemctl enable ssh sshd >/dev/null 2>&1 || true; '
        'service ssh start >/dev/null 2>&1 || service sshd start >/dev/null 2>&1 || /usr/sbin/sshd >/dev/null 2>&1 || true'
    )
    run_lxc('exec',name,'--','sh','-c',script,timeout=180)

def reprovision_instance(inst):
    """Re-create a missing LXC container from the stored instance config."""
    name=inst['name']; image=inst['os_image']; cpu=inst['cpu']; ram=inst['ram']; disk=inst.get('disk',10)
    lxc_args=['launch',image,name,'-c',f'limits.cpu={cpu}','-c',f'limits.memory={ram}MB']
    out,err,rc=run_lxc(*lxc_args,timeout=300)
    if rc!=0: return False,err
    if disk: run_lxc('config','device','set',name,'root','size',f'{disk}GB',timeout=15)
    ssh_pass=inst.get('ssh_password','')
    if ssh_pass: setup_container_ssh(name,ssh_pass)
    setup_container_cpu_info(name)
    time.sleep(2)
    for c in lxc_list():
        if c.get('name')==name:
            nets=(c.get('state') or {}).get('network',{})
            for iface,idata in nets.items():
                if iface=='lo': continue
                for addr in idata.get('addresses',[]):
                    if addr.get('family')=='inet':
                        db.update_instance(inst['id'],ip_address=addr['address']); break
    return True,''

class NodeClient:
    def __init__(self, host, port, api_key, timeout=15):
        self.base_url=f"http://{host}:{port}"; self.headers={'X-Api-Key':api_key,'Content-Type':'application/json'}; self.timeout=timeout
    def _get(self,path):
        try: r=requests.get(f"{self.base_url}{path}",headers=self.headers,timeout=self.timeout); return r.json()
        except Exception as e: return {'error':str(e)}
    def _post(self,path,data=None):
        try: r=requests.post(f"{self.base_url}{path}",headers=self.headers,json=data or {},timeout=self.timeout); return r.json()
        except Exception as e: return {'error':str(e)}
    def _delete(self,path):
        try: r=requests.delete(f"{self.base_url}{path}",headers=self.headers,timeout=self.timeout); return r.json()
        except Exception as e: return {'error':str(e)}
    def status(self): return self._get('/api/status')
    def list_instances(self): return self._get('/api/instances')
    def create(self,**kw): return self._post('/api/instances',kw)
    def start(self,name): return self._post(f'/api/instances/{name}/start')
    def stop(self,name): return self._post(f'/api/instances/{name}/stop')
    def restart(self,name): return self._post(f'/api/instances/{name}/restart')
    def delete(self,name): return self._delete(f'/api/instances/{name}')
    def reinstall(self,name,image): return self._post(f'/api/instances/{name}/reinstall',{'image':image})
    def stats(self,name): return self._get(f'/api/instances/{name}/stats')

def get_node_client(node): return NodeClient(node['host'],node['port'],node['api_key'])
def get_best_node():
    nodes=db.get_nodes(); best=None
    for n in nodes:
        if not n['active']: continue
        if n['is_main']: best=n
        else:
            try:
                info=NodeClient(n['host'],n['port'],n['api_key'],timeout=5).status()
                if 'error' not in info and best is None: best=n
            except: pass
    return best
def node_action(instance, action, **kwargs):
    node = db.get_node(instance['node_id']) if instance.get('node_id') else None
    if node and not node['is_main']:
        fn = getattr(get_node_client(node), action)
        return fn(instance['name'], **kwargs)
    if action=='start':
        if not lxc_container_exists(instance['name']):
            logger.warning(f"Container '{instance['name']}' not found in LXC — reprovisioning from stored config...")
            ok,err=reprovision_instance(instance)
            if not ok: return {'ok':False,'error':f'Container is missing and could not be reprovisioned: {err}'}
            db.update_instance(instance['id'],status='running')
            return {'ok':True,'error':''}
        _,err,rc=run_lxc('start',instance['name'])
    elif action=='stop': _,err,rc=run_lxc('stop',instance['name'],'--timeout','30')
    elif action=='restart': _,err,rc=run_lxc('restart',instance['name'])
    elif action=='delete':
        run_lxc('stop',instance['name'],'--timeout','10','--force')
        _,err,rc=run_lxc('delete',instance['name'],'--force')
    elif action=='reinstall':
        image=kwargs.get('image',instance['os_image'])
        run_lxc('stop',instance['name'],'--timeout','10','--force')
        run_lxc('delete',instance['name'],'--force')
        _,err,rc=run_lxc('launch',image,instance['name'],'-c',f"limits.cpu={instance['cpu']}",'-c',f"limits.memory={instance['ram']}MB")
        if rc==0 and instance.get('disk'): run_lxc('config','device','set',instance['name'],'root','size',f"{instance['disk']}GB",timeout=15)
        if rc==0 and instance.get('ssh_password'): setup_container_ssh(instance['name'],instance['ssh_password'])
        if rc==0: setup_container_cpu_info(instance['name'])
    elif action=='stats':
        state=lxc_container_stats(instance['name'])
        if state: return {'cpu':state.get('cpu',{}),'memory':state.get('memory',{}),'network':state.get('network',{}),'disk':state.get('disk',{})}
        return {}
    else: return {'error':f'Unknown action: {action}'}
    return {'ok':rc==0,'error':err if rc!=0 else ''}

def get_local_stats():
    cpu=psutil.cpu_percent(interval=0.5); mem=psutil.virtual_memory(); disk=psutil.disk_usage('/'); net_io=psutil.net_io_counters()
    return {'cpu_percent':cpu,'ram_used_mb':round(mem.used/1024/1024),'ram_total_mb':round(mem.total/1024/1024),
            'ram_percent':mem.percent,'disk_used_gb':round(disk.used/1024**3,1),'disk_total_gb':round(disk.total/1024**3,1),
            'disk_percent':disk.percent,'net_sent_mb':round(net_io.bytes_sent/1024/1024,1),'net_recv_mb':round(net_io.bytes_recv/1024/1024,1)}

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')
login_manager = LoginManager(app); login_manager.login_view = 'login'

@app.context_processor
def inject_globals():
    color = db.get_setting("accent_color", "#EAB308")
    _presets = {
        "#EAB308": ("#CA9B07","#FDE047"),
        "#3B82F6": ("#2563EB","#93C5FD"),
        "#8B5CF6": ("#7C3AED","#C4B5FD"),
        "#22C55E": ("#16A34A","#86EFAC"),
        "#EF4444": ("#DC2626","#FCA5A5"),
        "#06B6D4": ("#0891B2","#67E8F9"),
        "#F97316": ("#EA6C0A","#FDBA74"),
        "#EC4899": ("#DB2777","#F9A8D4"),
    }
    dark, light = _presets.get(color, ("#CA9B07","#FDE047"))
    pf_on = db.get_setting("port_forwarding_enabled","0") == "1"
    return dict(accent_color=color, accent_dark=dark, accent_light=light, pf_enabled=pf_on)

class User(UserMixin):
    def __init__(self, data):
        self.id=data['id']; self.username=data['username']; self.email=data.get('email','')
        self.role=data.get('role','user'); self.is_admin=data.get('role')=='admin'
        self.max_instances=data.get('max_instances',MAX_INSTANCES); self.banned=data.get('banned',0); self.instances=[]

@login_manager.user_loader
def load_user(uid):
    data=db.get_user_by_id(int(uid)); return User(data) if data else None

def admin_required(f):
    @wraps(f)
    def wrapper(*args,**kwargs):
        if not current_user.is_admin:
            return render_template('error.html',panel_name=PANEL_NAME,error='Access denied.',code=403),403
        return f(*args,**kwargs)
    return wrapper

def node_auth_required(f):
    @wraps(f)
    def wrapper(*args,**kwargs):
        if request.headers.get('X-Api-Key','')!=NODE_SECRET:
            return jsonify({'error':'Unauthorized'}),401
        return f(*args,**kwargs)
    return wrapper

@app.route('/')
def index():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    return render_template('index.html', panel_name=PANEL_NAME)

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    error=None
    if request.method=='POST':
        username=request.form.get('username','').strip(); password=request.form.get('password','')
        user_data=db.get_user(username)
        if user_data and check_password_hash(user_data['password'],password):
            if user_data.get('banned'): error='Your account has been suspended.'
            else:
                login_user(User(user_data),remember=True)
                db.log(user_data['id'],'login','',request.remote_addr)
                return redirect(url_for('dashboard'))
        else: error='Invalid username or password.'
    return render_template('login.html', panel_name=PANEL_NAME, error=error)

@app.route('/register', methods=['GET','POST'])
def register():
    reg_setting=db.get_setting('registration',REGISTRATION)
    if reg_setting=='disabled': return render_template('register.html',panel_name=PANEL_NAME,registration='disabled')
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    error=None
    if request.method=='POST':
        username=request.form.get('username','').strip(); email=request.form.get('email','').strip()
        password=request.form.get('password',''); confirm=request.form.get('confirm','')
        if len(username)<3: error='Username must be at least 3 characters.'
        elif not email or '@' not in email: error='A valid email address is required.'
        elif len(password)<8: error='Password must be at least 8 characters.'
        elif password!=confirm: error='Passwords do not match.'
        else:
            ok,err=db.create_user(username,email,password)
            if ok:
                user_data=db.get_user(username); login_user(User(user_data))
                db.log(user_data['id'],'register','',request.remote_addr); return redirect(url_for('dashboard'))
            else: error='Username or email already taken.'
    return render_template('register.html',panel_name=PANEL_NAME,error=error,registration=reg_setting)

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    uid=None if current_user.is_admin else current_user.id
    instances=db.get_instances(user_id=uid)
    lxc_map={}
    if BACKEND:
        for c in lxc_list(): lxc_map[c.get('name','')]=c.get('status','unknown').lower()
    for i in instances:
        live=lxc_map.get(i['name'])
        if live and live!=i['status']: db.update_instance(i['id'],status=live); i['status']=live
    return render_template('dashboard.html', panel_name=PANEL_NAME, instances=instances)

@app.route('/instances')
@login_required
def instances_list(): return redirect(url_for('dashboard'))

@app.route('/instances/create', methods=['GET','POST'])
@login_required
@admin_required
def create_instance():
    error=None; nodes=db.get_nodes(); users=db.get_all_users()
    if request.method=='POST':
        f=request.form; owner_id=int(f.get('user_id',current_user.id))
        cpu=max(1,min(64,int(f.get('cpu',1)))); ram=max(128,min(131072,int(f.get('ram',1024))))
        disk=max(5,min(2000,int(f.get('disk',20))))
        custom_img=f.get('custom_image','').strip()
        image=custom_img if custom_img else f.get('os_image',DEFAULT_IMAGES[0])
        vtype=f.get('vtype','lxc'); name=f.get('name','').strip() or gen_name()
        node_id=int(f.get('node_id',0)) or None
        expires_raw=f.get('expires_at','').strip(); expires_at=None
        if expires_raw:
            try: expires_at=datetime.strptime(expires_raw,'%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')
            except: pass
        user_data=db.get_user_by_id(owner_id)
        if not user_data: error='Invalid user.'
        elif not name.replace('-','').replace('_','').isalnum(): error='Name must contain only letters, numbers, hyphens.'
        else:
            iid=str(uuid.uuid4())[:8]; ssh_port=find_free_port(); ssh_pass=gen_password()
            node=db.get_node(node_id) if node_id else get_best_node()
            is_main=not node or node.get('is_main',1); real_node_id=node['id'] if node else None
            db.create_instance(iid,owner_id,real_node_id,name,image,vtype,cpu,ram,disk,ssh_port,ssh_pass,expires_at)
            db.log(current_user.id,'create_instance',name,request.remote_addr)
            def provision():
                if is_main:
                    if BACKEND:
                        lxc_args=['launch',image,name,'-c',f"limits.cpu={cpu}",'-c',f"limits.memory={ram}MB"]
                        _,err,rc=run_lxc(*lxc_args,timeout=300)
                        if rc==0 and disk: run_lxc('config','device','set',name,'root','size',f'{disk}GB',timeout=15)
                        status='running' if rc==0 else 'error'
                        if rc==0:
                            setup_container_ssh(name,ssh_pass)
                            setup_container_cpu_info(name)
                            time.sleep(3)
                            for c in lxc_list(force=True):
                                if c.get('name')==name:
                                    nets=(c.get('state') or {}).get('network',{})
                                    for iface,idata in nets.items():
                                        if iface=='lo': continue
                                        for addr in idata.get('addresses',[]):
                                            if addr.get('family')=='inet':
                                                db.update_instance(iid,ip_address=addr['address']); break
                    else: time.sleep(2); status='stopped'
                else:
                    res=get_node_client(node).create(name=name,image=image,cpu=cpu,ram=ram,disk=disk,ssh_port=ssh_port,ssh_password=ssh_pass)
                    status='running' if not res.get('error') else 'error'
                db.update_instance(iid,status=status)
            threading.Thread(target=provision,daemon=True).start()
            flash(f'Instance "{name}" is being provisioned.','success'); return redirect(url_for('dashboard'))
    return render_template('create_instance.html',panel_name=PANEL_NAME,error=error,images=DEFAULT_IMAGES,nodes=nodes,users=users)

@app.route('/instances/<iid>')
@login_required
def instance_detail(iid):
    inst=db.get_instance(iid)
    if not inst: return render_template('error.html',panel_name=PANEL_NAME,error='Instance not found.',code=404),404
    if not current_user.is_admin and inst['user_id']!=current_user.id:
        return render_template('error.html',panel_name=PANEL_NAME,error='Access denied.',code=403),403
    node=db.get_node(inst['node_id']) if inst.get('node_id') else None
    pf_list=db.get_port_forwards(iid) if db.get_setting("port_forwarding_enabled","0")=="1" else []
    return render_template('instance_detail.html',panel_name=PANEL_NAME,inst=inst,node=node,images=DEFAULT_IMAGES,port_forwards=pf_list)

@app.route('/instances/<iid>/<action>', methods=['POST'])
@login_required
def instance_action(iid, action):
    inst=db.get_instance(iid)
    if not inst:
        if request.is_json: return jsonify({'error':'Not found'}),404
        flash('Instance not found.','error'); return redirect(url_for('dashboard'))
    if not current_user.is_admin and inst['user_id']!=current_user.id:
        if request.is_json: return jsonify({'error':'Access denied'}),403
        flash('Access denied.','error'); return redirect(url_for('dashboard'))
    if inst.get('suspended') and action not in ('delete',):
        if request.is_json: return jsonify({'error':'Instance is suspended.'})
        flash('Instance is suspended.','error'); return redirect(url_for('instance_detail',iid=iid))
    if action=='delete':
        node_action(inst,'delete'); db.delete_instance(iid)
        db.log(current_user.id,'delete_instance',inst['name'],request.remote_addr)
        if request.is_json: return jsonify({'ok':True,'redirect':url_for('dashboard')})
        flash(f'Instance "{inst["name"]}" deleted.','success'); return redirect(url_for('dashboard'))
    if action=='reinstall':
        image=request.json.get('image',inst['os_image']) if request.is_json else request.form.get('image',inst['os_image'])
        res=node_action(inst,'reinstall',image=image)
        if res.get('ok'): db.update_instance(iid,os_image=image,status='running')
    else:
        res=node_action(inst,action); status_map={'start':'running','stop':'stopped','restart':'running'}
        if not res.get('error'): db.update_instance(iid,status=status_map.get(action,inst['status']))
    db.log(current_user.id,f'{action}_instance',inst['name'],request.remote_addr)
    if request.is_json: return jsonify(res)
    flash(f'Action "{action}" performed on {inst["name"]}.','success'); return redirect(url_for('instance_detail',iid=iid))

@app.route('/instances/<iid>/console')
@login_required
def console(iid):
    inst=db.get_instance(iid)
    if not inst: return render_template('error.html',panel_name=PANEL_NAME,error='Instance not found.',code=404),404
    if not current_user.is_admin and inst['user_id']!=current_user.id:
        return render_template('error.html',panel_name=PANEL_NAME,error='Access denied.',code=403),403
    return render_template('console.html',panel_name=PANEL_NAME,inst=inst)

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    error=success=None
    if request.method=='POST':
        cur_pw=request.form.get('current_password',''); new_pw=request.form.get('new_password',''); conf_pw=request.form.get('confirm_password','')
        user_data=db.get_user_by_id(current_user.id)
        if not check_password_hash(user_data['password'],cur_pw): error='Current password is incorrect.'
        elif len(new_pw)<8: error='New password must be at least 8 characters.'
        elif new_pw!=conf_pw: error='Passwords do not match.'
        else: db.update_user(current_user.id,password=generate_password_hash(new_pw)); flash('Password changed successfully.','success')
    instances=db.get_instances(user_id=current_user.id)
    return render_template('profile.html',panel_name=PANEL_NAME,error=error,success=success,instances=instances)

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    stats=get_local_stats(); activity=db.get_activity(20); users=db.get_all_users()
    instances=db.get_instances(); nodes=db.get_nodes()
    running=sum(1 for i in instances if i['status']=='running'); stopped=sum(1 for i in instances if i['status']!='running')
    return render_template('admin/dashboard.html',panel_name=PANEL_NAME,stats=stats,activity=activity,
        total_users=len(users),total_instances=len(instances),running_instances=running,stopped_instances=stopped,
        total_nodes=len(nodes),instances=instances[:10])

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users=db.get_all_users()
    for u in users: u['instance_count']=db.count_user_instances(u['id'])
    return render_template('admin/users.html',panel_name=PANEL_NAME,users=users)

@app.route('/admin/users/create', methods=['POST'])
@login_required
@admin_required
def admin_create_user():
    username=request.form.get('username','').strip(); email=request.form.get('email','').strip()
    password=request.form.get('password',''); role=request.form.get('role','user')
    ok,err=db.create_user(username,email,password,role)
    flash(f'User "{username}" created.' if ok else f'Error: {err}', 'success' if ok else 'error')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/action', methods=['POST'])
@login_required
@admin_required
def admin_user_action(uid):
    action=request.form.get('action')
    if uid==current_user.id: flash('Cannot modify your own account here.','error'); return redirect(url_for('admin_users'))
    msgs={'ban':('User banned.','banned',1),'unban':('User unbanned.','banned',0),'make_admin':('User promoted to admin.','role','admin'),'remove_admin':('Admin role removed.','role','user'),'delete':('User deleted.',None,None)}
    if action=='delete': db.delete_user(uid)
    elif action=='set_limit': db.update_user(uid,max_instances=int(request.form.get('max_instances',MAX_INSTANCES)))
    elif action in msgs:
        m,k,v=msgs[action]
        if k: db.update_user(uid,**{k:v})
    if action=='set_limit': flash('Instance limit updated.','success')
    elif action in msgs: flash(msgs[action][0],'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/instances')
@login_required
@admin_required
def admin_instances():
    return render_template('admin/instances.html',panel_name=PANEL_NAME,instances=db.get_instances())

@app.route('/admin/instances/<iid>/suspend', methods=['POST'])
@login_required
@admin_required
def admin_suspend(iid):
    inst=db.get_instance(iid)
    if inst: node_action(inst,'stop'); db.update_instance(iid,suspended=1,status='stopped'); flash(f'Instance {inst["name"]} suspended.','success')
    return redirect(url_for('admin_instances'))

@app.route('/admin/instances/<iid>/unsuspend', methods=['POST'])
@login_required
@admin_required
def admin_unsuspend(iid):
    db.update_instance(iid,suspended=0); flash('Instance unsuspended.','success'); return redirect(url_for('admin_instances'))

@app.route('/admin/nodes')
@login_required
@admin_required
def admin_nodes():
    nodes=db.get_nodes(); node_stats={}
    for n in nodes:
        if n['is_main']: node_stats[n['id']]=get_local_stats(); node_stats[n['id']]['online']=True
        else:
            try:
                s=NodeClient(n['host'],n['port'],n['api_key'],timeout=5).status()
                node_stats[n['id']]=s; node_stats[n['id']]['online']='error' not in s
            except: node_stats[n['id']]={'online':False}
    return render_template('admin/nodes.html',panel_name=PANEL_NAME,nodes=nodes,node_stats=node_stats,node_secret=NODE_SECRET)

@app.route('/admin/nodes/add', methods=['POST'])
@login_required
@admin_required
def admin_add_node():
    name=request.form.get('name','').strip(); host=request.form.get('host','').strip()
    port=int(request.form.get('port',4567)); api_key=request.form.get('api_key','').strip()
    location=request.form.get('location','Unknown')
    if not name or not host or not api_key: flash('Name, host, and API key are required.','error'); return redirect(url_for('admin_nodes'))
    db.add_node(name=name,host=host,port=port,api_key=api_key,location=location,is_main=0,active=1)
    flash(f'Node "{name}" added.','success'); return redirect(url_for('admin_nodes'))

@app.route('/admin/nodes/<int:nid>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_node(nid):
    node=db.get_node(nid)
    if node and not node['is_main']: db.delete_node(nid); flash('Node removed.','success')
    else: flash('Cannot remove main node.','error')
    return redirect(url_for('admin_nodes'))

@app.route('/admin/nodes/<int:nid>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_node(nid):
    node=db.get_node(nid)
    if node: db.update_node(nid,active=0 if node['active'] else 1)
    return redirect(url_for('admin_nodes'))

@app.route('/admin/settings', methods=['GET','POST'])
@login_required
@admin_required
def admin_settings():
    if request.method=='POST':
        for key in ('panel_name','registration','max_instances','welcome_msg','accent_color','port_forwarding_enabled'):
            val=request.form.get(key)
            if val is not None: db.set_setting(key,val)
        flash('Settings saved.','success')
    settings={
        'panel_name':db.get_setting('panel_name',PANEL_NAME),
        'registration':db.get_setting('registration',REGISTRATION),
        'max_instances':db.get_setting('max_instances',str(MAX_INSTANCES)),
        'welcome_msg':db.get_setting('welcome_msg',f'Welcome to {PANEL_NAME}'),
        'accent_color':db.get_setting('accent_color','#EAB308'),
        'port_forwarding_enabled':db.get_setting('port_forwarding_enabled','0'),
    }
    return render_template('admin/settings.html',panel_name=PANEL_NAME,settings=settings)

@app.route('/api/stats/system')
@login_required
def api_stats_system():
    if not current_user.is_admin: return jsonify({'error':'Admin only'}),403
    return jsonify(get_local_stats())

def apply_port_forward(container_ip, protocol, public_port, private_port, add=True):
    action = "-A" if add else "-D"
    try:
        subprocess.run(["iptables","-t","nat",action,"PREROUTING","-p",protocol,
            "--dport",str(public_port),"-j","DNAT","--to-destination",f"{container_ip}:{private_port}"],
            capture_output=True, timeout=5)
        if add:
            subprocess.run(["iptables",action,"FORWARD","-p",protocol,"-d",container_ip,
                "--dport",str(private_port),"-j","ACCEPT"], capture_output=True, timeout=5)
        else:
            subprocess.run(["iptables","-D","FORWARD","-p",protocol,"-d",container_ip,
                "--dport",str(private_port),"-j","ACCEPT"], capture_output=True, timeout=5)
        return True
    except Exception as e: logger.error(f"iptables error: {e}"); return False

@app.route('/instances/<iid>/port-forwards/add', methods=['POST'])
@login_required
def pf_add(iid):
    if db.get_setting("port_forwarding_enabled","0") != "1":
        return jsonify({"error":"Port forwarding is disabled by administrator"}),403
    inst=db.get_instance(iid)
    if not inst: return jsonify({"error":"Not found"}),404
    if not current_user.is_admin and inst["user_id"]!=current_user.id:
        return jsonify({"error":"Access denied"}),403
    data=request.json or {}
    proto=data.get("protocol","tcp")
    if proto not in ("tcp","udp"): proto="tcp"
    try: pub=int(data.get("public_port",0)); priv=int(data.get("private_port",0))
    except: return jsonify({"error":"Invalid port numbers"}),400
    if not 1<=pub<=65535 or not 1<=priv<=65535:
        return jsonify({"error":"Ports must be between 1 and 65535"}),400
    note=str(data.get("note",""))[:64]
    container_ip=inst.get("ip_address","")
    if not container_ip: return jsonify({"error":"Container has no IP yet — start it first"}),400
    fid=db.add_port_forward(iid,proto,pub,priv,note)
    apply_port_forward(container_ip,proto,pub,priv,add=True)
    db.log(current_user.id,"pf_add",f"{pub}->{container_ip}:{priv} ({proto})","")
    return jsonify({"ok":True,"id":fid,"public_port":pub,"private_port":priv,"protocol":proto,"note":note})

@app.route('/instances/<iid>/port-forwards/<int:fid>/delete', methods=['POST'])
@login_required
def pf_delete(iid, fid):
    inst=db.get_instance(iid)
    if not inst: return jsonify({"error":"Not found"}),404
    if not current_user.is_admin and inst["user_id"]!=current_user.id:
        return jsonify({"error":"Access denied"}),403
    pf=db.get_port_forward(fid)
    if pf:
        container_ip=inst.get("ip_address","")
        if container_ip: apply_port_forward(container_ip,pf["protocol"],pf["public_port"],pf["private_port"],add=False)
        db.delete_port_forward(fid)
        db.log(current_user.id,"pf_delete",f"port {pf['public_port']}","")
    return jsonify({"ok":True})

@app.route('/api/stats/instance/<iid>')
@login_required
def api_stats_instance(iid):
    inst=db.get_instance(iid)
    if not inst: return jsonify({'error':'Not found'}),404
    if not current_user.is_admin and inst['user_id']!=current_user.id: return jsonify({'error':'Access denied'}),403
    if inst.get('status')!='running':
        return jsonify({'cpu_percent':0,'ram_used_mb':0,'ram_total_mb':inst['ram'],'ram_percent':0,'net_in_mb':0,'net_out_mb':0})
    if BACKEND and (not inst.get('node_id') or db.get_node(inst['node_id']).get('is_main')):
        state=lxc_container_stats(inst['name'])
        if state:
            cpu_pct=state.get('cpu',{}).get('usage',0)/1e9/psutil.cpu_count() if state.get('cpu') else 0
            mem=state.get('memory',{}); ram_used=round(mem.get('usage',0)/1024/1024); ram_total=inst['ram']
            ram_pct=(ram_used/ram_total*100) if ram_total else 0
            net=state.get('network',{}); net_in=net_out=0
            for iface,nd in net.items():
                if iface!='lo': net_in+=nd.get('counters',{}).get('bytes_received',0); net_out+=nd.get('counters',{}).get('bytes_sent',0)
            disk_data=state.get('disk',{}); disk_used_bytes=0
            for dev,dinfo in disk_data.items():
                if isinstance(dinfo,dict): disk_used_bytes+=dinfo.get('usage',0)
            disk_total_mb=inst['disk']*1024; disk_used_mb=round(disk_used_bytes/1024/1024)
            disk_pct=round(disk_used_mb/disk_total_mb*100,1) if disk_total_mb else 0
            return jsonify({'cpu_percent':round(cpu_pct,1),'ram_used_mb':ram_used,'ram_total_mb':ram_total,
                'ram_percent':round(ram_pct,1),'net_in_mb':round(net_in/1024/1024,2),'net_out_mb':round(net_out/1024/1024,2),
                'disk_used_mb':disk_used_mb,'disk_total_mb':disk_total_mb,'disk_percent':disk_pct,'status':inst['status']})
    import random as _r
    return jsonify({'cpu_percent':round(_r.uniform(1,35),1),'ram_used_mb':_r.randint(50,inst['ram']),'ram_total_mb':inst['ram'],
        'ram_percent':round(_r.uniform(5,70),1),'net_in_mb':round(_r.uniform(0,5),2),'net_out_mb':round(_r.uniform(0,2),2),
        'disk_used_mb':_r.randint(0,inst['disk']*512),'disk_total_mb':inst['disk']*1024,'disk_percent':round(_r.uniform(0,60),1),'status':inst['status']})

@app.route('/api/node/register', methods=['POST'])
@node_auth_required
def node_register():
    data=request.json or {}
    name=data.get('name','Unknown')
    host=data.get('host',request.remote_addr)
    port=int(data.get('port',4567))
    api_key=data.get('api_key','') or NODE_SECRET
    location=data.get('location','Unknown')
    # Upsert: if a node with this api_key already exists, update it instead of
    # creating a duplicate (handles agent restarts and IP changes gracefully)
    existing=next((n for n in db.get_nodes() if not n['is_main'] and n['api_key']==api_key),None)
    if existing:
        db.update_node(existing['id'],name=name,host=host,port=port,location=location,active=1)
        nid=existing['id']
        logger.info(f"Node re-registered: '{name}' @ {host}:{port} (id={nid})")
    else:
        nid=db.add_node(name=name,host=host,port=port,api_key=api_key,location=location,is_main=0,active=1)
        logger.info(f"New node registered: '{name}' @ {host}:{port} (id={nid})")
    return jsonify({'ok':True,'node_id':nid})

ssh_sessions={}
lxc_exec_sessions={}

@socketio.on('connect',namespace='/console')
def console_connect():
    if not current_user.is_authenticated: return False

@socketio.on('start_ssh',namespace='/console')
def start_ssh(data):
    iid=data.get('iid')
    if not iid: return
    inst=db.get_instance(iid)
    if not inst or (not current_user.is_admin and inst['user_id']!=current_user.id):
        emit('error',{'msg':'Access denied'},namespace='/console'); return
    if inst.get('status')!='running':
        emit('error',{'msg':'Instance is not running.'},namespace='/console'); return
    if not BACKEND:
        emit('error',{'msg':'No LXC backend (demo mode).'},namespace='/console'); return
    sid=request.sid
    if sid in ssh_sessions:
        try: ssh_sessions[sid].close()
        except: pass
    # Try SSH first
    chan=None; ssh=None
    try:
        _ssh=paramiko.SSHClient(); _ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        host=inst.get('ip_address') or ''; port=inst.get('ssh_port') or 22; password=inst.get('ssh_password','')
        if host:
            _ssh.connect(host,port=port,username='root',password=password,timeout=8)
            chan=_ssh.invoke_shell(term='xterm',width=220,height=50); ssh=_ssh
    except: pass
    if chan and ssh:
        ssh_sessions[sid]=ssh
        def forward_ssh_output():
            try:
                while not chan.closed:
                    if chan.recv_ready():
                        out=chan.recv(4096).decode('utf-8',errors='replace')
                        socketio.emit('output',{'data':out},namespace='/console',room=sid)
                    else: time.sleep(0.02)
            except: pass
            finally: socketio.emit('output',{'data':'\r\n[disconnected]\r\n'},namespace='/console',room=sid)
        emit('connected',{'msg':'SSH session ready'},namespace='/console')
        threading.Thread(target=forward_ssh_output,daemon=True).start()
        return
    # Fallback: lxc exec with PTY
    try:
        import pty as _pty
        master_fd,slave_fd=_pty.openpty()
        proc=subprocess.Popen([BACKEND,'exec',inst['name'],'--','bash','-l'],
            stdin=slave_fd,stdout=slave_fd,stderr=slave_fd,close_fds=True)
        os.close(slave_fd); lxc_exec_sessions[sid]=(proc,master_fd)
        emit('connected',{'msg':'Console session ready'},namespace='/console')
        def forward_lxc_output():
            try:
                while proc.poll() is None:
                    rlist,_,_=select.select([master_fd],[],[],0.05)
                    if rlist:
                        try:
                            out=os.read(master_fd,4096).decode('utf-8',errors='replace')
                            socketio.emit('output',{'data':out},namespace='/console',room=sid)
                        except OSError: break
            except: pass
            finally: socketio.emit('output',{'data':'\r\n[disconnected]\r\n'},namespace='/console',room=sid)
        threading.Thread(target=forward_lxc_output,daemon=True).start()
    except Exception as ex: emit('error',{'msg':f'Could not connect to instance: {ex}'},namespace='/console')

@socketio.on('input',namespace='/console')
def console_input(data):
    sid=request.sid; payload=data.get('data','')
    ssh=ssh_sessions.get(sid)
    if ssh:
        try:
            t=ssh.get_transport()
            if t and t.is_active():
                for chan in t._channels.values():
                    if not chan.closed: chan.send(payload); break
        except: pass
        return
    lxc_sess=lxc_exec_sessions.get(sid)
    if lxc_sess:
        proc,master_fd=lxc_sess
        try: os.write(master_fd,payload.encode('utf-8',errors='replace'))
        except: pass

@socketio.on('resize',namespace='/console')
def console_resize(data):
    sid=request.sid; cols=data.get('cols',80); rows=data.get('rows',24)
    ssh=ssh_sessions.get(sid)
    if ssh:
        try:
            t=ssh.get_transport()
            if t:
                for chan in t._channels.values():
                    if not chan.closed: chan.resize_pty(width=cols,height=rows); break
        except: pass
        return
    lxc_sess=lxc_exec_sessions.get(sid)
    if lxc_sess:
        _,master_fd=lxc_sess
        try:
            import termios as _termios
            fcntl.ioctl(master_fd,_termios.TIOCSWINSZ,struct.pack('HHHH',rows,cols,0,0))
        except: pass

@socketio.on('disconnect',namespace='/console')
def console_disconnect():
    sid=request.sid
    ssh=ssh_sessions.pop(sid,None)
    if ssh:
        try: ssh.close()
        except: pass
    lxc_sess=lxc_exec_sessions.pop(sid,None)
    if lxc_sess:
        proc,master_fd=lxc_sess
        try: proc.terminate()
        except: pass
        try: os.close(master_fd)
        except: pass

def broadcast_stats():
    while True:
        try:
            now=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            for inst in db.get_instances():
                exp=inst.get('expires_at')
                if exp and exp<=now and inst['status'] not in ('stopped','deleted','suspended'):
                    logger.info(f"Instance {inst['name']} expired — stopping")
                    try: node_action(inst,'stop')
                    except: pass
                    db.update_instance(inst['id'],status='stopped')
                    db.log(0,'auto_expire',inst['name'],'')
        except Exception as e: logger.error(f"broadcast_stats: {e}")
        time.sleep(30)

@app.errorhandler(404)
def not_found(e): return render_template('error.html',panel_name=PANEL_NAME,error='Page not found.',code=404),404
@app.errorhandler(500)
def server_error(e): return render_template('error.html',panel_name=PANEL_NAME,error='Internal server error.',code=500),500

if __name__=='__main__':
    if not db.get_main_node():
        db.add_node(name='Main Node',host='127.0.0.1',port=PANEL_PORT,api_key=NODE_SECRET,location='Local',is_main=1,active=1)
    threading.Thread(target=broadcast_stats,daemon=True).start()
    print(f"""
\033[1;33m╔══════════════════════════════════════════════════════╗
║              HyperPanel  Starting...                  ║
╚══════════════════════════════════════════════════════╝\033[0m
  Panel Name : {PANEL_NAME}
  URL        : http://{PANEL_HOST}:{PANEL_PORT}
  Admin      : {ADMIN_USERNAME}
  LXC Backend: {BACKEND or 'NOT FOUND (demo mode)'}
  DB         : {DB_FILE}
""")
    socketio.run(app,host=PANEL_HOST,port=PANEL_PORT,debug=False,use_reloader=False,allow_unsafe_werkzeug=True)
ENDPANEL

# ═════════════════════════════════════════════════════════════════════════════
# Admin credentials prompt
# ═════════════════════════════════════════════════════════════════════════════
title "Admin account setup"
echo -e "  ${WHT}Please enter your admin credentials for HyperPanel.${NC}"
echo ""

# Username
while true; do
  read -rp "  Admin username [admin]: " ADMIN_USERNAME
  ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
  if [[ "${ADMIN_USERNAME}" =~ ^[a-zA-Z0-9_-]{3,32}$ ]]; then
    break
  fi
  echo -e "  ${RED}✗${NC}  Username must be 3–32 characters (letters, digits, _ or -)."
done

# Email
while true; do
  read -rp "  Admin email [admin@hyperpanel.local]: " ADMIN_EMAIL
  ADMIN_EMAIL="${ADMIN_EMAIL:-admin@hyperpanel.local}"
  if [[ "${ADMIN_EMAIL}" =~ ^[^@]+@[^@]+\.[^@]+$ ]]; then
    break
  fi
  echo -e "  ${RED}✗${NC}  Please enter a valid email address."
done

# Password (with confirmation, hidden input)
while true; do
  read -rsp "  Admin password (min 8 chars): " ADMIN_PASS
  echo ""
  if [ "${#ADMIN_PASS}" -lt 8 ]; then
    echo -e "  ${RED}✗${NC}  Password must be at least 8 characters."
    continue
  fi
  read -rsp "  Confirm password: " ADMIN_PASS_CONFIRM
  echo ""
  if [ "${ADMIN_PASS}" = "${ADMIN_PASS_CONFIRM}" ]; then
    break
  fi
  echo -e "  ${RED}✗${NC}  Passwords do not match. Try again."
done

ok "Admin credentials set for '${ADMIN_USERNAME}'"

# ═════════════════════════════════════════════════════════════════════════════
# FILE: .env
# ═════════════════════════════════════════════════════════════════════════════
title "Generating secrets & .env"
SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
NSECRET=$(python3 -c "import secrets; print(secrets.token_hex(24))")

cat > "$D/.env" << ENDENV
SECRET_KEY=${SECRET}
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASS}
ADMIN_EMAIL=${ADMIN_EMAIL}
PANEL_NAME=HyperPanel
PANEL_HOST=0.0.0.0
PANEL_PORT=5000
NODE_SECRET=${NSECRET}
LXC_BACKEND=${LXC_BACKEND}
DB_FILE=hyperpanel.db
REGISTRATION=open
MAX_INSTANCES_PER_USER=3
DEFAULT_IMAGES=ubuntu:22.04,ubuntu:20.04,debian:12,almalinux:9,alpine:3.19
ENDENV
ok ".env created"

# ── Python venv ───────────────────────────────────────────────────────────────
title "Python virtual environment"
cd "$D"
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
ok "Python packages installed"

# ── Systemd service ───────────────────────────────────────────────────────────
title "Systemd service"
cat > /etc/systemd/system/hyperpanel.service << ENDSVC
[Unit]
Description=HyperPanel VPS Management Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${D}
ExecStart=${D}/venv/bin/python panel.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
ENDSVC

systemctl daemon-reload
systemctl enable hyperpanel
ok "Service enabled"

# ── Firewall ──────────────────────────────────────────────────────────────────
if command -v ufw &>/dev/null; then
  ufw allow 5000/tcp >/dev/null 2>&1 || true; info "UFW: port 5000 opened"
fi

# ── Start ─────────────────────────────────────────────────────────────────────
title "Starting HyperPanel"
systemctl start hyperpanel
sleep 2
if systemctl is-active --quiet hyperpanel; then
  ok "HyperPanel is running!"
else
  echo -e "  ${RED}Panel failed to start — check logs:${NC}"
  echo "  journalctl -u hyperpanel -n 40 --no-pager"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "YOUR_IP")
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")

echo ""
echo -e "${WHT}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${WHT}║                  Installation Complete!                   ║${NC}"
echo -e "${WHT}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${WHT}┌─ Admin Credentials ─────────────────────────────────────┐${NC}"
echo -e "  ${WHT}│${NC}  Username : ${GRN}${ADMIN_USERNAME}${NC}"
echo -e "  ${WHT}│${NC}  Email    : ${GRN}${ADMIN_EMAIL}${NC}"
echo -e "  ${WHT}│${NC}  Password : ${GRN}(as entered during setup)${NC}"
echo -e "  ${WHT}└─────────────────────────────────────────────────────────┘${NC}"
echo ""
echo -e "  ${WHT}Access your panel:${NC}"
echo -e "     ${GRN}http://${LOCAL_IP}:5000${NC}"
[ -n "$TAILSCALE_IP" ] && echo -e "     ${GRN}http://${TAILSCALE_IP}:5000${NC}  (Tailscale)"
echo ""
echo -e "  ${WHT}Commands:${NC}"
echo -e "  ├── Logs    :  ${YEL}journalctl -u hyperpanel -f${NC}"
echo -e "  ├── Restart :  ${YEL}systemctl restart hyperpanel${NC}"
echo -e "  └── Config  :  ${YEL}nano ${D}/.env${NC}"
echo ""
