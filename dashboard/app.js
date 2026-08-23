/* aiZee Dashboard app - served externally so CSP can drop 'unsafe-inline'. */
'use strict';

function $(id) { return document.getElementById(id); }

// Escape HTML to prevent XSS when rendering dynamic content.
function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

// Navigation
function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-menu a').forEach(el => el.classList.remove('active'));

  document.getElementById(`${tabId}-tab`).classList.add('active');
  document.querySelector(`a[href="#${tabId}"]`).classList.add('active');

  const titles = {
    'overview': 'Overview',
    'memory': 'Memory Explorer',
    'policy': 'Policy Sandbox',
    'workflows': 'Workflows',
    'saga': 'Sagas',
    'chat': 'Chat',
    'stack': 'Tech Stack',
    'telemetry': 'Telemetry',
    'system': 'System Health',
    'audit': 'Audit Logs'
  };
  document.getElementById('page-title').textContent = titles[tabId];

  if (tabId === 'audit') loadAudit();
  if (tabId === 'workflows') loadWorkflows();
  if (tabId === 'stack') loadStack();
  if (tabId === 'telemetry') loadTelemetry();
  if (tabId === 'system') loadSystem();
}

// Theme toggle
function toggleTheme() {
  document.body.classList.toggle('light');
  localStorage.setItem('theme', document.body.classList.contains('light') ? 'light' : 'dark');
}
if (localStorage.getItem('theme') === 'light') document.body.classList.add('light');

// Command Palette
const COMMANDS = [
  { id: 'tab-overview', label: 'Overview', section: 'Navigation', run: () => switchTab('overview'), shortcut: 'O' },
  { id: 'tab-memory', label: 'Memory Explorer', section: 'Navigation', run: () => switchTab('memory'), shortcut: 'M' },
  { id: 'tab-policy', label: 'Policy Sandbox', section: 'Navigation', run: () => switchTab('policy'), shortcut: 'P' },
  { id: 'tab-workflows', label: 'Workflows', section: 'Navigation', run: () => { switchTab('workflows'); loadWorkflows(); }, shortcut: 'W' },
  { id: 'tab-saga', label: 'Sagas', section: 'Navigation', run: () => switchTab('saga'), shortcut: 'S' },
  { id: 'tab-chat', label: 'Chat', section: 'Navigation', run: () => switchTab('chat'), shortcut: 'C' },
  { id: 'tab-stack', label: 'Tech Stack', section: 'Navigation', run: () => { switchTab('stack'); loadStack(); }, shortcut: 'T' },
  { id: 'tab-telemetry', label: 'Telemetry', section: 'Navigation', run: () => { switchTab('telemetry'); loadTelemetry(); }, shortcut: 'E' },
  { id: 'tab-system', label: 'System Health', section: 'Navigation', run: () => { switchTab('system'); loadSystem(); }, shortcut: 'H' },
  { id: 'tab-audit', label: 'Audit Logs', section: 'Navigation', run: () => { switchTab('audit'); loadAudit(); }, shortcut: 'A' },
  { id: 'action-refresh', label: 'Refresh status', section: 'Actions', run: () => loadStatus(), shortcut: 'R' },
  { id: 'action-theme', label: 'Toggle theme', section: 'Actions', run: () => toggleTheme(), shortcut: 'L' },
];

let selectedCommand = 0;
let filteredCommands = [];

function openCommandPalette() {
  const overlay = document.getElementById('command-palette');
  const input = document.getElementById('command-input');
  overlay.classList.add('open');
  input.value = '';
  input.focus();
  selectedCommand = 0;
  filterCommands();
}

function closeCommandPalette() {
  document.getElementById('command-palette').classList.remove('open');
}

function filterCommands() {
  const q = document.getElementById('command-input').value.toLowerCase().trim();
  filteredCommands = q
    ? COMMANDS.filter(c => c.label.toLowerCase().includes(q) || c.section.toLowerCase().includes(q))
    : COMMANDS.slice();
  selectedCommand = Math.min(selectedCommand, Math.max(0, filteredCommands.length - 1));
  renderCommandList();
}

function renderCommandList() {
  const container = document.getElementById('command-list');
  if (filteredCommands.length === 0) {
    container.innerHTML = '<div class="command-section-title">No matching commands</div>';
    return;
  }
  const sections = {};
  filteredCommands.forEach((c, i) => {
    if (!sections[c.section]) sections[c.section] = [];
    sections[c.section].push({ ...c, index: i });
  });
  container.innerHTML = Object.entries(sections).map(([section, items]) => `
    <div class="command-section-title">${section}</div>
    ${items.map(item => `
      <div class="command-item ${item.index === selectedCommand ? 'selected' : ''}" data-index="${item.index}">
        <span>${item.label}</span>
        <span class="cmd-shortcut">${item.shortcut}</span>
      </div>
    `).join('')}
  `).join('');
}

