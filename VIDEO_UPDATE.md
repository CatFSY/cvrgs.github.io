# Comparison videos

## Multi-Exposure

The page exposes all seven baselines by method name: 3DGS, GS-MCMC, GS-W,
LumiGS, PPISP, HDR-GS and GaussHDR, across box, luckycat, flower and plant.
Each video shows the four protocols side by side: Bright-skewed, Dark-skewed,
Uniform Random and Extreme Bimodal. Baseline renders are above CVR-GS.

The static reference-image banner is labeled Input, with Overexposed (O),
Mid-exposure (M) and Underexposed (U) examples. These are recorded input
examples, not ground truth for the moving camera. The exposure diagrams are
schematic; they are not measured sampling-frequency histograms.

All annotations use Nimbus Roman No9 L Regular, matching the paper comparison
figure. Method names are drawn directly on the native images: there is no
white box, background tint or image cleanup beneath the labels.

The 28 videos are recomposed from original native render videos. The original
3DGS, GS-MCMC, GS-W and LumiGS clips retain their corresponding original CVR-GS
sources; the newer PPISP, HDR-GS and GaussHDR clips use the previously verified
120-pose renders from runs/hdr_path_video_20261117. All clips retain 120 frames
at 15 FPS (8 seconds). There is no photo slideshow, frame morphing, new model
training or checkpoint modification.

The source videos are unchanged. Every recomposed first-frame panel is checked
against its previously published counterpart outside the old label area; source
hashes and replay checks are retained per comparison. Pixels outside the text
glyphs are verified unchanged on the unencoded first-frame panels. Videos are
encoded as H.264 and checked by decoding their complete duration.

- Current videos: static/videos/v4/
- Poster frames: static/images/video_v4/
- Source hashes and composition checks: static/data/video_v4/
- Reproduction: tools/video_update/compose_annotated_hdr.py
- Scene and method control check: tools/video_update/check_video_switches.cjs

HDR-GS and GaussHDR retain own-max normalization and mu-law5000 display. PPISP
uses clamp-only direct GS RGB from training without exposure metadata, before
the Controller/ISP. CVR-GS uses its learned canonical intrinsic RGB. No new
exposure fitting, GT-mean alignment or external fusion is applied.

## Multi-Light Objects

The four synthetic videos cover hotdog, ficus, mic and chair. Only the
40-pixel top metadata band (scene, frame ID and train/test label) has been
removed; all six 400x400 image panels and method names remain intact.
The 200-frame sequence still includes 180 training and 20 held-out views.
Clean videos and posters are in static/videos/objects/ and
static/images/objects/, with provenance in static/data/objects/. PPISP is the GS branch
before Controller/ISP from training without exposure metadata. Source details
remain in static/data/video_v2/.

## Flashlight and LOM

The original videos are unchanged. Flashlight retains Input, DarkGS, LITA-GS,
LumiGS and CVR-GS. LOM retains 3DGS, LumiGS, LITA-GS and CVR-GS.

## Archived assets

Earlier website videos and provenance records are preserved in their original
paths, including static/videos/baselines/, static/videos/v3/ and
static/data/hdr_baselines/. They are replaced on the page by the same methods
with consistent annotations, rather than exposed through a version selector.
The v2 HDR held-out-camera clips remain archived; they are not continuous
camera-path videos. See VIDEO_UPDATE_V2_ARCHIVE.md for their construction.
