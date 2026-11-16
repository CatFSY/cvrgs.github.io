"""Restore the original HDR demo layout using native continuous-path renders."""
from pathlib import Path
import hashlib,json,subprocess,time
from PIL import Image,ImageDraw,ImageFont

ROOT=Path('/amax/home/fengshuangyu/cvrgs')
RUN=ROOT/'runs/hdr_path_video_20261117'
SITE=ROOT/'ExgsPage/cvrgs.github.io'
CONFIGS=['12U12M100O','100U12M12O','33U33M33O','50U50O']
SCENES=['box','luckycat','flower','plant']
LABELS=['Bright-skewed','Dark-skewed','Uniform Random','Extreme Bimodal']
METHODS={'ppisp':'PPISP','hdrgs':'HDR-GS','gausshdr':'GaussHDR'}
FONT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,nb_frames,r_frame_rate:format=duration','-of','json',str(p)]))

class Reader:
    def __init__(self,path):
        self.path=path
        info=probe(path)['streams'][0]
        assert int(info['nb_frames'])==120 and info['r_frame_rate']=='15/1',info
        self.size=(info['width'],info['height'])
        self.p=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-threads','1','-i',str(path),'-threads','1',
                                 '-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
    def next(self):
        raw=self.p.stdout.read(self.size[0]*self.size[1]*3)
        assert len(raw)==self.size[0]*self.size[1]*3,self.path
        return Image.frombytes('RGB',self.size,raw).resize((400,272),Image.Resampling.BICUBIC)
    def close(self):
        assert self.p.stdout.read(1)==b''
        self.p.stdout.close();assert self.p.wait()==0

def main():
    videos=SITE/'static/videos/v3';posters=SITE/'static/images/video_v3';protocols=SITE/'static/data/video_v3'
    for p in [videos,posters,protocols]:p.mkdir(parents=True,exist_ok=True)
    catalog=[]
    for scene in SCENES:
        legacy=SITE/'static/videos'/f'hdr_{scene}.mp4'
        raw=subprocess.check_output(['ffmpeg','-hide_banner','-loglevel','error','-i',str(legacy),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
        banner=Image.frombytes('RGB',(1648,930),raw).crop((0,0,1648,320))
        for method,label in METHODS.items():
            name=f'hdr_{scene}_{method}_path_v3'
            target=videos/f'{name}.mp4'
            records=[];sources=[]
            for config in CONFIGS:
                pair=[];rec=[]
                for m in [method,'ours']:
                    folder=RUN/'renders'/m/config/scene
                    deadline=time.monotonic()+1200
                    expected=sha(RUN/'trajectories'/f'{scene}.npz')
                    while (not (folder/'completed.json').exists() or
                           json.loads((folder/'completed.json').read_text())['trajectory_sha256']!=expected):
                        if time.monotonic()>deadline:raise RuntimeError(f'timed out waiting for {folder}')
                        print('WAIT',m,config,scene,flush=True);time.sleep(10)
                    d=json.loads((folder/'completed.json').read_text())
                    assert d['checkpoint_unchanged'] and d['heldout_reload_png_max_error']<=1
                    rec.append(d);pair.append(folder/'path_video.mp4')
                assert rec[0]['trajectory_sha256']==rec[1]['trajectory_sha256']
                records.append(rec);sources.append(pair)
            readers=[[Reader(path) for path in pair] for pair in sources]
            writer=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                '-s','1648x930','-r','15','-i','pipe:0','-an','-c:v','libx264','-crf','18',
                '-preset','medium','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],stdin=subprocess.PIPE)
            try:
                for frame in range(120):
                    canvas=Image.new('RGB',(1648,930),'white');canvas.paste(banner,(0,0));draw=ImageDraw.Draw(canvas)
                    for column,pair in enumerate(readers):
                        x=column*416
                        draw.text((x+200,357),LABELS[column],font=FONT,fill='black',anchor='mt')
                        for row,reader in enumerate(pair):
                            y=386+row*272;canvas.paste(reader.next(),(x,y))
                            text=label if row==0 else 'Ours'
                            length=draw.textlength(text,font=FONT)
                            draw.rectangle((x+196-length/2,y,x+204+length/2,y+26),fill='white')
                            draw.text((x+200,y+3),text,font=FONT,fill='black',anchor='mt')
                    writer.stdin.write(canvas.tobytes())
                    if frame in [0,60]:canvas.save(posters/f'{name}_{frame:03d}.png')
            finally:writer.stdin.close()
            assert writer.wait()==0
            for pair in readers:
                for reader in pair:reader.close()
            info=probe(target)
            assert info['streams'][0]['nb_frames']=='120' and float(info['format']['duration'])==8.
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(target),'-f','null','-'],check=True)
            record={'scene':scene,'method':method,'label':label,'video':str(target.relative_to(SITE)),
                'poster':str((posters/f'{name}_000.png').relative_to(SITE)),
                'frames':120,'fps':15,'seconds':8,'layout':[1648,930],
                'settings':CONFIGS,'setting_labels':LABELS,
                'layout_source':'ExgsPage/demo/README.md and original website video: static exposure examples; four setting columns; baseline above Ours',
                'exposure_banner_source':str(legacy),'exposure_banner_sha256':sha(legacy),
                'trajectory_source':json.loads((RUN/'trajectories'/f'{scene}.json').read_text()),
                'no_image_slideshow':True,'no_optical_flow_or_frame_morphing':True,
                'same_camera_poses_for_all_methods_and_settings':True,
                'novel_pose_gt':'No interpolated-camera GT is available. Static exposure examples are input references, not per-frame GT.',
                'display_resize':'Native panels resized to400x272 for the historical layout; no color/exposure fitting.',
                'native_runs':records,'bytes':target.stat().st_size,'sha256':sha(target),'probe':info}
            (protocols/f'{name}.json').write_text(json.dumps(record,indent=2))
            catalog.append(record)
            (protocols/'catalog.json').write_text(json.dumps(catalog,indent=2))
            print('COMPOSED',name,flush=True)
    print('ALL12_CONTINUOUS_COMPARISONS_DONE',flush=True)

if __name__=='__main__':main()
