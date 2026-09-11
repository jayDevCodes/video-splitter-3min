export function createTimelineState() {
  return { clips: new Map(), currentClip: null, waitingSeconds: 0 };
}

export function applyUploadEvent(state, event) {
  const clip = event.clip;
  if (clip) {
    if (!state.clips.has(clip)) state.clips.set(clip, { accounts: new Map(), status: 'queued' });
    const clipState = state.clips.get(clip);
    state.currentClip = clip;

    if (event.account_id) {
      clipState.accounts.set(event.account_id, {
        accountId: event.account_id,
        accountName: event.account_name || event.account_id,
        platform: event.platform,
        status: event.status || 'queued',
        progress: event.progress ?? 0,
        error: event.error || null,
        url: event.url || null,
      });
    }
    if (event.event === 'clip_completed') clipState.status = 'completed';
    if (event.event === 'clip_failed') clipState.status = 'failed';
    if (event.event === 'clip_started') clipState.status = 'running';
  }
  if (event.event === 'gap_tick' || event.event === 'gap_started') {
    state.waitingSeconds = event.remaining_seconds ?? 0;
  }
  if (event.event === 'gap_completed') state.waitingSeconds = 0;
  return state;
}
