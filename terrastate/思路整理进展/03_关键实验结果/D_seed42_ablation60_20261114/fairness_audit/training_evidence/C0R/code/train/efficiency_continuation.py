"""Explicit, fail-closed epoch-boundary continuation into an independent run."""
import hashlib
import json
from pathlib import Path

PATH_ARGS = {'output_dir', 'resume', 'parent_ckpt', 'train_dir', 'val_dir',
             'val_split_manifest', 'q4_partition_manifest', 'config'}
CONTROL_ARGS = {'allow_existing_out', 'handoff_dir', 'handoff_token', 'handoff_timeout',
                'continuation_manifest', 'history_state_only'}
PATH_METADATA = {'val_split_manifest_path': 'val_split_manifest_sha256',
                 'q4_partition_manifest_path': 'q4_partition_manifest_sha256',
                 'parent_logical_id': 'parent_file_sha256'}
ALLOWED_SOURCE_FILES = {'train/train_spanworld_full_base.py', 'train/c1_checkpoint.py',
                        'train/efficiency_continuation.py', 'train/progress_io.py', 'train/topology_migration.py', 'models/spanworld_full_base.py',
                        'models/encoders/contextformer_official.py',
                        'models/encoders/pvt_contextformer_q.py'}


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def previous_continuation(checkpoint):
    record = checkpoint.get('lineage', {}).get('efficiency_continuation')
    if not record:
        return None
    record = dict(record)
    record.setdefault('manifest_path', checkpoint.get('args', {}).get('continuation_manifest', ''))
    return record


def verified_manifest_chain(checkpoint):
    record = previous_continuation(checkpoint)
    seen = set()
    try:
        while record:
            location = record['manifest_path']
            if not location or location in seen or file_sha(location) != record['manifest_sha256']:
                return False
            seen.add(location)
            manifest = json.loads(Path(location).read_text(encoding='utf-8'))
            best = record['inherited_best']
            if (manifest.get('schema') != 'spanworld_efficiency_continuation_v1'
                    or manifest['checkpoint_sha256'] != record['checkpoint_sha256']
                    or Path(manifest['checkpoint_path']).resolve() != Path(record['checkpoint_source']).resolve()
                    or manifest['source_sha_pairs'] != record['source_sha_pairs']
                    or manifest['best_sha256'] != best['sha256']
                    or Path(manifest['best_path']).resolve() != Path(best['source_path']).resolve()):
                return False
            record = record.get('previous_continuation')
        return bool(seen)
    except (OSError, KeyError, TypeError, ValueError):
        return False


def inherited_best_matches(checkpoint, best, path):
    record = checkpoint.get('lineage', {}).get('efficiency_continuation', {}).get('inherited_best')
    if not record:
        return False
    if not verified_manifest_chain(checkpoint):
        return False
    return (file_sha(path) == record['sha256'] and best['sha'] == record['original_sha']
            and best['rmse_best'] == checkpoint['rmse_best'] == record['rmse_best']
            and best['step'] == record['step'] and best['epoch'] == record['epoch'])


