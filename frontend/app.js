/**
 * frontend/app.js
 * Vanilla JavaScript application connecting the PS-019 Dashboard to FastAPI endpoints.
 */

// Application State
const state = {
  inventory: [],
  gaps: [],
  evaluation: null,
  rules: null,
  summary: null,
};

// DOM Elements
const elements = {
  // Tabs
  tabButtons: document.querySelectorAll('.tab-btn'),
  tabPanes: document.querySelectorAll('.tab-pane'),

  // Header Actions
  btnRunScan: document.getElementById('btnRunScan'),
  btnRunAnalyze: document.getElementById('btnRunAnalyze'),
  scanBtnLabel: document.getElementById('scanBtnLabel'),
  scanBtnIcon: document.getElementById('scanBtnIcon'),
  statusDot: document.getElementById('systemStatusDot'),
  statusText: document.getElementById('systemStatusText'),

  // Overview Stats
  statScannedFields: document.getElementById('statScannedFields'),
  statCandidates: document.getElementById('statCandidates'),
  statComplete: document.getElementById('statComplete'),
  statGaps: document.getElementById('statGaps'),
  statReviewRequired: document.getElementById('statReviewRequired'),
  gapStatusList: document.getElementById('gapStatusList'),
  ovPrecision: document.getElementById('ovPrecision'),
  ovRecall: document.getElementById('ovRecall'),
  ovF1: document.getElementById('ovF1'),

  // Inventory
  inventoryTableBody: document.getElementById('inventoryTableBody'),
  inventoryCounter: document.getElementById('inventoryCounter'),
  invSearchInput: document.getElementById('invSearchInput'),
  invClassFilter: document.getElementById('invClassFilter'),
  invStatusFilter: document.getElementById('invStatusFilter'),
  invReviewFilter: document.getElementById('invReviewFilter'),
  btnResetInvFilter: document.getElementById('btnResetInvFilter'),

  // Evidence Gaps
  gapsTableBody: document.getElementById('gapsTableBody'),
  gapsCounter: document.getElementById('gapsCounter'),
  gapsSearchInput: document.getElementById('gapsSearchInput'),
  gapsStatusFilter: document.getElementById('gapsStatusFilter'),
  gapsClassFilter: document.getElementById('gapsClassFilter'),

  // Evaluation
  detPrecision: document.getElementById('detPrecision'),
  detRecall: document.getElementById('detRecall'),
  detF1: document.getElementById('detF1'),
  detCounts: document.getElementById('detCounts'),
  perClassTableBody: document.getElementById('perClassTableBody'),
  cmHeaderRow: document.getElementById('cmHeaderRow'),
  cmBody: document.getElementById('cmBody'),
  errorCountBadge: document.getElementById('errorCountBadge'),
  errorListContainer: document.getElementById('errorListContainer'),

  // Rules
  rulesContainer: document.getElementById('rulesContainer'),

  // Modal
  detailModal: document.getElementById('detailModal'),
  modalFieldTitle: document.getElementById('modalFieldTitle'),
  modalDetailsBody: document.getElementById('modalDetailsBody'),
  modalCloseBtn: document.getElementById('modalCloseBtn'),
  modalCloseBtnFooter: document.getElementById('modalCloseBtnFooter'),

  // Toasts
  toastContainer: document.getElementById('toastContainer'),
};

// ---------------------------------------------------------------------------
// Helpers & Utilities
// ---------------------------------------------------------------------------
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✔' : type === 'error' ? '✖' : 'ℹ'}</span><span>${message}</span>`;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function getClassBadge(cls) {
  if (!cls) return `<span class="badge" style="background:#20293a;color:#94a3b8;">Non-PII</span>`;
  const lower = cls.toLowerCase();
  if (lower.includes('identity')) return `<span class="badge badge-class-identity">Identity</span>`;
  if (lower.includes('contact')) return `<span class="badge badge-class-contact">Contact</span>`;
  if (lower.includes('location')) return `<span class="badge badge-class-location">Location</span>`;
  if (lower.includes('financial')) return `<span class="badge badge-class-financial">Financial</span>`;
  if (lower.includes('sensitive') || lower.includes('health')) return `<span class="badge badge-class-sensitive">Sensitive/Health</span>`;
  return `<span class="badge">${cls}</span>`;
}

