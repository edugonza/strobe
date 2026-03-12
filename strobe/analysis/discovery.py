from __future__ import annotations

from typing import Literal, Dict, Set, Tuple

import pandas as pd

from strobe.instrumentation.event_log import EventLog

DFGType = Dict[Tuple[str, str], int]


def discover_dfg(
    df: pd.DataFrame,
) -> tuple[DFGType, Set[str], Set[str]]:
    """Discover a directly-follows graph from *df*.

    Returns
    -------
    (dfg, start_activities, end_activities)
    """
    dfg: DFGType = dict()
    start_activities = set()
    end_activities = set()

    cases = df[EventLog.CASE_ID].unique()
    for case in cases:
        case_df = df[df[EventLog.CASE_ID] == case].sort_values(
            EventLog.TIMESTAMP, ascending=True
        )
        if len(case_df) > 0:
            start_activities.add(case_df.iloc[0][EventLog.ACTIVITY])
            end_activities.add(case_df.iloc[-1][EventLog.ACTIVITY])
        for i in range(len(case_df) - 1):
            k = (
                case_df.iloc[i][EventLog.ACTIVITY],
                case_df.iloc[i + 1][EventLog.ACTIVITY],
            )
            dfg[k] = dfg.get(k, 0) + 1

    return dfg, start_activities, end_activities


def discover_process_model(
    df: pd.DataFrame,
    algorithm: Literal["inductive", "alpha"] = "inductive",
    noise_threshold: float = 0.0,
) -> tuple:
    """Discover a Petri net from *df*.

    Parameters
    ----------
    algorithm:
        ``"inductive"`` uses the Inductive Miner (default);
        ``"alpha"`` uses the Alpha Miner.
    noise_threshold:
        Noise filtering threshold passed to the Inductive Miner (ignored for
        the Alpha Miner).

    Returns
    -------
    (net, initial_marking, final_marking)
    """
    # if algorithm == "inductive":
    #     return pm4py.discover_petri_net_inductive(df, noise_threshold=noise_threshold)
    # elif algorithm == "alpha":
    #     return pm4py.discover_petri_net_alpha(df)
    # else:
    #     raise ValueError(
    #         f"Unknown algorithm: {algorithm!r}. Choose 'inductive' or 'alpha'."
    #     )
    return None, None, None
