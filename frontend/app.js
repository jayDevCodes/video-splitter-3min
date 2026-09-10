const form = document.querySelector('#split-form');
const fileInput = document.querySelector('#video-file');
const fileName = document.querySelector('#file-name');
const splitButton = document.querySelector('#split-btn');
const statusBox = document.querySelector('#status');
const resultBox = document.querySelector('#result');

fileInput.addEventListener('change', () => {
  fileName.textContent = fileInput.files?.[0]?.name || 'MP4, MOV, MKV, AVI, WEBM and more';
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files?.[0];
  if (!file) return;

  splitButton.disabled = true;
  resultBox.hidden = true;
  statusBox.hidden = false;
  statusBox.textContent = 'Uploading, splitting and preparing Shorts…';

  const formData = new FormData();
  formData.append('file', file);
  formData.append('title_template', document.querySelector('#title-template').value);
  formData.append('description', document.querySelector('#description').value);
  formData.append('tags', document.querySelector('#tags').value);
  formData.append('privacy', document.querySelector('#privacy').value);
  formData.append('category_id', document.querySelector('#category-id').value);
  formData.append('made_for_kids', document.querySelector('#made-for-kids').checked ? 'true' : 'false');
  formData.append('auto_upload', document.querySelector('#auto-upload').checked ? 'true' : 'false');

  const thumbnail = document.querySelector('#thumbnail').files?.[0];
  if (thumbnail) formData.append('thumbnail', thumbnail);

  const chunkSeconds = Number(document.querySelector('#chunk-seconds').value || 180);
  const orientation = document.querySelector('#orientation').value;
  const size = orientation === 'vertical' ? '1080 × 1920 (9:16)' : '1920 × 1080 (16:9)';

  try {
    const response = await fetch(
      `/api/video/split?chunk_seconds=${encodeURIComponent(chunkSeconds)}&orientation=${encodeURIComponent(orientation)}`,
      { method: 'POST', body: formData },
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to split the video.');

    const autoUpload = document.querySelector('#auto-upload').checked;
    statusBox.textContent = autoUpload
      ? `Done — ${data.parts_created} part(s) created. Auto-upload watcher is processing the folder.`
      : `Done — ${data.parts_created} part(s) created at ${size}.`;
    resultBox.hidden = false;
    resultBox.innerHTML = `
      <strong>Output folder:</strong> <code>${escapeHtml(data.output_directory)}</code>
      <br><br>
      <strong>Format:</strong> ${escapeHtml(size)}
      <br><br>
      <strong>YouTube title template:</strong> <code>${escapeHtml(document.querySelector('#title-template').value)}</code>
      <br><br>
      <strong>Parts:</strong>
      <ul>${data.parts.map(name => `<li><code>${escapeHtml(name)}</code></li>`).join('')}</ul>
      <p class="muted">Metadata is saved in <code>_config/metadata.json</code>. Upload progress is saved in <code>_config/upload_status.json</code>.</p>
    `;
  } catch (error) {
    statusBox.textContent = error.message;
  } finally {
    splitButton.disabled = false;
  }
});

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));
}
