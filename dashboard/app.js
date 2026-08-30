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
    'audit': 'Audit Logs',
    'settings': 'Settings'
  };
  document.getElementById('page-title').textContent = titles[tabId];

  if (tabId === 'audit') loadAudit();
  if (tabId === 'workflows') loadWorkflows();
  if (tabId === 'stack') loadStack();
  if (tabId === 'telemetry') loadTelemetry();
  if (tabId === 'system') loadSystem();
  if (tabId === 'settings') loadSettings();
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
  { id: 'tab-settings', label: 'Settings', section: 'Navigation', run: () => switchTab('settings'), shortcut: ',' },
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
// Settings Panel
// ---------------------------------------------------------------------------

let currentSettingsSection = 'mcp_servers';
let settingsData = {};
let settingsDirty = false;

const SETTINGS_SECTION_TITLES = {
  'mcp_servers': 'MCP Servers',
  'budget': 'Budget & Costs',
  'guardian': 'Security & Gates',
  'injection_defense': 'Injection Defense',
  'plugins': 'Plugins & Persona',
  'dashboard': 'Dashboard & System',
};

// Sections that combine multiple underlying settings sections.
const SETTINGS_SECTION_MAP = {
  'mcp_servers': ['mcp_servers'],
  'budget': ['budget'],
  'guardian': ['guardian', 'mcp_firewall', 'policy', 'loop_detector'],
  'injection_defense': ['injection_defense'],
  'plugins': ['plugins', 'persona'],
  'dashboard': ['dashboard', 'telemetry', 'audit', 'memory', 'design'],
};

function showSettingsToast(msg, isError) {
  const toast = document.getElementById('settings-toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.className = 'settings-toast show' + (isError ? ' error' : ' success');
  setTimeout(() => { toast.className = 'settings-toast'; }, 3000);
}

async function loadSettings() {
  const body = document.getElementById('settings-body');
  if (!body) return;
  body.innerHTML = '<div class="spinner"></div> Loading settings...';
  settingsDirty = false;
  await renderSettingsSection(currentSettingsSection);
}

async function fetchSettingsSection(section) {
  const data = await fetchJson('/api/settings?section=' + encodeURIComponent(section));
  if (data.error) {
    showSettingsToast('Failed to load: ' + data.error, true);
    return null;
  }
  return data;
}

async function renderSettingsSection(section) {
  currentSettingsSection = section;
  const titleEl = document.getElementById('settings-section-title');
  if (titleEl) titleEl.textContent = SETTINGS_SECTION_TITLES[section] || section;

  // Update active nav button
  document.querySelectorAll('.settings-nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.settingsSection === section);
  });

  const body = document.getElementById('settings-body');
  if (!body) return;

  const subSections = SETTINGS_SECTION_MAP[section] || [section];
  const merged = {};
  for (const sub of subSections) {
    const data = await fetchSettingsSection(sub);
    if (data === null) {
      body.innerHTML = '<div class="error-msg">Failed to load settings.</div>';
      return;
    }
    merged[sub] = data;
  }
  settingsData = merged;

  if (section === 'mcp_servers') renderMcpSettings(body, merged);
  else if (section === 'budget') renderBudgetSettings(body, merged);
  else if (section === 'guardian') renderGuardianSettings(body, merged);
  else if (section === 'injection_defense') renderInjectionSettings(body, merged);
  else if (section === 'plugins') renderPluginsSettings(body, merged);
  else if (section === 'dashboard') renderDashboardSettings(body, merged);
}

