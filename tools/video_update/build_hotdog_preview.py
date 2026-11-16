"""Build an auditable preview from existing research outputs; no new inference."""
from pathlib import Path
import hashlib
import json
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/amax/home/fengshuangyu/cvrgs')
OUT = Path(__file__).resolve().parent
SITE = ROOT / 'ExgsPage/cvrgs.github.io'
DATA = ROOT / 'selfmade/hotdog'
PPISP = ROOT / 'runs/ppisp_3dgs_selfmade_400/models/hotdog'
GSW = ROOT / 'Z_com/Gaussian-Wild/outputs/hotdog'
OURS = ROOT / 'EXGS_test/output/hotdog'
LUMI = ROOT / 'EXGS_result/selfmade/LumiGS/hotdog/enh_video_20fps.mp4'
LABELS = ['Input', 'GS-W', 'LumiGS', 'PPISP', 'Ours', 'GT']
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 25)
SMALL = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 19)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(path):
    with Image.open(path) as im:
        rgba = im.convert('RGBA')
        bg = Image.new('RGBA', rgba.size, (0, 0, 0, 255))
        bg.alpha_composite(rgba)
        im = bg.convert('RGB')
        if im.size != (400, 400):
            im = im.resize((400, 400), Image.Resampling.BICUBIC)
        return im


def encoder(path, size):
    return subprocess.Popen([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}',
        '-r', '20', '-i', 'pipe:0', '-an', '-c:v', 'libx264',
        '-preset', 'medium', '-crf', '18', '-threads', '2',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)
    ], stdin=subprocess.PIPE)


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries',
        'stream=width,height,nb_frames,r_frame_rate:format=duration',
        '-of', 'json', str(path)
    ]))


