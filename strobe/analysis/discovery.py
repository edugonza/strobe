from __future__ import annotations

import enum
import itertools
from functools import cmp_to_key, partial
from typing import Literal, Dict, Set, Tuple, NamedTuple, List, AbstractSet

import networkx as nx
import pandas as pd

from strobe.instrumentation.event_log import EventLog

EFGType = Dict[str, Set[str]]
MSDType = Dict[str, Set[str]]


class DFGType:
    """Directly-follows graph."""

    edges: Dict[Tuple[str, str], int]
    start_nodes: Set[str]
    end_nodes: Set[str]

    def __init__(
        self,
        edges: Dict[Tuple[str, str], int] | None = None,
        start_nodes: Set[str] | None = None,
        end_nodes: Set[str] | None = None,
    ):
        self.edges = edges if edges is not None else dict()
        self.start_nodes = start_nodes if start_nodes is not None else set()
        self.end_nodes = end_nodes if end_nodes is not None else set()


def discover_dfg(
    df: pd.DataFrame,
) -> DFGType:
    """Discover a directly-follows graph from *df*.

    Returns
    -------
    DFGType
    """
    dfg = DFGType()

    cases = df[EventLog.CASE_ID].unique()
    for case in cases:
        case_df = df[df[EventLog.CASE_ID] == case].sort_values(
            EventLog.TIMESTAMP, ascending=True
        )
        if len(case_df) > 0:
            dfg.start_nodes.add(case_df.iloc[0][EventLog.ACTIVITY])
            dfg.end_nodes.add(case_df.iloc[-1][EventLog.ACTIVITY])
        for i in range(len(case_df) - 1):
            k = (
                case_df.iloc[i][EventLog.ACTIVITY],
                case_df.iloc[i + 1][EventLog.ACTIVITY],
            )
            dfg.edges[k] = dfg.edges.get(k, 0) + 1

    return dfg


def discover_efg(
    dfg: DFGType,
) -> EFGType:
    """Discover an eventually-follows graph from a directly-follows graph.

    Returns
    -------
    efg
    """
    efg: EFGType = dict()
    efg_inv: EFGType = dict()
    acts = set()

    if len(dfg.edges) > 0:
        for (a, b), _ in dfg.edges.items():
            efg[a] = efg.get(a, set())
            efg[a].add(b)
            efg_inv[b] = efg_inv.get(b, set())
            efg_inv[b].add(a)
            acts.add(a)
            acts.add(b)

    added = True
    while added:
        added = False
        for a in acts:
            for b in acts:
                if b not in efg.get(a, set()):
                    p = efg_inv.get(b, set())
                    s = efg.get(a, set())
                    if len(p.intersection(s)):
                        efg[a] = efg.get(a, set())
                        efg[a].add(b)
                        efg_inv[b] = efg_inv.get(b, set())
                        efg_inv[b].add(a)
                        added = True
    return efg


# def discover_msd(df: pd.DataFrame) -> MSDType:
#     m = dict()
#
#     new_df = df.assign(seq_idx=df.groupby(EventLog.CASE_ID).cumcount())
#
#     activities = df[EventLog.ACTIVITY].unique()
#     for a in activities:
#         events_of_a = new_df[df[EventLog.ACTIVITY] == a]
#         distance = events_of_a.groupby(EventLog.CASE_ID)["seq_idx"].diff()
#         m[a] = distance.min()
#     return None


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
    algorithms = ["inductive", "alpha"]
    if algorithm not in algorithms:
        raise ValueError(
            f"Unknown algorithm: {algorithm!r}. Choose from this list: {algorithms}."
        )
    # if algorithm == "inductive":
    #     return pm4py.discover_petri_net_inductive(df, noise_threshold=noise_threshold)
    # elif algorithm == "alpha":
    #     return pm4py.discover_petri_net_alpha(df)
    # else:
    #     raise ValueError(
    #         f"Unknown algorithm: {algorithm!r}. Choose 'inductive' or 'alpha'."
    #     )
    return None, None, None


