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
  onNodeDoubleClick?: (ottId: number) => void;
}

const RANK_SIZE: Record<string, number> = {
  class: 40,
  order: 36,
  family: 32,
  subfamily: 28,
  genus: 24,
  species: 18,
  subspecies: 16,
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

const LEGEND_RANKS = ["class", "order", "family", "genus", "species", "subspecies"] as const;

function getRankSize(rank: string): number {
  return RANK_SIZE[rank] ?? 22;
}

function getRankColor(rank: string): string {
  return RANK_COLOR[rank] ?? "#4fc3f7";
}

export default function GraphView({ graph, height = 600, onNodeDoubleClick }: GraphViewProps) {
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

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "",
            "background-color": "#4fc3f7",
            width: "data(rank)",
            height: "data(rank)",
            "border-width": 1,
            "border-color": "#333",
          } as cytoscape.Css.Node,
        },
        {
          selector: "edge[kind='taxonomy']",
          style: {
            "line-color": "#555",
            "line-style": "dashed",
            opacity: 0.4,
            width: 1,
            "curve-style": "bezier",
          } as cytoscape.Css.Edge,
        },
        {
          selector: "edge[kind='mi']",
          style: {
            "line-color": "#4fc3f7",
            "line-style": "solid",
            opacity: 0.8,
            width: 2,
            "curve-style": "bezier",
          } as cytoscape.Css.Edge,
        },
      ],
      layout: {
        name: "fcose",
        ...({
          animate: true,
          animationDuration: 500,
          nodeDimensionsIncludeLabels: true,
          idealEdgeLength: 100,
          nodeRepulsion: 6000,
        } as Record<string, unknown>),
      },
      minZoom: 0.2,
      maxZoom: 4,
    });

    // Apply rank-based node sizing and coloring
    cy.nodes().forEach((node) => {
      const rank = node.data("rank");
      const size = getRankSize(rank);
      node.style({ width: size, height: size, "background-color": getRankColor(rank) });
    });

    // Apply MI edge coloring and width based on distance
    cy.edges("[kind='mi']").forEach((edge) => {
      const dist = edge.data("distance") as number | null;
      const w = dist != null ? Math.max(1, 4 * (1 - dist)) : 2;
      edge.style({ width: w });
    });

    // Show label on hover with halo for readability
    cy.on("mouseover", "node", (evt) => {
      evt.target.style({
        label: evt.target.data("label"),
        "font-size": 12,
        color: "#ededed",
        "text-outline-color": "#000",
        "text-outline-width": 2,
        "text-valign": "top",
        "text-margin-y": -8,
      });
    });
    cy.on("mouseout", "node", (evt) => {
      evt.target.style({ label: "" });
    });

    // Single click: navigate to taxon detail
    cy.on("tap", "node", (evt) => {
      const ottId = evt.target.id();
      router.push(`/taxa/${ottId}`);
    });

    // Double-click: re-root callback
    if (onNodeDoubleClick) {
      cy.on("dbltap", "node", (evt) => {
        onNodeDoubleClick(Number(evt.target.id()));
      });
    }

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graph, router, onNodeDoubleClick]);

  return (
    <div>
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height,
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius)",
        }}
      />
      <div style={{
        display: "flex",
        gap: "1rem",
        padding: "0.5rem 0",
        flexWrap: "wrap",
        fontSize: "0.75rem",
        color: "#aaa",
      }}>
        {LEGEND_RANKS.map((rank) => (
          <span key={rank} style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
            <span style={{
              display: "inline-block",
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: RANK_COLOR[rank],
            }} />
            {rank}
          </span>
        ))}
      </div>
    </div>
  );
}
