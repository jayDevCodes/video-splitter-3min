const TASK_ANIMATIONS = {
  video_split: { icon: '✂️', className: 'anim-split', label: 'Splitting video' },
  video_analyze: { icon: '🔍', className: 'anim-analyze', label: 'Analyzing video' },
  youtube_upload: { icon: '▶️', className: 'anim-youtube', label: 'Uploading to YouTube' },
  facebook_upload: { icon: '🔵', className: 'anim-facebook', label: 'Uploading to Facebook' },
  instagram_upload: { icon: '🟣', className: 'anim-instagram', label: 'Publishing to Instagram' },
  waiting: { icon: '⏱️', className: 'anim-waiting', label: 'Waiting for next clip' },
  cleanup: { icon: '🧹', className: 'anim-cleanup', label: 'Cleaning up' },
  clip_upload: { icon: '🎬', className: 'anim-clip', label: 'Processing clip' },
};

export function animationFor(task) {
  return TASK_ANIMATIONS[task] || { icon: '⚙️', className: 'anim-generic', label: task || 'Working' };
}