function handleCommandKey(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    selectedCommand = (selectedCommand + 1) % filteredCommands.length;
    renderCommandList();
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    selectedCommand = (selectedCommand - 1 + filteredCommands.length) % filteredCommands.length;
    renderCommandList();
  } else if (e.key === 'Enter') {
    e.preventDefault();
    executeCommand(selectedCommand);
  } else if (e.key === 'Escape') {
    closeCommandPalette();
  }
}

function executeCommand(index) {
  const cmd = filteredCommands[index];
  if (!cmd) return;
  closeCommandPalette();
  cmd.run();
}

document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    openCommandPalette();
  } else if (e.key === 'Escape') {
    closeCommandPalette();
  }
});

// API Helpers
function getToken() {
  return sessionStorage.getItem('aizee-token') || '';
}

async function fetchJson(path, options = {}) {
  options.headers = Object.assign({}, options.headers, {
    'X-Requested-With': 'AIOS-Dashboard',
    'Authorization': 'Bearer ' + getToken(),
  });
  try {
    const res = await fetch(path, options);
    if (res.status === 401 && !options._retriedAuth) {
      const entered = window.prompt('Dashboard authentication required.\nEnter your dashboard token:');
      if (entered && entered.trim()) {
        sessionStorage.setItem('aizee-token', entered.trim());
        return fetchJson(path, Object.assign({}, options, { _retriedAuth: true }));
      }
    }
    if (!res.ok) throw new Error(res.status + ' ' + res.statusText);
    return await res.json();
  } catch (e) {
    return { error: e.message };
  }
}

function setStatus(ok, msg) {
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  dot.className = 'dot ' + (ok ? 'online' : 'offline');
  text.textContent = msg;
}

// Load Overview Status
async function loadStatus() {
  const data = await fetchJson('/api/status');
  if (data.error) {
    setStatus(false, 'Disconnected');
    document.getElementById('workflow-pill').textContent = 'Offline';
    document.getElementById('workflow-pill').className = 'status-pill danger';
    return;
  }
  setStatus(true, 'Connected');
  document.getElementById('version-badge').textContent = 'v' + data.version;
  document.getElementById('workflow-count').textContent = data.workflows.length;
  document.getElementById('rule-count').textContent = data.rules.length;
  document.getElementById('budget-count').textContent = data.budgets.length;
  document.getElementById('stack-count').textContent = Object.keys(data.tech_stack || {}).length;

  document.getElementById('workflow-pill').textContent = data.workflows.length > 0 ? 'Live' : 'Idle';
  document.getElementById('workflow-pill').className = 'status-pill ' + (data.workflows.length > 0 ? 'info' : 'warning');
  document.getElementById('rule-pill').textContent = data.rules.length > 0 ? 'Synced' : 'Empty';
  document.getElementById('rule-pill').className = 'status-pill ' + (data.rules.length > 0 ? 'success' : 'warning');
  document.getElementById('budget-pill').textContent = data.budgets.length > 0 ? 'Active' : 'No limits';
  document.getElementById('budget-pill').className = 'status-pill ' + (data.budgets.length > 0 ? 'warning' : 'danger');
  document.getElementById('stack-pill').textContent = Object.keys(data.tech_stack || {}).length > 0 ? 'Detected' : 'None';
  document.getElementById('stack-pill').className = 'status-pill ' + (Object.keys(data.tech_stack || {}).length > 0 ? 'info' : 'warning');

  const wf = document.getElementById('workflows-list');
  wf.innerHTML = '';
  data.workflows.forEach(w => {
    const li = document.createElement('li');
    li.textContent = w;
    wf.appendChild(li);
  });
}

// Memory Search
async function searchMemory() {
  const q = document.getElementById('memory-query').value;
  const kind = document.getElementById('memory-kind').value;
  const resContainer = document.getElementById('memory-results');

  if (!q) {
    resContainer.innerHTML = '<p class="muted">Enter a query to search FTS memory.</p>';
    return;
  }

  resContainer.innerHTML = '<div class="spinner"></div> Searching...';

  const data = await fetchJson(`/api/memory/search?q=${encodeURIComponent(q)}&kind=${encodeURIComponent(kind)}`);
  if (data.error) {
    resContainer.innerHTML = `<div class="error-msg">${escapeHtml(data.error)}</div>`;
    return;
  }

  if (data.length === 0) {
    resContainer.innerHTML = '<p class="muted">No results found.</p>';
    return;
  }

  resContainer.innerHTML = data.map(item => `
    <div class="memory-item">
      <div class="memory-header">
        <span class="badge">${escapeHtml(item.kind)}</span>
        <span class="source">${escapeHtml(item.source)}</span>
      </div>
      <pre class="memory-content">${escapeHtml(item.content)}</pre>
    </div>
  `).join('');
}

