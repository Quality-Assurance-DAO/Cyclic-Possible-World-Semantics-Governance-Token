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
    ys_from = [world_index[h["from_world"]] for h in history]
    ys_to = [world_index[h["to_world"]] for h in history]

    plt.figure(figsize=(14, 6))
    # Draw arrows from from_world to to_world
    for i, (x, y_from, y_to, h) in enumerate(zip(xs, ys_from, ys_to, history)):
        from_world = h["from_world"]
        to_world = h["to_world"]
        proposal_id = h.get("proposal_id", "unknown")
        
        # Mark source with a square and explicit label
        plt.plot(x, y_from, 's', color='green', markersize=14, markeredgecolor='darkgreen', 
                markeredgewidth=2, label='Source' if i == 0 else '', zorder=3)
        plt.annotate(f"FROM: {from_world}", (x, y_from), 
                    textcoords="offset points", xytext=(0, -25), ha='center', fontsize=9, 
                    color='darkgreen', weight='bold', bbox=dict(boxstyle='round,pad=0.3', 
                    facecolor='lightgreen', alpha=0.8))
        
        # Mark destination with a circle and explicit label
        plt.plot(x, y_to, 'o', color='blue', markersize=14, markeredgecolor='darkblue', 
                markeredgewidth=2, label='Destination' if i == 0 else '', zorder=3)
        plt.annotate(f"TO: {to_world}", (x, y_to), 
                    textcoords="offset points", xytext=(0, 25), ha='center', fontsize=9, 
                    color='darkblue', weight='bold', bbox=dict(boxstyle='round,pad=0.3', 
                    facecolor='lightblue', alpha=0.8))
        
        # Draw arrow from source to destination
        if y_from != y_to:
            arrow_offset = 0.2
            y_start = y_from + (arrow_offset if y_to > y_from else -arrow_offset)
            y_end = y_to - (arrow_offset if y_to > y_from else -arrow_offset)
            plt.annotate('', xy=(x, y_end), xytext=(x, y_start),
                        arrowprops=dict(arrowstyle='->', color='red', lw=3, alpha=0.8, zorder=2))
        
        # Add proposal ID and transition label
        mid_y = (y_from + y_to) / 2 if y_from != y_to else y_from
        transition_label = f"{proposal_id}\n{from_world} → {to_world}"
        plt.annotate(transition_label, (x, mid_y), 
                    textcoords="offset points", xytext=(0, 0), ha='center', fontsize=10, 
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.9, 
                    edgecolor='black', linewidth=2), weight='bold', zorder=4)
    
    plt.yticks(list(world_index.values()), list(world_index.keys()))
    plt.xlabel("Transition #")
    plt.ylabel("World")
    plt.title("Transition Timeline")
    plt.grid(True, alpha=0.3, axis='y')
    plt.legend(loc='upper right')
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
    ys_from = [world_index[h["from_world"]] for h in history]
    ys_to = [world_index[h["to_world"]] for h in history]

    plt.figure(figsize=(14, 6))
    # Draw arrows from from_world to to_world
    for i, (x, y_from, y_to, h) in enumerate(zip(xs, ys_from, ys_to, history)):
        from_world = h["from_world"]
        to_world = h["to_world"]
        proposal_id = h.get("proposal_id", "unknown")
        
        # Mark source with a square and explicit label
        plt.plot(x, y_from, 's', color='green', markersize=14, markeredgecolor='darkgreen', 
                markeredgewidth=2, label='Source' if i == 0 else '', zorder=3)
        plt.annotate(f"FROM: {from_world}", (x, y_from), 
                    textcoords="offset points", xytext=(0, -25), ha='center', fontsize=9, 
                    color='darkgreen', weight='bold', bbox=dict(boxstyle='round,pad=0.3', 
                    facecolor='lightgreen', alpha=0.8))
        
        # Mark destination with a circle and explicit label
        plt.plot(x, y_to, 'o', color='blue', markersize=14, markeredgecolor='darkblue', 
                markeredgewidth=2, label='Destination' if i == 0 else '', zorder=3)
        plt.annotate(f"TO: {to_world}", (x, y_to), 
                    textcoords="offset points", xytext=(0, 25), ha='center', fontsize=9, 
                    color='darkblue', weight='bold', bbox=dict(boxstyle='round,pad=0.3', 
                    facecolor='lightblue', alpha=0.8))
        
        # Draw arrow from source to destination
        if y_from != y_to:
            arrow_offset = 0.2
            y_start = y_from + (arrow_offset if y_to > y_from else -arrow_offset)
            y_end = y_to - (arrow_offset if y_to > y_from else -arrow_offset)
            plt.annotate('', xy=(x, y_end), xytext=(x, y_start),
                        arrowprops=dict(arrowstyle='->', color='red', lw=3, alpha=0.8, zorder=2))
        
        # Add proposal ID and transition label
        mid_y = (y_from + y_to) / 2 if y_from != y_to else y_from
        transition_label = f"{proposal_id}\n{from_world} → {to_world}"
        plt.annotate(transition_label, (x, mid_y), 
                    textcoords="offset points", xytext=(0, 0), ha='center', fontsize=10, 
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.9, 
                    edgecolor='black', linewidth=2), weight='bold', zorder=4)
    
    plt.yticks(list(world_index.values()), list(world_index.keys()))
    plt.xlabel("Transition #")
    plt.ylabel("World")
    plt.title("Transition Timeline")
    plt.grid(True, alpha=0.3, axis='y')
    plt.legend(loc='upper right')
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    return buf.getvalue()


