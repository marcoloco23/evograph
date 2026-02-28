"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import type { GraphResponse } from "@/lib/types";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";

cytoscape.use(fcose);

interface GraphViewProps {
  graph: GraphResponse;
  height?: number | string;
  layout?: "force" | "radial";
  onNodeDoubleClick?: (ottId: number) => void;
}

const RANK_SIZE: Record<string, number> = {
  class: 22,
  order: 16,
  family: 12,
  subfamily: 10,
  genus: 8,
  species: 6,
  subspecies: 5,
};

const RANK_COLOR: Record<string, string> = {
  class: "#ef5350",
  order: "#ffa726",
  family: "#ffee58",
  subfamily: "#aed581",
  genus: "#4dd0e1",
  species: "#ab47bc",
  subspecies: "#f48fb1",
};

const LEGEND_RANKS = ["class", "order", "family", "genus", "species"] as const;

export default function GraphView({
  graph,
  height = 600,
  layout = "force",
  onNodeDoubleClick,
}: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (!containerRef.current) return;

    const elements: cytoscape.ElementDefinition[] = [
      ...graph.nodes.map((n) => ({
        data: {
          id: String(n.ott_id),
          label: n.name,
          rank: n.rank,
        },
      })),
      ...graph.edges.map((e, i) => ({
        data: {
          id: `e${i}`,
          source: String(e.src),
          target: String(e.dst),
          kind: e.kind,
          distance: e.distance,
        },
      })),
    ];

    const hasMiEdges = graph.edges.some((e) => e.kind === "mi");

    // Rank-specific selectors for node coloring via stylesheet
    const rankStyles: cytoscape.Stylesheet[] = Object.entries(RANK_COLOR).map(
      ([rank, color]) => ({
        selector: `node[rank="${rank}"]`,
        style: {
          "background-color": color,
          width: RANK_SIZE[rank] ?? 6,
          height: RANK_SIZE[rank] ?? 6,
        } as cytoscape.Css.Node,
      })
    );

    // Always-visible labels for higher-rank nodes
    const labelStyles: cytoscape.Stylesheet[] = [
      {
        selector: 'node[rank="class"], node[rank="order"], node[rank="family"]',
        style: {
          label: "data(label)",
          "font-size": 9,
          color: "#ccc",
          "text-outline-color": "#000",
          "text-outline-width": 1.5,
          "text-valign": "top",
          "text-margin-y": -4,
        } as cytoscape.Css.Node,
      },
    ];

    const layoutConfig =
      layout === "radial"
        ? {
            name: "breadthfirst",
            ...({
              directed: true,
              circle: true,
              spacingFactor: 1.2,
              maximal: true,
              animate: false,
            } as Record<string, unknown>),
          }
        : {
            name: "fcose",
            ...({
              animate: false,
              quality: "proof",
              nodeDimensionsIncludeLabels: false,
              idealEdgeLength: hasMiEdges ? 80 : 150,
              nodeRepulsion: hasMiEdges ? 8000 : 40000,
              edgeElasticity: 0.2,
              gravity: 0.3,
              gravityRange: 2.0,
              numIter: 5000,
            } as Record<string, unknown>),
          };

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        // Default node style
        {
          selector: "node",
          style: {
            label: "",
            "background-color": "#4fc3f7",
            width: 6,
            height: 6,
            "border-width": 0,
          } as cytoscape.Css.Node,
        },
        // Rank-specific styles
        ...rankStyles,
        // Labels for high-rank nodes
        ...labelStyles,
        // Taxonomy edges: thin structural skeleton
        {
          selector: "edge[kind='taxonomy']",
          style: {
            "line-color": "#555",
            "line-style": "solid",
            opacity: hasMiEdges ? 0.12 : 0.5,
            width: hasMiEdges ? 0.5 : 1,
            "curve-style": "haystack",
          } as cytoscape.Css.Edge,
        },
        // MI similarity edges: colored arcs
        {
          selector: "edge[kind='mi']",
          style: {
            "line-color": "#4fc3f7",
            "line-style": "solid",
            opacity: 0.25,
            width: 1,
            "curve-style": "haystack",
          } as cytoscape.Css.Edge,
        },
      ],
      layout: layoutConfig,
      minZoom: 0.1,
      maxZoom: 8,
      pixelRatio: 1,
      hideEdgesOnViewport: graph.edges.length > 500,
      textureOnViewport: graph.edges.length > 500,
    } as cytoscape.CytoscapeOptions);

    // Apply MI edge width based on distance
    if (hasMiEdges) {
      cy.edges("[kind='mi']").forEach((edge) => {
        const dist = edge.data("distance") as number | null;
        if (dist != null) {
          // Closer = thicker + more opaque + bluer
          const t = Math.min(Math.max(dist, 0), 1);
          const w = Math.max(0.5, 2.5 * (1 - t));
          const op = 0.15 + 0.35 * (1 - t);
          // Blue (close) to red (far)
          const r = Math.round(79 + t * 160);
          const g = Math.round(195 - t * 150);
          const b = Math.round(247 - t * 200);
          edge.style({
            width: w,
            opacity: op,
            "line-color": `rgb(${r},${g},${b})`,
          });
        }
      });
    }

    // Hover: show label + highlight edges
    cy.on("mouseover", "node", (evt) => {
      const node = evt.target;
      node.style({
        label: node.data("label"),
        "font-size": 11,
        color: "#fff",
        "text-outline-color": "#000",
        "text-outline-width": 2,
        "text-valign": "top",
        "text-margin-y": -6,
        "z-index": 999,
      });
      // Brighten connected MI edges
      node.connectedEdges("[kind='mi']").style({ opacity: 0.7, width: 2 });
      node.connectedEdges("[kind='taxonomy']").style({ opacity: 0.4, width: 1 });
    });
    cy.on("mouseout", "node", (evt) => {
      const node = evt.target;
      const rank = node.data("rank");
      const isHighRank = ["class", "order", "family"].includes(rank);
      if (!isHighRank) {
        node.style({ label: "" });
      } else {
        node.style({ "font-size": 9, color: "#ccc" });
      }
      node.connectedEdges("[kind='mi']").forEach((edge: cytoscape.EdgeSingular) => {
        const dist = edge.data("distance") as number | null;
        const t = dist != null ? Math.min(Math.max(dist, 0), 1) : 0.5;
        edge.style({ opacity: 0.15 + 0.35 * (1 - t), width: Math.max(0.5, 2.5 * (1 - t)) });
      });
      node.connectedEdges("[kind='taxonomy']").style({
        opacity: hasMiEdges ? 0.12 : 0.5,
        width: hasMiEdges ? 0.5 : 1,
      });
    });

    // Click: navigate
    cy.on("tap", "node", (evt) => {
      router.push(`/taxa/${evt.target.id()}`);
    });

    // Double-click: re-root
    if (onNodeDoubleClick) {
      cy.on("dbltap", "node", (evt) => {
        onNodeDoubleClick(Number(evt.target.id()));
      });
    }

    // Fit after layout
    cy.on("layoutstop", () => {
      cy.fit(undefined, 30);
    });

    cyRef.current = cy;
    return () => { cy.destroy(); };
  }, [graph, router, layout, onNodeDoubleClick]);

  return (
    <div>
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height,
          background: "#0a0a0a",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius)",
        }}
      />
      <div style={{
        display: "flex",
        gap: "0.75rem",
        padding: "0.5rem 0",
        flexWrap: "wrap",
        fontSize: "0.7rem",
        color: "#666",
        alignItems: "center",
      }}>
        {LEGEND_RANKS.map((rank) => (
          <span key={rank} style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <span style={{
              display: "inline-block",
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: RANK_COLOR[rank],
            }} />
            {rank}
          </span>
        ))}
        <span style={{ color: "#444", margin: "0 0.25rem" }}>|</span>
        <span style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
          <span style={{ display: "inline-block", width: 14, height: 1, background: "#555" }} />
          taxonomy
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
          <span style={{ display: "inline-block", width: 14, height: 2, background: "#4fc3f7", opacity: 0.6 }} />
          MI similarity
        </span>
      </div>
    </div>
  );
}