function renderMcpSettings(body, data) {
  const servers = data.mcp_servers || {};
  const names = Object.keys(servers).sort();
  if (names.length === 0) {
    body.innerHTML = '<p class="muted">No MCP servers configured.</p>';
    return;
  }
  // Group by category (best-effort; uncategorized go to "Other")
  const categories = { Core: [], Freelance: [], Marketing: [], Social: [], Ads: [], Analytics: [], CRM: [], Billing: [], Other: [] };
  const categorized = new Set();
  const catMap = {
    aizee: 'Core', graphify: 'Core', context7: 'Core',
    upwork: 'Freelance', freelancer: 'Freelance', fiverr: 'Freelance', mostaql: 'Freelance', khamsat: 'Freelance',
    brevo: 'Marketing', sendgrid: 'Marketing', klaviyo: 'Marketing', kit: 'Marketing', listmonk: 'Marketing',
    twitter: 'Social', youtube: 'Social', postiz: 'Social', automatisch: 'Social',
    'google-ads': 'Ads', 'meta-ads': 'Ads', 'tiktok-ads': 'Ads', 'linkedin-ads': 'Ads',
    posthog: 'Analytics', growthbook: 'Analytics', flagsmith: 'Analytics', openreplay: 'Analytics',
    hubspot: 'CRM', twenty: 'CRM', chatwoot: 'CRM', formbricks: 'CRM', erpnext: 'CRM',
    lago: 'Billing',
  };
  for (const name of names) {
    const cat = catMap[name] || 'Other';
    categories[cat].push(name);
    categorized.add(name);
  }
  // Uncategorized
  for (const name of names) {
    if (!categorized.has(name)) categories.Other.push(name);
  }

  let html = '<div class="settings-search"><input type="text" id="mcp-search" placeholder="Filter servers..." class="settings-input"></div>';
  for (const [cat, srvs] of Object.entries(categories)) {
    if (srvs.length === 0) continue;
    const allOn = srvs.every(n => servers[n] && servers[n].enabled !== false);
    html += `<div class="settings-group">
      <div class="settings-group-header">
        <h4>${escapeHtml(cat)} <span class="settings-count">(${srvs.length})</span></h4>
        <label class="toggle-switch" title="Toggle all in group">
          <input type="checkbox" class="mcp-group-toggle" data-group="${escapeHtml(cat)}" ${allOn ? 'checked' : ''}>
          <span class="toggle-slider"></span>
        </label>
      </div>
      <div class="settings-group-body">`;
    for (const name of srvs) {
      const enabled = servers[name] && servers[name].enabled !== false;
      html += `<div class="settings-row" data-mcp-name="${escapeHtml(name)}">
        <span class="settings-label">${escapeHtml(name)}</span>
        <label class="toggle-switch">
          <input type="checkbox" class="mcp-toggle" data-server="${escapeHtml(name)}" ${enabled ? 'checked' : ''}>
          <span class="toggle-slider"></span>
        </label>
      </div>`;
    }
    html += '</div></div>';
  }
  body.innerHTML = html;

  // Wire toggles
  body.querySelectorAll('.mcp-toggle').forEach(el => {
    el.addEventListener('change', () => { settingsDirty = true; updateGroupToggles(); });
  });
  body.querySelectorAll('.mcp-group-toggle').forEach(el => {
    el.addEventListener('change', (e) => {
      const group = e.target.dataset.group;
      const checked = e.target.checked;
      body.querySelectorAll('.mcp-toggle').forEach(t => {
        const row = t.closest('.settings-group');
        if (row && row.querySelector('.settings-group-header h4').textContent.startsWith(group)) {
          t.checked = checked;
        }
      });
      settingsDirty = true;
    });
  });
  const search = document.getElementById('mcp-search');
  if (search) {
    search.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      body.querySelectorAll('.settings-row').forEach(row => {
        const name = (row.dataset.mcpName || '').toLowerCase();
        row.style.display = name.includes(q) ? '' : 'none';
      });
    });
  }
}

function updateGroupToggles() {
  const body = document.getElementById('settings-body');
  if (!body) return;
  body.querySelectorAll('.settings-group').forEach(group => {
    const toggles = group.querySelectorAll('.mcp-toggle');
    const groupToggle = group.querySelector('.mcp-group-toggle');
    if (groupToggle && toggles.length > 0) {
      groupToggle.checked = Array.from(toggles).every(t => t.checked);
    }
  });
}

