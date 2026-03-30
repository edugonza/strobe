from typing import List, Tuple

import pandas as pd


def group_by_trace_variant(df: pd.DataFrame) -> List[Tuple[Tuple[str], int]]:
    """Return a list of trace variants and their frequency.

    Variants are grouped by their unique activity sequence and sorted by
    frequency (descending). Each activity gets a consistent colour across
    all variants. The returned HTML is self-contained and scrollable.
    """
    case_col = "case:concept:name"
    activity_col = "concept:name"
    time_col = "time:timestamp"

    sorted_df = df.sort_values([case_col, time_col])

    variants: dict[tuple, int] = {}
    for _case_id, group in sorted_df.groupby(case_col, sort=False):
        trace = tuple(group[activity_col].tolist())
        variants[trace] = variants.get(trace, 0) + 1

    return sorted(variants.items(), key=lambda x: x[1], reverse=True)