function getStatusBadge(status) {
  switch (status) {
    case 'Complete':
      return `<span class="badge badge-status-complete">Complete</span>`;
    case 'Purpose Missing':
      return `<span class="badge badge-status-purp-miss">Purpose Missing</span>`;
    case 'Retention Missing':
      return `<span class="badge badge-status-ret-miss">Retention Missing</span>`;
    case 'Purpose & Retention Missing':
      return `<span class="badge badge-status-both-miss">Both Missing</span>`;
    case 'Not Mapped':
      return `<span class="badge badge-status-unmapped">Not Mapped</span>`;
    default:
      return `<span class="badge">${status || 'Unknown'}</span>`;
  }
}

// ---------------------------------------------------------------------------
// Tab Navigation
// ---------------------------------------------------------------------------
function initTabs() {
  elements.tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');
      elements.tabButtons.forEach(b => b.classList.remove('active'));
      elements.tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
    });
  });
}

// ---------------------------------------------------------------------------
// API Data Fetching
// ---------------------------------------------------------------------------
async function fetchSummary() {
  try {
    const res = await fetch('/api/summary');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.summary = data;

    elements.statScannedFields.textContent = data.scanned_fields || 84;
    elements.statCandidates.textContent = data.candidate_fields || 0;
    elements.statComplete.textContent = data.complete_metadata || 0;
    elements.statGaps.textContent = data.evidence_gaps || 0;
    elements.statReviewRequired.textContent = data.review_required || 0;

    // Render Gap Breakdown List in Overview
    const breakdown = data.gaps_by_status || {};
    let html = '';
    const gapCategories = [
      { key: 'Retention Missing', label: 'Retention Missing (Purpose Declared)', badge: 'badge-status-ret-miss' },
      { key: 'Purpose Missing', label: 'Purpose Missing (Retention Declared)', badge: 'badge-status-purp-miss' },
      { key: 'Purpose & Retention Missing', label: 'Purpose & Retention Missing', badge: 'badge-status-both-miss' },
      { key: 'Not Mapped', label: 'Not Mapped (No Governance Record)', badge: 'badge-status-unmapped' },
    ];

    gapCategories.forEach(cat => {
      const count = breakdown[cat.key] || 0;
      html += `
        <div style="display:flex; justify-content:space-between; align-items:center; background:var(--bg-secondary); padding:0.65rem 0.85rem; border-radius:6px;">
          <span style="font-size:0.85rem; color:var(--text-secondary);">${cat.label}</span>
          <span class="badge ${cat.badge}" style="font-size:0.85rem; padding:0.25rem 0.6rem;">${count}</span>
        </div>
      `;
    });
    elements.gapStatusList.innerHTML = html;

    // Snapshot evaluation
    if (data.evaluation) {
      const p = data.evaluation.detection_precision;
      const r = data.evaluation.detection_recall;
      const f = data.evaluation.detection_f1;
      elements.ovPrecision.textContent = p !== null ? `${(p * 100).toFixed(1)}%` : 'N/A';
      elements.ovRecall.textContent = r !== null ? `${(r * 100).toFixed(1)}%` : 'N/A';
      elements.ovF1.textContent = f !== null ? f.toFixed(3) : 'N/A';
    }
  } catch (err) {
    console.error('Error loading summary:', err);
  }
}

async function fetchInventory() {
  try {
    const res = await fetch('/api/inventory');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.inventory = data.records || [];
    renderInventory();
  } catch (err) {
    console.error('Error loading inventory:', err);
    elements.inventoryTableBody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--accent-rose); padding:2rem;">Failed to load inventory: ${err.message}</td></tr>`;
  }
}