function renderBudgetSettings(body, data) {
  const budget = data.budget || {};
  const scopes = ['global', 'session'];
  let html = '';
  for (const scope of scopes) {
    const cfg = budget[scope] || {};
    html += `<div class="settings-group">
      <div class="settings-group-header"><h4>${escapeHtml(scope)}</h4></div>
      <div class="settings-group-body">
        <div class="settings-form-row">
          <label>Max Tokens</label>
          <input type="number" class="settings-input" data-budget="${escapeHtml(scope)}" data-field="max_tokens" value="${cfg.max_tokens ?? 0}" min="0">
        </div>
        <div class="settings-form-row">
          <label>Max Cost (USD)</label>
          <input type="number" class="settings-input" data-budget="${escapeHtml(scope)}" data-field="max_cost_usd" value="${cfg.max_cost_usd ?? 0}" min="0" step="0.01">
        </div>
        <div class="settings-form-row">
          <label>Max Calls</label>
          <input type="number" class="settings-input" data-budget="${escapeHtml(scope)}" data-field="max_calls" value="${cfg.max_calls ?? 0}" min="0">
        </div>
        <div class="settings-form-row">
          <label>Period</label>
          <select class="settings-input" data-budget="${escapeHtml(scope)}" data-field="period">
            ${['session','hourly','daily','weekly','monthly'].map(p => `<option value="${p}" ${cfg.period === p ? 'selected' : ''}>${p}</option>`).join('')}
          </select>
        </div>
        <div class="settings-form-row">
          <label>On Exceed</label>
          <select class="settings-input" data-budget="${escapeHtml(scope)}" data-field="on_exceed">
            ${['warn','fallback','block'].map(o => `<option value="${o}" ${cfg.on_exceed === o ? 'selected' : ''}>${o}</option>`).join('')}
          </select>
        </div>
        <div class="settings-form-row">
          <label>Finalization Reserve (0-0.5)</label>
          <input type="number" class="settings-input" data-budget="${escapeHtml(scope)}" data-field="finalization_reserve" value="${cfg.finalization_reserve ?? 0}" min="0" max="0.5" step="0.05">
        </div>
        <div class="settings-form-row">
          <label>Token Weight Input</label>
          <input type="number" class="settings-input" data-budget="${escapeHtml(scope)}" data-field="token_weight_input" value="${cfg.token_weight_input ?? 1.0}" min="0" step="0.1">
        </div>
        <div class="settings-form-row">
          <label>Token Weight Output</label>
          <input type="number" class="settings-input" data-budget="${escapeHtml(scope)}" data-field="token_weight_output" value="${cfg.token_weight_output ?? 1.0}" min="0" step="0.1">
        </div>
        <div class="settings-form-row">
          <label>Fallback Model</label>
          <input type="text" class="settings-input" data-budget="${escapeHtml(scope)}" data-field="fallback_model" value="${escapeHtml(cfg.fallback_model ?? '')}" placeholder="e.g. gpt-4o-mini">
        </div>
      </div>
    </div>`;
  }
  body.innerHTML = html;
  body.querySelectorAll('.settings-input').forEach(el => {
    el.addEventListener('change', () => { settingsDirty = true; });
  });
}

