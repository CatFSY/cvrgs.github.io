# Comparison video update

This revision updates the Synthetic and Multi-Exposure sections. The previous
videos remain selectable. The Flashlight and LOM sections retain their original
content. No model was trained for this update.

## Synthetic

Four scenes: hotdog, ficus, mic, chair. Each video contains the original 200
recorded poses at 20 fps for 10 seconds, including 180 training and 20 test views.
The frame label identifies the split; these videos are not test-only evaluations.

The six panels are Input, GS-W, LumiGS, PPISP, Ours, and GT. Each panel is 400×400;
the layout uses two rows to preserve readability in the project page.

PPISP uses the existing 20000-step models trained without exposure metadata,
and shows the GS RGB before the Controller and ISP. Missing 180-view training
renders for chair, ficus, and mic were generated from these checkpoints. A test
view from each reloaded checkpoint matched the existing PNG exactly. Checkpoint
hashes were unchanged. No input pixels were supplied to the rasterizer.

GS-W uses the latest available native intrinsic PNGs in the original Z_com model
folders: 70000 steps for hotdog, ficus, and chair; 5000 for mic. This is a comparison
of existing runs, not a new experiment with equal training budgets.

Ours uses the full 30000-step model. Hotdog uses the recently rerendered intrinsic
PNGs; the other three scenes retain the existing intrinsic videos. LumiGS retains
the video source documented for the previous site. The legacy videos have no
per-frame camera metadata for independent pose verification; their existing
frame-index correspondence is preserved. GT is the original selfmade normal-light
reference, not the later seed42 Blender dataset.

## Multi-Exposure

Four scenes: box, luckycat, flower, plant. Each has four selectable settings:
12U12M100O,100U12M12O,33U33M33O,50U50O. The new comparison contains HDR-GS,
GaussHDR, PPISP, Ours and Fusion GT. All model runs are 20000 steps.

Each 8-second video shows all shared held-out camera poses (17 per scene, or 20
for plant), with each image held for several display frames. This is a sequence
of held-out views, not a newly rendered continuous camera path. Images are never
morphed or interpolated.

The display follows the previous comparison protocol: existing own-max
normalization and mu-law5000 for HDR-GS/GaussHDR; native intrinsic RGB for Ours;
clamp-only raw GS RGB for PPISP without exposure metadata. No external fusion,
GT-mean alignment, or new exposure fitting is applied. Fusion GT is an 8-bit PNG
reference, not calibrated linear-HDR ground truth. The reference pixels were
checked to match across all four methods for every displayed view.

## Artifacts and reproduction

- New videos: `static/videos/v2/`
- Lossless poster frames: `static/images/video_v2/`
- Per-video source paths, hashes, view lists, and display details:
  `static/data/video_v2/`
- Inventory: `static/data/video_v2/catalog.json`
- Playback controls: `static/js/comparisons-v2.js`

The website is served by GitHub Pages from this repository. Deployment status
is available in the repository Actions tab. To preview locally, serve this
directory with an HTTP server and open index.html.