function renderInventory() {
  const q = elements.invSearchInput.value.toLowerCase().trim();
  const cls = elements.invClassFilter.value;
  const stat = elements.invStatusFilter.value;
  const rev = elements.invReviewFilter.value;

  const filtered = state.inventory.filter(r => {
    if (q) {
      const matchesSearch =
        r.field_name.toLowerCase().includes(q) ||
        r.source_name.toLowerCase().includes(q) ||
        (r.purpose && r.purpose.toLowerCase().includes(q)) ||
        (r.detected_class && r.detected_class.toLowerCase().includes(q));
      if (!matchesSearch) return false;
    }
    if (cls !== 'All' && r.detected_class !== cls) return false;
    if (stat !== 'All' && r.overall_status !== stat) return false;
    if (rev === 'true' && !r.review_required) return false;
    if (rev === 'false' && r.review_required) return false;
    return true;
  });

  elements.inventoryCounter.textContent = `${filtered.length} of ${state.inventory.length} candidate fields`;

  if (filtered.length === 0) {
    elements.inventoryTableBody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--text-muted); padding:2rem;">No matching candidate fields found.</td></tr>`;
    return;
  }

  let rows = '';
  filtered.forEach((r, idx) => {
    const revBadge = r.review_required
      ? `<span class="badge badge-review" title="${r.detection_reason}">Review Required</span>`
      : `<span style="font-size:0.75rem; color:var(--accent-emerald);">Auto-Triage</span>`;

    const confVal = r.confidence ? r.confidence.toFixed(2) : '0.00';
    const confLevel = r.confidence_level || 'Low';

    rows += `
      <tr>
        <td class="font-mono" style="font-size:0.78rem; color:var(--text-secondary);">${r.source_name}</td>
        <td class="font-mono" style="font-weight:600; color:var(--accent-cyan);">${r.field_name}</td>
        <td>${getClassBadge(r.detected_class)}</td>
        <td>
          <span class="font-mono" style="font-weight:600;">${confVal}</span>
          <span style="font-size:0.72rem; color:var(--text-muted);">(${confLevel})</span>
        </td>
        <td>${revBadge}</td>
        <td style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${r.purpose || 'None declared'}">
          ${r.purpose ? r.purpose : '<span style="color:var(--text-muted); font-style:italic;">Missing</span>'}
        </td>
        <td style="max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${r.retention_period || 'None declared'}">
          ${r.retention_period ? r.retention_period : '<span style="color:var(--text-muted); font-style:italic;">Missing</span>'}
        </td>
        <td>${getStatusBadge(r.overall_status)}</td>
        <td>
          <button class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.75rem;" onclick="openFieldDetails(${idx})">Details</button>
        </td>
      </tr>
    `;
  });
  elements.inventoryTableBody.innerHTML = rows;
}

// ---------------------------------------------------------------------------
// Evidence Gaps Fetching & Rendering
// ---------------------------------------------------------------------------
async function fetchGaps() {
  try {
    const res = await fetch('/api/gaps');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.gaps = data.gaps || [];
    renderGaps();
  } catch (err) {
    console.error('Error loading gaps:', err);
    elements.gapsTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--accent-rose); padding:2rem;">Failed to load gaps: ${err.message}</td></tr>`;
  }
}

function renderGaps() {
  const q = elements.gapsSearchInput.value.toLowerCase().trim();
  const stat = elements.gapsStatusFilter.value;
  const cls = elements.gapsClassFilter.value;

  const filtered = state.gaps.filter(g => {
    if (q) {
      const match =
        g.field_name.toLowerCase().includes(q) ||
        g.source_name.toLowerCase().includes(q) ||
        (g.evidence_note && g.evidence_note.toLowerCase().includes(q));
      if (!match) return false;
    }
    if (stat !== 'All' && g.overall_status !== stat) return false;
    if (cls !== 'All' && g.detected_class !== cls) return false;
    return true;
  });

  elements.gapsCounter.textContent = `${filtered.length} of ${state.gaps.length} evidence gaps`;

  if (filtered.length === 0) {
    elements.gapsTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:2rem;">No matching evidence gaps found.</td></tr>`;
    return;
  }

  let rows = '';
  filtered.forEach((g) => {
    const missingStr = g.missing_items && g.missing_items.length > 0
      ? g.missing_items.join(', ')
      : 'purpose, retention';

    rows += `
      <tr>
        <td class="font-mono" style="font-size:0.78rem; color:var(--text-secondary);">${g.source_name}</td>
        <td class="font-mono" style="font-weight:600; color:var(--accent-cyan);">${g.field_name}</td>
        <td>${getClassBadge(g.detected_class)}</td>
        <td>${getStatusBadge(g.overall_status)}</td>
        <td class="font-mono" style="font-size:0.78rem; color:var(--accent-amber);">${missingStr}</td>
        <td style="font-size:0.8rem; color:var(--text-secondary); max-width:280px;">${g.evidence_note}</td>
        <td>
          <button class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.75rem;" onclick="openGapDetails('${g.source_name}', '${g.field_name}')">Inspect</button>
        </td>
      </tr>
    `;
  });
  elements.gapsTableBody.innerHTML = rows;
}

