/* One active video per dataset; preserve the previous comparisons for reference. */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-comparison-group]').forEach(group => {
    const kind = group.dataset.comparisonGroup;
    const video = group.querySelector('video');
    const version = group.querySelector('[data-version]');
    const setting = group.querySelector('[data-setting]');
    const method = group.querySelector('[data-method]');
    const download = group.querySelector('[data-download]');
    const protocol = group.querySelector('[data-protocol]');
    const caption = group.querySelector('[data-caption]');
    const error = group.querySelector('[data-video-error]');
    let scene = group.querySelector('[data-scene][aria-pressed="true"]').dataset.scene;
    const update = () => {
      const legacy = version.value === 'legacy';
      const prefix = kind === 'hdr' ? 'hdr' : 'syn';
      const continuous = kind === 'hdr' && method !== null;
      const stem = continuous ? `${prefix}_${scene}_${method.value}_path_v3`
        : kind === 'hdr' ? `${prefix}_${scene}_${setting.value}_v2` : `${prefix}_${scene}_v2`;
      const revision = continuous ? 'v3' : 'v2';
      const src = legacy ? `static/videos/${prefix}_${scene}.mp4` : `static/videos/${revision}/${stem}.mp4`;
      const wasPlaying = !video.paused;
      video.pause();
      video.src = src;
      video.poster = legacy ? '' : `static/images/video_${revision}/${stem}${continuous ? '_000' : ''}.png`;
      download.href = src;
      download.download = src.split('/').pop();
      protocol.hidden = legacy;
      protocol.href = `static/data/video_${revision}/${stem}.json`;
      error.hidden = true;
      if (setting) group.querySelector('[data-setting-control]').hidden = legacy;
      if (method) group.querySelector('[data-method-control]').hidden = legacy;
      caption.textContent = legacy ? group.dataset.legacyCaption : group.dataset.caption;
      video.load();
      if (wasPlaying) video.play().catch(() => {});
    };
    group.querySelectorAll('[data-scene]').forEach(button => {
      button.addEventListener('click', () => {
        scene = button.dataset.scene;
        group.querySelectorAll('[data-scene]').forEach(other => {
          const active = other === button;
          other.setAttribute('aria-pressed', String(active));
          other.classList.toggle('is-link', active);
          other.classList.toggle('is-light', !active);
        });
        update();
      });
    });
    version.addEventListener('change', update);
    if (setting) setting.addEventListener('change', update);
    if (method) method.addEventListener('change', update);
    video.addEventListener('error', () => { error.hidden = false; });
    update();
  });
});
