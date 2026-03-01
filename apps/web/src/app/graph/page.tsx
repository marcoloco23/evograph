"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { getMiNetwork } from "@/lib/api";
import type { GraphResponse, GraphNode } from "@/lib/types";
import { GraphPageSkeleton } from "@/components/Skeleton";

const GraphViewSigma = dynamic(
  () => import("@/components/GraphViewSigma"),
  { ssr: false }
);

function NodeSearchBox({
  nodes,
  onSelect,
}: {
  nodes: GraphNode[];
  onSelect: (ottId: number | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const matches = useMemo(() => {
    if (query.length < 2) return [];
    const q = query.toLowerCase();
    return nodes
      .filter((n) => n.name.toLowerCase().includes(q))
      .slice(0, 12);
  }, [query, nodes]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} className="graph-search-box">
      <input
        type="text"
        placeholder="Search nodes..."
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          if (e.target.value.length < 2) onSelect(null);
        }}
        onFocus={() => setOpen(true)}
        className="graph-search-input"
      />
      {open && matches.length > 0 && (
        <div className="graph-search-dropdown">
          {matches.map((n) => (
            <button
              key={n.ott_id}
              className="graph-search-item"
              onClick={() => {
                onSelect(n.ott_id);
                setQuery(n.name);
                setOpen(false);
              }}
            >
              <span className={n.rank === "species" ? "italic" : ""}>
                {n.name}
              </span>
              <span className="graph-search-rank">{n.rank}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function GraphPage() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [highlightedNode, setHighlightedNode] = useState<number | null>(null);

  useEffect(() => {
    getMiNetwork()
      .then(setGraph)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (error) {
    return <div className="error">Failed to load graph: {error}</div>;
  }

  const miCount = graph ? graph.edges.filter((e) => e.kind === "mi").length : 0;
  const speciesCount = graph ? graph.nodes.length : 0;

  return (
    <div>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>
        MI Similarity Network
      </h1>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem", gap: "0.75rem" }}>
        <p style={{ color: "#666", fontSize: "0.85rem", margin: 0, flex: 1 }}>
          Species with COI barcodes connected by mutual information similarity.
          Closer species have thicker, brighter edges. Hover to highlight, click to view details.
        </p>

        {graph && !loading && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexShrink: 0 }}>
            <NodeSearchBox nodes={graph.nodes} onSelect={setHighlightedNode} />
            <span style={{ fontSize: "0.75rem", color: "#555", whiteSpace: "nowrap" }}>
              {speciesCount} species / {miCount} MI edges
            </span>
          </div>
        )}
      </div>

      {loading ? (
        <GraphPageSkeleton />
      ) : graph ? (
        <GraphViewSigma
          graph={graph}
          height="78vh"
          layout="force"
          highlightedNodeId={highlightedNode}
        />
      ) : null}
    </div>
  );
}