// ---------------------------------------------------------------------------
// Evaluation Fetching & Rendering
// ---------------------------------------------------------------------------
async function fetchEvaluation() {
  try {
    const res = await fetch('/api/evaluation');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.evaluation = data;

    // 1. Detection Metrics
    const dm = data.detection_metrics || {};
    elements.detPrecision.textContent = dm.precision !== null ? `${(dm.precision * 100).toFixed(1)}%` : 'N/A';
    elements.detRecall.textContent = dm.recall !== null ? `${(dm.recall * 100).toFixed(1)}%` : 'N/A';
    elements.detF1.textContent = dm.f1 !== null ? dm.f1.toFixed(3) : 'N/A';
    elements.detCounts.textContent = `TP: ${dm.tp} | FP: ${dm.fp} | FN: ${dm.fn} | TN: ${dm.tn}`;

    // 2. Per-Class Table
    const perClass = data.per_class_metrics || [];
    let pRows = '';
    perClass.forEach(m => {
      const prec = m.precision !== null ? m.precision.toFixed(3) : 'N/A';
      const rec = m.recall !== null ? m.recall.toFixed(3) : 'N/A';
      const f1 = m.f1 !== null ? m.f1.toFixed(3) : 'N/A';
      const isLimited = m.status && m.status.includes('Limited Sample');
      const statusNote = isLimited
        ? `<span class="badge badge-review">${m.status}</span>`
        : `<span style="font-size:0.75rem; color:var(--text-muted);">${m.status}</span>`;

      pRows += `
        <tr>
          <td>${getClassBadge(m.class_name)}</td>
          <td class="font-mono">${m.tp}</td>
          <td class="font-mono">${m.fp}</td>
          <td class="font-mono">${m.fn}</td>
          <td class="font-mono" style="font-weight:600;">${m.support}</td>
          <td class="font-mono" style="color:var(--accent-cyan);">${prec}</td>
          <td class="font-mono" style="color:var(--accent-emerald);">${rec}</td>
          <td class="font-mono" style="font-weight:700; color:var(--accent-teal);">${f1}</td>
          <td>${statusNote}</td>
        </tr>
      `;
    });
    elements.perClassTableBody.innerHTML = pRows;

    // 3. Confusion Matrix
    const cm = data.confusion_matrix || {};
    const rowKeys = Object.keys(cm);
    if (rowKeys.length > 0) {
      const colKeys = Object.keys(cm[rowKeys[0]]);
      let headerHtml = '<th>Expected ↓ / Pred →</th>';
      colKeys.forEach(col => {
        headerHtml += `<th style="text-align:center;">${col}</th>`;
      });
      elements.cmHeaderRow.innerHTML = headerHtml;

      let cmRows = '';
      rowKeys.forEach(rKey => {
        cmRows += `<tr><td style="font-weight:600; color:var(--text-secondary);">${rKey}</td>`;
        colKeys.forEach(cKey => {
          const val = cm[rKey][cKey] || 0;
          const isDiagonal = rKey === cKey || (rKey === 'Non-PII' && cKey === 'Not Detected');
          const style = isDiagonal
            ? 'background:rgba(0, 210, 255, 0.12); font-weight:700; color:var(--accent-cyan);'
            : (val > 0 ? 'background:rgba(244, 63, 94, 0.12); color:var(--accent-rose); font-weight:600;' : 'color:var(--text-muted);');
          cmRows += `<td class="font-mono" style="text-align:center; ${style}">${val}</td>`;
        });
        cmRows += '</tr>';
      });
      elements.cmBody.innerHTML = cmRows;
    }

    // 4. Discrepancies & Errors List
    const errors = data.detailed_errors || [];
    elements.errorCountBadge.textContent = errors.length;
    if (errors.length === 0) {
      elements.errorListContainer.innerHTML = `<div style="color:var(--accent-emerald); font-size:0.85rem;">No misclassifications or false detections found.</div>`;
    } else {
      let errHtml = '';
      errors.forEach((e, idx) => {
        errHtml += `
          <div style="background:var(--bg-secondary); border:1px solid var(--border-color); padding:0.85rem; border-radius:6px; margin-bottom:0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
              <span class="font-mono" style="font-weight:600; color:var(--accent-cyan); font-size:0.85rem;">${e.source_name} → ${e.field_name}</span>
              <span class="badge badge-status-both-miss" style="font-size:0.72rem;">${e.error_type}</span>
            </div>
            <div style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:0.25rem;">
              <strong>Expected:</strong> ${e.expected_class || 'Non-PII'} &nbsp;|&nbsp; 
              <strong>Predicted:</strong> ${e.predicted_class || 'Not Detected'} (Conf: ${e.confidence || 'N/A'})
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); font-style:italic;">
              ${e.reason || 'No reasoning captured.'}
            </div>
          </div>
        `;
      });
      elements.errorListContainer.innerHTML = errHtml;
    }

  } catch (err) {
    console.error('Error loading evaluation:', err);
  }
}

