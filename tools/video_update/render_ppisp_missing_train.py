"""Render only the missing training poses; never edit completed checkpoints."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '1'
from pathlib import Path
import sys, json, hashlib, gc, time
ROOT = Path('/amax/home/fengshuangyu/cvrgs')
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'Z_com/ppisp-3dgs/gaussian-splatting'), str(ROOT/'experiments/ppisp')]
import torch
import numpy as np
from PIL import Image
from torchvision.utils import save_image
from scene import GaussianModel
from scene.cameras import Camera
from renderer_3dgs import render
torch.set_num_threads(2)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

records = []
for scene in ['chair', 'ficus', 'mic']:
    model = ROOT/'runs/ppisp_3dgs_selfmade_400/models'/scene
    manifest = json.loads((model/'input_manifest.json').read_text())
    folder = model/'raw_gs/train/ours_20000/renders'
    folder.mkdir(parents=True, exist_ok=True)
    checkpoint = model/'point_cloud/iteration_20000'
    hashes = {p.name: sha(p) for p in checkpoint.iterdir() if p.is_file()}
    g = GaussianModel(3, 'default')
    g.load_ply(str(checkpoint/'point_cloud.ply'), False)
    bg = torch.zeros(3, device='cuda')
    start = time.monotonic()
    with torch.inference_mode():
        for split, entries in [('test', manifest['test'][:1]), ('train', manifest['train'])]:
            for uid, entry in enumerate(entries):
                c = Camera(resolution=(400,400), colmap_id=uid,
                           R=np.asarray(entry['R']), T=np.asarray(entry['T']),
                           FoVx=entry['fovx'], FoVy=entry['fovy'], depth_params=None,
                           image=Image.new('RGB', (400,400)), invdepthmap=None,
                           image_name=entry['name'], uid=uid, is_test_view=split=='test')
                c.original_image = None
                raw = render(c, g, bg)['radiance']
                assert torch.isfinite(raw).all()
                if split == 'test':
                    expected = np.asarray(Image.open(model/'raw_gs/test/ours_20000/renders'/f"{entry['name']}.png"))
                    actual = (raw.clamp(0,1).permute(1,2,0).cpu().numpy()*255+.5).clip(0,255).astype(np.uint8)
                    error = int(np.abs(expected.astype(int)-actual.astype(int)).max())
                    assert error == 0, (scene,error)
                else:
                    save_image(raw.clamp(0,1), folder/f"{entry['name']}.png")
                del c, raw
    assert all(sha(checkpoint/name) == value for name,value in hashes.items())
    assert len(list(folder.glob('*.png'))) == 180
    records.append({'scene':scene,'train_views':180,'test_reload_png_max_error':error,
                    'seconds':time.monotonic()-start,'checkpoint_sha256':hashes,
                    'metadata_used':False,'controller_isp_bypassed':True,
                    'photo_pixels_loaded':False,'weights_unchanged':True,'gpu':1})
    (OUT/'ppisp_supplemental_render_protocol.json').write_text(json.dumps(records,indent=2))
    print(records[-1], flush=True)
    del g, bg
    gc.collect()
    torch.cuda.empty_cache()
