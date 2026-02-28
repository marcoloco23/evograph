"use client";

import Link from "next/link";
import SearchBox from "@/components/SearchBox";

const QUICK_LINKS = [
  { name: "Aves", ottId: 81461, rank: "class" },
  { name: "Passeriformes", ottId: 1041547, rank: "order" },
  { name: "Corvidae", ottId: 187411, rank: "family" },
  { name: "Columbidae", ottId: 938413, rank: "family" },
  { name: "Strigiformes", ottId: 1028829, rank: "order" },
  { name: "Psittaciformes", ottId: 1020133, rank: "order" },
] as const;

export default function HomePage() {
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", paddingTop: "3rem" }}>
      <h1 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "0.5rem" }}>
        Explore the Tree of Life
      </h1>
      <p style={{ color: "#aaa", marginBottom: "2rem", lineHeight: 1.7 }}>
        EvoGraph maps evolutionary relationships using mutual information
        between genetic sequences. Search for any taxon to explore its
        phylogenetic neighborhood, or browse the full graph view.
      </p>
      <SearchBox />

      <div style={{ marginTop: "2.5rem" }}>
        <Link
          href="/graph"
          style={{
            display: "inline-block",
            padding: "0.6rem 1.5rem",
            background: "var(--accent)",
            color: "#000",
            borderRadius: "var(--radius)",
            fontWeight: 600,
            fontSize: "0.95rem",
            textDecoration: "none",
          }}
        >
          Open Graph Explorer
        </Link>
      </div>

      <section style={{ marginTop: "2.5rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--accent)", marginBottom: "0.75rem" }}>
          Quick Explore
        </h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {QUICK_LINKS.map((t) => (
            <Link
              key={t.ottId}
              href={`/taxa/${t.ottId}`}
              className="card"
              style={{
                padding: "0.5rem 1rem",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                textDecoration: "none",
                color: "var(--fg)",
              }}
            >
              <span className="badge">{t.rank}</span>
              {t.name}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
