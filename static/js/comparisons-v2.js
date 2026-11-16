/* Scene and method selection for the published comparisons. */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-comparison-group]').forEach(group => {
    const kind = group.dataset.comparisonGroup;
    const video = group.querySelector('video');
    const download = group.querySelector('[data-download]');
    const error = group.querySelector('[data-video-error]');
    let scene = group.querySelector('[data-scene][aria-pressed="true"]').dataset.scene;
    let method = group.querySelector('[data-method][aria-pressed="true"]')?.dataset.method;

    const update = () => {
      let src;
      let poster = '';
      if (kind === 'hdr') {
        const stem = `hdr_${scene}_${method}_path_v4`;
        src = `static/videos/v4/${stem}.mp4`;
        poster = `static/images/video_v4/${stem}_000.png`;
      } else if (kind === 'syn') {
        const stem = `syn_${scene}_v2`;
        src = `static/videos/v2/${stem}.mp4`;
        poster = `static/images/video_v2/${stem}.png`;
      } else {
        src = `static/videos/${kind}_${scene}.mp4`;
      }
      // Keep an active comparison playing when switching its scene or method.
      const wasPlaying = !video.paused;
      video.pause();
      video.src = src;
      if (poster) video.poster = poster;
      else video.removeAttribute('poster');
      download.href = src;
      download.download = src.split('/').pop();
      error.hidden = true;
      video.load();
      if (wasPlaying) video.play().catch(() => {});
    };

    ['scene', 'method'].forEach(choice => {
      group.querySelectorAll(`[data-${choice}]`).forEach(button => {
        button.addEventListener('click', () => {
          if (button.getAttribute('aria-pressed') === 'true') return;
          if (choice === 'scene') scene = button.dataset.scene;
          else method = button.dataset.method;
          group.querySelectorAll(`[data-${choice}]`).forEach(other => {
            other.setAttribute('aria-pressed', String(other === button));
          });
          update();
        });
      });
    });
    video.addEventListener('error', () => { error.hidden = false; });
    video.addEventListener('loadeddata', () => { error.hidden = true; });
  });
});