// Policy Sandbox
async function testPolicy() {
  const action = document.getElementById('policy-action').value;
  const argsStr = document.getElementById('policy-args').value;
  const resContainer = document.getElementById('policy-result');

  if (!action) return;

  let args = {};
  if (argsStr) {
    try {
      args = JSON.parse(argsStr);
    } catch (e) {
      resContainer.style.display = 'block';
      resContainer.innerHTML = `<div class="error-msg">Invalid JSON in arguments</div>`;
      return;
    }
  }

  resContainer.style.display = 'block';
  resContainer.innerHTML = '<div class="spinner"></div> Evaluating...';

  const data = await fetchJson('/api/policy/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, args })
  });

  if (data.error) {
    resContainer.innerHTML = `<div class="policy-result denied">
      <h4>Denied</h4>
      <p>${escapeHtml(data.error)}</p>
      <pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>
    </div>`;
  } else {
    resContainer.innerHTML = `<div class="policy-result ${data.ok ? 'allowed' : 'denied'}">
      <h4>${data.ok ? 'Allowed' : 'Blocked/Denied'}</h4>
      <pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>
    </div>`;
  }
}

// Workflows
async function loadWorkflows() {
  const select = document.getElementById('workflow-select');
  const data = await fetchJson('/api/workflows');
  if (data.error) {
    select.innerHTML = '<option value="">Error loading workflows</option>';
    return;
  }
  select.innerHTML = data.map(w => `<option value="${w}">${w}</option>`).join('');
  if (data.length === 0) {
    select.innerHTML = '<option value="">No workflows found</option>';
  }
}

async function runWorkflow() {
  const workflow = document.getElementById('workflow-select').value;
  const contextStr = document.getElementById('workflow-context').value;
  const resContainer = document.getElementById('workflow-result');

  if (!workflow) return;

  let context = {};
  if (contextStr) {
    try {
      context = JSON.parse(contextStr);
    } catch (e) {
      resContainer.style.display = 'block';
      resContainer.innerHTML = `<div class="error-msg">Invalid JSON in context</div>`;
      return;
    }
  }

  resContainer.style.display = 'block';
  resContainer.innerHTML = '<div class="spinner"></div> Running...';

  const data = await fetchJson('/api/workflow/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workflow_id: workflow, context })
  });

  if (data.error) {
    resContainer.innerHTML = `<div class="policy-result denied"><h4>Failed</h4><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></div>`;
  } else {
    resContainer.innerHTML = `<div class="policy-result allowed"><h4>Completed</h4><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></div>`;
  }
}

// Sagas
async function runSaga() {
  const sagaId = document.getElementById('saga-id').value;
  const stepsStr = document.getElementById('saga-steps').value;
  const contextStr = document.getElementById('saga-context').value;
  const resContainer = document.getElementById('saga-result');

  if (!sagaId || !stepsStr) return;

  let steps = [];
  let context = {};
  try {
    steps = JSON.parse(stepsStr);
    if (contextStr) context = JSON.parse(contextStr);
  } catch (e) {
    resContainer.style.display = 'block';
    resContainer.innerHTML = `<div class="error-msg">Invalid JSON</div>`;
    return;
  }

  resContainer.style.display = 'block';
  resContainer.innerHTML = '<div class="spinner"></div> Running...';

  const data = await fetchJson('/api/saga/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ saga_id: sagaId, steps, context })
  });

  if (data.error) {
    resContainer.innerHTML = `<div class="policy-result denied"><h4>Failed</h4><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></div>`;
  } else {
    resContainer.innerHTML = `<div class="policy-result ${data.ok ? 'allowed' : 'denied'}"><h4>${data.ok ? 'Completed' : 'Compensated'}</h4><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></div>`;
  }
}

// Chat
async function sendChat() {
  const input = document.getElementById('chat-message');
  const msg = input.value.trim();
  if (!msg) return;
  const history = document.getElementById('chat-history');
  history.innerHTML += `<div class="chat-msg user"><strong>You:</strong> ${escapeHtml(msg)}</div>`;
  input.value = '';
  const data = await fetchJson('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg })
  });
  const reply = data.reply || data.error || JSON.stringify(data);
  history.innerHTML += `<div class="chat-msg assistant"><strong>AiZee:</strong> ${escapeHtml(reply)}</div>`;
  history.scrollTop = history.scrollHeight;
}

