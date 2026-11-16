"""Replace only the two requested comparison sections in the cloned site."""
from pathlib import Path
import re
ROOT=Path('/amax/home/fengshuangyu/cvrgs')
SITE=ROOT/'ExgsPage/cvrgs.github.io'


def section(kind,title,scenes):
    hdr=kind=='hdr'
    caption=('HDR-GS, GaussHDR, PPISP, Ours and Fusion GT at the same held-out camera poses. '
             'Choose one of the four training exposure settings. HDR-GS and GaussHDR use the existing '
             'mu-law display; PPISP uses direct GS RGB without exposure metadata, and Ours uses canonical appearance. '
             'Frames are held for inspection; this is a held-out view sequence, not a continuous camera path.' if hdr else
             'Input, GS-W, LumiGS, PPISP, Ours and GT at corresponding views. PPISP uses the model trained without '
             'exposure metadata and renders direct GS RGB before the Controller and ISP. '
             'All 200 views are shown in their recorded order; each frame identifies its training or test split.')
    legacy=('Previous four-setting comparison video.' if hdr else 'Previous four-column video: Input, GS-W, LumiGS and Ours.')
    buttons='\n'.join(f'<button type="button" class="button {"is-link" if i==0 else "is-light"}" data-scene="{s}" aria-pressed="{str(i==0).lower()}">{s}</button>' for i,s in enumerate(scenes))
    settings=''
    if hdr:
        settings='''<div data-setting-control>
              <label for="hdr-setting-v2">Training exposure setting</label>
              <div class="select"><select id="hdr-setting-v2" data-setting>
                <option value="12U12M100O">Bright-skewed (12U12M100O)</option>
                <option value="100U12M12O">Dark-skewed (100U12M12O)</option>
                <option value="33U33M33O">Uniform Random (33U33M33O)</option>
                <option value="50U50O" selected>Extreme Bimodal (50U50O)</option>
              </select></div>
            </div>'''
    first=f'hdr_{scenes[0]}_50U50O_v2' if hdr else f'syn_{scenes[0]}_v2'
    return f'''<section class="section comparison-v2" data-comparison-group="{kind}"
  data-caption="{caption}" data-legacy-caption="{legacy}">
  <div class="container is-max-desktop">
    <h2 class="title is-3 has-text-centered">{title}</h2>
    <div class="scene-buttons" role="group" aria-label="{title} scenes">
      {buttons}
    </div>
    <div class="comparison-controls">
      <div>
        <label for="{kind}-version-v2">Comparison</label>
        <div class="select"><select id="{kind}-version-v2" data-version>
          <option value="v2">Updated methods</option>
          <option value="legacy">Previous video</option>
        </select></div>
      </div>
      {settings}
    </div>
    <video src="static/videos/v2/{first}.mp4" poster="static/images/video_v2/{first}.png"
      controls loop muted playsinline preload="metadata" aria-label="{title} method comparison"></video>
    <p data-video-error role="alert" hidden>Unable to load the video. Use the MP4 download below.</p>
    <p class="comparison-caption" data-caption>{caption}</p>
    <div class="comparison-downloads">
      <a data-download href="static/videos/v2/{first}.mp4" download>Download MP4</a>
      <a data-protocol href="static/data/video_v2/{first}.json">Sources and display protocol</a>
    </div>
  </div>
</section>

'''


path=SITE/'index.html'
text=path.read_text()
original=ROOT/'output/project_video_update_20261117/index_before.html'
if not original.exists():original.write_text(text)
else:text=original.read_text()
start=text.index('<!-- Tabbed Scans -->')
end=text.index('<!-- Flashlight Scenes -->')
replacement=('<!-- Updated Multi-Exposure Scenes -->\n'+section('hdr','Multi-Exposure Scenes',['box','luckycat','flower','plant'])+
             '<!-- Updated Synthetic Scenes -->\n'+section('syn','Synthetic Dataset',['hotdog','ficus','mic','chair']))
text=text[:start]+replacement+text[end:]
text=text.replace('</head>','  <link rel="stylesheet" href="./static/css/comparisons-v2.css">\n  <script defer src="./static/js/comparisons-v2.js"></script>\n</head>')
path.write_text(text)
print(path)
