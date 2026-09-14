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
  fileName.textContent = fileInput.files?.[0]?.name || 'MP4, MOV, MKV, AVI, WEBM and more';
});

splitForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files?.[0];
  if (!file) return;

  splitButton.disabled = true;
  resultBox.hidden = true;
  statusBox.hidden = true;
  progressSection.hidden = false;
  setProgress(0, 'Uploading source video…');

  const chunkSeconds = Number(document.querySelector('#chunk-seconds').value || 180);
  const orientation = document.querySelector('#orientation').value;
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`/api/video/split/start?chunk_seconds=${encodeURIComponent(chunkSeconds)}&orientation=${encodeURIComponent(orientation)}`, {
      method: 'POST',
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to start the split job.');

    await watchJob(data.job_id);
  } catch (error) {
    setProgress(100, 'Split failed.');
    statusBox.hidden = false;
    statusBox.textContent = error.message;
  } finally {
    splitButton.disabled = false;
  }
});

async function watchJob(jobId) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
  const job = await response.json();
  if (!response.ok) throw new Error(job.detail || 'Unable to read the split job.');

  const stream = new EventSource(`/api/jobs/${encodeURIComponent(jobId)}/events`);
  return new Promise((resolve, reject) => {
    stream.addEventListener('task_started', event => updateFromEvent(event));
    stream.addEventListener('split_progress', event => updateFromEvent(event));
    stream.addEventListener('task_completed', event => updateFromEvent(event));
    stream.addEventListener('task_failed', event => {
      const data = parseEvent(event);
      stream.close();
      setProgress(100, 'Split failed.');
      statusBox.hidden = false;
      statusBox.textContent = data.error || 'Video splitting failed.';
      reject(new Error(data.error || 'Video splitting failed.'));
    });
    stream.addEventListener('job_completed', event => {
      const data = parseEvent(event);
      stream.close();
      const result = data.result || {};
      renderResult(result);
      resolve(result);
    });
    stream.addEventListener('job_failed', event => {
      const data = parseEvent(event);
      stream.close();
      setProgress(100, 'Split failed.');
      statusBox.hidden = false;
      statusBox.textContent = data.error || 'Video splitting failed.';
      reject(new Error(data.error || 'Video splitting failed.'));
    });
    stream.onerror = () => {
      // The server closes SSE after terminal events. Give the final job state
      // one short fallback check before treating the connection as an error.
      setTimeout(async () => {
        try {
          const check = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
          const latest = await check.json();
          if (latest.status === 'completed') {
            stream.close();
            renderResult(latest.result || {});
            resolve(latest.result || {});
          } else if (latest.status === 'failed') {
            stream.close();
            reject(new Error(latest.error || 'Video splitting failed.'));
          }
        } catch (error) {
          stream.close();
          reject(error);
        }
      }, 300);
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
  try { return JSON.parse(event.data); } catch { return {}; }
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
    <strong>Video split completed.</strong><br><br>
    <strong>Source:</strong> ${escapeHtml(data.source_filename || '—')}<br>
    <strong>Part length:</strong> ${escapeHtml(data.chunk_seconds || '—')} seconds<br>
    <strong>Output folder:</strong> <code>${escapeHtml(data.output_directory || '—')}</code><br><br>
    <strong>Generated clips:</strong>
    <ul>${(data.parts || []).map(name => `<li><code>${escapeHtml(name)}</code></li>`).join('')}</ul>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'\"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}
