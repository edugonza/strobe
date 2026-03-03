from __future__ import annotations

from typing import Literal

import pandas as pd
import pm4py


def discover_dfg(
    df: pd.DataFrame,
) -> tuple[dict, dict, dict]:
    """Discover a directly-follows graph from *df*.

    Returns
    -------
    (dfg, start_activities, end_activities)
    """
    return pm4py.discover_dfg(df)


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
    if algorithm == "inductive":
        return pm4py.discover_petri_net_inductive(df, noise_threshold=noise_threshold)
    elif algorithm == "alpha":
        return pm4py.discover_petri_net_alpha(df)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm!r}. Choose 'inductive' or 'alpha'.")
