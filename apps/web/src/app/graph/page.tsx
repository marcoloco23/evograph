"use client";

import { useEffect, useState, useCallback } from "react";
import { getSubtreeGraph } from "@/lib/api";
import GraphView from "@/components/GraphView";
import type { GraphResponse } from "@/lib/types";

const DEFAULT_ROOT = 81461; // Aves

export default function GraphPage() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [depth, setDepth] = useState(1);
  const [rootOttId, setRootOttId] = useState(DEFAULT_ROOT);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getSubtreeGraph(rootOttId, depth)
      .then(setGraph)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [rootOttId, depth]);

  const handleReRoot = useCallback((ottId: number) => {
    setRootOttId(ottId);
    setDepth(1);
  }, []);

  if (error) {
    return <div className="error">Failed to load graph: {error}</div>;
  }

  return (
    <div>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>
        Phylogenetic Graph Explorer
      </h1>
      <p style={{ color: "#aaa", marginBottom: "1rem", fontSize: "0.9rem" }}>
        Solid colored edges = mutual information similarity. Dashed gray = taxonomic parentage.
        Click a node to view details. Double-click to re-root the graph.
      </p>

      {/* Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.85rem", color: "#aaa" }}>Depth:</span>
          {[1, 2, 3].map((d) => (
            <button
              key={d}
              onClick={() => setDepth(d)}
              style={{
                padding: "0.3rem 0.75rem",
                borderRadius: "var(--radius)",
                border: `1px solid ${d === depth ? "var(--accent)" : "var(--border)"}`,
                background: d === depth ? "var(--accent)" : "var(--bg-card)",
                color: d === depth ? "#000" : "var(--fg)",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: d === depth ? 700 : 400,
              }}
            >
              {d}
            </button>
          ))}
        </div>

        {rootOttId !== DEFAULT_ROOT && (
          <button
            onClick={() => { setRootOttId(DEFAULT_ROOT); setDepth(1); }}
            style={{
              padding: "0.3rem 0.75rem",
              borderRadius: "var(--radius)",
              border: "1px solid var(--border)",
              background: "var(--bg-card)",
              color: "var(--fg)",
              cursor: "pointer",
              fontSize: "0.85rem",
            }}
          >
            Reset to Aves
          </button>
        )}

        {graph && !loading && (
          <span style={{ fontSize: "0.8rem", color: "#666", marginLeft: "auto" }}>
            {graph.nodes.length} nodes / {graph.edges.length} edges
          </span>
        )}
      </div>

      {loading && !graph ? (
        <div className="loading">Loading graph...</div>
      ) : loading ? (
        <>
          <div style={{ fontSize: "0.8rem", color: "#666", marginBottom: "0.5rem" }} className="loading">
            Updating...
          </div>
          <GraphView graph={graph!} height="70vh" onNodeDoubleClick={handleReRoot} />
        </>
      ) : graph ? (
        <GraphView graph={graph} height="70vh" onNodeDoubleClick={handleReRoot} />
      ) : null}
    </div>
  );
}
