"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { getMiNetwork } from "@/lib/api";
import type { GraphResponse } from "@/lib/types";
import { GraphPageSkeleton } from "@/components/Skeleton";

const GraphViewSigma = dynamic(
  () => import("@/components/GraphViewSigma"),
  { ssr: false }
);

export default function GraphPage() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
        <p style={{ color: "#666", fontSize: "0.85rem", margin: 0 }}>
          Species with COI barcodes connected by mutual information similarity.
          Closer species have thicker, brighter edges. Hover to highlight, click to view details.
        </p>

        {graph && !loading && (
          <span style={{ fontSize: "0.75rem", color: "#555", whiteSpace: "nowrap", marginLeft: "1rem" }}>
            {speciesCount} species / {miCount} MI edges
          </span>
        )}
      </div>

      {loading ? (
        <GraphPageSkeleton />
      ) : graph ? (
        <GraphViewSigma
          graph={graph}
          height="78vh"
          layout="force"
        />
      ) : null}
    </div>
  );
}
