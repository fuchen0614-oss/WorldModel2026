CASES=[{'id': 'new_Q98', 'receiver': 'JAS19/minicube_29_30TWK_40.05_-2.43.nc', 'expected_dates': ['2019-07-03', '2019-07-08', '2019-07-13', '2019-07-18', '2019-07-23', '2019-07-28', '2019-08-02', '2019-08-07', '2019-08-12', '2019-08-17', '2019-08-22', '2019-08-27', '2019-09-01', '2019-09-06', '2019-09-11', '2019-09-16', '2019-09-21', '2019-09-26', '2019-10-01', '2019-10-06']}, {'id': 'new_Q95', 'receiver': 'SON17/minicube_223_34TEL_40.70_21.54.nc', 'expected_dates': ['2017-09-01', '2017-09-06', '2017-09-11', '2017-09-16', '2017-09-21', '2017-09-26', '2017-10-01', '2017-10-06', '2017-10-11', '2017-10-16', '2017-10-21', '2017-10-26', '2017-10-31', '2017-11-05', '2017-11-10', '2017-11-15', '2017-11-20', '2017-11-25', '2017-11-30', '2017-12-05']}, {'id': 'new_Q50', 'receiver': 'MJJ18/minicube_89_31UGS_50.75_7.36.nc', 'expected_dates': ['2018-05-05', '2018-05-10', '2018-05-15', '2018-05-20', '2018-05-25', '2018-05-30', '2018-06-04', '2018-06-09', '2018-06-14', '2018-06-19', '2018-06-24', '2018-06-29', '2018-07-04', '2018-07-09', '2018-07-14', '2018-07-19', '2018-07-24', '2018-07-29', '2018-08-03', '2018-08-08']}, {'id': 'Q90', 'receiver': 'MJJ17/minicube_22_30STJ_38.85_-5.31.nc', 'expected_dates': ['2017-05-02', '2017-05-07', '2017-05-12', '2017-05-17', '2017-05-22', '2017-05-27', '2017-06-01', '2017-06-06', '2017-06-11', '2017-06-16', '2017-06-21', '2017-06-26', '2017-07-01', '2017-07-06', '2017-07-11', '2017-07-16', '2017-07-21', '2017-07-26', '2017-07-31', '2017-08-05']}]
from pathlib import Path
import os,sys,json,time,hashlib,traceback,argparse,subprocess
R=Path(__file__).parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(n,d):(R/n).write_text(json.dumps(d,ensure_ascii=False,indent=2))
try:
 import numpy as np,torch,xarray as xr
 sys.path.insert(0,'/data/zs/_downloads/emp-v0.1.0')
 from earthnet_models_pytorch.data.en21x_data import EarthNet2021XDataset
 from earthnet_models_pytorch.model import MODELS
 from earthnet_models_pytorch.utils import parse_setting
 ck=Path('/data/zs/_downloads/greenearthnet_official_weights_20260912/model_weights/predrnn/predrnn1M/seed=42.ckpt');cfg=Path('/data/zs/_downloads/greenearthnet/model_configs/predrnn/predrnn1M/seed=42.yaml')
 assert sha(ck)=='7e84f48934e70b925cb47340aabd97b4c4ca82cd92b67385381a96515e3a5f02';assert sha(cfg)=='f0ab89f5ddc6bebf46576d0d95fe9cc70be057d6e27a56e016fb37aba18c1b1e'
 torch.manual_seed(42);torch.set_num_threads(2);device=torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
 setting=parse_setting(cfg,track='iid_chopped');cls=MODELS[setting['Architecture']];parser=cls.add_model_specific_args(argparse.ArgumentParser(add_help=False));args=parser.parse_args([f'--{k}={v}' for k,v in setting['Model'].items()]);model=cls(args);checkpoint=torch.load(ck,map_location='cpu',weights_only=False);state={k[6:]:v for k,v in checkpoint['state_dict'].items() if k.startswith('model.')};model.load_state_dict(state,strict=True);model.to(device).eval()
 def batch(v):
  if torch.is_tensor(v):return v.unsqueeze(0).to(device)
  if isinstance(v,list):return [batch(x) for x in v]
  if isinstance(v,dict):return {k:batch(x) for k,x in v.items()}
  return v
 receipts=[]
 for c in CASES:
  put('state.json',dict(stage='PREDICTING',case=c['id'],done=len(receipts),pid=os.getpid()))
  cube=Path('/data/zs/TrainData/EarthNet2021/earthnet2021x/iid_chopped')/c['receiver'];ds=EarthNet2021XDataset(cube.parent,dl_cloudmask=True,allow_fastaccess=False);inds=[i for i,p in enumerate(ds.filepaths) if Path(p).resolve()==cube.resolve()];assert len(inds)==1
  data=batch(ds[inds[0]]);data['global_step']=torch.tensor(0.,device=device)
  with torch.inference_mode():pred,_=model(data,pred_start=10,preds_length=20)
  pred=pred[0,:,0].float().cpu().numpy();assert pred.shape==(20,128,128) and np.isfinite(pred).all()
  gt=data['dynamic'][0][0,10:30,0].cpu().numpy();lc=data['landcover'][0,0];valid=((data['dynamic_mask'][0][0,10:30,0]<1)&(lc>=10)&(lc<=40)).cpu().numpy()
  with xr.open_dataset(cube) as nc:dates=[str(v)[:10] for v in nc.time.values[4::5][10:30]]
  assert dates==c['expected_dates'];dest=R/c['id'];dest.mkdir(exist_ok=True);np.savez_compressed(dest/'arrays.npz',predrnn=pred,gt=gt,valid=valid)
  meta=dict(**c,dates=dates,checkpoint=str(ck),checkpoint_sha256=sha(ck),config_sha256=sha(cfg),seed=42,strict_load=True,array_sha256=sha(dest/'arrays.npz'),dataset_sha256=sha(cube),model_code_commit=subprocess.check_output(['git','-C','/data/zs/_downloads/emp-v0.1.0','rev-parse','HEAD'],text=True).strip());(dest/'metadata.json').write_text(json.dumps(meta));receipts.append(meta)
 put('receipt.json',dict(status='PASS',business_exit=0,cases=receipts));put('state.json',dict(stage='COMPLETE',business_exit=0,pid=os.getpid()))
except BaseException:
 put('receipt.json',dict(status='FAILED',business_exit=1,error=traceback.format_exc()));raise
