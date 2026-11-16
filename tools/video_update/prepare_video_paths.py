"""Replay the historical render_path.py spline from saved camera keyframes."""
from pathlib import Path
import ast, hashlib, importlib.util, json, math
import numpy as np

ROOT=Path('/amax/home/fengshuangyu/cvrgs')
OUT=ROOT/'runs/hdr_path_video_20261117'
SCENES=['box','luckycat','flower','plant']
SETTINGS=['12U12M100O','100U12M12O','33U33M33O','50U50O']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    spec=importlib.util.spec_from_file_location('historical_traj',ROOT/'exgs_test2/traj.py')
    traj=importlib.util.module_from_spec(spec);spec.loader.exec_module(traj)
    dest=OUT/'trajectories';dest.mkdir(parents=True,exist_ok=True)
    for scene in SCENES:
        folder=ROOT/'exgs_test2/hdr_8scenes_33U33M33O'/scene
        selected=np.load(folder/'path_prefixes.npy').tolist()
        cams=json.loads((folder/'cameras.json').read_text())
        by_prefix={}
        for c in cams:by_prefix.setdefault(c['img_name'].split('_')[0],c)
        # Saved cfg.eval=False: render_path loads all views in sorted name order.
        ordered=sorted(selected)
        keys=[]
        for prefix in ordered:
            c=by_prefix[prefix]
            keys.append(np.column_stack([np.asarray(c['rotation']),np.asarray(c['position'])]))
        poses=traj.generate_interpolated_path(np.stack(keys),40)
        assert poses.shape==(120,3,4)
        # camera_to_JSON may preserve pre-crop dimensions in historical model
        # folders. render_path used loadCam's cropped FoV, recovered verbatim
        # from the matched native camera calibration at the same first prefix.
        calibration=ROOT/'runs/hdr_baselines/models/hdrgs/33U33M33O'/scene/'cameras.json'
        first=next(c for c in json.loads(calibration.read_text()) if c['img_name'].split('_')[0]==min(by_prefix))
        fovx=2*math.atan(first['width']/(2*first['fx']))
        fovy=2*math.atan(first['height']/(2*first['fy']))
        for setting in SETTINGS:
            assert np.load(ROOT/'exgs_test2'/f'hdr_8scenes_{setting}'/scene/'path_prefixes.npy').tolist()==selected
        target=dest/f'{scene}.npz'
        same=False
        if target.exists():
            saved=np.load(target)
            same=(np.array_equal(saved['c2w'],poses) and float(saved['fovx'])==fovx and float(saved['fovy'])==fovy)
        if not same:np.savez(target,c2w=poses,fovx=fovx,fovy=fovy,keyframes=np.stack(keys))
        protocol={'scene':scene,'selected_prefixes':selected,'keyframe_order':ordered,
                  'frames':120,'fps':15,'seconds':8,'interpolation':'original generate_interpolated_path:40 samples per segment, degree5 capped to3, smoothness0.03, rot_weight0.1',
                  'historical_eval':False,'pose_convention':'unchanged historical c2w; no axis flips',
                  'source_camera_file':str(folder/'cameras.json'),'source_camera_sha256':sha(folder/'cameras.json'),
                  'source_prefix_file':str(folder/'path_prefixes.npy'),'source_prefix_sha256':sha(folder/'path_prefixes.npy'),
                  'historical_render_code':str(ROOT/'exgs_test2/render_path.py'),
                  'historical_trajectory_code_sha256':sha(ROOT/'exgs_test2/traj.py'),
                  'cropped_reference_calibration':str(calibration),'reference_camera':first['img_name'],
                  'fovx':fovx,'fovy':fovy,'trajectory_sha256':sha(target),'all_settings_share_path':True}
        (dest/f'{scene}.json').write_text(json.dumps(protocol,indent=2))
        print(scene,ordered,poses.shape,flush=True)

if __name__=='__main__':main()
