from __future__ import annotations

from neurogolf.cost import conv2d_macs, conv2d_parameter_count, score_from_total_cost, tensor_nbytes


def test_cost_helpers_match_expected_counts():
    params = conv2d_parameter_count(10, 10, 3, 3, bias=False)
    macs = conv2d_macs(30, 30, 10, 10, 3, 3)
    mem = tensor_nbytes((10, 10, 3, 3))

    assert params == 900
    assert macs == 810000
    assert mem == 3600
    assert score_from_total_cost(params + mem + macs) > 1.0
