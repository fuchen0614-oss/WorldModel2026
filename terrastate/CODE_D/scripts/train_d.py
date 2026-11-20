"""Generate or execute the historical D training command with explicit local paths."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PARENT_SHA = '438e8d93505827ce2a1b7ffaef78b64e46e5d65920cf79af25305af5b72e10fb'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', choices=['C1', 'C0R'], required=True)
    p.add_argument('--seed', type=int, choices=[27, 42, 97], required=True)
    p.add_argument('--train-dir', type=Path, required=True)
    p.add_argument('--val-dir', type=Path, required=True)
    p.add_argument('--parent-dir', type=Path, required=True,
                   help='Contains original best_val.pt and matching summary.json')
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--execute', action='store_true', help='Actually start 4-GPU training; otherwise print only')
    a = p.parse_args()
    source = ROOT / ('source_c1' if a.arm == 'C1' else 'source_c0r')
    config = json.loads((ROOT / 'configs' / f'D_{a.arm}.json').read_text())
    parent = (a.parent_dir / 'best_val.pt').resolve()
    out = a.output_dir.resolve()
    config.update(seed=a.seed, parent_ckpt=str(parent), expected_parent_sha256=PARENT_SHA)
    config_path = out / 'reproduction_config.json'
    argv = [sys.executable, '-m', 'torch.distributed.run', '--standalone', '--nproc_per_node=4',
            str(source / 'train/train_spanworld_full_base.py'), '--runtime-world-size', '4',
            '--config', str(config_path), '--stage', 'stage2', '--variant', 'D',
            '--arm', a.arm, '--factual-path', 'recursive' if a.arm == 'C1' else 'direct',
            '--seed', str(a.seed), '--train-dir', str(a.train_dir.resolve()),
            '--val-dir', str(a.val_dir.resolve()),
            '--val-split-manifest', str(ROOT / 'manifests/data/candidate_c_eo_split_manifest_v1.json'),
            '--val-split-selector', 'validation_subsplit.val_dev.ids',
            '--q4-partition-manifest', str(ROOT / 'manifests/data/candidate_c_q4_partition_manifest_v1.json'),
            '--parent-ckpt', str(parent), '--expected-parent-sha256', PARENT_SHA,
            '--num-workers', '4', '--log-interval', '10', '--verify-data-manifest',
            '--expect-train-manifest-sha', '17c645d92e9dd4c38ce5bf14a412115c5f6622109cff3c19118b098e604b2554',
            '--expect-val-manifest-sha', '555d44c0d59ab3902cf7d929ca86ce8bf4e3ce7cfda66c1c72b45a2ed3fd76c9',
            '--device', 'cuda', '--output-dir', str(out), '--history-state-only']
    if not a.execute:
        print(json.dumps({'command': shlex.join(argv), 'argv': argv, 'generated_config': config,
                          'executed': False}, indent=2))
        return
    if out.exists():
        raise FileExistsError('Use a new output directory; this entry point does not resume runs')
    for path in (parent, a.parent_dir / 'summary.json', a.train_dir, a.val_dir):
        if not path.exists():
            raise FileNotFoundError(path)
    with parent.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != PARENT_SHA:
            raise ValueError('Parent checkpoint SHA mismatch')
    sys.path.insert(0, str(source))
    from train.full_base_policy import verify_stage1_completion
    verify_stage1_completion(parent)
    out.mkdir(parents=True)
    config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2')
    raise SystemExit(subprocess.call(argv, cwd=source, env=env))

if __name__ == '__main__':
    main()