function renderGuardianSettings(body, data) {
  const guardian = data.guardian || {};
  const firewall = data.mcp_firewall || {};
  const policy = data.policy || {};
  const loop = data.loop_detector || {};

  let html = '<div class="settings-group"><div class="settings-group-header"><h4>Guardian</h4></div><div class="settings-group-body">';
  html += `<div class="settings-form-row"><label>Default Decision</label>
    <select class="settings-input" data-guardian-field="default_decision">
      ${['allow','deny','ask','require_approval'].map(d => `<option value="${d}" ${guardian.default_decision === d ? 'selected' : ''}>${d}</option>`).join('')}
    </select></div>`;
  html += `<div class="settings-form-row"><label>On Evaluation Error</label>
    <select class="settings-input" data-guardian-field="on_evaluation_error">
      ${['allow','deny','ask'].map(d => `<option value="${d}" ${guardian.on_evaluation_error === d ? 'selected' : ''}>${d}</option>`).join('')}
    </select></div>`;
  html += '</div></div>';

  html += '<div class="settings-group"><div class="settings-group-header"><h4>Kill Switch</h4></div><div class="settings-group-body">';
  const ks = guardian.kill_switch || {};
  for (const f of ['cost_ceiling', 'file_touched_count', 'tool_call_count', 'time_limit']) {
    html += `<div class="settings-form-row"><label>${escapeHtml(f)}</label>
      <input type="number" class="settings-input" data-killswitch="${escapeHtml(f)}" value="${ks[f] ?? 0}" min="0"><span class="muted"> (0 = disabled)</span></div>`;
  }
  html += '</div></div>';

  html += '<div class="settings-group"><div class="settings-group-header"><h4>MCP Firewall</h4></div><div class="settings-group-body">';
  html += `<div class="settings-form-row"><label>Catch-all Action</label>
    <select class="settings-input" data-firewall-field="catch_all_action">
      ${['allow','deny','require_approval'].map(d => `<option value="${d}" ${firewall.catch_all_action === d ? 'selected' : ''}>${d}</option>`).join('')}
    </select></div>`;
  html += '</div></div>';

  html += '<div class="settings-group"><div class="settings-group-header"><h4>Policy Engine</h4></div><div class="settings-group-body">';
  html += `<div class="settings-form-row"><label>Default Action</label>
    <select class="settings-input" data-policy-field="default_action">
      ${['allow','deny','ask'].map(d => `<option value="${d}" ${policy.default_action === d ? 'selected' : ''}>${d}</option>`).join('')}
    </select></div>`;
  html += '</div></div>';

  html += '<div class="settings-group"><div class="settings-group-header"><h4>Loop Detector</h4></div><div class="settings-group-body">';
  html += `<div class="settings-form-row"><label>Window Size</label>
    <input type="number" class="settings-input" data-loop-field="window" value="${loop.window ?? 20}" min="1"></div>`;
  html += `<div class="settings-form-row"><label>Threshold</label>
    <input type="number" class="settings-input" data-loop-field="threshold" value="${loop.threshold ?? 5}" min="1"></div>`;
  html += '</div></div>';

  body.innerHTML = html;
  body.querySelectorAll('.settings-input').forEach(el => {
    el.addEventListener('change', () => { settingsDirty = true; });
  });
}

function renderInjectionSettings(body, data) {
  const inj = data.injection_defense || {};
  const boolFields = ['injection_detector', 'defensive_injector', 'tool_output_sanitizer', 'baseline_registry', 'dual_llm', 'taint_enforcement', 'agent_baseline'];
  const labels = {
    injection_detector: 'Injection Detector (13-technique scanner)',
    defensive_injector: 'Defensive Injector (active counter-injection)',
    tool_output_sanitizer: 'Tool Output Sanitizer (indirect injection)',
    baseline_registry: 'Baseline Registry (behavioral anomaly)',
    dual_llm: 'Dual LLM (Simon Willison pattern)',
    taint_enforcement: 'Taint Enforcement (Bell-LaPadula)',
    agent_baseline: 'Agent Baseline (anomaly detection)',
  };
  let html = '<div class="settings-group"><div class="settings-group-header"><h4>Defense Modules</h4></div><div class="settings-group-body">';
  for (const f of boolFields) {
    const checked = inj[f] !== false;
    html += `<div class="settings-row">
      <span class="settings-label">${escapeHtml(labels[f] || f)}</span>
      <label class="toggle-switch"><input type="checkbox" data-injection="${escapeHtml(f)}" ${checked ? 'checked' : ''}><span class="toggle-slider"></span></label>
    </div>`;
  }
  html += '</div></div>';
  html += '<div class="settings-group"><div class="settings-group-header"><h4>Thresholds</h4></div><div class="settings-group-body">';
  html += `<div class="settings-form-row"><label>Block Threshold</label>
    <input type="number" class="settings-input" data-injection-num="block_threshold" value="${inj.block_threshold ?? 12}" min="0"></div>`;
  html += `<div class="settings-form-row"><label>Suspicious Threshold</label>
    <input type="number" class="settings-input" data-injection-num="suspicious_threshold" value="${inj.suspicious_threshold ?? 5}" min="0"></div>`;
  html += '</div></div>';
  body.innerHTML = html;
  body.querySelectorAll('[data-injection], [data-injection-num]').forEach(el => {
    el.addEventListener('change', () => { settingsDirty = true; });
  });
}

