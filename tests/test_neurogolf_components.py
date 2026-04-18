from __future__ import annotations

import numpy as np

from neurogolf.components import component_mask, connected_components, extract_component
from neurogolf.structural_encode import encode_grid_structurally


def test_connected_components_and_extract_component():
    grid = np.array(
        [
            [1, 1, 0, 2],
            [1, 0, 0, 2],
            [0, 3, 3, 0],
            [0, 0, 3, 0],
        ],
        dtype=np.int64,
    )

    labels, components = connected_components(grid)

    assert len(components) == 3
    assert [component.color for component in components] == [1, 2, 3]
    assert [component.area for component in components] == [3, 2, 3]

    third_mask = component_mask(labels, components[2].label)
    assert third_mask.sum() == 3

    extracted = extract_component(grid, labels, components[2].label)
    assert np.array_equal(
        extracted,
        np.array(
            [
                [3, 3],
                [0, 3],
            ],
            dtype=np.int64,
        ),
    )


def test_structural_encoding_includes_component_state():
    grid = np.array(
        [
            [1, 0, 2],
            [1, 0, 2],
            [0, 3, 0],
        ],
        dtype=np.int64,
    )

    encoding = encode_grid_structurally(grid, target_size=5)

    assert encoding.component_labels.shape == (5, 5)
    assert len(encoding.components) == 3
    assert sorted(component.color for component in encoding.components) == [1, 2, 3]
