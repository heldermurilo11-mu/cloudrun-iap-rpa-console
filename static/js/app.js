/**
 * GCP RPA Orchestrator - Client-side SPA Controller
 * Modo Zero-Build com Page Visibility API e Polling Inteligente
 */

const state = {
  currentView: 'dashboard',
  selectedPool: '',
  poolsList: [],
  poolMetrics: null,
  poolItems: [],
  statusFilter: 'ALL',
  searchQuery: '',
  jobs: [],
  executions: [],
  schedulers: [],
  logs: [],
  auditLogs: [],
  selectedItem: null,
  isPollingActive: true,
  lastPollTime: null,
  pollingInterval: null
};

// --- Inicialização ---
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupVisibilityListener();
  loadInitialData();
  startPolling();
});

// --- Navegação entre Módulos ---
function setupNavigation() {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const view = el.getAttribute('data-view');
      navigateTo(view);
    });
  });
}

function navigateTo(viewName) {
  state.currentView = viewName;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.getAttribute('data-view') === viewName);
  });
  
  document.getElementById('pageTitle').textContent = {
    dashboard: 'Visão Geral & Métricas',
    datapools: 'Datapools (Filas de Trabalho)',
    jobs: 'Automações & Execuções (Cloud Run)',
    schedulers: 'Agendamentos (Cloud Scheduler)',
    logs: 'Logs Estruturados (Cloud Logging)',
    audit: 'Trilha de Auditoria (Audit Trail)'
  }[viewName] || 'Orquestrador';

  renderCurrentView();
}

// --- Page Visibility API (Pausa polling quando aba está oculta) ---
function setupVisibilityListener() {
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopPolling();
      updateStatusIndicator(false);
    } else {
      startPolling();
      refreshData();
      updateStatusIndicator(true);
    }
  });
}

function startPolling() {
  if (state.pollingInterval) clearInterval(state.pollingInterval);
  state.pollingInterval = setInterval(refreshData, 15000); // 15s baseline
  state.isPollingActive = true;
  updateStatusIndicator(true);
}

function stopPolling() {
  if (state.pollingInterval) clearInterval(state.pollingInterval);
  state.pollingInterval = null;
  state.isPollingActive = false;
}

function updateStatusIndicator(active) {
  const dot = document.getElementById('pulseDot');
  const txt = document.getElementById('pollStatusText');
  if (dot && txt) {
    dot.style.backgroundColor = active ? '#22c55e' : '#64748b';
    dot.style.boxShadow = active ? '0 0 8px #22c55e' : 'none';
    txt.textContent = active ? 'Ao Vivo (15s)' : 'Pausado (Aba em 2º plano)';
  }
}

// --- Carregamento de Dados ---
async function loadInitialData() {
  await Promise.all([fetchCurrentUser(), fetchDatapoolsList()]);
  if (state.poolsList.length > 0) {
    state.selectedPool = state.poolsList[0];
  }
  await refreshData();
}

async function fetchCurrentUser() {
  try {
    const res = await fetch('/api/me');
    if (!res.ok) return;
    const user = await res.json();
    const emailEl = document.getElementById('userEmail');
    const roleEl = document.getElementById('userRole');
    const avatarEl = document.getElementById('userAvatar');
    if (emailEl && user.email) {
      emailEl.textContent = user.email;
    }
    if (roleEl && user.role) {
      roleEl.textContent = user.role === 'admin' ? 'Administrador' : 'Operador Autorizado';
    }
    if (avatarEl && user.email) {
      avatarEl.textContent = user.email.slice(0, 2).toUpperCase();
    }
  } catch (err) {
    console.error('Erro ao buscar usuário autenticado:', err);
  }
}

async function refreshData() {
  state.lastPollTime = new Date();
  if (state.currentView === 'dashboard') {
    await fetchDashboardSummary();
  } else if (state.currentView === 'datapools') {
    await fetchDatapoolDetails();
  } else if (state.currentView === 'jobs') {
    await fetchJobsAndExecutions();
  } else if (state.currentView === 'schedulers') {
    await fetchSchedulers();
  } else if (state.currentView === 'logs') {
    await fetchLogs();
  } else if (state.currentView === 'audit') {
    await fetchAuditLogs();
  }
}