// Tech Stack
async function loadStack() {
  const container = document.getElementById('stack-results');
  const data = await fetchJson('/api/status');
  if (data.error) {
    container.innerHTML = `<div class="error-msg">${escapeHtml(data.error)}</div>`;
    return;
  }
  const stack = data.tech_stack || {};
  if (Object.keys(stack).length === 0) {
    container.innerHTML = '<p class="muted">No lockfiles detected.</p>';
    return;
  }
  container.innerHTML = Object.entries(stack).map(([name, info]) => `
    <div class="memory-item">
      <div class="memory-header">
        <span class="badge">${escapeHtml(name)}</span>
        <span class="source">${escapeHtml(info.version)}</span>
      </div>
      <div class="memory-content">${escapeHtml(info.path)}</div>
    </div>
  `).join('');
}

// Telemetry
let telemetryChart = null;
async function loadTelemetry() {
  const type = document.getElementById('telemetry-type').value;
  const container = document.getElementById('telemetry-results');
  const data = await fetchJson(`/api/telemetry?limit=100&type=${encodeURIComponent(type)}`);
  if (data.error) {
    container.innerHTML = `<div class="error-msg">${escapeHtml(data.error)}</div>`;
    return;
  }
  if (data.length === 0) {
    container.innerHTML = '<p class="muted">No telemetry events yet.</p>';
    return;
  }
  container.innerHTML = data.map(e => `
    <div class="audit-entry">
      <div class="audit-time">${escapeHtml(e.timestamp)}</div>
      <div class="audit-type type-${e.status === 'allowed' ? 'success' : 'info'}">${escapeHtml(e.type)}</div>
      <pre class="audit-data">${escapeHtml(JSON.stringify(e, null, 2))}</pre>
    </div>
  `).join('');

  const counts = {};
  data.forEach(e => { counts[e.action] = (counts[e.action] || 0) + 1; });
  const ctx = document.getElementById('telemetry-chart').getContext('2d');
  if (telemetryChart) telemetryChart.destroy();
  telemetryChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Object.keys(counts),
      datasets: [{
        label: 'Events',
        data: Object.values(counts),
        backgroundColor: 'rgba(16, 185, 129, 0.5)'
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { color: '#f1f5f9' } }, x: { ticks: { color: '#f1f5f9' } } }
    }
  });
}

// System
async function loadSystem() {
  const data = await fetchJson('/api/system');
  if (data.error) return;
  document.getElementById('cpu-percent').textContent = data.cpu_percent.toFixed(1) + '%';
  document.getElementById('memory-percent').textContent = data.memory_percent.toFixed(1) + '%';
  document.getElementById('memory-used').textContent = data.memory_used_mb;
  document.getElementById('system-version').textContent = data.version;
}

// Audit Logs
async function loadAudit() {
  const container = document.getElementById('audit-logs');
  const data = await fetchJson('/api/audit');
  if (data.error) {
    container.innerHTML = `<div class="error-msg">${escapeHtml(data.error)}</div>`;
    return;
  }

  if (data.length === 0) {
    container.innerHTML = '<p class="muted">No audit logs found.</p>';
    return;
  }

  container.innerHTML = data.reverse().map(log => {
    let typeClass = 'info';
    if (log.type.includes('denied') || log.type.includes('blocked')) typeClass = 'error';
    if (log.type.includes('allowed')) typeClass = 'success';
    if (log.type.includes('asked')) typeClass = 'warning';

    return `
    <div class="audit-entry">
      <div class="audit-time">${escapeHtml(log.timestamp)}</div>
      <div class="audit-type type-${typeClass}">${escapeHtml(log.type)}</div>
      <pre class="audit-data">${escapeHtml(JSON.stringify(log.data, null, 2))}</pre>
    </div>
  `}).join('');
}

// ---------------------------------------------------------------------------
// Event bindings (replace inline onclick/onkeyup/onchange handlers so the
// CSP can omit 'unsafe-inline').
// ---------------------------------------------------------------------------

// Sidebar navigation
document.querySelectorAll('.nav-menu a').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const tab = (link.getAttribute('href') || '').replace('#', '');
    if (tab) switchTab(tab);
  });
});

// Top bar actions
const commandTriggerEl = document.querySelector('.command-trigger');
if (commandTriggerEl) commandTriggerEl.addEventListener('click', openCommandPalette);
const themeBtnEl = $('theme-toggle-btn');
if (themeBtnEl) themeBtnEl.addEventListener('click', toggleTheme);

