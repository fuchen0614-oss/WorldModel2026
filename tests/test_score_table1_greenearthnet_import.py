"""Regression guard for the strict GreenEarthNet Table 1 scorer wiring."""

from eval.eval_greenearthnet_official import score_directory as official_score_directory
from eval.score_table1_greenearthnet import score_directory


def test_strict_scorer_reuses_official_score_directory():
    assert score_directory is official_score_directory


def test_strict_scorer_rejects_stale_score_regions(tmp_path):
    from eval.score_table1_greenearthnet import _reject_stale_score_parquets

    expected_source = tmp_path / "expected" / "cube.nc"
    output = tmp_path / "scores"
    output.mkdir()
    (output / "scores_en21x_stale.parquet").write_bytes(b"stale")
    try:
        _reject_stale_score_parquets(output, [expected_source])
    except FileExistsError as error:
        assert "stale" in str(error)
    else:
        raise AssertionError("stale score region was accepted")