def canvas(panels, name, split, grid):
    columns = 3 if grid else 6
    rows = 2 if grid else 1
    width = columns * 400 + (columns - 1) * 8
    height = 40 + rows * 438 + (rows - 1) * 8
    result = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(result)
    draw.text((12, 9), f'Hotdog | {name} | {split} view', font=SMALL, fill='black')
    for i, (label, panel) in enumerate(zip(LABELS, panels)):
        x = (i % columns) * 408
        y = 40 + (i // columns) * 446
        draw.text((x + 200, y + 2), label, font=FONT, fill='black', anchor='mt')
        result.paste(panel, (x, y + 38))
    return result


def main():
    OUT.mkdir(exist_ok=True)
    manifest = json.loads((PPISP / 'input_manifest.json').read_text())
    entries = {row['name']: (split, row) for split in ['train', 'test']
               for row in manifest[split]}
    original = json.loads((DATA / 'transforms.json').read_text())
    frames = {Path(f['file_path']).stem: f for f in original['frames']}
    names = [f'r_{i:03d}' for i in range(200)]
    assert set(entries) == set(names) == set(frames)
    sources = []
    max_pose_error = 0.
    for name in names:
        split, row = entries[name]
        c2w = np.array(frames[name]['transform_matrix'])
        c2w[:3, 1:3] *= -1
        w2c = np.linalg.inv(c2w)
        err = max(float(np.abs(np.asarray(row['R']) - w2c[:3, :3].T).max()),
                  float(np.abs(np.asarray(row['T']) - w2c[:3, 3]).max()))
        assert err < 1e-6
        max_pose_error = max(max_pose_error, err)
        paths = [DATA / 'images' / f'{name}.png',
                 GSW / split / 'ours_70000/renders_intrinsic' / f'{name}.png',
                 PPISP / 'raw_gs' / split / 'ours_20000/renders' / f'{name}.png',
                 OURS / split / 'ours_30000/renders_intrinsic' / f'{name}.png',
                 DATA / 'input' / f'{name}.png']
        assert all(p.is_file() for p in paths), paths
        sources.append({'view': name, 'split': split,
                        'sources': [{'path': str(p), 'sha256': sha(p)} for p in paths]})

    info = probe(LUMI)['streams'][0]
    assert (info['width'], info['height'], int(info['nb_frames']), info['r_frame_rate']) == (800, 800, 200, '20/1')
    lumi = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error',
                             '-i', str(LUMI), '-f', 'rawvideo', '-pix_fmt',
                             'rgb24', 'pipe:1'], stdout=subprocess.PIPE)
    targets = [OUT / 'syn_hotdog_v2_wide.mp4', OUT / 'syn_hotdog_v2_grid.mp4']
    sizes = [(2440, 478), (1216, 924)]
    writers = [encoder(path, size) for path, size in zip(targets, sizes)]
    previews = []
    try:
        for i, record in enumerate(sources):
            raw = lumi.stdout.read(800 * 800 * 3)
            assert len(raw) == 800 * 800 * 3, i
            lp = Image.frombytes('RGB', (800, 800), raw).resize((400, 400), Image.Resampling.BICUBIC)
            panels = [rgb(Path(s['path'])) for s in record['sources']]
            panels.insert(2, lp)
            for grid, writer in zip([False, True], writers):
                frame = canvas(panels, record['view'], record['split'], grid)
                assert frame.size == sizes[int(grid)]
                writer.stdin.write(frame.tobytes())
                if i in [0, 6, 50, 173] and grid:
                    frame.save(OUT / f"preview_{record['view']}.png")
                    previews.append((record['view'], frame))
            if i % 50 == 0:
                print('encoded', i, flush=True)
        assert lumi.stdout.read(1) == b''
    finally:
        lumi.stdout.close()
        for writer in writers:
            writer.stdin.close()
    assert lumi.wait() == 0
    assert all(writer.wait() == 0 for writer in writers)
    verification = {p.name: probe(p) for p in targets}
    for d in verification.values():
        assert int(d['streams'][0]['nb_frames']) == 200
        assert abs(float(d['format']['duration']) - 10.) < .001
    sheet = Image.new('RGB', (1216, 924 * 2), 'white')
    for j, (_, im) in enumerate([previews[1], previews[-1]]):
        sheet.paste(im, (0, j * 924))
    sheet.save(OUT / 'preview_test_views.png')
    protocol = {
        'upstream_repository': 'https://github.com/CatFSY/cvrgs.github.io',
        'upstream_commit': subprocess.check_output(['git', '-C', str(SITE), 'rev-parse', 'HEAD'], text=True).strip(),
        'scene': 'hotdog', 'columns': LABELS, 'frame_order': names,
        'train_frames': 180, 'test_frames': 20, 'fps': 20, 'duration_seconds': 10,
        'panel_resolution': [400, 400], 'max_ppisp_vs_dataset_pose_error': max_pose_error,
        'methods': {
            'GS-W': 'Native intrinsic at 70000 steps, colornet_inter_weight=0.',
            'LumiGS': 'Existing 200-frame 20fps video from previous site source record; frame-index order preserved. Per-frame camera metadata unavailable for independent pose verification.',
            'PPISP': '20000 steps; trained without exposure metadata; raw GS RGB before controller/ISP. No external fusion.',
            'Ours': 'Full EXGS_test/output/hotdog, 30000 steps, native intrinsic.',
            'GT': 'Original selfmade/hotdog/input normal-light reference. Not seed42 Blender data.'},
        'lumigs_video': str(LUMI), 'lumigs_video_sha256': sha(LUMI),
        'image_operations': 'Black alpha composite; bicubic resize to400 if necessary. No exposure/GT-mean alignment, gamma correction, enhancement, crop or zoom. MP4 is lossy H.264 CRF18.',
        'checkpoint_mutations': False, 'verification': verification, 'frames': sources}
    (OUT / 'hotdog_v2_protocol.json').write_text(json.dumps(protocol, indent=2))
    for path in targets:
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(path), '-f', 'null', '-'], check=True)
    print('DONE', [str(p) for p in targets], flush=True)


if __name__ == '__main__':
    main()
