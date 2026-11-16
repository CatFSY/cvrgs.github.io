"""Export the current result groups as standalone, labeled comparison videos."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,subprocess,time
from PIL import Image,ImageDraw,ImageFont

SITE=Path(__file__).resolve().parents[2]
ROOT=SITE.parents[1]
OUT=ROOT/'output/standalone_video_20261117'
FONT=ROOT/'output/fig3_relighting_layout_preview/body_fonts/NimbusRomNo9L-Regu.otf'
FONTFILE=str(FONT)
SCENE_LABELS={'hotdog':'Hotdog','ficus':'Ficus','chair':'Chair','box':'Box','luckycat':'Luckycat','flower':'Flower','plant':'Plant','lab1':'Lab 1','lab2':'Lab 2','out2':'Outdoor','buu':'Buu','shrub':'Shrub','sofa':'Sofa'}
METHODS={'3dgs':'3DGS','mcmc':'GS-MCMC','gsw':'GS-W','lumi':'LumiGS','ppisp':'PPISP','hdrgs':'HDR-GS','gausshdr':'GaussHDR'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,nb_frames,r_frame_rate:format=duration,size','-of','json',str(p)]))
def font(n):return ImageFont.truetype(FONTFILE,n)
def card(path,title,subtitle=None):
 im=Image.new('RGB',(1920,1080),'white');d=ImageDraw.Draw(im)
 d.text((960,430),title,font=font(66),fill='#263342',anchor='mt')
 if subtitle:
  for i,line in enumerate(subtitle.split('\n')):
   d.text((960,545+i*56),line,font=font(38),fill='#505b66',anchor='mt')
 im.save(path)

def encode_card(name,title,subtitle,seconds):
 png=OUT/'cards'/f'{name}.png';target=OUT/'segments'/f'{name}.mp4'
 card(png,title,subtitle)
 subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-i',str(png),'-t',str(seconds),'-r','30','-an',
  '-c:v','libx264','-preset','medium','-crf','21','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
 return target

def cases():
 records=[]
 for scene in ['hotdog','ficus','chair']:
  records.append({'chapter':1,'dataset':'Multi-Light Objects','scene':scene,'source':SITE/'static/videos/objects_row'/f'{scene}.mp4','title':f'Multi-Light Objects  |  {SCENE_LABELS[scene]}'})
 for scene in ['box','luckycat','flower','plant']:
  for method,label in METHODS.items():
   records.append({'chapter':2,'dataset':'Multi-Exposure','scene':scene,'method':method,'source':SITE/'static/videos/v4'/f'hdr_{scene}_{method}_path_v4.mp4','title':f'Multi-Exposure  |  {SCENE_LABELS[scene]}  |  {label} vs. Ours'})
 for scene in ['lab1','lab2','out2']:
  records.append({'chapter':3,'dataset':'Flashlight','scene':scene,'source':SITE/'static/videos'/f'flash_{scene}.mp4','title':f'Flashlight  |  {SCENE_LABELS[scene]}'})
 for scene in ['buu','shrub','chair','sofa']:
  records.append({'chapter':4,'dataset':'Low-Light and Overexposure','scene':scene,'source':SITE/'static/videos'/f'lom_{scene}.mp4','title':f'Low-Light and Overexposure  |  {SCENE_LABELS[scene]}'})
 return records

def encode_case(index,r):
 before=sha(r['source']);target=OUT/'segments'/f'case_{index:02d}.mp4'
 # A title sits in the canvas margin. The complete comparison stays uncropped.
 titlefile=OUT/'cards'/f'title_{index:02d}.txt';titlefile.write_text(r['title'])
 filt=("scale=1888:984:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1,"
       "pad=1920:1080:(ow-iw)/2:88+(984-ih)/2:color=white,"
       f"drawtext=fontfile='{FONTFILE}':textfile='{titlefile}':fontsize=40:fontcolor=0x263342:x=(w-text_w)/2:y=20,"
       "fps=30")
 subprocess.run(['ffmpeg','-v','error','-y','-threads','2','-i',str(r['source']),'-vf',filt,'-an','-c:v','libx264',
  '-preset','medium','-crf','21','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
 assert sha(r['source'])==before
 info=probe(target);s=info['streams'][0]
 assert [s['width'],s['height'],s['r_frame_rate']]==[1920,1080,'30/1']
 d=dict(r);d.update(source=str(r['source']),source_sha256=before,segment=str(target),probe=info)
 print('SEGMENT',index,r['title'],flush=True)
 return d

def concat(paths,target):
 listing=target.with_suffix('.concat.txt')
 assert all("'" not in str(p) for p in paths)
 listing.write_text(''.join(f"file '{p}'\n" for p in paths))
 subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(target)],check=True)
 return target

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 for d in ['cards','segments','chapters','previews']:(OUT/d).mkdir(exist_ok=True)
 records=cases();assert len(records)==38
 assert not any(r['scene']=='mic' for r in records)
 assert all(r['source'].exists() for r in records)
 print('EXPORTING',len(records),'comparison clips',flush=True)
 intro=encode_card('intro','CVR-GS','Illumination-Robust Novel View Synthesis\nvia Cross-View Relighting',3)
 chapter_specs=[('01_Multi-Light_Objects','Multi-Light Objects','Spatially varying illumination'),('02_Multi-Exposure','Multi-Exposure','Bright-skewed / Dark-skewed / Uniform Random / Extreme Bimodal'),('03_Flashlight','Flashlight','Localized moving illumination'),('04_Low-Light_Overexposure','Low-Light and Overexposure','LOM dataset')]
 cards=[encode_card(name,title,subtitle,2) for name,title,subtitle in chapter_specs]
 indexed={}
 with ThreadPoolExecutor(max_workers=4) as pool:
  future_map={pool.submit(encode_case,i,r):i for i,r in enumerate(records)}
  for future in as_completed(future_map):indexed[future_map[future]]=future.result()
 ordered=[indexed[i] for i in range(len(records))]
 chapters=[]
 for i,(name,title,subtitle) in enumerate(chapter_specs,1):
  segment_paths=[Path(r['segment']) for r in ordered if r['chapter']==i]
  target=concat([cards[i-1]]+segment_paths,OUT/'chapters'/f'{name}.mp4')
  chapters.append(target)
 master=concat([intro]+chapters,OUT/'CVR-GS_comparisons_1080p.mp4')
 # Keep a higher-quality master if an extra upload-sized encode is necessary.
 upload=master
 if master.stat().st_size>95_000_000:
  upload=OUT/'CVR-GS_comparisons_1080p_compact.mp4'
  duration=float(probe(master)['format']['duration'])
  bitrate=int(88_000_000*8/duration)
  logfile=OUT/'upload_encode'
  for p in [1,2]:
   cmd=['ffmpeg','-v','error','-y','-threads','4','-i',str(master),'-an','-c:v','libx264','-preset','medium','-b:v',str(bitrate),'-threads','4',
        '-pass',str(p),'-passlogfile',str(logfile),'-pix_fmt','yuv420p']
   cmd+=['-f','null','/dev/null'] if p==1 else ['-movflags','+faststart',str(upload)]
   subprocess.run(cmd,check=True)
  assert upload.stat().st_size<95_000_000
 subprocess.run(['ffmpeg','-v','error','-i',str(upload),'-f','null','-'],check=True)
 # Preview a representative moment in each dataset chapter.
 for p in chapters:
  subprocess.run(['ffmpeg','-v','error','-y','-ss','3','-i',str(p),'-frames:v','1',str(OUT/'previews'/f'{p.stem}.png')],check=True)
 offset=3.;timeline=[]
 for i,chapter in enumerate(chapters,1):
  duration=float(probe(chapter)['format']['duration'])
  timeline.append({'chapter':i,'title':chapter_specs[i-1][1],'start_seconds':round(offset,3),'duration_seconds':duration,'file':str(chapter)})
  offset+=duration
 final=probe(upload)
 assert abs(float(final['format']['duration'])-offset)<.15,(final,offset)
 report={'primary_video':str(upload),'high_quality_master':str(master),'probe':final,'chapters':timeline,'comparisons':ordered,
  'audio':False,'mic_included':False,'objects_gt_shown':False,'object_layout':'Input / GS-W / LumiGS / PPISP / Ours, one row',
  'web_links_or_author_information_embedded':False,'camera_frames_blended':False,'timing':'Source timings retained. FPS conversion duplicates frames; no optical flow or temporal interpolation.',
  'source_clips_unchanged':True,'sha256':sha(upload)}
 (OUT/'video_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
 print('READY',upload,'bytes',upload.stat().st_size,'duration',final['format']['duration'],flush=True)
if __name__=='__main__':main()
