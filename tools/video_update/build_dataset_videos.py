"""Regenerate the two requested groups from existing, aligned experiment results."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from build_hotdog_preview import ROOT, OUT, rgb, probe, sha, encoder, canvas

SITE = ROOT/'ExgsPage/cvrgs.github.io'
DEST = SITE/'static/videos/v2'
POSTERS = SITE/'static/images/video_v2'
PROTOCOL = SITE/'static/data/video_v2'
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 23)
SMALL = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
CONFIGS = ['12U12M100O','100U12M12O','33U33M33O','50U50O']
SCENES = ['box','luckycat','flower','plant']
catalog = {'version':2, 'source_repository':'https://github.com/CatFSY/cvrgs.github.io',
           'synthetic':[], 'multi_exposure':[],
           'notes':['Videos contain existing model outputs; no retraining, GT fitting, fusion or new enhancement.',
                    'Synthetic sequences contain 180 training and20 held-out poses, labeled per frame.',
                    'Multi-exposure sequences contain held-out poses only, held for multiple frames; no image morphing.',
                    'HDR-GS/GaussHDR use existing own-max normalized mu-law5000 displays; Ours native intrinsic and PPISP raw GS RGB.',
                    'Legacy video sources have frame order documented in ExgsPage/demo/README.md; their per-frame camera metadata is unavailable.']}


class Reader:
    def __init__(self, path):
        info = probe(path)['streams'][0]
        assert int(info['nb_frames']) == 200 and info['r_frame_rate']=='20/1', (path,info)
        self.size=(info['width'],info['height'])
        self.pipe=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-i',str(path),
                                    '-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
    def next(self):
        raw=self.pipe.stdout.read(self.size[0]*self.size[1]*3)
        assert len(raw)==self.size[0]*self.size[1]*3
        return Image.frombytes('RGB',self.size,raw).resize((400,400),Image.Resampling.BICUBIC)
    def finish(self):
        assert self.pipe.stdout.read(1)==b''
        self.pipe.stdout.close()
        assert self.pipe.wait()==0


def publish_record(kind,scene,name,path,poster,protocol):
    info=probe(path)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(path),'-f','null','-'],check=True)
    pfile=PROTOCOL/f'{name}.json'
    pfile.write_text(json.dumps(protocol,indent=2))
    result={'scene':scene,'video':str(path.relative_to(SITE)),
            'poster':str(poster.relative_to(SITE)),
            'protocol':str(pfile.relative_to(SITE)),
            'bytes':path.stat().st_size,'sha256':sha(path),'probe':info}
    if kind=='multi_exposure': result['setting']=protocol['setting']
    catalog[kind]=[r for r in catalog[kind] if r['video']!=result['video']]
    catalog[kind].append(result)
    (PROTOCOL/'catalog.json').write_text(json.dumps(catalog,indent=2))
    print('DONE',name,flush=True)


def synthetic(scene):
    data=ROOT/'selfmade'/scene
    ppisp=ROOT/'runs/ppisp_3dgs_selfmade_400/models'/scene
    ours=ROOT/'EXGS_test/output'/scene
    gsw=ROOT/'Z_com/Gaussian-Wild/outputs'/scene
    ckpts=[int(p.name.split('_')[-1]) for p in (gsw/'train').glob('ours_*') if (p/'renders_intrinsic').exists()]
    iteration=max(ckpts)
    manifest=json.loads((ppisp/'input_manifest.json').read_text())
    entries={e['name']:(split,e) for split in ['train','test'] for e in manifest[split]}
    frames={Path(f['file_path']).stem:f for f in json.loads((data/'transforms.json').read_text())['frames']}
    lumi_path=ROOT/'EXGS_result/selfmade/LumiGS'/scene/'enh_video_20fps.mp4'
    readers={'LumiGS':Reader(lumi_path)}
    use_ours_png=scene=='hotdog'
    ours_video=ours/'renders_intrinsic.mp4'
    if not use_ours_png: readers['Ours']=Reader(ours_video)
    name=f'syn_{scene}_v2'
    target=DEST/f'{name}.mp4'
    writer=encoder(target,(1216,924))
    records=[]
    max_pose_error=0.
    try:
        for i in range(200):
            view=f'r_{i:03d}'
            split,entry=entries[view]
            c=np.asarray(frames[view]['transform_matrix']).copy(); c[:3,1:3]*=-1
            inv=np.linalg.inv(c)
            err=max(float(abs(np.asarray(entry['R'])-inv[:3,:3].T).max()),float(abs(np.asarray(entry['T'])-inv[:3,3]).max()))
            assert err<1e-6
            max_pose_error=max(max_pose_error,err)
            paths={
                'Input':data/'images'/f'{view}.png',
                'GS-W':gsw/split/f'ours_{iteration}/renders_intrinsic'/f'{view}.png',
                'PPISP':ppisp/'raw_gs'/split/'ours_20000/renders'/f'{view}.png',
                'GT':data/'input'/f'{view}.png'}
            panels={label:rgb(p) for label,p in paths.items()}
            panels['LumiGS']=readers['LumiGS'].next()
            if use_ours_png:
                paths['Ours']=ours/split/'ours_30000/renders_intrinsic'/f'{view}.png'
                panels['Ours']=rgb(paths['Ours'])
            else: panels['Ours']=readers['Ours'].next()
            im=canvas([panels[x] for x in ['Input','GS-W','LumiGS','PPISP','Ours','GT']],view,split,True)
            # Replace the sample-specific scene label while preserving the native panels.
            draw=ImageDraw.Draw(im);draw.rectangle((0,0,1216,39),fill='white')
            draw.text((12,9),f'{scene.capitalize()} | {view} | {split} view',font=SMALL,fill='black')
            writer.stdin.write(im.tobytes())
            if i==0: im.save(POSTERS/f'{name}.png')
            records.append({'view':view,'split':split,'camera_error':err,
                            'sources':{label:{'path':str(p),'sha256':sha(p)} for label,p in paths.items()}})
    finally: writer.stdin.close()
    assert writer.wait()==0
    for reader in readers.values():reader.finish()
    protocol={'dataset':'synthetic','scene':scene,'fps':20,'frames':200,'duration_seconds':10,
              'columns':['Input','GS-W','LumiGS','PPISP','Ours','GT'],'layout':'3 columns, 2 rows;400x400 panels',
              'pose_order':'r_000 through r_199;180 train and20 test; explicitly labeled',
              'max_ppisp_vs_dataset_camera_error':max_pose_error,'gsw_iteration':iteration,
              'gsw_branch':'native intrinsic','ppisp_iteration':20000,
              'ppisp_branch':'no exposure metadata; direct GS RGB; controller and ISP bypassed',
              'ours_source':('native full30000 intrinsic PNGs' if use_ours_png else str(ours_video)),
              'legacy_videos':{k:{'path':str(p),'sha256':sha(p)} for k,p in
                               [('LumiGS',lumi_path)]+([] if use_ours_png else [('Ours',ours_video)])},
              'legacy_video_pose_validation':'Frame order follows previous site source record; no per-frame metadata to independently revalidate.',
              'display':'No exposure fitting, GT-mean, gamma changes, zoom or crop. Bicubic resize and black alpha composite only. H264 CRF18.',
              'records':records}
    publish_record('synthetic',scene,name,target,POSTERS/f'{name}.png',protocol)


def hdr_frame(scene,setting,view,panels,size):
    w,h=size
    assert w%2==0 and h%2==0
    # Three columns with the last row centered, keeping every image's aspect ratio.
    height=64+2*(h+38)+8+32
    im=Image.new('RGB',(3*w+16,height),'white');d=ImageDraw.Draw(im)
    d.text((12,8),f'{scene.capitalize()} | {setting} | held-out view {view}',font=FONT,fill='black')
    d.text((12,38),'HDR-GS / GaussHDR / PPISP / Ours / Fusion GT',font=SMALL,fill='#444444')
    pitch=w+8
    positions=[(0,64),(pitch,64),(2*pitch,64),(pitch//2,64+h+46),(pitch//2+pitch,64+h+46)]
    for label,panel,(x,y) in zip(['HDR-GS','GaussHDR','PPISP','Ours','Fusion GT'],panels,positions):
        d.text((x+w//2,y+2),label,font=FONT,fill='black',anchor='mt')
        im.paste(panel,(x,y+38))
    d.text((12,height-25),'Held-out camera sequence; no frame interpolation.',font=SMALL,fill='#444444')
    return im


def multi_exposure(scene,setting):
    base=ROOT/'runs/hdr_baselines/models'
    dirs={m:base/m/setting/scene/'test/ours_20000' for m in ['hdrgs','gausshdr','exgs']}
    dirs['ppisp']=ROOT/'runs/ppisp_3dgs_no_metadata/models'/setting/scene/'raw_gs/test/ours_20000'
    info=json.loads((dirs['ppisp'].parents[2]/'data_info.json').read_text())
    # parents: ours_20000 -> test -> raw_gs -> scene
    views=info['test_prefixes']
    assert set(views).isdisjoint(info['train_prefixes'])
    source_sets={m:{p.stem for p in (d/('renders' if m=='ppisp' else 'intrinsic_native' if m=='exgs' else 'hdr_mu')).glob('*.png')}
                 for m,d in dirs.items()}
    assert all(names==set(views) for names in source_sets.values()),source_sets
    name=f'hdr_{scene}_{setting}_v2'
    target=DEST/f'{name}.mp4'
    frames=[];records=[];size=None
    for view in views:
        paths=[dirs['hdrgs']/'hdr_mu'/f'{view}.png',
               dirs['gausshdr']/'hdr_mu'/f'{view}.png',
               dirs['ppisp']/'renders'/f'{view}.png',
               dirs['exgs']/'intrinsic_native'/f'{view}.png',
               dirs['exgs']/'fused_reference'/f'{view}.png']
        panels=[Image.open(p).convert('RGB') for p in paths]
        if size is None:size=panels[0].size
        assert all(p.size==size for p in panels),(scene,setting,[p.size for p in panels])
        ref=np.asarray(panels[-1])
        for method in dirs:
            other=np.asarray(Image.open(dirs[method]/'fused_reference'/f'{view}.png').convert('RGB'))
            assert np.array_equal(ref,other),(scene,setting,view,method,'GT mismatch')
        frames.append(hdr_frame(scene,setting,view,panels,size))
        records.append({'view':view,'sources':[{'path':str(p),'sha256':sha(p)} for p in paths]})
    writer=encoder(target,frames[0].size)
    try:
        for i in range(160): writer.stdin.write(frames[min(i*len(frames)//160,len(frames)-1)].tobytes())
    finally:writer.stdin.close()
    assert writer.wait()==0
    frames[0].save(POSTERS/f'{name}.png')
    protocol={'dataset':'multi_exposure','scene':scene,'setting':setting,'fps':20,
              'frames':160,'duration_seconds':8,'unique_held_out_poses':len(views),
              'panel_resolution':list(size),'layout':'three top panels, two centered bottom panels',
              'columns':['HDR-GS','GaussHDR','PPISP','Ours','Fusion GT'],
              'iterations':20000,'hdrgs_gausshdr_display':'existing own-max normalization and mu-law5000 PNGs',
              'ours_display':'native intrinsic RGB','ppisp_display':'raw GS RGB; trained without exposure metadata; controller/ISP bypassed',
              'fusion_gt':'existing 8-bit fused PNG, byte/pixel-checked across all methods; not calibrated linear HDR ground truth',
              'view_selection':'all held-out poses in sorted prefix order; no hand picking',
              'temporal_processing':'Hold existing images for8 or10 display frames; no blending, interpolation, or morphing.',
              'spatial_processing':'No resizing, cropping, color or brightness adjustment before encoding H264 CRF18.',
              'records':records}
    publish_record('multi_exposure',scene,name,target,POSTERS/f'{name}.png',protocol)


if __name__=='__main__':
    for p in [DEST,POSTERS,PROTOCOL]:p.mkdir(parents=True,exist_ok=True)
    if (PROTOCOL/'catalog.json').exists():
        catalog=json.loads((PROTOCOL/'catalog.json').read_text())
    if '--hdr-only' not in sys.argv:
        for scene in ['hotdog','ficus','mic','chair']:synthetic(scene)
    if '--synthetic-only' not in sys.argv:
        scenes=SCENES
        if '--hdr-scenes' in sys.argv:
            scenes=sys.argv[sys.argv.index('--hdr-scenes')+1].split(',')
            assert all(s in SCENES for s in scenes)
        for scene in scenes:
            for setting in CONFIGS:multi_exposure(scene,setting)
