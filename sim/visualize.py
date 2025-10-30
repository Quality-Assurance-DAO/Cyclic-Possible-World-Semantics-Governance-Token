from __future__ import annotations

import json
import os
from typing import Dict, Any, List
from io import BytesIO

import matplotlib.pyplot as plt
import networkx as nx


def draw_graph_png(G: nx.DiGraph, active_world: str, labels: Dict[str, str], outfile: str) -> None:
    pos = nx.spring_layout(G, seed=7)
    plt.figure(figsize=(8, 6))
    node_colors = ["#ffcc00" if n == active_world else "#87ceeb" for n in G.nodes()]
    nx.draw(G, pos, with_labels=False, node_color=node_colors, arrows=True, arrowstyle='-|>')
    nx.draw_networkx_labels(G, pos, labels={n: labels.get(n, n) for n in G.nodes()}, font_size=8)
    plt.tight_layout()
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    plt.savefig(outfile)
    plt.close()


def draw_timeline(history_path: str, outfile: str) -> None:
    if not os.path.exists(history_path):
        return
    with open(history_path, 'r', encoding='utf-8') as f:
        history = json.load(f)
    if not history:
        return
    world_ids: List[str] = sorted(list({h["from_world"] for h in history} | {h["to_world"] for h in history}))
    world_index: Dict[str, int] = {w: i for i, w in enumerate(world_ids)}
    xs = list(range(len(history)))
    ys = [world_index[h["to_world"]] for h in history]
    labels = [h["to_world"] for h in history]

    plt.figure(figsize=(9, 3))
    plt.plot(xs, ys, marker='o')
    for i, lbl in enumerate(labels):
        plt.annotate(lbl, (xs[i], ys[i]), textcoords="offset points", xytext=(0, 8), ha='center', fontsize=8)
    plt.yticks(list(world_index.values()), list(world_index.keys()))
    plt.xlabel("Transition #")
    plt.ylabel("World")
    plt.title("Transition Timeline")
    plt.tight_layout()
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    plt.savefig(outfile)
    plt.close()


def graph_png_bytes(G: nx.DiGraph, active_world: str, labels: Dict[str, str]) -> bytes:
    pos = nx.spring_layout(G, seed=7)
    plt.figure(figsize=(8, 6))
    node_colors = ["#ffcc00" if n == active_world else "#87ceeb" for n in G.nodes()]
    nx.draw(G, pos, with_labels=False, node_color=node_colors, arrows=True, arrowstyle='-|>')
    nx.draw_networkx_labels(G, pos, labels={n: labels.get(n, n) for n in G.nodes()}, font_size=8)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    return buf.getvalue()


def timeline_png_bytes(history_path: str) -> bytes:
    if not os.path.exists(history_path):
        return b""
    with open(history_path, 'r', encoding='utf-8') as f:
        history = json.load(f)
    if not history:
        return b""
    world_ids: List[str] = sorted(list({h["from_world"] for h in history} | {h["to_world"] for h in history}))
    world_index: Dict[str, int] = {w: i for i, w in enumerate(world_ids)}
    xs = list(range(len(history)))
    ys = [world_index[h["to_world"]] for h in history]
    labels = [h["to_world"] for h in history]

    plt.figure(figsize=(9, 3))
    plt.plot(xs, ys, marker='o')
    for i, lbl in enumerate(labels):
        plt.annotate(lbl, (xs[i], ys[i]), textcoords="offset points", xytext=(0, 8), ha='center', fontsize=8)
    plt.yticks(list(world_index.values()), list(world_index.keys()))
    plt.xlabel("Transition #")
    plt.ylabel("World")
    plt.title("Transition Timeline")
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    return buf.getvalue()


