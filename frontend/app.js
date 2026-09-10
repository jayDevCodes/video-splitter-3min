const splitForm = document.querySelector('#split-form');
const youtubeForm = document.querySelector('#youtube-form');
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

let generatedFolder = '';

fileInput.addEventListener('change', () => {
  fileName.textContent = fileInput.files?.[0]?.name || 'MP4, MOV, MKV, AVI, WEBM and more';
});

splitForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files?.[0];
  if (!file) return;

  splitButton.disabled = true;
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

    generatedFolder = data.output_directory;
    uploadOutputDirectory.value = generatedFolder;
    outputFolderBox.textContent = generatedFolder;
    partsCountBox.textContent = String(data.parts_created);
    statusBox.textContent = `Generation complete — ${data.parts_created} Short(s) created at ${size}.`;
    resultBox.hidden = false;
    resultBox.innerHTML = `<strong>All Shorts generated successfully.</strong><br><br><strong>Output folder:</strong> <code>${escapeHtml(data.output_directory)}</code><br><br><strong>Generated Shorts:</strong><ul>${data.parts.map(name => `<li><code>${escapeHtml(name)}</code></li>`).join('')}</ul><p class="muted">Nothing was uploaded to YouTube during generation.</p>`;
    uploadSection.hidden = false;
    uploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    statusBox.textContent = error.message;
  } finally {
    splitButton.disabled = false;
  }
});

youtubeForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!generatedFolder) return;

  uploadButton.disabled = true;
  splitButton.disabled = true;
  uploadResultBox.hidden = true;
  statusBox.hidden = false;
  statusBox.textContent = 'Uploading Shorts in generated order…';

  const formData = new FormData();
  formData.append('output_directory', generatedFolder);
  formData.append('title_template', document.querySelector('#upload-title-template').value);
  formData.append('description', document.querySelector('#upload-description').value);
  formData.append('tags', '');
  formData.append('privacy', 'private');
  formData.append('category_id', '22');
  formData.append('made_for_kids', 'false');
  formData.append('gap_seconds', document.querySelector('#upload-gap').value || '60');
  formData.append('delete_after_upload', document.querySelector('#delete-after-upload').checked ? 'true' : 'false');

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
  } catch (error) {
    statusBox.textContent = error.message;
  } finally {
    uploadButton.disabled = false;
    splitButton.disabled = false;
  }
});

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}