// --- Chamadas API REST ---
async function fetchDatapoolsList() {
  try {
    const res = await fetch('/api/datapools');
    const data = await res.json();
    state.poolsList = data.datapools || [];
  } catch (err) {
    console.error('Erro ao buscar lista de datapools:', err);
  }
}

async function fetchDashboardSummary() {
  try {
    const res = await fetch('/api/datapools/summary');
    const data = await res.json();
    renderDashboard(data);
  } catch (err) {
    console.error('Erro ao buscar resumo:', err);
  }
}

async function fetchDatapoolDetails() {
  if (!state.selectedPool) return;
  try {
    const [metricsRes, itemsRes] = await Promise.all([
      fetch(`/api/datapools/${state.selectedPool}/metrics`),
      fetch(`/api/datapools/${state.selectedPool}/items?status=${state.statusFilter}&search=${encodeURIComponent(state.searchQuery)}&limit=50`)
    ]);
    state.poolMetrics = await metricsRes.json();
    const itemsData = await itemsRes.json();
    state.poolItems = itemsData.items || [];
    renderDatapools();
  } catch (err) {
    console.error('Erro ao carregar detalhes do datapool:', err);
  }
}

async function fetchJobsAndExecutions() {
  try {
    const [jobsRes, execRes] = await Promise.all([
      fetch('/api/jobs'),
      fetch('/api/jobs/executions?limit=30')
    ]);
    const jobsData = await jobsRes.json();
    const execData = await execRes.json();
    state.jobs = jobsData.jobs || [];
    state.executions = execData.executions || [];
    renderJobs();
  } catch (err) {
    console.error('Erro ao carregar jobs:', err);
  }
}

async function fetchSchedulers() {
  try {
    const res = await fetch('/api/schedulers');
    const data = await res.json();
    state.schedulers = data.schedulers || [];
    renderSchedulers();
  } catch (err) {
    console.error('Erro ao carregar schedulers:', err);
  }
}

async function fetchLogs() {
  try {
    const res = await fetch('/api/logs?limit=50');
    const data = await res.json();
    state.logs = data.logs || [];
    renderLogs();
  } catch (err) {
    console.error('Erro ao carregar logs:', err);
  }
}

async function fetchAuditLogs() {
  try {
    const res = await fetch('/api/audit?limit=50');
    const data = await res.json();
    state.auditLogs = data.events || [];
    renderAudit();
  } catch (err) {
    console.error('Erro ao carregar auditoria:', err);
  }
}

// --- Renderizadores de Tela ---
function renderCurrentView() {
  refreshData();
}

