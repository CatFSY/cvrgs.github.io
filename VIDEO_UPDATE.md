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

The page shows Hotdog, Ficus and Chair. Mic is excluded from the displayed
scene selector and standalone export. Each video uses a single row of five
400x400 panels: Input, GS-W, LumiGS, PPISP and Ours. GT is omitted, along with
the scene/frame/train-test metadata badge. The image panels are preserved
without cropping or color changes before video encoding, and method labels
use the same Nimbus Roman font as the HDR comparisons.

- Videos: static/videos/objects_row/
- Posters: static/images/objects_row/
- Source crops, hashes and sequence metadata: static/data/objects_row/
- Reproduction: tools/video_update/reformat_object_row.py

The 200-frame sequence still includes 180 training and 20 held-out views.
PPISP is the GS branch before Controller/ISP, trained without exposure metadata.
Original source details remain in static/data/video_v2/.

## Standalone comparison video

Run tools/video_update/build_standalone_video.py to export the currently
selected four datasets independently of the website. Output is written outside
the site repository to output/standalone_video_20261117/. The export includes
38 comparison clips, dataset chapter cards, scene/method headings and a
1080p H.264 master. The complete render panels retain their aspect ratio; FPS
conversion only repeats frames. No model is retrained, and no new optical-flow
interpolation, appearance fitting, audio, authors or website links are added.
The export manifest records clip sources and chapter timing.

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