class ProcessTreeOperator(enum.Enum):
    XOR = "xor"
    SEQ = "->"
    LOOP = "loop"
    PARALLEL = "parallel"
    SILENT = "silent"
    ACTIVITY = "activity"


class ProcessTree(NamedTuple):
    activity: str | None = None
    subtrees: List[ProcessTree] | None = None
    operator: ProcessTreeOperator | None = ProcessTreeOperator.ACTIVITY

    def is_silent(self) -> bool:
        return self.operator == ProcessTreeOperator.SILENT

    def is_activity(self) -> bool:
        return self.operator == ProcessTreeOperator.ACTIVITY

    def size(self) -> int:
        if self.is_silent():
            return 1
        elif self.is_activity():
            return 1
        else:
            return 1 + (sum(t.size() for t in self.subtrees) if self.subtrees else 0)

    def __repr__(self):
        if self.is_silent():
            return "τ"
        elif self.is_activity():
            return f"{{{self.activity}}}"
        else:
            return f"{self.operator}({','.join(sorted(str(t) for t in self.subtrees))})"


def xor_cut(dfg: DFGType) -> List[Set[str]] | None:
    cuts: List[Set[str]] = []

    g = nx.Graph()
    g.add_edges_from(dfg.edges.keys())
    g.add_nodes_from(dfg.start_nodes)
    g.add_nodes_from(dfg.end_nodes)
    comp = nx.connected_components(g)
    for c in comp:
        cuts.append(c)

    if len(cuts) < 2:
        return None
    return cuts


def xor_log_split(df: pd.DataFrame, cuts: List[Set[str]]) -> List[pd.DataFrame]:
    acts_per_trace_df = df.groupby(EventLog.CASE_ID)[EventLog.ACTIVITY].agg(set)

    sublogs = []
    for cut in cuts:
        trace_ids_cut = acts_per_trace_df[
            acts_per_trace_df.apply(lambda s: s.issubset(cut))
        ].index.to_list()
        sublogs.append(df[df[EventLog.CASE_ID].isin(trace_ids_cut)])

    return sublogs


def xor_split(df: pd.DataFrame, dfg: DFGType) -> List[pd.DataFrame] | None:
    cuts = xor_cut(dfg)
    if cuts is None:
        return None

    return xor_log_split(df, cuts)


def seq_cut(dfg: DFGType, efg: EFGType) -> List[AbstractSet[str]] | None:
    map_sets = dict()
    acts_in_dfg = set()
    for (a, b), _ in dfg.edges.items():
        acts_in_dfg.add(a)
        acts_in_dfg.add(b)
    acts_in_dfg.update(dfg.start_nodes)
    acts_in_dfg.update(dfg.end_nodes)

    for a in acts_in_dfg:
        map_sets[a] = frozenset([a])

    for a, b in itertools.product(acts_in_dfg, acts_in_dfg):
        if (b in efg.get(a, set())) and (a in efg.get(b, set())):
            joined_set = frozenset(map_sets[a].union(map_sets[b]))
            map_sets[a] = joined_set
            map_sets[b] = joined_set
        if (b not in efg.get(a, set())) and (a not in efg.get(b, set())):
            joined_set = frozenset(map_sets[a].union(map_sets[b]))
            map_sets[a] = joined_set
            map_sets[b] = joined_set
    cuts = set(map_sets.values())

    def cmp_reachability(a_set: AbstractSet[str], b_set: AbstractSet[str]) -> int:
        a_less_b = True
        for a in a_set:
            efg_a = efg.get(a, set())
            if not efg_a.issuperset(b_set):
                a_less_b = False
                break

        b_less_a = True
        for b in b_set:
            efg_b = efg.get(b, set())
            if not efg_b.issuperset(a_set):
                b_less_a = False
                break

        if a_less_b == b_less_a:
            return 0
        elif a_less_b:
            return -1
        else:
            return 1

    if len(cuts) > 1:
        # We found a sequential cut
        return sorted(cuts, key=cmp_to_key(cmp_reachability))
    return None


