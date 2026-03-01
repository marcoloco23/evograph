"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getTaxon, getSequences } from "@/lib/api";
import type { TaxonDetail, SequenceOut } from "@/lib/types";
import { SkeletonLine } from "@/components/Skeleton";

// ── DNA base colors ─────────────────────────────────
const BASE_COLORS: Record<string, string> = {
  A: "#4fc3f7", // blue
  T: "#ef5350", // red
  C: "#66bb6a", // green
  G: "#ffa726", // orange
  N: "#888",
};

function colorForBase(base: string): string {
  return BASE_COLORS[base.toUpperCase()] ?? "#888";
}

// ── Sequence display ────────────────────────────────
function SequenceViewer({ sequence }: { sequence: string }) {
  const chunkSize = 10;
  const lineSize = 60; // bases per line
  const lines: string[] = [];
  for (let i = 0; i < sequence.length; i += lineSize) {
    lines.push(sequence.slice(i, i + lineSize));
  }

  return (
    <div className="sequence-viewer">
      {lines.map((line, lineIdx) => {
        const offset = lineIdx * lineSize;
        const chunks: string[] = [];
        for (let i = 0; i < line.length; i += chunkSize) {
          chunks.push(line.slice(i, i + chunkSize));
        }
        return (
          <div key={lineIdx} className="sequence-line">
            <span className="sequence-offset">{offset + 1}</span>
            <span className="sequence-bases">
              {chunks.map((chunk, ci) => (
                <span key={ci} className="sequence-chunk">
                  {[...chunk].map((base, bi) => (
                    <span key={bi} style={{ color: colorForBase(base) }}>
                      {base}
                    </span>
                  ))}
                </span>
              ))}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Composition bar ─────────────────────────────────
function CompositionBar({ sequence }: { sequence: string }) {
  const counts: Record<string, number> = { A: 0, T: 0, C: 0, G: 0, N: 0 };
  for (const base of sequence.toUpperCase()) {
    if (base in counts) counts[base]++;
    else counts["N"]++;
  }
  const total = sequence.length;

  return (
    <div className="composition-section">
      <div className="composition-bar">
        {(["A", "T", "C", "G", "N"] as const).map((base) => {
          const pct = (counts[base] / total) * 100;
          if (pct === 0) return null;
          return (
            <div
              key={base}
              style={{
                width: `${pct}%`,
                background: BASE_COLORS[base],
                height: "100%",
              }}
              title={`${base}: ${counts[base]} (${pct.toFixed(1)}%)`}
            />
          );
        })}
      </div>
      <div className="composition-legend">
        {(["A", "T", "C", "G"] as const).map((base) => (
          <span key={base} className="composition-item">
            <span className="composition-dot" style={{ background: BASE_COLORS[base] }} />
            <span style={{ color: BASE_COLORS[base], fontWeight: 600 }}>{base}</span>
            <span style={{ color: "#888" }}>
              {counts[base]} ({((counts[base] / total) * 100).toFixed(1)}%)
            </span>
          </span>
        ))}
        {counts["N"] > 0 && (
          <span className="composition-item">
            <span className="composition-dot" style={{ background: "#888" }} />
            <span style={{ color: "#888", fontWeight: 600 }}>N</span>
            <span style={{ color: "#888" }}>
              {counts["N"]} ({((counts["N"] / total) * 100).toFixed(1)}%)
            </span>
          </span>
        )}
      </div>
    </div>
  );
}

// ── Main page ───────────────────────────────────────
export default function SequencesPage() {
  const params = useParams<{ ottId: string }>();
  const ottId = Number(params.ottId);

  const [taxon, setTaxon] = useState<TaxonDetail | null>(null);
  const [sequences, setSequences] = useState<SequenceOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (isNaN(ottId)) {
      setError("Invalid taxon ID");
      setLoading(false);
      return;
    }

    Promise.all([getTaxon(ottId), getSequences(ottId)])
      .then(([t, seqPage]) => {
        setTaxon(t);
        setSequences(seqPage.items);
        // Auto-expand canonical sequence
        const canonical = seqPage.items.find((seq) => seq.is_canonical);
        if (canonical) setExpanded(canonical.id);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [ottId]);

  if (error) return <div className="error">Error: {error}</div>;
  if (loading) {
    return (
      <div>
        <SkeletonLine width="300px" height="1.5rem" />
        <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <SkeletonLine width="100%" height="4rem" />
          <SkeletonLine width="100%" height="4rem" />
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      {/* Breadcrumb */}
      <nav className="breadcrumbs">
        {taxon && (
          <>
            {taxon.lineage.map((ancestor, i) => (
              <span key={ancestor.ott_id}>
                <Link href={`/taxa/${ancestor.ott_id}`}>{ancestor.name}</Link>
                <span className="breadcrumb-sep">&rsaquo;</span>
              </span>
            ))}
            <Link href={`/taxa/${ottId}`}>{taxon.name}</Link>
            <span className="breadcrumb-sep">&rsaquo;</span>
            <span className="breadcrumb-current">Sequences</span>
          </>
        )}
      </nav>

      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.25rem" }}>
        COI Sequences
      </h1>
      {taxon && (
        <p style={{ color: "#888", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
          <span className={taxon.rank === "species" ? "italic" : ""}>
            {taxon.name}
          </span>
          {" "}&mdash; {sequences.length} sequence{sequences.length !== 1 ? "s" : ""}
        </p>
      )}

      {sequences.length === 0 ? (
        <div style={{ color: "#888", padding: "2rem 0" }}>
          No COI sequences found for this taxon.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {sequences.map((seq) => {
            const isExpanded = expanded === seq.id;
            return (
              <div key={seq.id} className="card sequence-card">
                <button
                  className="sequence-card-header"
                  onClick={() => setExpanded(isExpanded ? null : seq.id)}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: 1, minWidth: 0 }}>
                    {seq.is_canonical && (
                      <span className="badge" style={{ background: "var(--accent)", color: "#000" }}>
                        canonical
                      </span>
                    )}
                    <span className="badge">{seq.source}</span>
                    <span style={{ fontFamily: "monospace", fontSize: "0.85rem", color: "var(--fg)" }}>
                      {seq.accession}
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexShrink: 0 }}>
                    <span style={{ fontSize: "0.8rem", color: "#888" }}>
                      {seq.length} bp
                    </span>
                    <span className="collapsible-arrow" data-open={isExpanded}>&#9656;</span>
                  </div>
                </button>

                {isExpanded && (
                  <div className="sequence-card-body">
                    <CompositionBar sequence={seq.sequence} />
                    <SequenceViewer sequence={seq.sequence} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