function renderPluginsSettings(body, data) {
  const plugins = data.plugins || {};
  const persona = data.persona || {};
  const names = Object.keys(plugins).sort();
  let html = '<div class="settings-group"><div class="settings-group-header"><h4>Plugins</h4></div><div class="settings-group-body">';
  if (names.length === 0) {
    html += '<p class="muted">No plugins discovered. Place plugins in the <code>plugins/</code> directory.</p>';
  } else {
    for (const name of names) {
      const enabled = plugins[name] && plugins[name].enabled !== false;
      html += `<div class="settings-row">
        <span class="settings-label">${escapeHtml(name)}</span>
        <label class="toggle-switch"><input type="checkbox" data-plugin="${escapeHtml(name)}" ${enabled ? 'checked' : ''}><span class="toggle-slider"></span></label>
      </div>`;
    }
  }
  html += '</div></div>';

  html += '<div class="settings-group"><div class="settings-group-header"><h4>Persona</h4></div><div class="settings-group-body">';
  html += `<div class="settings-form-row"><label>Default Persona</label>
    <input type="text" class="settings-input" data-persona-field="default" value="${escapeHtml(persona.default || 'ARCH')}"></div>`;
  html += `<div class="settings-row"><span class="settings-label">Multi-persona detection</span>
    <label class="toggle-switch"><input type="checkbox" data-persona-bool="multi" ${persona.multi !== false ? 'checked' : ''}><span class="toggle-slider"></span></label></div>`;
  html += `<div class="settings-row"><span class="settings-label">Autoload lord skills</span>
    <label class="toggle-switch"><input type="checkbox" data-persona-bool="autoload_lords" ${persona.autoload_lords !== false ? 'checked' : ''}><span class="toggle-slider"></span></label></div>`;
  html += '</div></div>';
  body.innerHTML = html;
  body.querySelectorAll('[data-plugin], [data-persona-field], [data-persona-bool]').forEach(el => {
    el.addEventListener('change', () => { settingsDirty = true; });
  });
}

function renderDashboardSettings(body, data) {
  const dash = data.dashboard || {};
  const telemetry = data.telemetry || {};
  const audit = data.audit || {};
  const memory = data.memory || {};
  const design = data.design || {};

  let html = '<div class="settings-group"><div class="settings-group-header"><h4>Dashboard</h4></div><div class="settings-group-body">';
  html += `<div class="settings-form-row"><label>Rate Limit (req/window)</label>
    <input type="number" class="settings-input" data-dash-field="rate_limit" value="${dash.rate_limit ?? 120}" min="1"></div>`;
  html += `<div class="settings-form-row"><label>Rate Window (seconds)</label>
    <input type="number" class="settings-input" data-dash-field="rate_window" value="${dash.rate_window ?? 60}" min="1"></div>`;
  html += `<div class="settings-form-row"><label>Max Body Size (bytes)</label>
    <input type="number" class="settings-input" data-dash-field="max_body_size" value="${dash.max_body_size ?? 1048576}" min="1024"></div>`;
  html += `<div class="settings-form-row"><label>Bind Host</label>
    <input type="text" class="settings-input" data-dash-field="bind_host" value="${escapeHtml(dash.bind_host || '127.0.0.1')}"></div>`;
  html += '</div></div>';

  html += '<div class="settings-group"><div class="settings-group-header"><h4>Telemetry</h4></div><div class="settings-group-body">';
  html += `<div class="settings-row"><span class="settings-label">Telemetry enabled</span>
    <label class="toggle-switch"><input type="checkbox" data-telemetry-bool="enabled" ${telemetry.enabled !== false ? 'checked' : ''}><span class="toggle-slider"></span></label></div>`;
  html += `<div class="settings-form-row"><label>SSE Interval (seconds)</label>
    <input type="number" class="settings-input" data-telemetry-num="sse_interval" value="${telemetry.sse_interval ?? 5}" min="1"></div>`;
  html += '</div></div>';

  html += '<div class="settings-group"><div class="settings-group-header"><h4>Audit</h4></div><div class="settings-group-body">';
  html += `<div class="settings-form-row"><label>Retention (days)</label>
    <input type="number" class="settings-input" data-audit-field="retention_days" value="${audit.retention_days ?? 30}" min="0"></div>`;
  html += '</div></div>';

  html += '<div class="settings-group"><div class="settings-group-header"><h4>Memory</h4></div><div class="settings-group-body">';
  html += `<div class="settings-row"><span class="settings-label">Decay enabled</span>
    <label class="toggle-switch"><input type="checkbox" data-memory-bool="decay_enabled" ${memory.decay_enabled !== false ? 'checked' : ''}><span class="toggle-slider"></span></label></div>`;
  html += `<div class="settings-row"><span class="settings-label">Vector search</span>
    <label class="toggle-switch"><input type="checkbox" data-memory-bool="vector_search" ${memory.vector_search !== false ? 'checked' : ''}><span class="toggle-slider"></span></label></div>`;
  html += '</div></div>';

  html += '<div class="settings-group"><div class="settings-group-header"><h4>Design Tooling</h4></div><div class="settings-group-body">';
  html += `<div class="settings-row"><span class="settings-label">Design slop verifier</span>
    <label class="toggle-switch"><input type="checkbox" data-design-bool="slop_verifier" ${design.slop_verifier !== false ? 'checked' : ''}><span class="toggle-slider"></span></label></div>`;
  html += `<div class="settings-row"><span class="settings-label">Design library autoload</span>
    <label class="toggle-switch"><input type="checkbox" data-design-bool="library_autoload" ${design.library_autoload !== false ? 'checked' : ''}><span class="toggle-slider"></span></label></div>`;
  html += '</div></div>';

  body.innerHTML = html;
  body.querySelectorAll('.settings-input, [data-telemetry-bool], [data-memory-bool], [data-design-bool]').forEach(el => {
    el.addEventListener('change', () => { settingsDirty = true; });
  });
}

