"""Expose the restored continuous four-setting HDR comparisons on the site."""
from pathlib import Path
import shutil
ROOT=Path('/amax/home/fengshuangyu/cvrgs')
SITE=ROOT/'ExgsPage/cvrgs.github.io'
caption=('Continuous novel-view rendering along the original120-pose B-spline camera path (15 FPS,8 seconds). '
         'Four columns show Bright-skewed, Dark-skewed, Uniform Random and Extreme Bimodal training settings. '
         'The selected comparison method is above Ours. Every method and setting uses the same camera poses. '
         'The top row contains static exposure examples; these are not per-frame ground truth.')
caption=caption.replace('original120','original 120').replace('FPS,8','FPS, 8')
buttons='\n'.join(f'<button type="button" class="button {"is-link" if i==0 else "is-light"}" data-scene="{s}" aria-pressed="{str(i==0).lower()}">{s}</button>' for i,s in enumerate(['box','luckycat','flower','plant']))
section=f'''<!-- Updated Multi-Exposure Scenes -->
<section class="section comparison-v2" data-comparison-group="hdr"
  data-caption="{caption}" data-legacy-caption="Previous four-setting comparison video.">
  <div class="container is-max-desktop">
    <h2 class="title is-3 has-text-centered">Multi-Exposure Scenes</h2>
    <div class="scene-buttons" role="group" aria-label="Multi-Exposure Scenes scenes">
      {buttons}
    </div>
    <div class="comparison-controls">
      <div>
        <label for="hdr-version-v2">Comparison</label>
        <div class="select"><select id="hdr-version-v2" data-version>
          <option value="v3">Continuous camera path</option>
          <option value="legacy">Previous video</option>
        </select></div>
      </div>
      <div data-method-control>
        <label for="hdr-method-v3">Comparison method</label>
        <div class="select"><select id="hdr-method-v3" data-method>
          <option value="ppisp">PPISP</option>
          <option value="hdrgs">HDR-GS</option>
          <option value="gausshdr">GaussHDR</option>
        </select></div>
      </div>
    </div>
    <video src="static/videos/v3/hdr_box_ppisp_path_v3.mp4"
      poster="static/images/video_v3/hdr_box_ppisp_path_v3_000.png"
      controls loop muted playsinline preload="metadata" aria-label="Multi-Exposure Scenes method comparison"></video>
    <p data-video-error role="alert" hidden>Unable to load the video. Use the MP4 download below.</p>
    <p class="comparison-caption" data-caption>{caption}</p>
    <div class="comparison-downloads">
      <a data-download href="static/videos/v3/hdr_box_ppisp_path_v3.mp4" download>Download MP4</a>
      <a data-protocol href="static/data/video_v3/hdr_box_ppisp_path_v3.json">Sources and display protocol</a>
    </div>
  </div>
</section>

'''
path=SITE/'index.html';html=path.read_text()
start=html.index('<!-- Updated Multi-Exposure Scenes -->')
end=html.index('<!-- Updated Synthetic Scenes -->')
html=html[:start]+section+html[end:]
html=html.replace('./static/js/comparisons-v2.js','./static/js/comparisons-v2.js?v=path-v3')
path.write_text(html)
dest=SITE/'tools/video_update'
for name in ['prepare_video_paths.py','render_video_paths.py','compose_video_paths.py','update_video_path_site.py']:
    shutil.copy2(ROOT/'experiments/hdr_baselines'/name,dest/name)
print(path)
