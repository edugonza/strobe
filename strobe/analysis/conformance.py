from __future__ import annotations

import pandas as pd
import pm4py


def check_conformance(
    df: pd.DataFrame,
    net,
    initial_marking,
    final_marking,
) -> dict[str, float]:
    """Run token-based replay conformance checking.

    Parameters
    ----------
    df:
        pm4py-formatted event log DataFrame.
    net, initial_marking, final_marking:
        Petri net model (e.g. from :func:`~strobe.analysis.discover_process_model`).

    Returns
    -------
    dict with keys ``fitness``, ``precision``, ``generalization``, ``simplicity``.
    """
    fitness = pm4py.fitness_token_based_replay(df, net, initial_marking, final_marking)
    precision = pm4py.precision_token_based_replay(df, net, initial_marking, final_marking)
    generalization = pm4py.generalization_tbr(df, net, initial_marking, final_marking)
    simplicity = pm4py.simplicity_petri_net(net, initial_marking, final_marking)

    return {
        "fitness": fitness.get("average_trace_fitness", float("nan")),
        "precision": float(precision),
        "generalization": float(generalization),
        "simplicity": float(simplicity),
    }
