"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { getTaxon, getNeighbors, getSubtreeGraph, getChildren } from "@/lib/api";
import { wikipediaUrl, inaturalistUrl, gbifUrl, ncbiUrl } from "@/lib/external-links";
import type { TaxonDetail, TaxonSummary, NeighborOut, GraphResponse } from "@/lib/types";
import TaxonCard from "@/components/TaxonCard";
import { TaxonDetailSkeleton } from "@/components/Skeleton";

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

// ── shared rank colors ──────────────────────────────
const SHARED_RANK_COLORS: Record<string, string> = {
  genus: "#81c784",
  family: "#fff176",
  subfamily: "#dce775",
  order: "#ffb74d",
  class: "#e57373",
};

// ── neighbor card ───────────────────────────────────
function NeighborCard({ neighbor }: { neighbor: NeighborOut }) {
  // Use actual NMI (normalized mutual information) as similarity percentage
  const nmiPct = Math.round(neighbor.mi_norm * 100);
  // Color: green (high NMI) → red (low NMI)
  const hue = Math.round(neighbor.mi_norm * 120); // 120=green, 0=red
  const barColor = `hsl(${hue}, 70%, 50%)`;

  return (
    <Link href={`/taxa/${neighbor.ott_id}`} className="neighbor-card">
      <div className="neighbor-bar-bg" style={{ width: `${nmiPct}%`, background: barColor }} />
      <div className="neighbor-card-content">
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: 1, minWidth: 0 }}>
          <span className={neighbor.rank === "species" ? "italic" : ""} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {neighbor.name}
          </span>
          {neighbor.shared_rank && (
            <span
              className="neighbor-shared-rank"
              style={{ background: SHARED_RANK_COLORS[neighbor.shared_rank] ?? "#666", color: "#000" }}
            >
              {neighbor.shared_rank}
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexShrink: 0 }}>
          <span className="neighbor-similarity" style={{ color: barColor }}>
            {nmiPct}% NMI
          </span>
          <span className="neighbor-meta">
            {neighbor.align_len} cols
          </span>
        </div>
      </div>
    </Link>
  );
}

// ── main component ──────────────────────────────────
export default function TaxonDetailPage() {
  const params = useParams<{ ottId: string }>();
  const ottId = Number(params.ottId);

  const [taxon, setTaxon] = useState<TaxonDetail | null>(null);
  const [allChildren, setAllChildren] = useState<TaxonSummary[]>([]);
  const [neighbors, setNeighbors] = useState<NeighborOut[]>([]);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    if (isNaN(ottId)) {
      setError("Invalid taxon ID");
      return;
    }

    setTaxon(null);
    setAllChildren([]);
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
        setAllChildren(t.children);
        setNeighbors(n);
        setGraph(g);
      })
      .catch((err: Error) => setError(err.message));
  }, [ottId]);

  const loadMoreChildren = () => {
    if (!taxon || loadingMore) return;
    setLoadingMore(true);
    getChildren(ottId, allChildren.length, 100)
      .then((page) => {
        setAllChildren((prev) => [...prev, ...page.items]);
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false));
  };

  if (error) return <div className="error">Error: {error}</div>;
  if (!taxon) return <TaxonDetailSkeleton />;

  const isSpecies = taxon.rank === "species" || taxon.rank === "subspecies";
  const hasMiEdges = graph?.edges.some((e) => e.kind === "mi") ?? false;
  const showGraph = hasMiEdges && neighbors.length > 0;
  const grouped = groupByRank(allChildren);
  const hasMoreChildren = allChildren.length < taxon.total_children;
  // Count how many neighbors share genus vs family for the summary
  const genusCount = neighbors.filter((n) => n.shared_rank === "genus").length;
  const familyCount = neighbors.filter((n) => n.shared_rank === "family" || n.shared_rank === "subfamily").length;

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
          <div className="flex gap-sm" style={{ alignItems: "center", marginTop: "0.5rem", flexWrap: "wrap" }}>
            <span className="badge" style={{ background: rankColor(taxon.rank), color: "#000" }}>
              {taxon.rank}
            </span>
            {taxon.is_extinct && (
              <span className="badge" style={{ background: "#78909c", color: "#fff" }}>
                extinct
              </span>
            )}
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
            <a href={gbifUrl(taxon.name)} target="_blank" rel="noopener noreferrer" className="ext-link">
              GBIF
            </a>
            {taxon.ncbi_tax_id && (
              <a href={ncbiUrl(taxon.ncbi_tax_id)} target="_blank" rel="noopener noreferrer" className="ext-link">
                NCBI Taxonomy
              </a>
            )}
            {taxon.has_canonical_sequence && (
              <Link href={`/taxa/${taxon.ott_id}/sequences`} className="ext-link">
                COI Sequences
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Stats bar */}
      {taxon.total_children > 0 && <StatsBar items={allChildren} />}

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
              <h2 style={sectionTitle}>
                Children
                {hasMoreChildren && (
                  <span style={{ fontSize: "0.8rem", fontWeight: 400, color: "#888", marginLeft: "0.5rem" }}>
                    ({allChildren.length} of {taxon.total_children})
                  </span>
                )}
              </h2>
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
              {hasMoreChildren && (
                <button
                  onClick={loadMoreChildren}
                  disabled={loadingMore}
                  style={{
                    marginTop: "0.75rem",
                    padding: "0.5rem 1.25rem",
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    color: "var(--accent)",
                    cursor: loadingMore ? "wait" : "pointer",
                    fontSize: "0.85rem",
                    fontWeight: 500,
                  }}
                >
                  {loadingMore
                    ? "Loading..."
                    : `Load more (${taxon.total_children - allChildren.length} remaining)`}
                </button>
              )}
            </section>
          )}

          {/* MI Neighbors */}
          {neighbors.length > 0 && (
            <section>
              <h2 style={sectionTitle}>MI Neighbors ({neighbors.length})</h2>
              <div className="neighbor-coherence">
                <span>Taxonomic coherence:</span>
                {genusCount > 0 && (
                  <span style={{ color: "#81c784" }}>
                    {genusCount} same genus
                  </span>
                )}
                {familyCount > 0 && (
                  <span style={{ color: "#fff176" }}>
                    {familyCount} same family
                  </span>
                )}
                {neighbors.length - genusCount - familyCount > 0 && (
                  <span style={{ color: "#e57373" }}>
                    {neighbors.length - genusCount - familyCount} cross-family
                  </span>
                )}
              </div>
              <div className="neighbor-grid">
                {neighbors.map((n) => (
                  <NeighborCard key={n.ott_id} neighbor={n} />
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
