const splitForm = document.querySelector('#split-form');
const fileInput = document.querySelector('#video-file');
const fileName = document.querySelector('#file-name');
const splitButton = document.querySelector('#split-btn');
const statusBox = document.querySelector('#status');
const resultBox = document.querySelector('#result');
const progressSection = document.querySelector('#progress-section');
const progressBar = document.querySelector('#progress-bar');
const progressValue = document.querySelector('#progress-value');
const progressLabel = document.querySelector('#progress-label');

fileInput.addEventListener('change', () => {
  fileName.textContent = fileInput.files?.[0]?.name || 'Select your source video';
});

splitForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const file = fileInput.files?.[0];
  if (!file) return;

  splitButton.disabled = true;
  statusBox.hidden = true;
  resultBox.hidden = true;
  progressSection.hidden = false;
  setProgress(0, 'Starting split…');

  const chunkSeconds = Number(document.querySelector('#chunk-seconds').value || 180);
  const orientation = document.querySelector('#orientation').value;
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(
      `/api/video/split/start?chunk_seconds=${encodeURIComponent(chunkSeconds)}&orientation=${encodeURIComponent(orientation)}`,
      { method: 'POST', body: formData },
    );

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to start video splitting.');

    await watchJob(data.job_id);
  } catch (error) {
    setProgress(100, 'Split failed.');
    statusBox.hidden = false;
    statusBox.textContent = error.message || 'Video splitting failed.';
  } finally {
    splitButton.disabled = false;
  }
});

function watchJob(jobId) {
  return new Promise((resolve, reject) => {
    const stream = new EventSource(`/api/jobs/${encodeURIComponent(jobId)}/events`);

    stream.addEventListener('task_started', updateFromEvent);
    stream.addEventListener('split_progress', updateFromEvent);
    stream.addEventListener('task_completed', updateFromEvent);

    stream.addEventListener('job_completed', (event) => {
      const data = parseEvent(event);
      stream.close();
      renderResult(data.result || {});
      resolve(data.result || {});
    });

    const fail = (event) => {
      const data = parseEvent(event);
      stream.close();
      const message = data.error || 'Video splitting failed.';
      setProgress(100, 'Split failed.');
      statusBox.hidden = false;
      statusBox.textContent = message;
      reject(new Error(message));
    };

    stream.addEventListener('task_failed', fail);
    stream.addEventListener('job_failed', fail);
    stream.onerror = () => {
      stream.close();
      reject(new Error('Connection to the split job was lost.'));
    };
  });
}

function updateFromEvent(event) {
  const data = parseEvent(event);
  const progress = Number(data.progress ?? 0);
  const part = data.part && data.total_parts ? `Part ${data.part} of ${data.total_parts}` : '';
  setProgress(progress, part || data.label || 'Processing…');
}

function parseEvent(event) {
  try {
    return JSON.parse(event.data);
  } catch {
    return {};
  }
}

function setProgress(value, label) {
  const safeValue = Math.max(0, Math.min(100, Math.round(value)));
  progressBar.style.width = `${safeValue}%`;
  progressValue.textContent = `${safeValue}%`;
  progressLabel.textContent = label;
}

function renderResult(data) {
  setProgress(100, 'All clips created successfully.');
  statusBox.hidden = false;
  statusBox.textContent = `${data.parts_created || 0} clip(s) created and saved locally.`;
  resultBox.hidden = false;
  resultBox.innerHTML = `
    <strong>Split completed.</strong><br><br>
    <strong>Source:</strong> ${escapeHtml(data.source_filename || '—')}<br>
    <strong>Part length:</strong> ${escapeHtml(data.chunk_seconds || '—')} seconds<br>
    <strong>Output folder:</strong> <code>${escapeHtml(data.output_directory || '—')}</code><br><br>
    <strong>Generated clips:</strong>
    <ul>${(data.parts || []).map(name => `<li><code>${escapeHtml(name)}</code></li>`).join('')}</ul>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}
