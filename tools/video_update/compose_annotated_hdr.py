"""Compose HDR comparisons from native videos with paper labels and no label boxes."""
from pathlib import Path
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import argparse, hashlib, json, math, subprocess, time
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageStat
from compose_video_paths import Reader, probe

ROOT=Path('/amax/home/fengshuangyu/cvrgs')
SITE=ROOT/'ExgsPage/cvrgs.github.io'
RUN=ROOT/'runs/hdr_path_video_20261117'
FONT_PATH=ROOT/'output/fig3_relighting_layout_preview/body_fonts/NimbusRomNo9L-Regu.otf'
SCENES=['box','luckycat','flower','plant']
CONFIGS=['12U12M100O','100U12M12O','33U33M33O','50U50O']
LABELS=['Bright-skewed','Dark-skewed','Uniform Random','Extreme Bimodal']
METHODS={'3dgs':'3DGS','mcmc':'GS-MCMC','gsw':'GS-W','lumi':'LumiGS','ppisp':'PPISP','hdrgs':'HDR-GS','gausshdr':'GaussHDR'}
PATTERNS={
 '3dgs':'Z_com/gaussian-splatting/output_3dgs_{config}/{scene}/path_video.mp4',
 'mcmc':'Z_com/3dgs-mcmc/output_mcmc_{config}/{scene}/path_video.mp4',
 'gsw':'Z_com/Gaussian-Wild/nn_8scenes_{config}/{scene}/path_video.mp4',
 'lumi':'Z_com/Luminance-GS_ours/Luminance-GS/result_hdr_8scenes_{config}/{scene}/video.mp4',
}
OLD_MAP={'box':'3dgs','luckycat':'mcmc','flower':'gsw','plant':'lumi'}
HEADING=ImageFont.truetype(str(FONT_PATH),28)
SMALL=ImageFont.truetype(str(FONT_PATH),20)
INPUT_FONT=ImageFont.truetype(str(FONT_PATH),23)
AXIS=ImageFont.truetype(str(FONT_PATH),18)
METHOD_FONT=ImageFont.truetype(str(FONT_PATH),23)
INK='#263342'; MUTED='#667382'; COLORS=['#344d68','#a5adb5','#e4b86d']

@lru_cache(maxsize=None)
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

