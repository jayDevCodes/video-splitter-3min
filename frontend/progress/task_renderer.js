import { animationFor } from './animation_manager.js';

function esc(value) {
  return String(value ?? '').replace(/[&<>\"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}

function statusLabel(status) {
  return ({ completed: 'Completed', running: 'Working', waiting: 'Waiting', failed: 'Failed', queued: 'Queued', encoding: 'Encoding' })[status] || status || 'Working';
}

function platformIcon(platform) {
  return platform === 'youtube' ? '▶️' : platform === 'facebook' ? '🔵' : platform === 'instagram' ? '🟣' : '🌐';
}

export function renderProgress(root, model) {
  if (!root) return;
  const currentTask = model.currentTask || 'generic';
  const animation = animationFor(currentTask);
  const status = model.status || 'queued';
  const title = model.label || animation.label;
  const detail = model.detail || model.clip || (status === 'completed' ? 'Finished' : 'Starting…');
  const percent = Number.isFinite(model.progress) ? Math.max(0, Math.min(100, model.progress)) : 0;
  const indeterminate = model.indeterminate && status === 'running';

  root.innerHTML = `
    <div class="live-progress-head">
      <div>
        <div class="section-kicker">LIVE TASK MONITOR</div>
        <h3>${esc(title)}</h3>
        <p>${esc(detail)}</p>
      </div>
      <span class="live-job-status status-${esc(status)}">${esc(statusLabel(status))}</span>
    </div>
    <div class="task-animation ${animation.className} ${status === 'running' || status === 'waiting' || status === 'encoding' ? 'is-active' : ''}">
      <div class="task-animation-icon">${animation.icon}</div>
      <div class="task-animation-track"><div class="task-animation-bar ${indeterminate ? 'indeterminate' : ''}" style="width:${percent}%"></div></div>
      <strong>${indeterminate ? 'Uploading…' : `${percent}%`}</strong>
    </div>
    ${model.accountRows?.length ? `<div class="live-account-list">${model.accountRows.map((row) => `
      <div class="live-account-row account-${esc(row.status)}">
        <span class="account-platform-icon">${platformIcon(row.platform)}</span>
        <div class="live-account-copy"><strong>${esc(row.accountName)}</strong><small>${esc(statusLabel(row.status))}${row.error ? ` · ${esc(row.error)}` : ''}</small></div>
        <span class="live-account-progress">${row.status === 'running' ? '…' : row.status === 'completed' ? '✓' : row.status === 'failed' ? '!' : '⏳'}</span>
      </div>`).join('')}</div>` : ''}
    ${model.waitingSeconds > 0 ? `<div class="gap-countdown"><span>⏱️ Next clip in</span><strong>${model.waitingSeconds}s</strong></div>` : ''}
    ${model.error ? `<div class="live-error">${esc(model.error)}</div>` : ''}
  `;
}
