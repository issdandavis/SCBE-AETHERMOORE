from python.helm import det_tools
from python.helm.query_dispatch import dispatch


def test_det_tools_statistics_cover_percentile_weighted_mean_and_correlation():
    assert det_tools.percentile([10, 20, 30, 40], 25) == 17.5
    assert det_tools.percentile([10, 20, 30, 40], 50) == 25.0
    assert det_tools.weighted_mean([0, 1, 1], [3, 1, 1]) == 0.4
    assert det_tools.correlation([1, 2, 3], [2, 4, 6]) == 1.0
    assert det_tools.correlation([1, 1, 1], [2, 4, 6]) is None


def test_query_dispatch_routes_deeper_statistics_without_model():
    assert dispatch("25th percentile of 10 20 30 40")["answer"] == 17.5
    assert dispatch("weighted mean of 0 1 1 weights 3 1 1")["answer"] == 0.4
    assert dispatch("correlation of 1 2 3 and 2 4 6")["answer"] == 1.0