// ---------------------------------------------------------------------------
// Detection Rules Fetching & Rendering
// ---------------------------------------------------------------------------
async function fetchRules() {
  try {
    const res = await fetch('/api/rules');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.rules = data;

    const classes = data.classes || {};
    let html = '';

    for (const [clsName, conf] of Object.entries(classes)) {
      const keywords = (conf.keywords || []).slice(0, 14).join(', ');
      const moreKw = conf.keywords && conf.keywords.length > 14 ? ` + ${conf.keywords.length - 14} more` : '';
      const patterns = (conf.patterns || []).map(p => `<code>${p.name}</code> (${p.regex})`).join(', ') || 'None';

      html += `
        <div style="background:var(--bg-secondary); border:1px solid var(--border-color); padding:1.15rem; border-radius:8px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
              ${getClassBadge(clsName)}
              <span style="font-size:0.85rem; color:var(--text-secondary);">${conf.description || ''}</span>
            </div>
            <span class="font-mono" style="font-size:0.75rem; color:var(--text-muted);">${(conf.keywords || []).length} keywords</span>
          </div>
          <div style="font-size:0.8rem; margin-bottom:0.4rem;">
            <strong style="color:var(--text-muted);">Keywords:</strong> <span class="font-mono" style="color:var(--text-secondary);">${keywords}${moreKw}</span>
          </div>
          <div style="font-size:0.8rem;">
            <strong style="color:var(--text-muted);">Regex Patterns:</strong> <span class="font-mono" style="color:var(--accent-cyan);">${patterns}</span>
          </div>
        </div>
      `;
    }
    elements.rulesContainer.innerHTML = html;
  } catch (err) {
    console.error('Error loading rules:', err);
    elements.rulesContainer.innerHTML = `<div style="color:var(--accent-rose); font-size:0.85rem;">Failed to load rules: ${err.message}</div>`;
  }
}

// ---------------------------------------------------------------------------
// Modal Details Viewer
// ---------------------------------------------------------------------------
window.openFieldDetails = function(idx) {
  const item = state.inventory[idx];
  if (!item) return;

  elements.modalFieldTitle.textContent = `${item.source_name} → ${item.field_name}`;
  elements.modalDetailsBody.innerHTML = `
    <div class="detail-row"><div class="detail-label">Source Type</div><div class="detail-value font-mono">${item.source_type}</div></div>
    <div class="detail-row"><div class="detail-label">Source File / DB</div><div class="detail-value font-mono">${item.source_name}</div></div>
    <div class="detail-row"><div class="detail-label">Field Name</div><div class="detail-value font-mono" style="color:var(--accent-cyan); font-weight:600;">${item.field_name}</div></div>
    <div class="detail-row"><div class="detail-label">Detected Class</div><div class="detail-value">${getClassBadge(item.detected_class)}</div></div>
    <div class="detail-row"><div class="detail-label">Confidence Score</div><div class="detail-value font-mono">${item.confidence ? item.confidence.toFixed(4) : '0.00'} (${item.confidence_level})</div></div>
    <div class="detail-row"><div class="detail-label">Triage Flag</div><div class="detail-value">${item.review_required ? '<span class="badge badge-review">Human Review Required</span>' : '<span style="color:var(--accent-emerald);">Automated High-Confidence</span>'}</div></div>
    <div class="detail-row"><div class="detail-label">Declared Purpose</div><div class="detail-value">${item.purpose || '<em style="color:var(--text-muted);">Not declared (Evidence Gap)</em>'}</div></div>
    <div class="detail-row"><div class="detail-label">Retention Period</div><div class="detail-value">${item.retention_period || '<em style="color:var(--text-muted);">Not declared (Evidence Gap)</em>'}</div></div>
    <div class="detail-row"><div class="detail-label">Metadata Owner</div><div class="detail-value">${item.metadata_owner || '<em style="color:var(--text-muted);">Unassigned</em>'}</div></div>
    <div class="detail-row"><div class="detail-label">Metadata Status</div><div class="detail-value">${getStatusBadge(item.overall_status)}</div></div>
    <div class="detail-row"><div class="detail-label">Missing Items</div><div class="detail-value font-mono" style="color:var(--accent-amber);">${item.missing_items && item.missing_items.length > 0 ? item.missing_items.join(', ') : 'None (Complete)'}</div></div>
    <div class="detail-row"><div class="detail-label">Detection Reason</div><div class="detail-value" style="font-size:0.8rem; color:var(--text-secondary); background:var(--bg-secondary); padding:0.5rem; border-radius:4px;">${item.detection_reason || 'N/A'}</div></div>
    <div class="detail-row"><div class="detail-label">Governance Note</div><div class="detail-value" style="font-size:0.8rem; color:var(--text-secondary); background:var(--bg-secondary); padding:0.5rem; border-radius:4px;">${item.evidence_note || 'N/A'}</div></div>
  `;
  elements.detailModal.classList.add('active');
};