def seq_log_split(df: pd.DataFrame, cuts: List[AbstractSet[str]]) -> List[pd.DataFrame]:
    def filter_case(target_activities, group):
        in_target = group[EventLog.ACTIVITY].isin(target_activities)
        non_target_mask = ~in_target

        # Cumsum becomes 1+ after we see the first non-target activity
        cumsum = non_target_mask.cumsum()

        # Keep rows that are in target AND haven't hit a non-target yet (cumsum == 0)
        return group[in_target & (cumsum == 0)]

    rest_log = df
    sublogs = []

    for cut in cuts:
        result = rest_log.groupby(EventLog.CASE_ID, group_keys=False).apply(
            partial(filter_case, cut)
        )
        rest_log = rest_log.drop(result.index)
        sublogs.append(result)

    return sublogs


def seq_split(
    df: pd.DataFrame, dfg: DFGType, efg: EFGType
) -> List[pd.DataFrame] | None:
    cuts = seq_cut(dfg, efg)
    if cuts is None:
        return None

    return seq_log_split(df, cuts)


def parallel_cut(dfg: DFGType, msd: MSDType) -> List[Set[str]] | None:
    # acts_in_dfg = set()
    # for (a, b), _ in dfg.edges.items():
    #     acts_in_dfg.add(a)
    #     acts_in_dfg.add(b)
    # acts_in_dfg.update(dfg.start_nodes)
    # acts_in_dfg.update(dfg.end_nodes)
    #
    # map_sets = dict()
    #
    # for a in acts_in_dfg:
    #     map_sets[a] = frozenset([a])
    #
    # for a, b in itertools.product(acts_in_dfg, acts_in_dfg):
    #     if a == b:
    #         continue
    #     elif ((a, b) not in dfg.edges) and ((b, a) not in dfg.edges):
    #         joined_set = frozenset(map_sets[a].union(map_sets[b]))
    #         map_sets[a] = joined_set
    #         map_sets[b] = joined_set
    #
    # map_sets.values()
    # return cuts
    return []


def parallel_log_split(df: pd.DataFrame, cuts: List[Set[str]]) -> List[pd.DataFrame]:
    return []


def parallel_split(df: pd.DataFrame, dfg: DFGType) -> List[pd.DataFrame] | None:
    # cuts = parallel_cut(dfg)
    cuts = None
    if cuts is None:
        return None

    return parallel_log_split(df, cuts)


def loop_split(df: pd.DataFrame, dfg: DFGType) -> List[pd.DataFrame] | None:
    return None


def select(df: pd.DataFrame) -> Tuple[ProcessTreeOperator, List[pd.DataFrame]] | None:
    dfg = discover_dfg(df)
    efg = discover_efg(dfg)

    if len(df) < 2:
        return None
    elif c := xor_split(df, dfg):
        return ProcessTreeOperator.XOR, c
    elif c := seq_split(df, dfg, efg):
        return ProcessTreeOperator.SEQ, c
    elif c := parallel_split(df, dfg):
        return ProcessTreeOperator.PARALLEL, c
    elif c := loop_split(df, dfg):
        return ProcessTreeOperator.LOOP, c
    return None


def fallback(df: pd.DataFrame) -> ProcessTree:
    return ProcessTree(None, None, ProcessTreeOperator.SILENT)  # FIXME


def single_activity_log(df: pd.DataFrame) -> bool:
    return (df.groupby(EventLog.CASE_ID).size().max() == 1) and (
        df[EventLog.ACTIVITY].nunique() == 1
    )


def inductive_miner(df: pd.DataFrame, noise_threshold: float = 0.0) -> ProcessTree:

    if len(df) == 0:
        return ProcessTree(None, None, ProcessTreeOperator.SILENT)

    if single_activity_log(df):
        return ProcessTree(
            df.iloc[0][EventLog.ACTIVITY], None, ProcessTreeOperator.ACTIVITY
        )

    p = select(df)
    if p is None:
        return fallback(df)

    op, sublogs = p
    return ProcessTree(
        operator=op,
        subtrees=[inductive_miner(sublog, noise_threshold) for sublog in sublogs],
    )
