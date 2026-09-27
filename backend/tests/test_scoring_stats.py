import os

import numpy as np
import pytest

from app.services.scoring.stats import _percentile_of_valid, percentile_rank


def test_percentile_rank_ties_use_average() -> None:
    ranks = percentile_rank([1, 2, 2, 3], higher_is_better=True)
    assert ranks[0] == 0.0
    assert ranks[1] == ranks[2]
    assert ranks[1] == 50.0
    assert ranks[3] == 100.0


def test_percentile_rank_excludes_nan() -> None:
    ranks = percentile_rank([1, None, 3], higher_is_better=True)
    assert ranks[0] == 0.0
    assert ranks[1] is None
    assert ranks[2] == 100.0


def test_percentile_rank_lower_is_better() -> None:
    ranks = percentile_rank([1, 2, 3], higher_is_better=False)
    assert ranks[0] == 100.0
    assert ranks[1] == 50.0
    assert ranks[2] == 0.0


@pytest.mark.skipif(
    os.environ.get("INSPECT_PERCENTILE") != "1",
    reason="Interactive pdb: INSPECT_PERCENTILE=1 pytest tests/test_scoring_stats.py::test_percentile_of_valid_breakpoint -s",
)
def test_percentile_of_valid_breakpoint() -> None:
    """Stop here, then type `s` to step into `_percentile_of_valid`.

    Useful pdb commands:
      s  step into the next call
      n  next line in the current frame
      l  list surrounding source
      p valid, count, average_rank, percentiles, result
      c  continue
    """
    # Mix of values, a NaN (dropped from ranking), and a tie at 20.
    values = np.array([10.0, np.nan, 50.0, 20.0, 20.0])
    breakpoint()
    result = _percentile_of_valid(values, higher_is_better=True)
    # After `c`, this is what you should see:
    # index 0 (10) -> 0, index 1 (nan) -> nan, index 2 (50) -> 100,
    # indices 3 and 4 (tied 20s) -> 50 each.
    print("result:", result)


def test_percentile_rank_groups_separately() -> None:
    ranks = percentile_rank(
        [1, 10, 2, 20],
        higher_is_better=True,
        group=["a", "b", "a", "b"],
    )
    assert ranks[0] == 0.0
    assert ranks[2] == 100.0
    assert ranks[1] == 0.0
    assert ranks[3] == 100.0
