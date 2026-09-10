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
  statusBox.textContent = 'Uploading and splitting… Large videos can take some time.';

  const formData = new FormData();
  formData.append('file', file);
  const chunkSeconds = Number(document.querySelector('#chunk-seconds').value || 180);

  try {
    const response = await fetch(`/api/video/split?chunk_seconds=${encodeURIComponent(chunkSeconds)}`, {
      method: 'POST',
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to split the video.');

    statusBox.textContent = `Done — ${data.parts_created} part(s) created.`;
    resultBox.hidden = false;
    resultBox.innerHTML = `
      <strong>Output folder:</strong> <code>${escapeHtml(data.output_directory)}</code>
      <br><br>
      <strong>Parts:</strong>
      <ul>${data.parts.map(name => `<li><code>${escapeHtml(name)}</code></li>`).join('')}</ul>
      <p class="muted">Files are saved inside the project's <code>output/</code> folder.</p>
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