@lru_cache(maxsize=None)
def first_frame(path):
 info=probe(path)['streams'][0]
 raw=subprocess.check_output(['ffmpeg','-v','error','-threads','1','-i',str(path),'-frames:v','1','-threads','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
 return Image.frombytes('RGB',(info['width'],info['height']),raw)

def template(scene):
 original=first_frame(SITE/'static/videos'/f'hdr_{scene}.mp4')
 assert original.size==(1648,930)
 c=Image.new('RGB',(1648,1064),'white'); d=ImageDraw.Draw(c)
 d.text((824,10),'Input',font=HEADING,fill=INK,anchor='mt')
 c.paste(original.crop((0,0,1648,320)),(0,48))
 for x,label in zip([104,584,1064],['Overexposed (O)','Mid-exposure (M)','Underexposed (U)']):
  # This rectangle belongs to the static header, outside the model renders.
  d.rectangle((x,48,x+479,75),fill='white')
  d.text((x+240,51),label,font=INPUT_FONT,fill=INK,anchor='mt')
 d.text((824,382),'Exposure settings (schematic)',font=SMALL,fill=MUTED,anchor='mt')
 for col,(title,heights) in enumerate(zip(LABELS,[[7,0,35],[35,0,7],[23,23,23],[30,0,30]])):
  x=col*416
  d.text((x+200,413),title,font=HEADING,fill=INK,anchor='mt')
  for i,(height,color,letter) in enumerate(zip(heights,COLORS,['U','M','O'])):
   bx=x+118+i*58
   d.line((bx-16,493,bx+16,493),fill='#d6dde4',width=1)
   if height: d.rounded_rectangle((bx-16,491-height,bx+16,491),radius=3,fill=color)
   else: d.line((bx-15,489,bx+15,489),fill='#d6dde4',width=2)
   d.text((bx,498),letter,font=AXIS,fill=MUTED,anchor='mt')
 return c

def source_pairs(scene,method):
 pairs=[]
 for i,config in enumerate(CONFIGS):
  if method in PATTERNS:
   source_config=['20U100O','100U20O','333333','50U50O'][i] if method in ['3dgs','mcmc'] else config
   baseline=ROOT/PATTERNS[method].format(config=source_config,scene=scene)
   ours=ROOT/'exgs_test2'/f'hdr_8scenes_{config}'/scene/'path_video.mp4'
  else:
   baseline=RUN/'renders'/method/config/scene/'path_video.mp4'
   ours=RUN/'renders/ours'/config/scene/'path_video.mp4'
  assert baseline.is_file() and ours.is_file(),(baseline,ours)
  pairs.append([baseline,ours])
 return pairs

def source_reference(scene,method):
 if method in PATTERNS:
  p=SITE/'static/videos'/f'hdr_{scene}.mp4' if OLD_MAP[scene]==method else SITE/'static/videos/baselines'/f'hdr_{scene}_{method}.mp4'
 else: p=SITE/'static/videos/v3'/f'hdr_{scene}_{method}_path_v3.mp4'
 return first_frame(p)

def compose(scene,method):
 started=time.monotonic()
 stem=f'hdr_{scene}_{method}_path_v4'
 target=SITE/'static/videos/v4'/f'{stem}.mp4'
 poster=SITE/'static/images/video_v4'/f'{stem}_000.png'
 sources=source_pairs(scene,method)
 records=[[{'path':str(p),'sha256':sha(p)} for p in pair] for pair in sources]
 readers=[[Reader(p) for p in pair] for pair in sources]
 background=template(scene)
 reference=source_reference(scene,method)
 checks=[]
 writer=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1648x1064','-r','15','-i','pipe:0',
  '-an','-c:v','libx264','-crf','18','-preset','medium','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],stdin=subprocess.PIPE)
 try:
  for frame in range(120):
   canvas=background.copy()
   for col,pair in enumerate(readers):
    x=col*416
    for row,reader in enumerate(pair):
     panel=reader.next(); y=520+272*row
     canvas.paste(panel,(x,y))
     text=METHODS[method] if row==0 else 'Ours'
     if frame==0:
      ref=reference.crop((x,386+272*row,x+400,386+272*(row+1))).crop((0,32,400,272))
      native=panel.crop((0,32,400,272))
      rms=ImageStat.Stat(ImageChops.difference(ref,native)).rms
      mse=sum(v*v for v in rms)/3
      psnr=math.inf if mse==0 else 10*math.log10(255**2/mse)
      checks.append({'column':col,'row':row,'reference_psnr':round(psnr,3)})
      if psnr<26: raise RuntimeError(f'Source does not reproduce existing comparison: {scene}/{method}/{col}/{row}: {psnr}')
     draw=ImageDraw.Draw(canvas)
     # Transparent text overlay: no rectangle, tint, patch, or image cleanup.
     draw.text((x+200,y+1),text,font=METHOD_FONT,fill='black',anchor='mt')
     if frame==0:
      mask=Image.new('L',(400,272),0)
      ImageDraw.Draw(mask).text((200,1),text,font=METHOD_FONT,fill=255,anchor='mt')
      support=mask.point(lambda v:255 if v else 0)
      changed=ImageChops.difference(canvas.crop((x,y,x+400,y+272)),panel).convert('L')
      assert ImageChops.multiply(changed,ImageChops.invert(support)).getbbox() is None
   writer.stdin.write(canvas.tobytes())
   if frame==0: canvas.save(poster)
   elif frame==60:
    qa=ROOT/'output/hdr_video_labels_20261117/qa_frames'
    qa.mkdir(parents=True,exist_ok=True)
    canvas.save(qa/f'{stem}_060.png')
 finally:
  writer.stdin.close()
  if writer.poll() is None and len(checks)<8: writer.terminate()
 assert writer.wait()==0
 for pair in readers:
  for reader in pair: reader.close()
 info=probe(target)
 assert info['streams'][0]['nb_frames']=='120' and float(info['format']['duration'])==8
 subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],check=True)
 for pair in records:
  for r in pair: assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']
 record={'scene':scene,'method':method,'label':METHODS[method],'video':str(target.relative_to(SITE)),'poster':str(poster.relative_to(SITE)),
  'sha256':sha(target),'frames':120,'fps':15,'layout':[1648,1064],'settings':CONFIGS,'setting_labels':LABELS,
  'font':str(FONT_PATH),'font_sha256':sha(FONT_PATH),'label_background_added':False,
  'only_glyph_pixels_changed_over_rendered_panels':True,'schematic_not_measured_histogram':True,
  'source_videos':records,'source_replay_checks':checks,'elapsed_seconds':round(time.monotonic()-started,2),'probe':info}
 (SITE/'static/data/video_v4'/f'{stem}.json').write_text(json.dumps(record,indent=2)+'\n')
 print('COMPOSED',scene,method,'minimum source replay PSNR',min(c['reference_psnr'] for c in checks),flush=True)
 return record

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--scenes',nargs='+',default=SCENES);parser.add_argument('--methods',nargs='+',default=list(METHODS));args=parser.parse_args()
 for directory in ['static/videos/v4','static/images/video_v4','static/data/video_v4']: (SITE/directory).mkdir(parents=True,exist_ok=True)
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures=[pool.submit(compose,s,m) for s in args.scenes for m in args.methods]
  catalog=[f.result() for f in futures]
 (SITE/'static/data/video_v4/catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
 print('COMPLETED',len(catalog),'comparisons',flush=True)
if __name__=='__main__':main()
