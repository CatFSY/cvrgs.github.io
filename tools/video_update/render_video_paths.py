"""Native checkpoint rendering along the original EXGS continuous camera path."""
import argparse, ast, gc, hashlib, json, math, os, sys, subprocess, time
from pathlib import Path
from types import SimpleNamespace

ROOT=Path('/amax/home/fengshuangyu/cvrgs')
OUT=ROOT/'runs/hdr_path_video_20261117'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--method',choices=['hdrgs','gausshdr','ppisp','ours'],required=True)
    ap.add_argument('--gpu',default='1')
    ap.add_argument('--scenes',nargs='+',default=['box','luckycat','flower','plant'])
    ap.add_argument('--settings',nargs='+',default=['12U12M100O','100U12M12O','33U33M33O','50U50O'])
    cli=ap.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES']=cli.gpu
    os.environ['OMP_NUM_THREADS']='2'
    repos={'hdrgs':'Z_com/HDR-GS','gausshdr':'Z_com/GaussHDR',
           'ppisp':'Z_com/ppisp-3dgs/gaussian-splatting','ours':'exgs_test2'}
    repo=ROOT/repos[cli.method];sys.path.insert(0,str(repo))
    sys.path.append(str(ROOT/'experiments/ppisp'))
    if cli.method=='ours':
        sys.path.insert(0,str(ROOT/'EXGS_test/submodules/diff-gaussian-rasterization'))
    import numpy as np
    import torch
    from PIL import Image
    from torchvision.utils import save_image
    from scene import GaussianModel
    from utils.graphics_utils import getWorld2View2,getProjectionMatrix
    torch.set_num_threads(2)

    def camera(c2w,fovx,fovy,width,height):
        inv=np.linalg.inv(np.vstack([c2w,[0,0,0,1]]))
        R=inv[:3,:3].T;T=inv[:3,3]
        view=torch.tensor(getWorld2View2(R,T),device='cuda').T.contiguous()
        proj=getProjectionMatrix(.01,100.,float(fovx),float(fovy)).T.cuda()
        return SimpleNamespace(R=R,T=T,FoVx=float(fovx),FoVy=float(fovy),
            image_width=int(width),image_height=int(height),uid=0,colmap_id=0,
            original_image=None,world_view_transform=view,projection_matrix=proj,
            full_proj_transform=view@proj,camera_center=view.inverse()[3,:3],
            exps=np.array([1.],dtype=np.float32),expos={0:1.},image_name='path')

    def historical_camera(entry):
        c2w=np.column_stack([np.asarray(entry['rotation']),np.asarray(entry['position'])])
        return camera(c2w,2*math.atan(entry['width']/(2*entry['fx'])),
                      2*math.atan(entry['height']/(2*entry['fy'])),entry['width'],entry['height'])

    for scene_name in cli.scenes:
        for setting in cli.settings:
            dest=OUT/'renders'/cli.method/setting/scene_name
            if ((dest/'completed.json').exists() and
                json.loads((dest/'completed.json').read_text())['trajectory_sha256']==sha(OUT/'trajectories'/f'{scene_name}.npz')):
                print('SKIP',cli.method,setting,scene_name,flush=True);continue
            dest.mkdir(parents=True,exist_ok=True)
            start=time.monotonic()
            if cli.method=='ppisp':modeldir=ROOT/'runs/ppisp_3dgs_no_metadata/models'/setting/scene_name
            elif cli.method=='ours':modeldir=ROOT/'exgs_test2'/f'hdr_8scenes_{setting}'/scene_name
            else:modeldir=ROOT/'runs/hdr_baselines/models'/cli.method/setting/scene_name
            ckpt=modeldir/('ckpts_point_cloud' if cli.method=='ours' else 'point_cloud')/'iteration_20000'
            hashes={p.name:sha(p) for p in ckpt.iterdir() if p.is_file()}
            cfg={}
            if cli.method!='ppisp':
                n=ast.parse((modeldir/'cfg_args').read_text(),mode='eval').body
                cfg={k.arg:ast.literal_eval(k.value) for k in n.keywords}
            pipe=SimpleNamespace(debug=False,compute_cov3D_python=False,convert_SHs_python=cli.method=='hdrgs')
            cached={}
            with torch.no_grad():
                if cli.method=='hdrgs':
                    from gaussian_renderer import render
                    model=GaussianModel(cfg['sh_degree']);model.load_ply(str(ckpt/'point_cloud.ply'))
                    model.load_tonemapper(str(ckpt/'tone_mapper.pth'))
                    for net in [model.tone_mapper_r,model.tone_mapper_g,model.tone_mapper_b]:net.cuda().eval()
                    def call(cam):return render(cam,model,pipe,torch.zeros(3,device='cuda'),iteration=20000,render_mode='hdr')['render']
                elif cli.method=='gausshdr':
                    from gaussian_renderer import render,prefilter_voxel
                    names=['feat_dim','n_offsets','voxel_size','update_depth','update_init_factor','update_hierachy_factor','use_feat_bank','appearance_dim','ratio','add_opacity_dist','add_cov_dist','add_color_dist','data_type']
                    model=GaussianModel(*(cfg[k] for k in names))
                    model.set_appearance(len(json.loads((modeldir/'input_manifest.json').read_text())['train']))
                    model.load_ply_sparse_gaussian(str(ckpt/'point_cloud.ply'))
                    model.load_mlp_checkpoints(str(ckpt));model.eval()
                    assert cfg['appearance_dim']==0
                    def call(cam):
                        bg=torch.zeros(3,device='cuda');visible=prefilter_voxel(cam,model,pipe,bg)
                        return render(cam,model,pipe,bg,1.,visible_mask=visible,training_iter=20000)['image_HDR']
                elif cli.method=='ppisp':
                    from renderer_3dgs import render
                    model=GaussianModel(3,'default');model.load_ply(str(ckpt/'point_cloud.ply'),False)
                    def call(cam):return render(cam,model,torch.zeros(3,device='cuda'))['radiance']
                else:
                    from diff_gaussian_rasterization import GaussianRasterizationSettings,GaussianRasterizer
                    from arguments import ModelParams,PipelineParams
                    parser=argparse.ArgumentParser();ModelParams(parser);PipelineParams(parser)
                    args=argparse.Namespace(**(vars(parser.parse_args([]))|cfg));args.device='cuda:0'
                    model=GaussianModel(args.sh_degree,args);model.load_ckpt_ply(str(ckpt/'point_cloud.ply'));model.set_eval(True)
                    net=model.color_net;pos=model.get_xyz
                    embedded=net.embed_fns[0](pos) if net.use_pencoding[0] else pos
                    feat=model._features_intrinsic.reshape(len(pos),-1)
                    colors=net.base_head(net.gs_encoder(torch.cat([embedded,feat],1)))
                    cached['features']=torch.cat([colors,torch.zeros_like(colors[:,:1]),colors],1).contiguous()
                    def call(cam):
                        settings=GaussianRasterizationSettings(image_height=cam.image_height,image_width=cam.image_width,
                            tanfovx=math.tan(cam.FoVx/2),tanfovy=math.tan(cam.FoVy/2),
                            bg=torch.zeros(7,device='cuda'),scale_modifier=1.,viewmatrix=cam.world_view_transform,
                            projmatrix=cam.full_proj_transform,sh_degree=0,campos=cam.camera_center,prefiltered=False,debug=False)
                        im,_=GaussianRasterizer(settings)(means3D=model.get_xyz,means2D=torch.zeros_like(model.get_xyz),
                            colors_precomp=cached['features'],shs=None,opacities=model.get_opacity,
                            scales=model.get_scaling,rotations=model.get_rotation,cov3D_precomp=None)
                        return im[:3]

                def display(raw):
                    assert torch.isfinite(raw).all()
                    if cli.method in ['hdrgs','gausshdr']:
                        raw=raw.clamp_min(0)
                        return torch.log1p(5000*raw/raw.max().clamp_min(1e-8))/math.log1p(5000)
                    return raw.clamp(0,1)

                # Verify a saved test view before novel-view rendering. No test RGB enters inference.
                evaldir=(ROOT/'runs/hdr_baselines/models/exgs'/setting/scene_name if cli.method=='ours' else modeldir)
                camjson=(ROOT/'runs/hdr_baselines/models/hdrgs'/setting/scene_name/'cameras.json') if cli.method in ['ppisp','ours'] else modeldir/'cameras.json'
                entries=json.loads(camjson.read_text());entry=entries[0]
                name=entry['img_name'];name=next(iter(name.values())) if isinstance(name,dict) else name
                prefix=name.split('_')[0]
                folder='intrinsic_native' if cli.method=='ours' else 'renders' if cli.method=='ppisp' else 'hdr_mu'
                rootout=evaldir/('raw_gs/test/ours_20000' if cli.method=='ppisp' else 'test/ours_20000')
                target=rootout/folder/f'{prefix}.png'
                assert target.exists(),target
                predicted=display(call(historical_camera(entry)))
                saved=np.asarray(Image.open(target).convert('RGB'))
                actual=(predicted.permute(1,2,0).cpu().numpy()*255+.5).clip(0,255).astype(np.uint8)
                assert actual.shape==saved.shape
                error=int(abs(actual.astype(int)-saved.astype(int)).max())
                assert error<=1,(cli.method,setting,scene_name,'checkpoint replay differs',error)
                width,height=entry['width'],entry['height']
                path=OUT/'trajectories'/f'{scene_name}.npz';trajectory=np.load(path)
                video=dest/'path_video.mp4'
                writer=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                    '-s',f'{width}x{height}','-r','15','-i','pipe:0','-an','-c:v','libx264','-crf','18',
                    '-preset','medium','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
                signatures=[]
                try:
                    for idx,pose in enumerate(trajectory['c2w']):
                        cam=camera(pose,trajectory['fovx'],trajectory['fovy'],width,height)
                        img=display(call(cam))
                        array=(img.permute(1,2,0).cpu().numpy()*255+.5).clip(0,255).astype(np.uint8)
                        signatures.append(hashlib.sha256(array.tobytes()).hexdigest())
                        writer.stdin.write(array.tobytes())
                        if idx in [0,40,80,119]:Image.fromarray(array).save(dest/f'frame_{idx:03d}.png')
                finally:writer.stdin.close()
                assert writer.wait()==0
            assert hashes=={p.name:sha(p) for p in ckpt.iterdir() if p.is_file()}
            assert len(set(signatures))>115,'unexpected repeated frames'
            record={'method':cli.method,'setting':setting,'scene':scene_name,'frames':120,'fps':15,'seconds':8,
                'width':width,'height':height,'trajectory':str(path),'trajectory_sha256':sha(path),
                'checkpoint_dir':str(ckpt),'checkpoint_sha256':hashes,'checkpoint_unchanged':True,
                'heldout_reload_png_max_error':error,'unique_raw_frames':len(set(signatures)),
                'rendering':'checkpoint -> native renderer at120 distinct spline camera poses -> video',
                'no_photo_interpolation':True,'test_rgb_used_for_inference':False,
                'display':('existing own-max + mu-law5000' if cli.method in ['hdrgs','gausshdr'] else 'clamp only'),
                'ppisp_controller_isp_bypassed':cli.method=='ppisp','elapsed_seconds':time.monotonic()-start}
            (dest/'completed.json').write_text(json.dumps(record,indent=2))
            print('DONE',cli.method,setting,scene_name,'seconds',round(record['elapsed_seconds'],1),'replay_error',error,flush=True)
            del model,call,cached,img,predicted
            gc.collect();torch.cuda.empty_cache()

if __name__=='__main__':main()