// Overview
const refreshStatusEl = $('refresh-status-btn');
if (refreshStatusEl) refreshStatusEl.addEventListener('click', loadStatus);

// Memory Explorer
const memoryQueryEl = $('memory-query');
if (memoryQueryEl) memoryQueryEl.addEventListener('keyup', e => { if (e.key === 'Enter') searchMemory(); });
const memorySearchBtnEl = $('memory-search-btn');
if (memorySearchBtnEl) memorySearchBtnEl.addEventListener('click', searchMemory);

// Policy Sandbox
const policyEvalBtnEl = $('policy-eval-btn');
if (policyEvalBtnEl) policyEvalBtnEl.addEventListener('click', testPolicy);

// Workflows
const refreshWorkflowsEl = $('refresh-workflows-btn');
if (refreshWorkflowsEl) refreshWorkflowsEl.addEventListener('click', loadWorkflows);
const workflowRunBtnEl = $('workflow-run-btn');
if (workflowRunBtnEl) workflowRunBtnEl.addEventListener('click', runWorkflow);

// Sagas
const sagaRunBtnEl = $('saga-run-btn');
if (sagaRunBtnEl) sagaRunBtnEl.addEventListener('click', runSaga);

// Chat
const chatMessageEl = $('chat-message');
if (chatMessageEl) chatMessageEl.addEventListener('keyup', e => { if (e.key === 'Enter') sendChat(); });
const chatSendBtnEl = $('chat-send-btn');
if (chatSendBtnEl) chatSendBtnEl.addEventListener('click', sendChat);

// Tech Stack
const stackRefreshBtnEl = $('stack-refresh-btn');
if (stackRefreshBtnEl) stackRefreshBtnEl.addEventListener('click', loadStack);

// Telemetry
const telemetryTypeEl = $('telemetry-type');
if (telemetryTypeEl) telemetryTypeEl.addEventListener('change', loadTelemetry);
const telemetryRefreshBtnEl = $('telemetry-refresh-btn');
if (telemetryRefreshBtnEl) telemetryRefreshBtnEl.addEventListener('click', loadTelemetry);

// System
const systemRefreshBtnEl = $('system-refresh-btn');
if (systemRefreshBtnEl) systemRefreshBtnEl.addEventListener('click', loadSystem);

// Audit Logs
const auditRefreshBtnEl = $('audit-refresh-btn');
if (auditRefreshBtnEl) auditRefreshBtnEl.addEventListener('click', loadAudit);

// Command palette
const paletteOverlayEl = $('command-palette');
if (paletteOverlayEl) {
  paletteOverlayEl.addEventListener('click', e => {
    if (e.target === paletteOverlayEl) closeCommandPalette();
  });
}
const commandInputEl = $('command-input');
if (commandInputEl) {
  commandInputEl.addEventListener('input', filterCommands);
  commandInputEl.addEventListener('keydown', handleCommandKey);
}
const commandListEl = $('command-list');
if (commandListEl) {
  commandListEl.addEventListener('click', e => {
    const item = e.target.closest('.command-item');
    if (!item) return;
    executeCommand(parseInt(item.dataset.index, 10));
  });
}

// Init
loadStatus();
setInterval(loadStatus, 15000);

// --- Theme toggle (light/dark/auto) ---
(function() {
  const saved = localStorage.getItem('aizee-theme') || 'auto';
  if (saved !== 'auto') {
    document.documentElement.setAttribute('data-theme', saved);
  }
  const btn = document.createElement('button');
  btn.id = 'theme-toggle';
  btn.style.cssText = 'position:fixed;top:12px;right:12px;z-index:9999;padding:6px 12px;border-radius:6px;border:1px solid var(--border);background:var(--bg-elevated);color:var(--text-main);cursor:pointer;font-size:12px;';
  btn.textContent = '\u25D0';
  btn.title = 'Toggle theme (auto/light/dark)';
  const cycle = ['auto', 'light', 'dark'];
  btn.addEventListener('click', () => {
    const current = localStorage.getItem('aizee-theme') || 'auto';
    const next = cycle[(cycle.indexOf(current) + 1) % cycle.length];
    localStorage.setItem('aizee-theme', next);
    if (next === 'auto') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', next);
    }
    btn.textContent = next === 'auto' ? '\u25D0' : next === 'light' ? '\u2600' : '\u263E';
  });
  btn.textContent = saved === 'auto' ? '\u25D0' : saved === 'light' ? '\u2600' : '\u263E';
  document.body.appendChild(btn);
})();