window.openGapDetails = function(sourceName, fieldName) {
  const idx = state.inventory.findIndex(r => r.source_name === sourceName && r.field_name === fieldName);
  if (idx !== -1) {
    window.openFieldDetails(idx);
  }
};

function closeModal() {
  elements.detailModal.classList.remove('active');
}

// ---------------------------------------------------------------------------
// Run Full Scan & Run Pipeline Triggers
// ---------------------------------------------------------------------------
async function handleRunScan() {
  elements.btnRunScan.disabled = true;
  elements.scanBtnLabel.textContent = 'Scanning Data...';
  elements.scanBtnIcon.innerHTML = '<span class="spinner"></span>';

  try {
    const res = await fetch('/api/scan', { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    showToast(`Scan complete: ${data.detected_candidates_count} candidates discovered across ${data.scanned_fields_count} fields.`, 'success');
    
    // Automatically refresh full application state
    await refreshAll();
  } catch (err) {
    console.error('Scan error:', err);
    showToast(`Scan failed: ${err.message}`, 'error');
  } finally {
    elements.btnRunScan.disabled = false;
    elements.scanBtnLabel.textContent = 'Run Full Scan';
    elements.scanBtnIcon.textContent = '▶';
  }
}

async function handleRunAnalyze() {
  elements.btnRunAnalyze.disabled = true;
  elements.btnRunAnalyze.innerHTML = '<span class="spinner"></span> <span>Running Pipeline...</span>';

  try {
    const res = await fetch('/api/analyze', { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    showToast(`Pipeline complete: ${data.inventory_count} inventory records, ${data.total_gaps_count} evidence gaps evaluated.`, 'success');
    await refreshAll();
  } catch (err) {
    console.error('Analysis error:', err);
    showToast(`Pipeline failed: ${err.message}`, 'error');
  } finally {
    elements.btnRunAnalyze.disabled = false;
    elements.btnRunAnalyze.innerHTML = '<span>⚙</span> <span>Run Pipeline</span>';
  }
}

async function refreshAll() {
  await Promise.all([
    fetchSummary(),
    fetchInventory(),
    fetchGaps(),
    fetchEvaluation(),
    fetchRules(),
  ]);
}

// ---------------------------------------------------------------------------
// Event Listeners Initialization
// ---------------------------------------------------------------------------
function initEvents() {
  initTabs();

  // Action Buttons
  elements.btnRunScan.addEventListener('click', handleRunScan);
  elements.btnRunAnalyze.addEventListener('click', handleRunAnalyze);

  // Modal Close
  elements.modalCloseBtn.addEventListener('click', closeModal);
  elements.modalCloseBtnFooter.addEventListener('click', closeModal);
  elements.detailModal.addEventListener('click', (e) => {
    if (e.target === elements.detailModal) closeModal();
  });

  // Inventory Filters
  elements.invSearchInput.addEventListener('input', renderInventory);
  elements.invClassFilter.addEventListener('change', renderInventory);
  elements.invStatusFilter.addEventListener('change', renderInventory);
  elements.invReviewFilter.addEventListener('change', renderInventory);
  elements.btnResetInvFilter.addEventListener('click', () => {
    elements.invSearchInput.value = '';
    elements.invClassFilter.value = 'All';
    elements.invStatusFilter.value = 'All';
    elements.invReviewFilter.value = 'All';
    renderInventory();
  });

  // Gaps Filters
  elements.gapsSearchInput.addEventListener('input', renderGaps);
  elements.gapsStatusFilter.addEventListener('change', renderGaps);
  elements.gapsClassFilter.addEventListener('change', renderGaps);
}

// Bootstrap
document.addEventListener('DOMContentLoaded', () => {
  initEvents();
  refreshAll();
});
