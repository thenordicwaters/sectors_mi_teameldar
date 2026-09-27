from collections.abc import Sequence

import numpy as np
import pandas as pd


def percentile_rank(
    values: Sequence[float | None],
    higher_is_better: bool = True,
    group: Sequence[object] | None = None,
) -> list[float | None]:
    """Average-rank percentiles on [0, 100]. NaN / None are excluded. Best = 100 if higher_is_better."""
    numeric = np.array(
        [np.nan if value is None else float(value) for value in values],
        dtype=float,
    )
    out = np.full(numeric.shape, np.nan)
    if group is None:
        out = _percentile_of_valid(numeric, higher_is_better)
    else:
        group_labels = np.array(list(group), dtype=object)
        for label in pd.unique(group_labels):
            mask = group_labels == label
            out[mask] = _percentile_of_valid(numeric[mask], higher_is_better)
    return [None if np.isnan(value) else float(value) for value in out]


def _percentile_of_valid(values: np.ndarray, higher_is_better: bool) -> np.ndarray:
    result = np.full(values.shape, np.nan)
    valid_mask = ~np.isnan(values)
    valid = values[valid_mask]
    count = int(valid.size)
    if count == 0:
        return result
    series = pd.Series(valid if higher_is_better else -valid)
    average_rank = series.rank(method="average", ascending=True)
    if count == 1:
        percentiles = np.array([100.0])
    else:
        percentiles = ((average_rank - 1.0) / (count - 1.0) * 100.0).to_numpy()
    result[valid_mask] = percentiles
    return result
