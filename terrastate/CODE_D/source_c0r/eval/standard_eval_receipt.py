"""Dependency-free queue acceptance for completed standard four-split evaluation."""
COUNTS = {'iid_chopped':2856,'ood-t_chopped':1904,'ood-s_chopped':10536,'ood-st_chopped':7024}
def validate_receipt(receipt, process_exit, expected_sha, variant):
    if process_exit != 0 or receipt.get('status') != 'PASS' or receipt.get('probe') is not False:
        raise ValueError('evaluation did not complete successfully')
    if receipt.get('checkpoint_sha256') != expected_sha or len(expected_sha) != 64:
        raise ValueError('evaluation checkpoint differs')
    cfg = receipt.get('model_config', {})
    if cfg.get('arch') != 'SpanWorldFullBase' or cfg.get('training_stage') != 'stage2' or cfg.get('variant') != variant:
        raise ValueError('evaluation model route/stage/variant differs')
    if receipt.get('scorer_commit') != 'a0329636631371a4aaa9a95c75ed0a37d27b8c4f':
        raise ValueError('scorer differs')
    if set(receipt.get('splits', {})) != set(COUNTS) or receipt.get('total_samples') != 22320:
        raise ValueError('incomplete splits')
    import math
    for name, count in COUNTS.items():
        r = receipt['splits'][name]
        if r.get('count') != count or r.get('coverage_complete') is not True or r.get('checkpoint_sha256') != expected_sha:
            raise ValueError('incomplete split or changed checkpoint: '+name)
        if not 0 <= r.get('empty', -1) < count or len(r.get('relative_ids_sha256','')) != 64:
            raise ValueError('invalid coverage audit: '+name)
        if not r.get('metrics') or any(not math.isfinite(v) for v in r['metrics'].values()):
            raise ValueError('invalid metric values: '+name)
    return True