function collectSettingsData() {
  const body = document.getElementById('settings-body');
  if (!body) return {};
  const section = currentSettingsSection;
  const result = {};

  if (section === 'mcp_servers') {
    const servers = {};
    body.querySelectorAll('.mcp-toggle').forEach(el => {
      servers[el.dataset.server] = { enabled: el.checked };
    });
    result.mcp_servers = servers;
  } else if (section === 'budget') {
    const budget = {};
    body.querySelectorAll('[data-budget]').forEach(el => {
      const scope = el.dataset.budget;
      const field = el.dataset.field;
      if (!budget[scope]) budget[scope] = {};
      let val = el.value;
      if (['max_tokens', 'max_calls'].includes(field)) val = parseInt(val, 10) || 0;
      else if (['max_cost_usd', 'finalization_reserve', 'token_weight_input', 'token_weight_output'].includes(field)) val = parseFloat(val) || 0;
      else if (field === 'fallback_model') val = val.trim() || null;
      budget[scope][field] = val;
    });
    result.budget = budget;
  } else if (section === 'guardian') {
    const guardian = { rules: {}, kill_switch: {} };
    body.querySelectorAll('[data-guardian-field]').forEach(el => {
      guardian[el.dataset.guardianField] = el.value;
    });
    body.querySelectorAll('[data-killswitch]').forEach(el => {
      guardian.kill_switch[el.dataset.killswitch] = parseInt(el.value, 10) || 0;
    });
    result.guardian = guardian;
    const firewall = { rules: {} };
    body.querySelectorAll('[data-firewall-field]').forEach(el => {
      firewall[el.dataset.firewallField] = el.value;
    });
    result.mcp_firewall = firewall;
    const policy = {};
    body.querySelectorAll('[data-policy-field]').forEach(el => {
      policy[el.dataset.policyField] = el.value;
    });
    result.policy = policy;
    const loop = {};
    body.querySelectorAll('[data-loop-field]').forEach(el => {
      loop[el.dataset.loopField] = parseInt(el.value, 10) || 1;
    });
    result.loop_detector = loop;
  } else if (section === 'injection_defense') {
    const inj = {};
    body.querySelectorAll('[data-injection]').forEach(el => {
      inj[el.dataset.injection] = el.checked;
    });
    body.querySelectorAll('[data-injection-num]').forEach(el => {
      inj[el.dataset.injectionNum] = parseInt(el.value, 10) || 0;
    });
    result.injection_defense = inj;
  } else if (section === 'plugins') {
    const plugins = {};
    body.querySelectorAll('[data-plugin]').forEach(el => {
      plugins[el.dataset.plugin] = { enabled: el.checked };
    });
    result.plugins = plugins;
    const persona = {};
    body.querySelectorAll('[data-persona-field]').forEach(el => {
      persona[el.dataset.personaField] = el.value.trim();
    });
    body.querySelectorAll('[data-persona-bool]').forEach(el => {
      persona[el.dataset.personaBool] = el.checked;
    });
    result.persona = persona;
  } else if (section === 'dashboard') {
    const dash = {};
    body.querySelectorAll('[data-dash-field]').forEach(el => {
      const f = el.dataset.dashField;
      dash[f] = (f === 'bind_host') ? el.value : (parseInt(el.value, 10) || 0);
    });
    result.dashboard = dash;
    const telemetry = {};
    body.querySelectorAll('[data-telemetry-bool]').forEach(el => {
      telemetry[el.dataset.telemetryBool] = el.checked;
    });
    body.querySelectorAll('[data-telemetry-num]').forEach(el => {
      telemetry[el.dataset.telemetryNum] = parseInt(el.value, 10) || 1;
    });
    result.telemetry = telemetry;
    const audit = {};
    body.querySelectorAll('[data-audit-field]').forEach(el => {
      audit[el.dataset.auditField] = parseInt(el.value, 10) || 0;
    });
    result.audit = audit;
    const memory = {};
    body.querySelectorAll('[data-memory-bool]').forEach(el => {
      memory[el.dataset.memoryBool] = el.checked;
    });
    result.memory = memory;
    const design = {};
    body.querySelectorAll('[data-design-bool]').forEach(el => {
      design[el.dataset.designBool] = el.checked;
    });
    result.design = design;
  }
  return result;
}

