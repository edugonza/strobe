"""Pure Plotly figure factories — no Streamlit dependency."""

from __future__ import annotations

from collections import defaultdict, deque

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _hierarchical_layout(G: nx.DiGraph, spacing: float = 2.0) -> dict:
    """Compute hierarchical (top-down flowchart) positions for a directed graph.

    Uses BFS from source nodes to assign layers, arranging them top-to-bottom
    for a flowchart-like appearance. Falls back to spring layout if no sources found.
    """
    # Assign nodes to layers using BFS from sources
    in_degree = dict(G.in_degree())
    sources = [n for n in G.nodes() if in_degree[n] == 0]

    if not sources:
        # No sources found (all nodes in cycles), use spring layout fallback
        return nx.spring_layout(G, seed=42)

    layer_assignment = {}
    queue = deque(sources)

    for source in sources:
        layer_assignment[source] = 0

    while queue:
        node = queue.popleft()

        for successor in G.successors(node):
            # Assign to max layer of predecessors + 1
            max_pred_layer = max(
                (layer_assignment.get(pred, -1) for pred in G.predecessors(successor)),
                default=-1,
            )
            new_layer = max_pred_layer + 1
            layer_assignment[successor] = max(
                layer_assignment.get(successor, -1), new_layer
            )

            if (
                successor not in layer_assignment
                or layer_assignment[successor] == new_layer
            ):
                queue.append(successor)

    # Group nodes by layer
    layers_dict = defaultdict(list)
    for node, layer in layer_assignment.items():
        layers_dict[layer].append(node)

    # Compute positions: layers go top-to-bottom, nodes spread left-right
    pos = {}
    max_layer = max(layers_dict.keys()) if layers_dict else 0

    for layer, nodes in sorted(layers_dict.items()):
        y = max_layer - layer  # top-down: layer 0 at top
        num_nodes = len(nodes)
        for i, node in enumerate(nodes):
            # Spread nodes horizontally
            x = (i - num_nodes / 2) * spacing
            pos[node] = (x, y)

    return pos