def validate_continuation(ck, args, current_sha, world, accum):
    import torch
    manifest = json.loads(Path(args.continuation_manifest).read_text(encoding='utf-8'))
    if manifest.get('schema') != 'spanworld_efficiency_continuation_v1':
        raise ValueError('invalid continuation manifest schema')
    if file_sha(args.resume) != manifest['checkpoint_sha256']:
        raise ValueError('continuation checkpoint SHA mismatch')
    if Path(args.resume).resolve() != Path(manifest['checkpoint_path']).resolve():
        raise ValueError('continuation checkpoint path mismatch')
    out = Path(args.output_dir).resolve()
    if out in (Path(args.resume).resolve().parent, Path(manifest['best_path']).resolve().parent):
        raise ValueError('continuation output must be independent')
    if list(out.glob('*.pt')):
        raise ValueError('continuation output already contains checkpoints')
    if not (args.stage == ck['training_stage'] == 'stage2' and args.variant == ck['variant'] == 'D'):
        raise ValueError('only authorized stage2 D continuation supported')
    if (world, args.per_gpu_batch, accum, args.global_batch, ck['world_size'], ck['accum'], ck['global_batch']) != (4, 8, 1, 32, 4, 2, 32):
        raise ValueError('only tested D 4x4x2 to 4x8x1 continuation allowed')
    if ck['args']['per_gpu_batch']!=4 or ck['args'].get('runtime_per_gpu_batch')!=4 or args.runtime_per_gpu_batch is not None:
        raise ValueError('unexpected nominal/runtime batch representation')
    if manifest.get('topology')!={'source':[4,4,2], 'target':[4,8,1], 'global_batch':32}:
        raise ValueError('explicit tested topology manifest required')
    if ck['total_steps'] != 74500 or not 0 < ck['step'] < 74500 or ck['micro_in_epoch'] != 0:
        raise ValueError('continuation requires unfinished original budget at epoch boundary')
    if ck['completion_reason'] != 'epoch_complete' or not ck['validation_history']:
        raise ValueError('continuation checkpoint is not a validated complete epoch')
    tail = ck['validation_history'][-1]
    if (tail['epoch'], tail['step']) != (ck['epoch'], ck['step']):
        raise ValueError('epoch checkpoint/history mismatch')
    old_args, new_args = ck['args'], vars(args)
    delta_args = {k: [old_args.get(k), new_args.get(k)] for k in old_args.keys() | new_args.keys()
                  if old_args.get(k) != new_args.get(k)}
    forbidden = delta_args.keys() - PATH_ARGS - CONTROL_ARGS - {'per_gpu_batch','runtime_per_gpu_batch'}
    if forbidden:
        raise ValueError(f'continuation scientific arguments changed: {sorted(forbidden)}')
    before = ck['sha']
    path_changes = {}
    for key in before.keys() | current_sha.keys():
        if key in {'source_sha256', 'config_sha256'}:
            continue
        if before.get(key) == current_sha.get(key):
            continue
        if key in PATH_METADATA and before.get(PATH_METADATA[key]) and before[PATH_METADATA[key]] == current_sha.get(PATH_METADATA[key]):
            if key == 'parent_logical_id' and not all(str(v).startswith('/') for v in (before[key], current_sha[key])):
                raise ValueError('non-path logical parent ID cannot be rebound')
            path_changes[key] = [before[key], current_sha[key]]
        else:
            raise ValueError(f'continuation content provenance changed: {key}')
    old_files, new_files = before['source_sha256'], current_sha['source_sha256']
    changes = {k: [old_files.get(k), new_files.get(k)] for k in old_files.keys() | new_files.keys()
               if old_files.get(k) != new_files.get(k)}
    if set(changes) - ALLOWED_SOURCE_FILES or changes != manifest['source_sha_pairs']:
        raise ValueError('continuation source changes not exactly approved')
    release = json.loads((Path(__file__).resolve().parents[1] / 'continuation_release.json').read_text())
    if old_files['train/train_spanworld_full_base.py'] not in release['approved_source_trainer_sha256']:
        raise ValueError('continuation source is not the frozen D trainer')
    for rel, digest in release['files'].items():
        if file_sha(Path(__file__).resolve().parents[1] / rel) != digest:
            raise ValueError(f'continuation release file changed: {rel}')
    if file_sha(manifest['best_path']) != manifest['best_sha256']:
        raise ValueError('inherited best SHA mismatch')
    best = torch.load(manifest['best_path'], map_location='cpu', weights_only=False)
    if (best['rmse_best'], best['epoch'], best['step']) != (ck['rmse_best'], ck['rmse_best']['epoch'], ck['rmse_best']['step']):
        raise ValueError('inherited best metadata differs from checkpoint history')
    if best['sha'] != ck['sha'] and not inherited_best_matches(ck, best, manifest['best_path']):
        raise ValueError('inherited best provenance differs from source run or unverified chain')
    return {'checkpoint_source': str(Path(args.resume).resolve()),
            'checkpoint_sha256': manifest['checkpoint_sha256'],
            'manifest_sha256': file_sha(args.continuation_manifest),
            'manifest_path': str(Path(args.continuation_manifest).resolve()),
            'previous_continuation': previous_continuation(ck),
            'source_sha_pairs': changes, 'argument_changes': delta_args, 'path_changes': path_changes,
            'is_bitwise_exact_historical_resume': False,
            'topology':manifest['topology'],
            'numerical_note':'Same global batch and samples; changed FP32 reduction grouping, not bitwise exact.',
            'cuda_rng_note': 'Legacy source CUDA RNG may be empty; no missing historical RNG is fabricated.',
            'remaining_effective_steps': 74500 - ck['step'],
            'inherited_best': {'source_path': str(Path(manifest['best_path']).resolve()),
                               'sha256': manifest['best_sha256'], 'original_sha': best['sha'],
                               'rmse_best': best['rmse_best'], 'step': best['step'], 'epoch': best['epoch']}}
