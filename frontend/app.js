const splitForm = document.querySelector('#split-form');
const youtubeForm = document.querySelector('#youtube-form');
const fileInput = document.querySelector('#video-file');
const fileName = document.querySelector('#file-name');
const splitButton = document.querySelector('#split-btn');
const oldUploadButton = document.querySelector('#old-upload-btn');
const uploadButton = document.querySelector('#upload-btn');
const statusBox = document.querySelector('#status');
const resultBox = document.querySelector('#result');
const uploadResultBox = document.querySelector('#upload-result');
const uploadSection = document.querySelector('#upload-section');
const pendingSection = document.querySelector('#pending-section');
const pendingList = document.querySelector('#pending-list');
const pendingCountBadge = document.querySelector('#pending-count-badge');
const outputFolderBox = document.querySelector('#output-folder');
const partsCountBox = document.querySelector('#parts-count');
const uploadOutputDirectory = document.querySelector('#upload-output-directory');
const uploadSummary = document.querySelector('#upload-summary');
const uploadHeading = document.querySelector('#upload-heading');

let generatedFolder = '';

fileInput.addEventListener('change', () => {
  fileName.textContent = fileInput.files?.[0]?.name || 'MP4, MOV, MKV, AVI, WEBM and more';
});

oldUploadButton.addEventListener('click', async () => {
  pendingSection.hidden = false;
  statusBox.hidden = false;
  statusBox.textContent = 'Loading previously generated output folders…';
  try {
    await loadPendingFolders();
    pendingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    statusBox.textContent = 'Select a folder to continue its YouTube upload queue.';
  } catch (error) {
    statusBox.textContent = error.message;
  }
});

splitForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files?.[0];
  if (!file) return;

  splitButton.disabled = true;
  oldUploadButton.disabled = true;
  uploadSection.hidden = true;
  resultBox.hidden = true;
  uploadResultBox.hidden = true;
  statusBox.hidden = false;
  statusBox.textContent = 'Generating all Shorts… YouTube upload is paused until generation finishes.';

  const chunkSeconds = Number(document.querySelector('#chunk-seconds').value || 180);
  const orientation = document.querySelector('#orientation').value;
  const size = orientation === 'vertical' ? '1080 × 1920 (9:16)' : '1920 × 1080 (16:9)';
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`/api/video/split?chunk_seconds=${encodeURIComponent(chunkSeconds)}&orientation=${encodeURIComponent(orientation)}`, { method: 'POST', body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to generate the Shorts.');

    showUploadForm({ output_directory: data.output_directory, folder: data.output_directory.split('/').pop(), remaining: data.parts_created, generated_now: data.parts_created, uploaded: 0, metadata: {} });
    statusBox.textContent = `Generation complete — ${data.parts_created} Short(s) created at ${size}.`;
    resultBox.hidden = false;
    resultBox.innerHTML = `<strong>All Shorts generated successfully.</strong><br><br><strong>Output folder:</strong> <code>${escapeHtml(data.output_directory)}</code><br><br><strong>Generated Shorts:</strong><ul>${data.parts.map(name => `<li><code>${escapeHtml(name)}</code></li>`).join('')}</ul><p class="muted">Nothing was uploaded to YouTube during generation.</p>`;
    await loadPendingFolders();
    uploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    statusBox.textContent = error.message;
  } finally {
    splitButton.disabled = false;
    oldUploadButton.disabled = false;
  }
});

youtubeForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!generatedFolder) return;

  uploadButton.disabled = true;
  splitButton.disabled = true;
  oldUploadButton.disabled = true;
  uploadResultBox.hidden = true;
  statusBox.hidden = false;
  statusBox.textContent = 'Uploading Shorts in generated order…';

  const formData = new FormData();
  formData.append('output_directory', generatedFolder);
  formData.append('title_template', document.querySelector('#upload-title-template').value);
  formData.append('description', document.querySelector('#upload-description').value);
  formData.append('tags', document.querySelector('#upload-tags').value);
  formData.append('privacy', document.querySelector('#upload-privacy').value);
  formData.append('category_id', document.querySelector('#upload-category-id').value);
  formData.append('made_for_kids', 'false');
  formData.append('gap_seconds', document.querySelector('#upload-gap').value || '60');
  formData.append('delete_after_upload', 'true');
  const thumbnail = document.querySelector('#upload-thumbnail').files?.[0];
  if (thumbnail) formData.append('thumbnail', thumbnail);

  try {
    const response = await fetch('/api/youtube/upload', { method: 'POST', body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to upload to YouTube.');

    const successCount = data.results.filter(item => item.status === 'uploaded').length;
    const failedCount = data.results.filter(item => item.status === 'failed').length;
    statusBox.textContent = failedCount
      ? `${successCount} uploaded. Queue stopped on an error; ${data.remaining_files} Short(s) remain.`
      : `YouTube upload complete — ${successCount} Short(s) uploaded.`;
    uploadResultBox.hidden = false;
    uploadResultBox.innerHTML = `<strong>YouTube upload report</strong><br><br><strong>Order:</strong> part_001 → part_002 → part_003 → …<br><strong>Remaining local MP4s:</strong> ${data.remaining_files}<br><br><ul>${data.results.map(item => `<li><code>${escapeHtml(item.filename)}</code> — <strong>${escapeHtml(item.status)}</strong>${item.url ? ` — <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">Open on YouTube</a>` : ''}${item.deleted ? ' — deleted locally' : ''}${item.error ? ` — ${escapeHtml(item.error)}` : ''}</li>`).join('')}</ul>`;
    await loadPendingFolders();
  } catch (error) {
    statusBox.textContent = error.message;
  } finally {
    uploadButton.disabled = false;
    splitButton.disabled = false;
    oldUploadButton.disabled = false;
  }
});

async function loadPendingFolders() {
  const response = await fetch('/api/youtube/folders', { cache: 'no-store' });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Unable to load output folders.');
  renderPendingFolders(data.folders || []);
  return data.folders || [];
}

function renderPendingFolders(folders) {
  if (!folders.length) {
    pendingSection.hidden = true;
    pendingCountBadge.textContent = '0 FOLDERS';
    pendingList.innerHTML = '';
    return;
  }

  pendingSection.hidden = false;
  pendingCountBadge.textContent = `${folders.length} ${folders.length === 1 ? 'FOLDER' : 'FOLDERS'}`;
  pendingList.innerHTML = folders.map(folder => `
    <article class="pending-item">
      <div class="pending-main">
        <div class="pending-icon">YT</div>
        <div class="pending-copy">
          <strong>${escapeHtml(folder.folder)}</strong>
          <span>${folder.generated_now} generated · ${folder.uploaded} uploaded · <b>${folder.remaining} remaining</b></span>
        </div>
      </div>
      <button class="continue-btn" type="button" data-folder="${escapeHtml(folder.output_directory)}">Continue Upload</button>
    </article>
  `).join('');

  pendingList.querySelectorAll('.continue-btn').forEach(button => {
    button.addEventListener('click', () => openExistingFolder(button.dataset.folder));
  });
}

async function openExistingFolder(outputDirectory) {
  statusBox.hidden = false;
  statusBox.textContent = 'Loading saved YouTube details…';
  try {
    const response = await fetch(`/api/youtube/folder?output_directory=${encodeURIComponent(outputDirectory)}`, { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to open this upload queue.');
    showUploadForm(data);
    pendingSection.hidden = true;
    statusBox.textContent = `${data.remaining} Short(s) are waiting in this folder. Saved settings are loaded.`;
    uploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    statusBox.textContent = error.message;
  }
}

function showUploadForm(data) {
  generatedFolder = data.output_directory;
  uploadOutputDirectory.value = data.output_directory;
  outputFolderBox.textContent = data.folder || data.output_directory;
  partsCountBox.textContent = String(data.remaining ?? data.pending_order?.length ?? 0);

  const metadata = data.metadata || {};
  const youtube = metadata.youtube || {};
  const upload = metadata.upload || {};
  document.querySelector('#upload-title-template').value = metadata.title_template || '{filename} #{number}';
  document.querySelector('#upload-description').value = metadata.description || '';
  document.querySelector('#upload-tags').value = Array.isArray(metadata.tags) ? metadata.tags.join(', ') : 'shorts,youtube';
  document.querySelector('#upload-gap').value = String(upload.gap_seconds ?? 60);
  document.querySelector('#upload-privacy').value = youtube.privacy || 'private';
  document.querySelector('#upload-category-id').value = youtube.category_id || '22';

  uploadSection.hidden = false;
  uploadHeading.textContent = data.uploaded > 0 ? 'Continue YouTube Upload' : 'Now Upload to YouTube';
  uploadSummary.textContent = data.remaining
    ? `${data.remaining} Short(s) remain. Saved title, description and upload gap have been restored.`
    : 'This folder has no remaining Shorts to upload.';
  uploadButton.disabled = !data.remaining;
}

loadPendingFolders().catch(() => {});

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}
