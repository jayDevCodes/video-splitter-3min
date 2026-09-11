import { ProgressManager } from './progress/progress_manager.js';

const $ = (selector) => document.querySelector(selector);
const splitForm = $('#split-form');
const uploadForm = $('#multi-upload-form');
const accountForm = $('#account-form');
const oldBtn = $('#show-old-upload-btn');
const oldSection = $('#old-upload-section');
const uploadSection = $('#upload-section');
const folderSelect = $('#old-folder-select');
const folderEmpty = $('#old-folder-empty');
const fileInput = $('#video-file');
const fileName = $('#file-name');
const statusBox = $('#status');
const resultBox = $('#result');
const uploadResultBox = $('#upload-result');
const accountTargetsBox = $('#account-targets');
const uploadButton = $('#upload-btn');
const splitButton = $('#split-btn');
const outputFolderBox = $('#output-folder');
const partsCountBox = $('#parts-count');
const outputDirectoryInput = $('#upload-output-directory');
const titleInput = $('#upload-title-template');
const descriptionInput = $('#upload-description');
const gapInput = $('#upload-gap');
const tagsInput = $('#upload-tags');
const privacyInput = $('#upload-privacy');
const categoryInput = $('#upload-category-id');
const deleteInput = $('#delete-after-upload');
const thumbnailInput = $('#upload-thumbnail');
const liveProgressBox = $('#live-progress');

let generatedFolder = '';
let accounts = { youtube: [], facebook: [], instagram: [] };
const progress = new ProgressManager(liveProgressBox);

fileInput?.addEventListener('change', () => {
  fileName.textContent = fileInput.files?.[0]?.name || 'MP4, MOV, MKV, AVI, WEBM and more';
});

async function loadAccounts() {
  const response = await fetch('/api/accounts', { cache: 'no-store' });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Unable to load accounts.');
  accounts = data.accounts || accounts;
  renderAccounts();
}

function renderAccounts(savedTargets = []) {
  const saved = new Set(savedTargets.map((item) => item.account_id));
  const groups = [['youtube', 'YouTube Channels'], ['facebook', 'Facebook Pages'], ['instagram', 'Instagram Accounts']];
  accountTargetsBox.innerHTML = groups.map(([platform, label]) => {
    const list = accounts[platform] || [];
    const rows = list.length ? list.map((account) => `
      <label class="account-option">
        <input type="checkbox" data-account-id="${escapeHtml(account.id)}" data-platform="${platform}" ${saved.has(account.id) ? 'checked' : ''} ${account.configured === false ? 'disabled' : ''}>
        <span><strong>${escapeHtml(account.name)}</strong><small>${account.configured === false ? 'Not connected' : 'Connected'}${account.external_id ? ` · ${escapeHtml(account.external_id)}` : ''}</small></span>
      </label>`).join('') : '<div class="muted">No accounts connected.</div>';
    return `<div class="account-group"><div class="account-group-title">${label}</div>${rows}</div>`;
  }).join('');
}

function selectedTargets() {
  return [...accountTargetsBox.querySelectorAll('input[data-account-id]:checked')].map((input) => ({ account_id: input.dataset.accountId, platform: input.dataset.platform }));
}

async function loadFolders() {
  const response = await fetch('/api/upload/folders', { cache: 'no-store' });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Unable to load folders.');
  folderSelect.innerHTML = '<option value="">Select an output folder…</option>';
  for (const folder of data.folders || []) {
    const option = document.createElement('option');
    option.value = folder.output_directory;
    option.textContent = `${folder.folder} — ${folder.remaining} remaining`;
    folderSelect.appendChild(option);
  }
  folderSelect.disabled = !(data.folders || []).length;
  folderEmpty.hidden = !!(data.folders || []).length;
  return data.folders || [];
}

async function openFolder(path) {
  const response = await fetch(`/api/upload/folder?output_directory=${encodeURIComponent(path)}`, { cache: 'no-store' });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Unable to open folder.');
  generatedFolder = data.output_directory;
  outputDirectoryInput.value = generatedFolder;
  outputFolderBox.textContent = data.folder || generatedFolder.split('/').pop();
  partsCountBox.textContent = String(data.remaining ?? 0);
  const metadata = data.metadata || {};
  const youtube = metadata.youtube || {};
  const upload = metadata.upload || {};
  titleInput.value = metadata.title_template || '{filename} #{number}';
  descriptionInput.value = metadata.description || '';
  tagsInput.value = Array.isArray(metadata.tags) ? metadata.tags.join(', ') : 'shorts,youtube';
  privacyInput.value = youtube.privacy || 'private';
  categoryInput.value = youtube.category_id || '22';
  gapInput.value = String(data.upload_job?.gap_seconds ?? upload.gap_seconds ?? 60);
  deleteInput.checked = upload.delete_after_upload !== false;
  thumbnailInput.value = '';
  renderAccounts(data.upload_job?.targets || []);
  uploadSection.hidden = false;
}

accountForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = {
    id: $('#account-id').value.trim(),
    platform: $('#account-platform').value,
    name: $('#account-name').value.trim(),
    external_id: $('#account-external-id').value.trim() || null,
    type: $('#account-platform').value === 'facebook' ? 'page' : $('#account-platform').value === 'instagram' ? 'professional_account' : 'channel',
    enabled: true,
    configured: $('#account-configured').checked,
  };
  if (!payload.id || !payload.name) return;
  try {
    const response = await fetch('/api/accounts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to save account.');
    accountForm.reset();
    $('#account-configured').checked = true;
    statusBox.hidden = false;
    statusBox.textContent = `Account saved: ${payload.name}.`;
    await loadAccounts();
  } catch (error) {
    statusBox.hidden = false;
    statusBox.textContent = error.message;
  }
});

splitForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files?.[0];
  if (!file) return;
  splitButton.disabled = true;
  oldBtn.disabled = true;
  statusBox.hidden = false;
  statusBox.textContent = 'Starting video split job…';
  liveProgressBox.hidden = false;
  liveProgressBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
  try {
    const formData = new FormData();
    formData.append('file', file);
    const chunk = Number($('#chunk-seconds').value || 180);
    const orientation = $('#orientation').value;
    const response = await fetch(`/api/video/split/start?chunk_seconds=${encodeURIComponent(chunk)}&orientation=${encodeURIComponent(orientation)}`, { method: 'POST', body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to start Shorts generation.');

    await progress.start(data.job_id, {
      onComplete: async (job) => {
        const result = job.result || {};
        await loadAccounts();
        await openFolder(result.output_directory);
        resultBox.hidden = false;
        resultBox.innerHTML = `<strong>Generation complete.</strong><br><br>Folder: <code>${escapeHtml(result.output_directory)}</code><br>Clips: ${result.parts_created}`;
        oldSection.hidden = true;
        uploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        statusBox.textContent = `Generated ${result.parts_created} clip(s). Choose exact upload accounts.`;
        splitButton.disabled = false;
        oldBtn.disabled = false;
      },
      onError: (message) => {
        statusBox.textContent = message;
        splitButton.disabled = false;
        oldBtn.disabled = false;
      },
    });
  } catch (error) {
    statusBox.textContent = error.message;
    splitButton.disabled = false;
    oldBtn.disabled = false;
  }
});

oldBtn?.addEventListener('click', async () => {
  oldSection.hidden = false;
  uploadSection.hidden = true;
  statusBox.hidden = false;
  statusBox.textContent = 'Loading folders and account connections…';
  try {
    await loadAccounts();
    const folders = await loadFolders();
    statusBox.textContent = folders.length ? 'Select a folder to configure its upload targets.' : 'No pending output folders found.';
  } catch (error) {
    statusBox.textContent = error.message;
  }
});

folderSelect?.addEventListener('change', async () => {
  if (!folderSelect.value) { uploadSection.hidden = true; return; }
  statusBox.hidden = false;
  statusBox.textContent = 'Restoring saved queue configuration…';
  try {
    await openFolder(folderSelect.value);
    statusBox.textContent = 'Saved queue loaded. Choose accounts or keep the saved selection.';
    uploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    statusBox.textContent = error.message;
  }
});

uploadForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const targets = selectedTargets();
  if (!generatedFolder) return;
  if (!targets.length) { statusBox.textContent = 'Select at least one account target.'; return; }
  const gap = Math.max(0, Math.min(86400, Number(gapInput.value || 0)));
  uploadButton.disabled = true; splitButton.disabled = true; oldBtn.disabled = true;
  statusBox.hidden = false;
  statusBox.textContent = `Starting ${targets.length} account target(s)…`;
  liveProgressBox.hidden = false;
  liveProgressBox.scrollIntoView({ behavior: 'smooth', block: 'center' });

  const formData = new FormData();
  formData.append('output_directory', generatedFolder);
  formData.append('targets', JSON.stringify(targets));
  formData.append('title_template', titleInput.value);
  formData.append('description', descriptionInput.value);
  formData.append('tags', tagsInput.value);
  formData.append('privacy', privacyInput.value);
  formData.append('category_id', categoryInput.value);
  formData.append('made_for_kids', 'false');
  formData.append('gap_seconds', String(gap));
  formData.append('delete_after_upload', deleteInput.checked ? 'true' : 'false');
  if (thumbnailInput.files?.[0]) formData.append('thumbnail', thumbnailInput.files[0]);

  try {
    const response = await fetch('/api/upload/start', { method: 'POST', body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Upload queue failed.');

    await progress.start(data.job_id, {
      onComplete: async (job) => {
        renderReport(job.result || {}, gap);
        await loadFolders();
        uploadButton.disabled = false; splitButton.disabled = false; oldBtn.disabled = false;
      },
      onError: async (message) => {
        statusBox.textContent = message;
        await loadFolders();
        uploadButton.disabled = false; splitButton.disabled = false; oldBtn.disabled = false;
      },
    });
  } catch (error) {
    statusBox.textContent = error.message;
    uploadButton.disabled = false; splitButton.disabled = false; oldBtn.disabled = false;
  }
});

function renderReport(data, gap) {
  statusBox.textContent = data.stopped_on_error ? `Queue paused after an account error. ${data.remaining_files} clip(s) remain.` : `Queue run saved. ${data.processed} clip(s) processed with a mandatory ${gap}s gap.`;
  uploadResultBox.hidden = false;
  uploadResultBox.innerHTML = (data.results || []).map((clip) => {
    const targets = Object.values(clip.targets || {}).map((target) => `<li><strong>${escapeHtml(target.account_name || target.account_id)}</strong> — ${escapeHtml(target.status)}${target.url ? ` — <a href="${escapeHtml(target.url)}" target="_blank" rel="noopener">Open</a>` : ''}${target.error ? ` — ${escapeHtml(target.error)}` : ''}</li>`).join('');
    return `<div><code>${escapeHtml(clip.filename)}</code><ul>${targets}</ul></div>`;
  }).join('') || '<strong>No clips processed.</strong>';
}

window.addEventListener('DOMContentLoaded', () => {
  uploadSection.hidden = true;
  oldSection.hidden = true;
  liveProgressBox.hidden = true;
  loadAccounts().catch(() => {});
});

function escapeHtml(value) {
  return String(value).replace(/[&<>\"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}
