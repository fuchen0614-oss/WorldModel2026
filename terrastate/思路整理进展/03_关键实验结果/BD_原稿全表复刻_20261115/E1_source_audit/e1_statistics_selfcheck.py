import json,gzip,base64,csv,io
from pathlib import Path
import bd_e1_statistics as s
outer=json.loads((Path(__file__).parent/'e1_current.json').read_text(encoding='utf-8'));remote=json.loads(outer['stdout']);key='B/ood-t_chopped';obj=remote['outputs'][key]
raw=gzip.decompress(base64.b64decode(obj['gzip_base64']));rows=list(csv.DictReader(io.StringIO(raw.decode())))
stats,pairs=s.aggregate(rows);assert (stats['suffix']['N'],stats['endpoint']['N'])==(1605,884);assert stats['suffix']['Groups']==stats['endpoint']['Groups']==80
reg=s.reference_regression(rows,stats)
result={'status':'PASS','actual_split':key,'real_worker_exit':obj['exit'],'rows':len(rows),'statistics':stats,'regression':reg}
(s.E/'statistics_adapter_real_split_test.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
