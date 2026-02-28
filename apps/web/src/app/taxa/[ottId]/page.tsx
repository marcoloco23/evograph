"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getTaxon, getNeighbors, getSubtreeGraph } from "@/lib/api";
import type { TaxonDetail, NeighborOut, GraphResponse } from "@/lib/types";
import GraphView from "@/components/GraphView";
import TaxonCard from "@/components/TaxonCard";

export default function TaxonDetailPage() {
  const params = useParams<{ ottId: string }>();
  const ottId = Number(params.ottId);

  const [taxon, setTaxon] = useState<TaxonDetail | null>(null);
  const [neighbors, setNeighbors] = useState<NeighborOut[]>([]);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isNaN(ottId)) {
      setError("Invalid taxon ID");
      return;
    }

    setTaxon(null);
    setNeighbors([]);
    setGraph(null);
    setError(null);

    Promise.all([
      getTaxon(ottId),
      getNeighbors(ottId),
      getSubtreeGraph(ottId, 2),
    ])
      .then(([t, n, g]) => {
        setTaxon(t);
        setNeighbors(n);
        setGraph(g);
      })
      .catch((err: Error) => setError(err.message));
  }, [ottId]);

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  if (!taxon) {
    return <div className="loading">Loading taxon...</div>;
  }

  const isSpecies = taxon.rank === "species" || taxon.rank === "subspecies";

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700 }}>
          <span style={isSpecies ? { fontStyle: "italic" } : undefined}>
            {taxon.name}
          </span>
        </h1>
        <div className="flex gap-sm" style={{ alignItems: "center", marginTop: "0.5rem" }}>
          <span className="badge">{taxon.rank}</span>
          <span style={{ color: "#888", fontSize: "0.85rem" }}>
            OTT {taxon.ott_id}
          </span>
          {taxon.ncbi_tax_id && (
            <span style={{ color: "#888", fontSize: "0.85rem" }}>
              NCBI {taxon.ncbi_tax_id}
            </span>
          )}
        </div>
        {taxon.parent_ott_id && (
          <p style={{ marginTop: "0.5rem", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ color: "#888" }}>Parent:</span>
            <Link href={`/taxa/${taxon.parent_ott_id}`} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
              {taxon.parent_name ?? `OTT ${taxon.parent_ott_id}`}
            </Link>
          </p>
        )}
      </div>

      {/* Two-column layout */}
      <div style={gridStyle}>
        {/* Left: children + neighbors */}
        <div>
          {/* Children */}
          {taxon.children.length > 0 && (
            <section style={{ marginBottom: "2rem" }}>
              <h2 style={sectionTitle}>
                Children ({taxon.children.length})
              </h2>
              <div className="flex flex-wrap gap-sm">
                {taxon.children.map((child) => (
                  <TaxonCard key={child.ott_id} {...child} />
                ))}
              </div>
            </section>
          )}

          {/* Neighbors */}
          {neighbors.length > 0 && (
            <section>
              <h2 style={sectionTitle}>
                MI Neighbors ({neighbors.length})
              </h2>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Name</th>
                    <th style={thStyle}>Rank</th>
                    <th style={thStyle}>Distance</th>
                    <th style={thStyle}>MI Norm</th>
                  </tr>
                </thead>
                <tbody>
                  {neighbors.map((n) => (
                    <tr key={n.ott_id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={tdStyle}>
                        <Link href={`/taxa/${n.ott_id}`}>
                          <span style={n.rank === "species" ? { fontStyle: "italic" } : undefined}>
                            {n.name}
                          </span>
                        </Link>
                      </td>
                      <td style={tdStyle}>
                        <span className="badge">{n.rank}</span>
                      </td>
                      <td style={tdStyle}>{n.distance.toFixed(4)}</td>
                      <td style={tdStyle}>{n.mi_norm.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </div>

        {/* Right: local graph */}
        <div>
          {graph && graph.nodes.length > 0 && (
            <section>
              <h2 style={sectionTitle}>Local Graph</h2>
              <GraphView graph={graph} height={400} />
            </section>
          )}
          {taxon.image_url && (
            <div style={{ marginTop: "1rem" }}>
              <img
                src={taxon.image_url}
                alt={taxon.name}
                style={{ width: "100%", borderRadius: "var(--radius)" }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const gridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "2rem",
};

const sectionTitle: React.CSSProperties = {
  fontSize: "1.1rem",
  fontWeight: 600,
  marginBottom: "0.75rem",
  color: "var(--accent)",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "0.9rem",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "0.5rem 0.75rem",
  borderBottom: "2px solid var(--border)",
  color: "#aaa",
  fontWeight: 600,
  fontSize: "0.8rem",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const tdStyle: React.CSSProperties = {
  padding: "0.5rem 0.75rem",
};
