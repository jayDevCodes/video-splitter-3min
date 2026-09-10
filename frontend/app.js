const splitForm = document.querySelector('#split-form');
const youtubeForm = document.querySelector('#youtube-form');
const showOldUploadBtn = document.querySelector('#show-old-upload-btn');
const generationSection = document.querySelector('#generation-section');
const oldUploadSection = document.querySelector('#old-upload-section');
const oldFolderSelect = document.querySelector('#old-folder-select');
const oldFolderEmpty = document.querySelector('#old-folder-empty');
const fileInput = document.querySelector('#video-file');
const fileName = document.querySelector('#file-name');
const splitButton = document.querySelector('#split-btn');
const uploadButton = document.querySelector('#upload-btn');
const statusBox = document.querySelector('#status');
const resultBox = document.querySelector('#result');
const uploadResultBox = document.querySelector('#upload-result');
const uploadSection = document.querySelector('#upload-section');
const outputFolderBox = document.querySelector('#output-folder');
const partsCountBox = document.querySelector('#parts-count');
const uploadOutputDirectory = document.querySelector('#upload-output-directory');
const uploadSummary = document.querySelector('#upload-summary');
const uploadTitle = document.querySelector('#upload-title-template');
const uploadDescription = document.querySelector('#upload-description');
const uploadGap = document.querySelector('#upload-gap');
const uploadTags = document.querySelector('#upload-tags');
const uploadPrivacy = document.querySelector('#upload-privacy');
const uploadCategory = document.querySelector('#upload-category-id');
const uploadDelete = document.querySelector('#delete-after-upload');
const uploadThumbnail = document.querySelector('#upload-thumbnail');
const savedThumbnailNote = document.querySelector('#saved-thumbnail-note');

let generatedFolder = '';

fileInput?.addEventListener('change', () => {
  fileName.textContent = fileInput.files?.[0]?.name || 'MP4, MOV, MKV, AVI, WEBM and more';
});

showOldUploadBtn?.addEventListener('click', async () => {
  generationSection.hidden = true;
  uploadSection.hidden = true;
  oldUploadSection.hidden = false;
  statusBox.hidden = false;
  statusBox.textContent = 'Loading output folders…';
  try {
    const folders = await loadOldFolders();
    oldUploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    statusBox.textContent = folders.length
      ? 'Select a folder. Its upload settings will open automatically.'
      : 'No output folders with pending Shorts are available.';
  } catch (error) {
    statusBox.textContent = error.message;
  }
});

oldFolderSelect?.addEventListener('change', () => {
  if (oldFolderSelect.value) openExistingFolder(oldFolderSelect.value);
  else uploadSection.hidden = true;
});

splitForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files?.[0];
  if (!file) return;

  splitButton.disabled = true;
  showOldUploadBtn.disabled = true;
  uploadSection.hidden = true;
  oldUploadSection.hidden = true;
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
    const response = await fetch(`/api/video/split?chunk_seconds=${encodeURIComponent(chunkSeconds)}&orientation=${encodeURIComponent(orientation)}`, {
      method: 'POST',
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to generate the Shorts.');

    await showUploadFormForNewFolder(data);
    statusBox.textContent = `Generation complete — ${data.parts_created} Short(s) created at ${size}.`;
    resultBox.hidden = false;
    resultBox.innerHTML = `
      <strong>All Shorts generated successfully.</strong><br><br>
      <strong>Output folder:</strong> <code>${escapeHtml(data.output_directory)}</code><br><br>
      <strong>Generated Shorts:</strong>
      <ul>${(data.parts || []).map(name => `<li><code>${escapeHtml(name)}</code></li>`).join('')}</ul>
      <p class="muted">Nothing was uploaded to YouTube during generation.</p>`;

    await loadOldFolders();
    uploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    statusBox.textContent = error.message;
  } finally {
    splitButton.disabled = false;
    showOldUploadBtn.disabled = false;
  }
});

youtubeForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!generatedFolder) return;

  uploadButton.disabled = true;
  splitButton.disabled = true;
  showOldUploadBtn.disabled = true;
  uploadResultBox.hidden = true;
  statusBox.hidden = false;
  statusBox.textContent = 'Uploading Shorts in generated order…';

  const formData = new FormData();
  formData.append('output_directory', generatedFolder);
  formData.append('title_template', uploadTitle.value);
  formData.append('description', uploadDescription.value);
  formData.append('tags', uploadTags.value);
  formData.append('privacy', uploadPrivacy.value);
  formData.append('category_id', uploadCategory.value);
  formData.append('made_for_kids', 'false');
  formData.append('gap_seconds', uploadGap.value || '60');
  formData.append('delete_after_upload', uploadDelete.checked ? 'true' : 'false');
  if (uploadThumbnail.files?.[0]) formData.append('thumbnail', uploadThumbnail.files[0]);

  try {
    const response = await fetch('/api/youtube/upload', { method: 'POST', body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to upload to YouTube.');

    const successCount = (data.results || []).filter(item => item.status === 'uploaded').length;
    const failedCount = (data.results || []).filter(item => item.status === 'failed').length;
    statusBox.textContent = failedCount
      ? `${successCount} uploaded. Queue stopped on an error; ${data.remaining_files} Short(s) remain.`
      : `YouTube upload complete — ${successCount} Short(s) uploaded.`;

    uploadResultBox.hidden = false;
    uploadResultBox.innerHTML = `
      <strong>YouTube upload report</strong><br><br>
      <strong>Order:</strong> part_001 → part_002 → part_003 → …<br>
      <strong>Remaining local MP4s:</strong> ${data.remaining_files}<br><br>
      <ul>${(data.results || []).map(item => `
        <li>
          <code>${escapeHtml(item.filename)}</code> — <strong>${escapeHtml(item.status)}</strong>
          ${item.url ? ` — <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">Open on YouTube</a>` : ''}
          ${item.deleted ? ' — deleted locally' : ''}
          ${item.error ? ` — ${escapeHtml(item.error)}` : ''}
        </li>`).join('')}</ul>`;

    await loadOldFolders();
  } catch (error) {
    statusBox.textContent = error.message;
  } finally {
    uploadButton.disabled = false;
    splitButton.disabled = false;
    showOldUploadBtn.disabled = false;
  }
});

async function loadOldFolders() {
  const response = await fetch('/api/youtube/folders', { cache: 'no-store' });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Unable to load output folders.');
  renderOldFolders(data.folders || []);
  return data.folders || [];
}

function renderOldFolders(folders) {
  oldFolderSelect.innerHTML = '';

  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = folders.length ? 'Select an output folder…' : 'No pending output folders';
  placeholder.selected = true;
  oldFolderSelect.appendChild(placeholder);
  oldFolderSelect.disabled = folders.length === 0;

  oldFolderEmpty.hidden = folders.length > 0;
  if (!folders.length) {
    uploadSection.hidden = true;
    return;
  }

  for (const folder of folders) {
    const option = document.createElement('option');
    option.value = folder.output_directory;
    option.textContent = `${folder.folder} — ${folder.remaining} remaining`;
    oldFolderSelect.appendChild(option);
  }
}

async function openExistingFolder(outputDirectory) {
  statusBox.hidden = false;
  statusBox.textContent = 'Loading saved YouTube details…';
  try {
    const response = await fetch(`/api/youtube/folder?output_directory=${encodeURIComponent(outputDirectory)}`, { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to open this upload queue.');
    showUploadForm(data);
    statusBox.textContent = `${data.remaining} Short(s) are waiting in this folder. Saved settings are loaded.`;
    uploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    statusBox.textContent = error.message;
  }
}

async function showUploadFormForNewFolder(data) {
  generatedFolder = data.output_directory;
  uploadOutputDirectory.value = data.output_directory;
  outputFolderBox.textContent = data.output_directory.split('/').pop();
  partsCountBox.textContent = String(data.parts_created || 0);
  uploadTitle.value = '{filename} #{number}';
  uploadDescription.value = '';
  uploadTags.value = 'shorts,youtube';
  uploadGap.value = '60';
  uploadPrivacy.value = 'private';
  uploadCategory.value = '22';
  uploadDelete.checked = true;
  uploadThumbnail.value = '';
  if (savedThumbnailNote) savedThumbnailNote.textContent = 'Optional. Select a thumbnail to reuse for every uploaded Short.';
  uploadSection.hidden = false;
}

function showUploadForm(data) {
  generatedFolder = data.output_directory;
  uploadOutputDirectory.value = data.output_directory;
  outputFolderBox.textContent = data.folder || data.output_directory;
  partsCountBox.textContent = String(data.remaining ?? data.pending_order?.length ?? 0);

  const metadata = data.metadata || {};
  const youtube = metadata.youtube || {};
  const upload = metadata.upload || {};

  uploadTitle.value = metadata.title_template || '{filename} #{number}';
  uploadDescription.value = metadata.description || '';
  uploadTags.value = Array.isArray(metadata.tags) ? metadata.tags.join(', ') : 'shorts,youtube';
  uploadGap.value = String(upload.gap_seconds ?? 60);
  uploadPrivacy.value = youtube.privacy || 'private';
  uploadCategory.value = youtube.category_id || '22';
  uploadDelete.checked = upload.delete_after_upload !== false;
  uploadThumbnail.value = '';

  if (savedThumbnailNote) {
    savedThumbnailNote.textContent = data.saved_thumbnail
      ? `Saved thumbnail: ${data.saved_thumbnail}. It will be reused automatically unless you choose a new thumbnail.`
      : 'Optional. Select a thumbnail to reuse for every uploaded Short.';
  }

  uploadSection.hidden = false;
  uploadButton.disabled = !data.remaining;
}

window.addEventListener('DOMContentLoaded', () => {
  uploadSection.hidden = true;
  oldUploadSection.hidden = true;
});

function escapeHtml(value) {
  return String(value).replace(/[&<>'\"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}
