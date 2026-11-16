# Comparison video update: continuous HDR camera paths

The Multi-Exposure section now follows the original camera-path rendering
workflow. It does not use the previous v2 held-out-image slideshow.

## Multi-Exposure (current v3)

Four scenes: box, luckycat, flower, plant. Choose 3DGS, GS-MCMC, GS-W,
LumiGS, PPISP, HDR-GS or GaussHDR. The original four baselines and three
new baselines share the method selector; no comparison is hidden behind a
historical-version menu.
Each video presents all four training settings side by side: Bright-skewed,
Dark-skewed, Uniform Random and Extreme Bimodal. The comparison method is
above Ours, matching the original 1648×930 demo layout.

The original four keyframe prefixes are replayed with the original B-spline
function from exgs_test2/traj.py. Each model is loaded and rendered at 120
continuous camera poses, producing 8 seconds at 15 FPS. Camera positions,
orientations and cropped field of view are shared by all methods and settings.
No image morphing, optical flow or interpolation between rendered photos is used.

The top exposure-example banner is retained from the original video. These
static recorded images illustrate exposure conditions; they are not GT for
novel camera positions. No captured GT is available at the spline camera poses.

For the three newly rendered comparisons, model runs use their existing
20000-step checkpoints. Each reloaded model
was checked against a saved test output, within one 8-bit quantization level.
Checkpoint hashes were checked before and after rendering. Native model frames
are distinct across the trajectory. No retraining, Gaussian filtering or
checkpoint changes were performed.

HDR-GS and GaussHDR retain the previous own-max normalization and mu-law5000
display. PPISP shows clamp-only raw GS RGB from its no-metadata model, before
Controller/ISP. Ours shows its learned canonical intrinsic RGB. There is no
GT-mean alignment, new exposure fitting or external fusion.

- Videos (12): static/videos/v3/
- Poster frames: static/images/video_v3/
- Source hashes, trajectories, checkpoint and replay checks: static/data/video_v3/
- Reproduction scripts: tools/video_update/prepare_video_paths.py,
  render_video_paths.py, compose_video_paths.py, update_video_path_site.py.
- Original workflow: exgs_test2/render_path.py, exgs_test2/traj.py,
  exgs_test2/render_path_once.sh, exgs_test2/render_all_path.sh, and
  ExgsPage/demo/README.md in the experiment workspace.

## Synthetic

The four v2 synthetic videos remain unchanged: hotdog, ficus, mic, chair.
Panels show Input, GS-W, LumiGS, PPISP, Ours and GT, with 180 training and 20 test
poses labeled in their recorded sequence. PPISP is the no-exposure-metadata
GS branch before Controller/ISP. Model PNGs and legacy method videos retain
the provenance recorded in static/data/video_v2/.

## Earlier assets

All original HDR baseline methods remain selectable by method name. Four
previously published clips are reused byte-for-byte; twelve other scene/method
clips are copied unchanged from ExgsPage/demo/Multi-exposure. Their original
CVR-GS comparisons remain intact. Source paths, hashes and media checks are in
static/data/hdr_baselines/catalog.json; the additional clips are in
static/videos/baselines and posters in static/images/hdr_baselines.

Synthetic retains GS-W and LumiGS alongside PPISP and GT. Flashlight retains
DarkGS, LITA-GS and LumiGS; LOM retains 3DGS, LumiGS and LITA-GS. Their videos
are unchanged. The site uses scene/method buttons rather than version menus.
The v2 HDR held-out-camera clips remain archived in static/videos/v2/; they are
not the current continuous-camera comparison. See VIDEO_UPDATE_V2_ARCHIVE.md
for their historical construction details.
