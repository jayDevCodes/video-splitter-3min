import { renderProgress } from './task_renderer.js';
import { createTimelineState, applyUploadEvent } from './upload_timeline.js';

export class ProgressManager {
  constructor(root) {
    this.root = root;
    this.source = null;
    this.state = createTimelineState();
    this.model = { status: 'queued', progress: 0, currentTask: 'generic' };
  }

  async start(jobId, { onComplete, onError } = {}) {
    this.stop();
    this.state = createTimelineState();
    this.model = { status: 'queued', progress: 0, currentTask: 'generic', jobId };
    renderProgress(this.root, this.model);

    const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Unable to load job status.');
    const snapshot = await response.json();
    this._applySnapshot(snapshot);
    renderProgress(this.root, this.model);

    this.source = new EventSource(`/api/jobs/${encodeURIComponent(jobId)}/events`);
    this.source.onmessage = (message) => this._handle(JSON.parse(message.data), onComplete, onError);
    this.source.onerror = async () => {
      if (!this.source) return;
      const current = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, { cache: 'no-store' }).then((r) => r.ok ? r.json() : null).catch(() => null);
      if (current?.status === 'completed' || current?.status === 'failed') {
        this._applySnapshot(current);
        renderProgress(this.root, this.model);
        this.stop();
        if (current.status === 'completed') onComplete?.(current);
        else onError?.(current.error || 'Job failed.');
      }
    };
    return jobId;
  }

  _applySnapshot(snapshot) {
    this.model.status = snapshot.status || this.model.status;
    const events = snapshot.events || [];
    if (events.length) {
      for (const event of events) this._applyEvent(event, false);
      const last = events[events.length - 1];
      this.model.status = last.status || this.model.status;
    }
  }

  _handle(event, onComplete, onError) {
    this._applyEvent(event, true);
    renderProgress(this.root, this.model);
    if (event.event === 'job_completed') {
      this.stop();
      fetch(`/api/jobs/${encodeURIComponent(event.job_id)}`, { cache: 'no-store' }).then((r) => r.json()).then((job) => onComplete?.(job));
    }
    if (event.event === 'job_failed') {
      this.stop();
      onError?.(event.error || 'Job failed.');
    }
  }

  _applyEvent(event, updateModel = true) {
    if (event.account_id || event.clip || event.task === 'clip_upload' || event.task === 'waiting') {
      applyUploadEvent(this.state, event);
    }
    if (event.task) this.model.currentTask = event.task;
    if (event.label) this.model.label = event.label;
    if (event.status) this.model.status = event.status;
    if (event.progress !== undefined) this.model.progress = Number(event.progress);
    if (event.clip) this.model.clip = event.clip;
    if (event.indeterminate !== undefined) this.model.indeterminate = event.indeterminate;
    if (event.error) this.model.error = event.error;
    if (event.remaining_seconds !== undefined) this.model.waitingSeconds = event.remaining_seconds;
    if (event.event === 'gap_completed') this.model.waitingSeconds = 0;

    const current = this.state.currentClip ? this.state.clips.get(this.state.currentClip) : null;
    this.model.accountRows = current ? [...current.accounts.values()] : [];
    if (event.event === 'job_completed') this.model.progress = 100;
    if (event.event === 'job_failed') this.model.status = 'failed';
    if (!updateModel) this.model.lastSequence = event.sequence;
  }

  stop() {
    this.source?.close();
    this.source = null;
  }
}
