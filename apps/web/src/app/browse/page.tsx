"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { browseSpecies } from "@/lib/api";
import type { SpeciesSummary, SpeciesBrowsePage } from "@/lib/types";

const RANK_COLORS: Record<string, string> = {
  species: "#4fc3f7",
};

const PAGE_SIZE = 50;

type FilterKey = "all" | "with_sequences" | "with_edges";

function SpeciesCard({ species }: { species: SpeciesSummary }) {
  const accent = RANK_COLORS[species.rank] ?? "#888";

  return (
    <Link
      href={`/taxa/${species.ott_id}`}
      style={{ textDecoration: "none", color: "inherit" }}
    >
      <div className="card taxon-card" style={{ borderLeftColor: accent }}>
        {species.image_url && (
          <img
            src={species.image_url}
            alt={species.name}
            className="taxon-card-img"
          />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="italic taxon-card-name">{species.name}</div>
          <div
            className="flex gap-sm"
            style={{ alignItems: "center", marginTop: "0.25rem", flexWrap: "wrap" }}
          >
            {species.is_extinct && (
              <span
                className="badge"
                style={{
                  background: "#78909c",
                  color: "#fff",
                  fontSize: "0.65rem",
                }}
              >
                extinct
              </span>
            )}
            {species.has_sequence && (
              <span
                className="badge"
                style={{
                  background: "#2a9d8f",
                  color: "#fff",
                  fontSize: "0.65rem",
                }}
              >
                COI
              </span>
            )}
            {species.edge_count > 0 && (
              <span
                className="badge"
                style={{
                  background: "#f4a261",
                  color: "#000",
                  fontSize: "0.65rem",
                }}
              >
                {species.edge_count} MI edges
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}

export default function BrowsePage() {
  const [data, setData] = useState<SpeciesBrowsePage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [filter, setFilter] = useState<FilterKey>("with_edges");
  const [showExtinct, setShowExtinct] = useState(false);
  const [sort, setSort] = useState<"name" | "edges">("edges");

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);

    const params: Record<string, unknown> = {
      offset,
      limit: PAGE_SIZE,
      sort,
    };

    if (filter === "with_sequences") {
      params.has_sequences = true;
    } else if (filter === "with_edges") {
      params.has_edges = true;
    }

    if (!showExtinct) {
      params.is_extinct = false;
    }

    browseSpecies(params as Parameters<typeof browseSpecies>[0])
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [offset, filter, showExtinct, sort]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Reset offset when filters change
  useEffect(() => {
    setOffset(0);
  }, [filter, showExtinct, sort]);

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div style={{ maxWidth: 800, margin: "0 auto" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "1rem",
        }}
      >
        <h1 style={{ fontSize: "1.5rem", margin: 0 }}>Browse Species</h1>
      </div>

      <p style={{ color: "#aaa", marginBottom: "1.5rem", fontSize: "0.9rem" }}>
        Explore species in the database. Filter to those with COI sequences or
        MI similarity edges to find species with genetic data.
      </p>

      {/* Filter controls */}
      <div
        className="card"
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          alignItems: "center",
          padding: "0.75rem 1rem",
          marginBottom: "1rem",
        }}
      >
        <div style={{ display: "flex", gap: "0.35rem" }}>
          {(
            [
              ["with_edges", "With MI edges"],
              ["with_sequences", "With COI"],
              ["all", "All species"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              style={{
                padding: "0.35rem 0.75rem",
                borderRadius: "var(--radius)",
                border: "1px solid",
                borderColor:
                  filter === key ? "var(--accent)" : "var(--border)",
                background:
                  filter === key ? "rgba(79, 195, 247, 0.15)" : "transparent",
                color: filter === key ? "var(--accent)" : "#aaa",
                cursor: "pointer",
                fontSize: "0.8rem",
                fontFamily: "inherit",
                fontWeight: filter === key ? 600 : 400,
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginLeft: "auto",
          }}
        >
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
              fontSize: "0.8rem",
              color: "#aaa",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={showExtinct}
              onChange={(e) => setShowExtinct(e.target.checked)}
              style={{ accentColor: "var(--accent)" }}
            />
            Include extinct
          </label>

          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as "name" | "edges")}
            style={{
              padding: "0.3rem 0.5rem",
              borderRadius: "var(--radius)",
              border: "1px solid var(--border)",
              background: "var(--bg-input)",
              color: "var(--fg)",
              fontSize: "0.8rem",
              fontFamily: "inherit",
              cursor: "pointer",
            }}
          >
            <option value="name">Sort: A-Z</option>
            <option value="edges">Sort: Most edges</option>
          </select>
        </div>
      </div>

      {/* Results count */}
      {data && !loading && (
        <div
          style={{
            fontSize: "0.8rem",
            color: "#888",
            marginBottom: "0.75rem",
          }}
        >
          {data.total.toLocaleString()} species found
          {totalPages > 1 && ` · Page ${currentPage} of ${totalPages}`}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="error" style={{ marginBottom: "1rem" }}>
          Failed to load species: {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {Array.from({ length: 8 }, (_, i) => (
            <div
              key={i}
              className="card skeleton"
              style={{ height: 60 }}
            />
          ))}
        </div>
      )}

      {/* Results */}
      {!loading && data && (
        <>
          {data.items.length === 0 ? (
            <div
              className="card"
              style={{
                textAlign: "center",
                padding: "2rem",
                color: "#888",
              }}
            >
              No species match the current filters.
            </div>
          ) : (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
              }}
            >
              {data.items.map((sp) => (
                <SpeciesCard key={sp.ott_id} species={sp} />
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                gap: "1rem",
                marginTop: "1.5rem",
              }}
            >
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                style={{
                  padding: "0.4rem 1rem",
                  borderRadius: "var(--radius)",
                  border: "1px solid var(--border)",
                  background: offset === 0 ? "transparent" : "var(--bg-card)",
                  color: offset === 0 ? "#555" : "var(--fg)",
                  cursor: offset === 0 ? "default" : "pointer",
                  fontSize: "0.85rem",
                  fontFamily: "inherit",
                }}
              >
                Previous
              </button>
              <span
                style={{
                  fontSize: "0.85rem",
                  color: "#aaa",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= (data?.total ?? 0)}
                style={{
                  padding: "0.4rem 1rem",
                  borderRadius: "var(--radius)",
                  border: "1px solid var(--border)",
                  background:
                    offset + PAGE_SIZE >= (data?.total ?? 0)
                      ? "transparent"
                      : "var(--bg-card)",
                  color:
                    offset + PAGE_SIZE >= (data?.total ?? 0)
                      ? "#555"
                      : "var(--fg)",
                  cursor:
                    offset + PAGE_SIZE >= (data?.total ?? 0)
                      ? "default"
                      : "pointer",
                  fontSize: "0.85rem",
                  fontFamily: "inherit",
                }}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
