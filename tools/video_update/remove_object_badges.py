"""Remove only the 40-pixel metadata band from the four object comparisons."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,subprocess
from PIL import Image

SITE=Path(__file__).resolve().parents[2]
SCENES=['hotdog','ficus','mic','chair']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(scene):
 source=SITE/'static/videos/v2'/f'syn_{scene}_v2.mp4'
 target=SITE/'static/videos/objects'/f'{scene}.mp4'
 poster_source=SITE/'static/images/video_v2'/f'syn_{scene}_v2.png'
 poster=SITE/'static/images/objects'/f'{scene}.png'
 before=sha(source)
 subprocess.run(['ffmpeg','-v','error','-y','-threads','2','-i',str(source),'-vf','crop=iw:ih-40:0:40','-an',
  '-c:v','libx264','-preset','medium','-crf','18','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
 im=Image.open(poster_source).convert('RGB');assert im.size==(1216,924)
 clean=im.crop((0,40,1216,924));clean.save(poster)
 assert clean.size==(1216,884)
 assert sha(source)==before
 subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],check=True)
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,nb_frames,r_frame_rate:format=duration','-of','json',str(target)]))
 st=info['streams'][0]
 assert [st['width'],st['height'],int(st['nb_frames']),st['r_frame_rate']]==[1216,884,200,'20/1']
 assert float(info['format']['duration'])==10
 record={'scene':scene,'source':str(source.relative_to(SITE)),'source_sha256':before,
  'video':str(target.relative_to(SITE)),'sha256':sha(target),'poster':str(poster.relative_to(SITE)),
  'annotation_removed':'scene name, frame ID and train/test view label in the top 40-pixel band',
  'rendered_image_panels_cropped':False,'all_six_method_panels_retained':True,
  'frames':200,'fps':20,'duration_seconds':10,'train_views':180,'heldout_views':20,
  'original_view_metadata':f'static/data/video_v2/syn_{scene}_v2.json','probe':info}
 (SITE/'static/data/objects'/f'{scene}.json').write_text(json.dumps(record,indent=2)+'\n')
 print('REMOVED BADGE',scene,flush=True)
 return record

def main():
 for folder in ['static/videos/objects','static/images/objects','static/data/objects']:(SITE/folder).mkdir(parents=True,exist_ok=True)
 with ThreadPoolExecutor(max_workers=2) as pool:records=list(pool.map(run,SCENES))
 (SITE/'static/data/objects/catalog.json').write_text(json.dumps(records,indent=2)+'\n')
if __name__=='__main__':main()
