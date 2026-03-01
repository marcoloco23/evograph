"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getStats } from "@/lib/api";
import type { StatsResponse } from "@/lib/types";

const RANK_COLORS: Record<string, string> = {
  class: "#e57373",
  order: "#ffb74d",
  family: "#fff176",
  genus: "#81c784",
  species: "#4fc3f7",
};

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="card" style={{ textAlign: "center", padding: "1.25rem 1rem" }}>
      <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--accent)" }}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      <div style={{ fontSize: "0.85rem", color: "#aaa", marginTop: "0.25rem" }}>
        {label}
      </div>
      {sub && (
        <div style={{ fontSize: "0.75rem", color: "#666", marginTop: "0.25rem" }}>
          {sub}
        </div>
      )}
    </div>
  );
}

function RankBar({
  ranks,
  total,
}: {
  ranks: Record<string, number>;
  total: number;
}) {
  if (total === 0) return null;

  const ordered = Object.entries(ranks).sort((a, b) => b[1] - a[1]);

  return (
    <div>
      <div
        style={{
          display: "flex",
          height: 12,
          borderRadius: 6,
          overflow: "hidden",
          marginBottom: "0.75rem",
        }}
      >
        {ordered.map(([rank, count]) => (
          <div
            key={rank}
            style={{
              width: `${(count / total) * 100}%`,
              background: RANK_COLORS[rank] || "#666",
              minWidth: count > 0 ? 2 : 0,
            }}
            title={`${rank}: ${count.toLocaleString()}`}
          />
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", fontSize: "0.8rem" }}>
        {ordered.map(([rank, count]) => (
          <div key={rank} style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: RANK_COLORS[rank] || "#666",
                flexShrink: 0,
              }}
            />
            <span style={{ textTransform: "capitalize" }}>{rank}</span>
            <span style={{ color: "#888" }}>{count.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function StatsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (error) {
    return <div className="error">Failed to load stats: {error}</div>;
  }

  if (loading || !stats) {
    return (
      <div>
        <h1 style={{ fontSize: "1.5rem", marginBottom: "1.5rem" }}>Database Stats</h1>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
            gap: "1rem",
          }}
        >
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card skeleton" style={{ height: 90 }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", margin: 0 }}>Database Stats</h1>
        <Link href="/" style={{ fontSize: "0.85rem" }}>
          Back to Home
        </Link>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "1rem",
          marginBottom: "2rem",
        }}
      >
        <StatCard label="Total Taxa" value={stats.taxa.total} />
        <StatCard label="Total Sequences" value={stats.sequences.total} />
        <StatCard label="MI Edges" value={stats.edges.total} />
        <StatCard
          label="Sequence Coverage"
          value={`${stats.sequences.coverage_pct}%`}
          sub={`${stats.sequences.species_with_sequences} / ${stats.sequences.species_total} species`}
        />
      </div>

      <div className="detail-grid">
        <section>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--accent)", marginBottom: "0.75rem" }}>
            Taxa by Rank
          </h2>
          <div className="card" style={{ padding: "1rem" }}>
            <RankBar ranks={stats.taxa.by_rank} total={stats.taxa.total} />
          </div>
        </section>

        <section>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--accent)", marginBottom: "0.75rem" }}>
            Sequences by Source
          </h2>
          <div className="card" style={{ padding: "1rem" }}>
            {Object.entries(stats.sequences.by_source).length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {Object.entries(stats.sequences.by_source)
                  .sort((a, b) => b[1] - a[1])
                  .map(([source, count]) => (
                    <div
                      key={source}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span style={{ fontWeight: 600 }}>{source}</span>
                      <span style={{ color: "#aaa" }}>{count.toLocaleString()}</span>
                    </div>
                  ))}
              </div>
            ) : (
              <p style={{ color: "#666", margin: 0 }}>No sequences ingested yet.</p>
            )}
          </div>

          {stats.edges.distance && (
            <>
              <h2
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 600,
                  color: "var(--accent)",
                  marginBottom: "0.75rem",
                  marginTop: "1.5rem",
                }}
              >
                MI Distance Distribution
              </h2>
              <div className="card" style={{ padding: "1rem" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", fontSize: "0.9rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#aaa" }}>Min</span>
                    <span style={{ fontVariantNumeric: "tabular-nums" }}>
                      {stats.edges.distance.min.toFixed(4)}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#aaa" }}>Max</span>
                    <span style={{ fontVariantNumeric: "tabular-nums" }}>
                      {stats.edges.distance.max.toFixed(4)}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#aaa" }}>Average</span>
                    <span style={{ fontVariantNumeric: "tabular-nums" }}>
                      {stats.edges.distance.avg.toFixed(4)}
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
