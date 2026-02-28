"use client";

import { useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Graph from "graphology";
import Sigma from "sigma";
import { circular } from "graphology-layout";
import forceAtlas2 from "graphology-layout-forceatlas2";
import type { GraphResponse } from "@/lib/types";

interface GraphViewSigmaProps {
  graph: GraphResponse;
  height?: number | string;
  layout?: "force" | "radial";
  onNodeDoubleClick?: (ottId: number) => void;
  highlightedNodeId?: number | null;
}

/* ── Visual config ─────────────────────────────────────── */

const RANK_SIZE: Record<string, number> = {
  class: 14, order: 11, family: 8, subfamily: 6,
  genus: 5, species: 3.5, subspecies: 3,
};

const RANK_COLOR: Record<string, string> = {
  class: "#f4a261",
  order: "#e9c46a",
  family: "#2a9d8f",
  subfamily: "#52b788",
  genus: "#7fb8d8",
  species: "#b5a7d5",
  subspecies: "#d4a5a5",
};

const LEGEND_RANKS = ["class", "order", "family", "genus", "species"] as const;

// Background color for alpha blending (sigma doesn't support hex alpha on edges)
const BG = { r: 6, g: 8, b: 16 };

/** Blend a color with the background to simulate transparency. */
function blendWithBg(r: number, g: number, b: number, alpha: number): string {
  const br = Math.round(r * alpha + BG.r * (1 - alpha));
  const bg = Math.round(g * alpha + BG.g * (1 - alpha));
  const bb = Math.round(b * alpha + BG.b * (1 - alpha));
  return `rgb(${br},${bg},${bb})`;
}

/* ── Graph building ────────────────────────────────────── */

function buildGraph(data: GraphResponse, mode: "force" | "radial"): Graph {
  const g = new Graph({ type: "undirected" });
  const nodeIds = new Set(data.nodes.map((n) => String(n.ott_id)));

  for (const n of data.nodes) {
    const id = String(n.ott_id);
    const rank = n.rank || "species";
    g.addNode(id, {
      label: n.name,
      x: 0, y: 0,
      size: RANK_SIZE[rank] ?? 3.5,
      color: RANK_COLOR[rank] ?? "#b5a7d5",
      rank,
      ottId: n.ott_id,
    });
  }

  for (let i = 0; i < data.edges.length; i++) {
    const e = data.edges[i];
    const src = String(e.src);
    const dst = String(e.dst);
    if (!nodeIds.has(src) || !nodeIds.has(dst) || g.hasEdge(src, dst)) continue;

    if (e.kind === "mi") {
      const dist = e.distance ?? 0.5;
      const t = Math.min(Math.max(dist, 0), 1);
      // Strength: 1 = very close, 0 = far
      const strength = 1 - t;

      // Only show edges with meaningful similarity
      if (dist > 0.55) continue;

      // Color: teal (close) fading toward background (distant)
      // Alpha: strong=0.35, weak=0.04
      const alpha = 0.04 + 0.31 * (strength * strength);
      const color = blendWithBg(42, 157, 143, alpha);
      const size = Math.max(0.3, 2.0 * strength);

      g.addEdge(src, dst, {
        kind: "mi",
        color,
        size,
        origColor: color,
        origSize: size,
        distance: dist,
      });
    } else if (mode === "radial") {
      // Only show taxonomy edges in tree mode, very faint
      g.addEdge(src, dst, {
        kind: "taxonomy",
        color: blendWithBg(255, 255, 255, 0.06),
        size: 0.3,
        origColor: blendWithBg(255, 255, 255, 0.06),
        origSize: 0.3,
      });
    }
    // Skip taxonomy edges in MI mode — they just add noise
  }

  return g;
}

/* ── Layout ────────────────────────────────────────────── */

function applyLayout(g: Graph, mode: "force" | "radial"): void {
  if (mode === "radial") {
    circular.assign(g, { scale: 300 });
    return;
  }

  // Random initial positions
  g.forEachNode((node) => {
    g.setNodeAttribute(node, "x", (Math.random() - 0.5) * 200);
    g.setNodeAttribute(node, "y", (Math.random() - 0.5) * 200);
  });

  // Fast layout: 100 iterations is plenty for 200 nodes
  const inferred = forceAtlas2.inferSettings(g);
  forceAtlas2.assign(g, {
    iterations: 100,
    settings: {
      ...inferred,
      linLogMode: true,
      scalingRatio: 40,
      gravity: 0.08,
      strongGravityMode: false,
      barnesHutOptimize: true,
      adjustSizes: false,
      slowDown: 1,
    },
  });
}

/* ── Component ─────────────────────────────────────────── */

export default function GraphViewSigma({
  graph: graphData,
  height = 600,
  layout = "force",
  onNodeDoubleClick,
  highlightedNodeId = null,
}: GraphViewSigmaProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const router = useRouter();
  const hoveredRef = useRef<string | null>(null);

  /** Highlight a node's neighborhood, dim everything else */
  const focusNode = useCallback((g: Graph, nodeId: string | null) => {
    if (!nodeId) {
      // Restore all
      g.forEachEdge((edge, attr) => {
        g.setEdgeAttribute(edge, "color", attr.origColor as string);
        g.setEdgeAttribute(edge, "size", attr.origSize as number);
      });
      g.forEachNode((node) => {
        const rank = g.getNodeAttribute(node, "rank") as string;
        g.setNodeAttribute(node, "color", RANK_COLOR[rank] ?? "#b5a7d5");
      });
      return;
    }

    const neighbors = new Set(g.neighbors(nodeId));
    neighbors.add(nodeId);

    g.forEachNode((node) => {
      if (!neighbors.has(node)) {
        g.setNodeAttribute(node, "color", "#111520");
      }
    });

    g.forEachEdge((edge, attr, source, target) => {
      if (source === nodeId || target === nodeId) {
        g.setEdgeAttribute(edge, "color", blendWithBg(42, 157, 143, 0.7));
        g.setEdgeAttribute(edge, "size", Math.min((attr.origSize as number) * 2.5, 4));
      } else {
        g.setEdgeAttribute(edge, "color", blendWithBg(42, 157, 143, 0.01));
        g.setEdgeAttribute(edge, "size", 0.1);
      }
    });
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const g = buildGraph(graphData, layout);
    graphRef.current = g;
    applyLayout(g, layout);

    const sigma = new Sigma(g, containerRef.current, {
      allowInvalidContainer: true,
      renderLabels: true,
      renderEdgeLabels: false,
      defaultNodeColor: "#b5a7d5",
      defaultEdgeColor: blendWithBg(42, 157, 143, 0.08),
      labelColor: { color: "#9a958a" },
      labelDensity: 0.08,
      labelGridCellSize: 100,
      labelRenderedSizeThreshold: 6,
      labelFont: "system-ui, -apple-system, sans-serif",
      labelSize: 11,
      labelWeight: "400",
      zIndex: true,
      stagePadding: 50,
      nodeReducer: (_node, data) => {
        return { ...data };
      },
      edgeReducer: (_edge, data) => {
        return { ...data };
      },
    });

    sigmaRef.current = sigma;

    // Resize handling
    requestAnimationFrame(() => sigma.resize());
    const ro = new ResizeObserver(() => sigma.resize());
    ro.observe(containerRef.current);

    sigma.getCamera().animatedReset({ duration: 300 });

    // Hover
    sigma.on("enterNode", ({ node }) => {
      hoveredRef.current = node;
      focusNode(g, node);
      sigma.refresh();
      if (containerRef.current) containerRef.current.style.cursor = "pointer";
    });
    sigma.on("leaveNode", () => {
      hoveredRef.current = null;
      focusNode(g, null);
      sigma.refresh();
      if (containerRef.current) containerRef.current.style.cursor = "default";
    });

    // Click → navigate
    sigma.on("clickNode", ({ node }) => {
      router.push(`/taxa/${node}`);
    });

    // Double-click → re-root
    sigma.on("doubleClickNode", ({ node }) => {
      if (onNodeDoubleClick) onNodeDoubleClick(Number(node));
    });

    return () => {
      ro.disconnect();
      sigma.kill();
      sigmaRef.current = null;
      graphRef.current = null;
      hoveredRef.current = null;
    };
  }, [graphData, layout, router, onNodeDoubleClick, focusNode]);

  // External highlight (from search)
  useEffect(() => {
    if (highlightedNodeId == null || !graphRef.current || !sigmaRef.current) return;
    const nodeId = String(highlightedNodeId);
    if (graphRef.current.hasNode(nodeId)) {
      focusNode(graphRef.current, nodeId);
      sigmaRef.current.refresh();
      const pos = graphRef.current.getNodeAttributes(nodeId);
      sigmaRef.current.getCamera().animate(
        { x: pos.x as number, y: pos.y as number, ratio: 0.4 },
        { duration: 400 }
      );
    }
  }, [highlightedNodeId, focusNode]);

  return (
    <div className="graph-wrapper">
      <div
        ref={containerRef}
        className="graph-sigma-container"
        style={{ height }}
      />
      <div className="graph-legend">
        {LEGEND_RANKS.map((rank) => (
          <span key={rank} className="graph-legend-item">
            <span className="graph-legend-dot" style={{ background: RANK_COLOR[rank] }} />
            {rank}
          </span>
        ))}
        <span className="graph-legend-sep">&middot;</span>
        <span className="graph-legend-item">
          <span className="graph-legend-line graph-legend-line-mi" />
          MI similarity
        </span>
        <span className="graph-legend-hint">
          Hover to focus &middot; Click to open &middot; Scroll to zoom
        </span>
      </div>
    </div>
  );
}
