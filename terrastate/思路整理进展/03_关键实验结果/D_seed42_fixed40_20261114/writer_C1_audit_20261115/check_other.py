import pathlib,json
p=pathlib.Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/spanworld_D_multiseed_909_D_C0R_s97_20261114_01/eval_code_BD_original_E2_20261115_01')
o={}
for n in ['plan.json','state.json']:
 if (p/n).exists():o[n]=(p/n).read_text()
print(json.dumps(o))