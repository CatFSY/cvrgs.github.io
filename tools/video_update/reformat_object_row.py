"""Present the selected object scenes as Input + four methods in one row."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,subprocess
from PIL import Image,ImageDraw,ImageFont
SITE=Path(__file__).resolve().parents[2]
ROOT=SITE.parents[1]
FONT=ROOT/'output/fig3_relighting_layout_preview/body_fonts/NimbusRomNo9L-Regu.otf'
SCENES=['hotdog','ficus','chair']
LABELS=['Input','GS-W','LumiGS','PPISP','Ours']
BOXES=[(0,78,400,478),(408,78,808,478),(816,78,1216,478),(0,524,400,924),(408,524,808,924)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def frame_row(source):
 out=Image.new('RGB',(2032,438),'white');d=ImageDraw.Draw(out)
 for col,(label,box) in enumerate(zip(LABELS,BOXES)):
  x=col*408
  out.paste(source.crop(box),(x,38))
  d.text((x+200,3),label,font=ImageFont.truetype(str(FONT),30),fill='black',anchor='mt')
  assert out.crop((x,38,x+400,438)).tobytes()==source.crop(box).tobytes()
 return out

def run(scene):
 source=SITE/'static/videos/v2'/f'syn_{scene}_v2.mp4'
 target=SITE/'static/videos/objects_row'/f'{scene}.mp4'
 poster=SITE/'static/images/objects_row'/f'{scene}.png'
 before=sha(source)
 reader=subprocess.Popen(['ffmpeg','-v','error','-threads','1','-i',str(source),'-threads','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
 writer=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','2032x438','-r','20','-i','pipe:0',
  '-an','-c:v','libx264','-preset','medium','-crf','18','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],stdin=subprocess.PIPE)
 for i in range(200):
  raw=reader.stdout.read(1216*924*3);assert len(raw)==1216*924*3
  source_frame=Image.frombytes('RGB',(1216,924),raw)
  result=frame_row(source_frame)
  writer.stdin.write(result.tobytes())
 assert reader.stdout.read(1)==b''
 reader.stdout.close();assert reader.wait()==0
 writer.stdin.close();assert writer.wait()==0
 frame_row(Image.open(SITE/'static/images/video_v2'/f'syn_{scene}_v2.png').convert('RGB')).save(poster)
 assert sha(source)==before
 subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],check=True)
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,nb_frames,r_frame_rate:format=duration','-of','json',str(target)]))
 s=info['streams'][0];assert [s['width'],s['height'],s['nb_frames'],s['r_frame_rate']]==[2032,438,'200','20/1']
 record={'scene':scene,'source':str(source.relative_to(SITE)),'source_sha256':before,'video':str(target.relative_to(SITE)),'sha256':sha(target),'poster':str(poster.relative_to(SITE)),
  'columns':LABELS,'layout':'single row','gt_shown':False,'mic_included':False,'source_crops':BOXES,'rendered_panel_pixels_preserved_before_encoding':True,
  'frames':200,'fps':20,'duration_seconds':10,'training_views':180,'heldout_views':20,'font':str(FONT),'probe':info}
 (SITE/'static/data/objects_row'/f'{scene}.json').write_text(json.dumps(record,indent=2)+'\n')
 print('ONE ROW',scene,flush=True)
 return record

def main():
 for p in ['static/videos/objects_row','static/images/objects_row','static/data/objects_row']:(SITE/p).mkdir(parents=True,exist_ok=True)
 with ThreadPoolExecutor(max_workers=2) as pool:records=list(pool.map(run,SCENES))
 (SITE/'static/data/objects_row/catalog.json').write_text(json.dumps(records,indent=2)+'\n')
if __name__=='__main__':main()
