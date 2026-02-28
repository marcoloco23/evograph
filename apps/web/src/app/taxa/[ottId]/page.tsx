"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { getTaxon, getNeighbors, getSubtreeGraph } from "@/lib/api";
import { wikipediaUrl, inaturalistUrl, ebirdUrl } from "@/lib/external-links";
import type { TaxonDetail, TaxonSummary, NeighborOut, GraphResponse } from "@/lib/types";
import TaxonCard from "@/components/TaxonCard";

const GraphView = dynamic(() => import("@/components/GraphView"), { ssr: false });

// ── rank color map ──────────────────────────────────
const RANK_COLORS: Record<string, string> = {
  class: "#e57373",
  order: "#ffb74d",
  family: "#fff176",
  subfamily: "#dce775",
  genus: "#81c784",
  species: "#4fc3f7",
  subspecies: "#4dd0e1",
};

function rankColor(rank: string): string {
  return RANK_COLORS[rank] ?? "#888";
}

// ── collapsible section ─────────────────────────────
function CollapsibleSection({
  title,
  count,
  defaultOpen,
  children,
}: {
  title: string;
  count: number;
  defaultOpen: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="collapsible-section">
      <button
        className="collapsible-toggle"
        onClick={() => setOpen(!open)}
      >
        <span className="collapsible-arrow" data-open={open}>&#9656;</span>
        <span>{title}</span>
        <span className="collapsible-count">{count}</span>
      </button>
      {open && <div className="collapsible-body">{children}</div>}
    </div>
  );
}

// ── group children by rank ──────────────────────────
function groupByRank(children: TaxonSummary[]): [string, TaxonSummary[]][] {
  const groups = new Map<string, TaxonSummary[]>();
  for (const child of children) {
    const list = groups.get(child.rank) ?? [];
    list.push(child);
    groups.set(child.rank, list);
  }
  // Sort by rank hierarchy
  const order = ["order", "suborder", "infraorder", "family", "subfamily", "tribe", "genus", "species", "subspecies"];
  return [...groups.entries()].sort((a, b) => {
    const ai = order.indexOf(a[0]);
    const bi = order.indexOf(b[0]);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });
}

// ── stats bar ───────────────────────────────────────
function pluralRank(rank: string, count: number): string {
  if (count === 1) return rank;
  if (rank === "species" || rank === "subspecies") return rank;
  if (rank === "family" || rank === "subfamily") return rank.slice(0, -1) + "ies";
  if (rank === "genus") return "genera";
  if (rank === "class") return "classes";
  return rank + "s";
}

function StatsBar({ items }: { items: TaxonSummary[] }) {
  const groups = groupByRank(items);
  return (
    <div className="stats-bar">
      <span className="stats-total">{items.length} children</span>
      <span className="stats-sep">&mdash;</span>
      {groups.map(([rank, list]) => (
        <span key={rank} className="stats-item">
          <span className="stats-count">{list.length}</span>{" "}
          <span style={{ color: rankColor(rank) }}>{pluralRank(rank, list.length)}</span>
        </span>
      ))}
    </div>
  );
}

// ── neighbor card ───────────────────────────────────
function NeighborCard({ neighbor, maxDist }: { neighbor: NeighborOut; maxDist: number }) {
  // Similarity: 1 = identical, 0 = maximally distant
  const similarity = Math.max(0, 1 - neighbor.distance / maxDist);
  const pct = Math.round(similarity * 100);
  // Color: green (similar) → orange (distant)
  const hue = Math.round(similarity * 120); // 120=green, 0=red
  const barColor = `hsl(${hue}, 70%, 50%)`;

  return (
    <Link href={`/taxa/${neighbor.ott_id}`} className="neighbor-card">
      <div className="neighbor-bar-bg" style={{ width: `${pct}%`, background: barColor }} />
      <div className="neighbor-card-content">
        <span className={neighbor.rank === "species" ? "italic" : ""}>
          {neighbor.name}
        </span>
        <span className="neighbor-similarity" style={{ color: barColor }}>
          {pct}% similar
        </span>
      </div>
    </Link>
  );
}