function renderDashboard(data) {
  const container = document.getElementById('contentArea');
  if (!data) return;

  container.innerHTML = `
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-title">Filas Homologadas</div>
        <div class="kpi-value">${data.total_pools || 0}</div>
        <div class="kpi-sub">Total de Datapools</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Itens Pendentes</div>
        <div class="kpi-value" style="color: var(--badge-queued-text);">${data.total_queued || 0}</div>
        <div class="kpi-sub">Aguardando Worker</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Em Processamento</div>
        <div class="kpi-value" style="color: var(--badge-processing-text);">${data.total_processing || 0}</div>
        <div class="kpi-sub">Lock Ativo</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Concluídos</div>
        <div class="kpi-value" style="color: var(--badge-done-text);">${data.total_done || 0}</div>
        <div class="kpi-sub">Processados com sucesso</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Falhas / Timeouts</div>
        <div class="kpi-value" style="color: var(--badge-failed-text);">${data.total_failed || 0}</div>
        <div class="kpi-sub">Amostras Rejeitadas</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Taxa de Sucesso</div>
        <div class="kpi-value">${data.overall_success_rate || 100}%</div>
        <div class="kpi-sub">Acurácia Global</div>
      </div>
    </div>

    <div class="table-container" style="margin-top: 24px;">
      <div style="padding: 16px; font-weight: 700; border-bottom: 1px solid var(--border);">Filas Recentes</div>
      <table>
        <thead>
          <tr>
            <th>Nome do Datapool</th>
            <th>Pendentes</th>
            <th>Processando</th>
            <th>Concluídos</th>
            <th>Falhas</th>
            <th>Total</th>
            <th>Taxa de Sucesso</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          ${(data.recent_pools || []).map(p => `
            <tr>
              <td style="font-weight: 600;">${escapeHtml(p.datapool)}</td>
              <td><span class="badge badge-QUEUED">${p.counts.QUEUED}</span></td>
              <td><span class="badge badge-PROCESSING">${p.counts.PROCESSING}</span></td>
              <td><span class="badge badge-DONE">${p.counts.DONE}</span></td>
              <td><span class="badge badge-FAILED">${p.counts.FAILED + p.counts.TIMEOUT}</span></td>
              <td>${p.counts.TOTAL}</td>
              <td style="font-weight: 600; color: #34d399;">${p.success_rate}%</td>
              <td>
                <button class="btn" style="padding: 4px 8px; font-size: 11px;" onclick="selectAndGoToPool('${escapeHtml(p.datapool)}')">Abrir Fila</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function selectAndGoToPool(poolName) {
  state.selectedPool = poolName;
  navigateTo('datapools');
}

function renderDatapools() {
  const container = document.getElementById('contentArea');
  const metrics = state.poolMetrics ? state.poolMetrics.counts : { QUEUED: 0, PROCESSING: 0, DONE: 0, FAILED: 0, TIMEOUT: 0, CANCELED: 0, TOTAL: 0 };

  container.innerHTML = `
    <div class="filter-bar">
      <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
        <select class="select-input" id="poolSelector" onchange="changePool(this.value)">
          ${state.poolsList.map(p => `<option value="${escapeHtml(p)}" ${p === state.selectedPool ? 'selected' : ''}>${escapeHtml(p)}</option>`).join('')}
        </select>
        <select class="select-input" id="statusFilter" onchange="changeStatusFilter(this.value)">
          <option value="ALL" ${state.statusFilter === 'ALL' ? 'selected' : ''}>Todos os Status</option>
          <option value="QUEUED" ${state.statusFilter === 'QUEUED' ? 'selected' : ''}>Pendente (QUEUED)</option>
          <option value="PROCESSING" ${state.statusFilter === 'PROCESSING' ? 'selected' : ''}>Processando</option>
          <option value="DONE" ${state.statusFilter === 'DONE' ? 'selected' : ''}>Concluído (DONE)</option>
          <option value="FAILED" ${state.statusFilter === 'FAILED' ? 'selected' : ''}>Falhou (FAILED)</option>
        </select>
        <input type="text" class="search-input" placeholder="Buscar por código ou arquivo..." value="${escapeHtml(state.searchQuery)}" oninput="searchItems(this.value)">
      </div>
      <button class="btn btn-primary" onclick="refreshData()">Atualizar</button>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-title">Pendentes</div>
        <div class="kpi-value" style="color: var(--badge-queued-text);">${metrics.QUEUED}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Processando</div>
        <div class="kpi-value" style="color: var(--badge-processing-text);">${metrics.PROCESSING}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Concluídos</div>
        <div class="kpi-value" style="color: var(--badge-done-text);">${metrics.DONE}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Falhas</div>
        <div class="kpi-value" style="color: var(--badge-failed-text);">${metrics.FAILED}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Total de Itens</div>
        <div class="kpi-value">${metrics.TOTAL}</div>
      </div>
    </div>

    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>ID / Amostra</th>
            <th>Arquivo PDF</th>
            <th>Status</th>
            <th>Tentativas</th>
            <th>Criado em</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          ${state.poolItems.length === 0 ? '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">Nenhuma amostra encontrada.</td></tr>' : ''}
          ${state.poolItems.map(item => `
            <tr>
              <td style="font-weight: 600; color: #38bdf8;">${escapeHtml(item.sample_ref || item.id)}</td>
              <td style="color: var(--text-muted);">${escapeHtml(item.file_name || 'N/A')}</td>
              <td><span class="badge badge-${escapeHtml(item.status || 'QUEUED')}">${escapeHtml(item.status || 'QUEUED')}</span></td>
              <td>${item.attempts || 0}</td>
              <td style="font-size: 11px; color: var(--text-muted);">${item.created_at ? new Date(item.created_at).toLocaleString('pt-BR') : 'N/A'}</td>
              <td>
                <button class="btn" style="padding: 4px 8px; font-size: 11px;" onclick="inspectItem('${escapeHtml(item.id)}')">Inspecionar JSON</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function changePool(name) {
  state.selectedPool = name;
  fetchDatapoolDetails();
}

function changeStatusFilter(val) {
  state.statusFilter = val;
  fetchDatapoolDetails();
}

function searchItems(query) {
  state.searchQuery = query;
  fetchDatapoolDetails();
}

function inspectItem(itemId) {
  const item = state.poolItems.find(i => i.id === itemId);
  if (!item) return;

  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.id = 'inspectModal';
  modal.innerHTML = `
    <div class="modal-box">
      <div class="modal-header">
        <div style="font-weight: 700;">Amostra: ${escapeHtml(item.sample_ref || item.id)}</div>
        <button class="btn" style="padding: 2px 8px;" onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <div style="margin-bottom: 12px; display: flex; gap: 8px;">
          <span class="badge badge-${escapeHtml(item.status || 'QUEUED')}">${escapeHtml(item.status || 'QUEUED')}</span>
          <span style="color: var(--text-muted);">Arquivo: ${escapeHtml(item.file_name || 'N/A')}</span>
        </div>
        <div class="json-viewer">${escapeHtml(JSON.stringify(item, null, 2))}</div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

function closeModal() {
  const m = document.getElementById('inspectModal');
  if (m) m.remove();
}

function renderJobs() {
  const container = document.getElementById('contentArea');
  container.innerHTML = `
    <div class="table-container" style="margin-bottom: 24px;">
      <div style="padding: 16px; font-weight: 700; border-bottom: 1px solid var(--border);">Robôs Homologados (Cloud Run Jobs)</div>
      <table>
        <thead>
          <tr>
            <th>Job Name</th>
            <th>Imagem de Contêiner</th>
            <th>CPU / Memória</th>
            <th>Timeout</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${state.jobs.map(j => `
            <tr>
              <td style="font-weight: 700; color: #818cf8;">${escapeHtml(j.job_name)}</td>
              <td style="font-family: monospace; font-size: 11px; color: var(--text-muted);">${escapeHtml(j.image)}</td>
              <td>${escapeHtml(j.cpu)} vCPU / ${escapeHtml(j.memory)}</td>
              <td>${escapeHtml(j.timeout)}</td>
              <td><span class="badge badge-ENABLED">PRONTO</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>

    <div class="table-container">
      <div style="padding: 16px; font-weight: 700; border-bottom: 1px solid var(--border);">Histórico de Execuções Recentes</div>
      <table>
        <thead>
          <tr>
            <th>Execution ID</th>
            <th>Robô</th>
            <th>Status</th>
            <th>Itens Processados</th>
            <th>Iniciado em</th>
            <th>Mensagem</th>
          </tr>
        </thead>
        <tbody>
          ${state.executions.length === 0 ? '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">Nenhuma execução recente registrada.</td></tr>' : ''}
          ${state.executions.map(ex => `
            <tr>
              <td style="font-family: monospace; font-size: 11px;">${escapeHtml(ex.execution_id || ex.task_id)}</td>
              <td style="font-weight: 600;">${escapeHtml(ex.bot_name || 'N/A')}</td>
              <td><span class="badge badge-${ex.status === 'SUCCESS' ? 'DONE' : 'FAILED'}">${escapeHtml(ex.status)}</span></td>
              <td>${ex.processed_items || 0} / ${ex.total_items || 0}</td>
              <td style="font-size: 11px; color: var(--text-muted);">${ex.started_at ? new Date(ex.started_at).toLocaleString('pt-BR') : 'N/A'}</td>
              <td style="font-size: 12px; color: var(--text-muted);">${escapeHtml(ex.message || '')}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderSchedulers() {
  const container = document.getElementById('contentArea');
  container.innerHTML = `
    <div class="table-container">
      <div style="padding: 16px; font-weight: 700; border-bottom: 1px solid var(--border);">Gatilhos Automáticos (Cloud Scheduler)</div>
      <table>
        <thead>
          <tr>
            <th>Nome do Agendamento</th>
            <th>Expressão Cron</th>
            <th>Fuso Horário</th>
            <th>Estado Atual</th>
          </tr>
        </thead>
        <tbody>
          ${state.schedulers.map(s => `
            <tr>
              <td style="font-weight: 700; color: #818cf8;">${escapeHtml(s.scheduler_name)}</td>
              <td style="font-family: monospace; font-weight: bold; color: #38bdf8;">${escapeHtml(s.schedule)}</td>
              <td>${escapeHtml(s.timezone)}</td>
              <td><span class="badge badge-${escapeHtml(s.state)}">${escapeHtml(s.state)}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderLogs() {
  const container = document.getElementById('contentArea');
  container.innerHTML = `
    <div class="table-container">
      <div style="padding: 16px; font-weight: 700; border-bottom: 1px solid var(--border);">Logs Estruturados dos Robôs (Cloud Logging)</div>
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Severidade</th>
            <th>Origem</th>
            <th>Mensagem</th>
          </tr>
        </thead>
        <tbody>
          ${state.logs.length === 0 ? '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 24px;">Nenhum log encontrado.</td></tr>' : ''}
          ${state.logs.map(l => `
            <tr>
              <td style="font-size: 11px; font-family: monospace; white-space: nowrap; color: var(--text-muted);">${escapeHtml(l.timestamp)}</td>
              <td><span class="badge badge-${l.severity === 'ERROR' ? 'FAILED' : (l.severity === 'WARNING' ? 'PROCESSING' : 'DONE')}">${escapeHtml(l.severity)}</span></td>
              <td style="font-size: 11px; font-family: monospace;">${escapeHtml(l.log_name)}</td>
              <td style="font-size: 12px; font-family: monospace;">${escapeHtml(l.message)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderAudit() {
  const container = document.getElementById('contentArea');
  container.innerHTML = `
    <div class="table-container">
      <div style="padding: 16px; font-weight: 700; border-bottom: 1px solid var(--border);">Registro Autoritativo de Auditoria (Audit Trail)</div>
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Usuário / Ator</th>
            <th>Ação</th>
            <th>Recurso Alvo</th>
            <th>Resultado</th>
            <th>Motivo</th>
          </tr>
        </thead>
        <tbody>
          ${state.auditLogs.length === 0 ? '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">Nenhum registro de auditoria gravado.</td></tr>' : ''}
          ${state.auditLogs.map(a => `
            <tr>
              <td style="font-size: 11px; font-family: monospace; color: var(--text-muted);">${escapeHtml(a.timestamp)}</td>
              <td style="font-weight: 600;">${escapeHtml(a.actor_email)}</td>
              <td><span class="badge badge-QUEUED">${escapeHtml(a.action)}</span></td>
              <td style="font-family: monospace; font-size: 11px;">${escapeHtml(a.target_resource)}</td>
              <td><span class="badge badge-${a.result_code === 'SUCCESS' ? 'DONE' : 'FAILED'}">${escapeHtml(a.result_code)}</span></td>
              <td style="font-size: 12px; color: var(--text-muted);">${escapeHtml(a.reason || 'N/A')}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