def plot_dfg(dfg: dict, start_activities: dict, end_activities: dict) -> go.Figure:
    """Return an interactive DFG figure.

    Edge width and colour encode frequency. Hover shows the frequency count.
    """
    G = nx.DiGraph()
    for (src, tgt), freq in dfg.items():
        G.add_edge(src, tgt, freq=freq)
    for act in list(start_activities) + list(end_activities):
        if act not in G:
            G.add_node(act)

    pos = _hierarchical_layout(G)

    max_freq = max((d["freq"] for _, _, d in G.edges(data=True)), default=1)

    edge_traces = []
    for src, tgt, data in G.edges(data=True):
        freq = data["freq"]
        x0, y0 = pos[src]
        x1, y1 = pos[tgt]
        width = 1 + 5 * freq / max_freq
        color = f"rgba(31,119,180,{0.3 + 0.7 * freq / max_freq:.2f})"
        edge_traces.append(
            go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(width=width, color=color),
                hoverinfo="text",
                text=f"{src} → {tgt}: {freq}",
                showlegend=False,
            )
        )

    node_x, node_y, node_text, node_hover = [], [], [], []
    node_colors = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        if node in start_activities and node in end_activities:
            label = f"{node}<br>(start+end)"
            node_colors.append("purple")
        elif node in start_activities:
            label = f"{node}<br>(start)"
            node_colors.append("green")
        elif node in end_activities:
            label = f"{node}<br>(end)"
            node_colors.append("red")
        else:
            label = node
            node_colors.append("steelblue")
        node_hover.append(label)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        hovertext=node_hover,
        hoverinfo="text",
        marker=dict(size=20, color=node_colors, line=dict(width=2, color="white")),
        showlegend=False,
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        title="Directly-Follows Graph",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_petri_net(net, initial_marking, final_marking) -> go.Figure:
    """Return an interactive Petri net figure.

    Places are rendered as circles; transitions as squares.
    Source/sink places are highlighted in green/red.
    """
    G = nx.DiGraph()
    place_ids = {}
    trans_ids = {}

    source_places = set(initial_marking.keys())
    sink_places = set(final_marking.keys())

    for place in net.places:
        node_id = f"p:{place.name}"
        place_ids[place] = node_id
        G.add_node(node_id, kind="place", name=place.name)

    for trans in net.transitions:
        node_id = f"t:{trans.name}"
        trans_ids[trans] = node_id
        label = trans.label if trans.label else f"τ({trans.name})"
        G.add_node(node_id, kind="transition", name=label)

    for arc in net.arcs:
        src = arc.source
        tgt = arc.target
        src_id = place_ids.get(src) or trans_ids.get(src)
        tgt_id = place_ids.get(tgt) or trans_ids.get(tgt)
        if src_id and tgt_id:
            G.add_edge(src_id, tgt_id)

    pos = _hierarchical_layout(G)

    edge_traces = []
    for src_id, tgt_id in G.edges():
        x0, y0 = pos[src_id]
        x1, y1 = pos[tgt_id]
        edge_traces.append(
            go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(width=1.5, color="gray"),
                hoverinfo="none",
                showlegend=False,
            )
        )

    place_x, place_y, place_text, place_colors = [], [], [], []
    for place, node_id in place_ids.items():
        x, y = pos[node_id]
        place_x.append(x)
        place_y.append(y)
        place_text.append(place.name)
        if place in source_places and place in sink_places:
            place_colors.append("purple")
        elif place in source_places:
            place_colors.append("green")
        elif place in sink_places:
            place_colors.append("red")
        else:
            place_colors.append("steelblue")

    place_trace = go.Scatter(
        x=place_x,
        y=place_y,
        mode="markers+text",
        text=place_text,
        textposition="top center",
        hoverinfo="text",
        marker=dict(
            symbol="circle",
            size=18,
            color=place_colors,
            line=dict(width=2, color="white"),
        ),
        name="Places",
    )

    trans_x, trans_y, trans_text = [], [], []
    for trans, node_id in trans_ids.items():
        x, y = pos[node_id]
        trans_x.append(x)
        trans_y.append(y)
        label = trans.label if trans.label else f"τ({trans.name})"
        trans_text.append(label)

    trans_trace = go.Scatter(
        x=trans_x,
        y=trans_y,
        mode="markers+text",
        text=trans_text,
        textposition="top center",
        hoverinfo="text",
        marker=dict(
            symbol="square",
            size=16,
            color="orange",
            line=dict(width=2, color="white"),
        ),
        name="Transitions",
    )

    fig = go.Figure(data=edge_traces + [place_trace, trans_trace])
    fig.update_layout(
        title="Petri Net",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_throughput_times(series: pd.Series) -> go.Figure:
    """Return a violin + box plot of per-case throughput times (in seconds)."""
    durations_s = series.dt.total_seconds()
    fig = px.violin(
        y=durations_s,
        box=True,
        points="all",
        labels={"y": "Duration (s)"},
        title="Throughput Times",
    )
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    return fig


def plot_activity_statistics(df: pd.DataFrame) -> go.Figure:
    """Return a dual-axis grouped bar chart: count (left) + mean duration (right)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    activities = df["activity"] if "activity" in df.columns else df.iloc[:, 0]

    fig.add_trace(
        go.Bar(
            x=activities,
            y=df["count"],
            name="Count",
            marker_color="steelblue",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=activities,
            y=df["mean_duration_s"],
            name="Mean duration (s)",
            marker_color="darkorange",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Activity Statistics",
        barmode="group",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_yaxes(title_text="Count", secondary_y=False)
    fig.update_yaxes(title_text="Mean duration (s)", secondary_y=True)
    return fig


def plot_conformance(scores: dict[str, float]) -> go.Figure:
    """Return a horizontal bar chart of the four conformance metrics."""
    metrics = ["fitness", "precision", "generalization", "simplicity"]
    values = [scores.get(m, 0.0) for m in metrics]
    colors = [f"rgba({int(255 * (1 - v))},{int(200 * v)},80,0.85)" for v in values]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=metrics,
            orientation="h",
            marker=dict(color=colors),
            text=[f"{v:.3f}" for v in values],
            textposition="outside",
            hovertemplate="%{y}: %{x:.3f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Conformance Scores",
        xaxis=dict(range=[0, 1.1], title="Score"),
        margin=dict(l=20, r=60, t=40, b=20),
    )
    return fig