// ── main component ──────────────────────────────────
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

  if (error) return <div className="error">Error: {error}</div>;
  if (!taxon) return <div className="loading">Loading taxon...</div>;

  const isSpecies = taxon.rank === "species" || taxon.rank === "subspecies";
  const hasMiEdges = graph?.edges.some((e) => e.kind === "mi") ?? false;
  const showGraph = hasMiEdges && neighbors.length > 0;
  const grouped = groupByRank(taxon.children);
  const neighborMaxDist = neighbors.length > 0
    ? Math.max(...neighbors.map((n) => n.distance)) * 1.1  // 10% headroom
    : 1;

  return (
    <div>
      {/* Breadcrumbs */}
      {taxon.lineage.length > 0 && (
        <nav className="breadcrumbs">
          {taxon.lineage.map((ancestor, i) => (
            <span key={ancestor.ott_id}>
              <Link href={`/taxa/${ancestor.ott_id}`}>
                {ancestor.name}
              </Link>
              {i < taxon.lineage.length - 1 && (
                <span className="breadcrumb-sep">&rsaquo;</span>
              )}
            </span>
          ))}
          <span className="breadcrumb-sep">&rsaquo;</span>
          <span className="breadcrumb-current">{taxon.name}</span>
        </nav>
      )}

      {/* Hero section */}
      <div className="hero-section">
        {taxon.image_url && (
          <div className="hero-image-wrap">
            <img src={taxon.image_url} alt={taxon.name} className="hero-image" />
          </div>
        )}
        <div className="hero-info">
          <h1 className="hero-title">
            <span className={isSpecies ? "italic" : ""}>{taxon.name}</span>
          </h1>
          <div className="flex gap-sm" style={{ alignItems: "center", marginTop: "0.5rem" }}>
            <span className="badge" style={{ background: rankColor(taxon.rank), color: "#000" }}>
              {taxon.rank}
            </span>
            <span style={{ color: "#888", fontSize: "0.85rem" }}>OTT {taxon.ott_id}</span>
            {taxon.ncbi_tax_id && (
              <span style={{ color: "#888", fontSize: "0.85rem" }}>NCBI {taxon.ncbi_tax_id}</span>
            )}
          </div>

          {/* External links */}
          <div className="external-links">
            <a href={taxon.wikipedia_url ?? wikipediaUrl(taxon.name)} target="_blank" rel="noopener noreferrer" className="ext-link">
              Wikipedia
            </a>
            <a href={inaturalistUrl(taxon.name)} target="_blank" rel="noopener noreferrer" className="ext-link">
              iNaturalist
            </a>
            <a href={ebirdUrl(taxon.name)} target="_blank" rel="noopener noreferrer" className="ext-link">
              eBird
            </a>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      {taxon.children.length > 0 && <StatsBar items={taxon.children} />}

      {/* Empty state */}
      {grouped.length === 0 && neighbors.length === 0 && (
        <div style={{ color: "#888", padding: "2rem 0", fontSize: "0.95rem" }}>
          No child taxa or MI neighbors in the database.
          {taxon.has_canonical_sequence && " This species has a canonical COI sequence."}
        </div>
      )}

      {/* Two-column layout */}
      <div className="detail-grid">
        {/* Left: children + neighbors */}
        <div>
          {/* Children grouped by rank */}
          {grouped.length > 0 && (
            <section style={{ marginBottom: "2rem" }}>
              <h2 style={sectionTitle}>Children</h2>
              {grouped.map(([rank, items]) => (
                <CollapsibleSection
                  key={rank}
                  title={rank}
                  count={items.length}
                  defaultOpen={items.length <= 12}
                >
                  <div className="flex flex-wrap gap-sm">
                    {items.map((child) => (
                      <TaxonCard key={child.ott_id} {...child} />
                    ))}
                  </div>
                </CollapsibleSection>
              ))}
            </section>
          )}

          {/* MI Neighbors */}
          {neighbors.length > 0 && (
            <section>
              <h2 style={sectionTitle}>MI Neighbors ({neighbors.length})</h2>
              <div className="neighbor-grid">
                {neighbors.map((n) => (
                  <NeighborCard key={n.ott_id} neighbor={n} maxDist={neighborMaxDist} />
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Right: local graph */}
        <div>
          {showGraph && graph && (
            <section>
              <h2 style={sectionTitle}>Local Graph</h2>
              <GraphView graph={graph} height={400} />
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

const sectionTitle: React.CSSProperties = {
  fontSize: "1.1rem",
  fontWeight: 600,
  marginBottom: "0.75rem",
  color: "var(--accent)",
};