async function saveSettings() {
  const data = collectSettingsData();
  const subSections = SETTINGS_SECTION_MAP[currentSettingsSection] || [currentSettingsSection];
  let allOk = true;
  for (const sub of subSections) {
    if (!data[sub]) continue;
    const res = await fetchJson('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section: sub, data: data[sub] }),
    });
    if (res.error) {
      allOk = false;
      showSettingsToast('Save failed (' + sub + '): ' + res.error, true);
    }
  }
  if (allOk) {
    settingsDirty = false;
    showSettingsToast('Settings saved. Click "Restart aiZee" to apply.', false);
  }
}

async function resetSettingsSection() {
  if (!confirm('Reset this section to defaults? This cannot be undone.')) return;
  const subSections = SETTINGS_SECTION_MAP[currentSettingsSection] || [currentSettingsSection];
  for (const sub of subSections) {
    await fetchJson('/api/settings/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section: sub }),
    });
  }
  showSettingsToast('Section reset to defaults.', false);
  await renderSettingsSection(currentSettingsSection);
}

async function restartAizee() {
  if (!confirm('Restart aiZee kernel? This will reload all policies, reset MCP connections, and re-read settings. Continue?')) return;
  const res = await fetchJson('/api/settings/restart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  });
  if (res.error) {
    showSettingsToast('Restart failed: ' + res.error, true);
  } else {
    showSettingsToast('aiZee kernel reloaded successfully.', false);
    settingsDirty = false;
    setTimeout(() => loadStatus(), 500);
  }
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

// Settings — sidenav
document.querySelectorAll('.settings-nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const section = btn.dataset.settingsSection;
    if (section) renderSettingsSection(section);
  });
});
// Settings — action buttons
const settingsSaveBtnEl = $('settings-save-btn');
if (settingsSaveBtnEl) settingsSaveBtnEl.addEventListener('click', saveSettings);
const settingsResetBtnEl = $('settings-reset-btn');
if (settingsResetBtnEl) settingsResetBtnEl.addEventListener('click', resetSettingsSection);
const settingsRestartBtnEl = $('settings-restart-btn');
if (settingsRestartBtnEl) settingsRestartBtnEl.addEventListener('click', restartAizee);

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
