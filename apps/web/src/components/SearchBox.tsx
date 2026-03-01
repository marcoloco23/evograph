"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { searchTaxa } from "@/lib/api";
import type { TaxonSummary } from "@/lib/types";

export default function SearchBox() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<TaxonSummary[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (query.trim().length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setIsLoading(true);
      try {
        const data = await searchTaxa(query.trim());
        setResults(data.items);
        setIsOpen(data.items.length > 0);
      } catch {
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSelect(ottId: number) {
    setIsOpen(false);
    setQuery("");
    router.push(`/taxa/${ottId}`);
  }

  return (
    <div ref={wrapperRef} style={{ position: "relative", maxWidth: 480, width: "100%" }}>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setIsOpen(true)}
        placeholder="Search taxa (e.g. Corvidae, Homo sapiens)..."
        style={inputStyle}
      />
      {isLoading && (
        <span style={spinnerStyle}>...</span>
      )}
      {isOpen && results.length > 0 && (
        <ul style={dropdownStyle}>
          {results.map((taxon) => (
            <li
              key={taxon.ott_id}
              style={itemStyle}
              onMouseDown={() => handleSelect(taxon.ott_id)}
            >
              <span style={taxon.rank === "species" ? { fontStyle: "italic" } : undefined}>
                {taxon.name}
              </span>
              <span className="badge">{taxon.rank}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.75rem 1rem",
  fontSize: "1rem",
  background: "var(--bg-input)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  color: "var(--fg)",
  outline: "none",
};

const spinnerStyle: React.CSSProperties = {
  position: "absolute",
  right: 12,
  top: "50%",
  transform: "translateY(-50%)",
  color: "#888",
};

const dropdownStyle: React.CSSProperties = {
  position: "absolute",
  top: "100%",
  left: 0,
  right: 0,
  margin: 0,
  padding: 0,
  listStyle: "none",
  background: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderTop: "none",
  borderRadius: "0 0 var(--radius) var(--radius)",
  maxHeight: 320,
  overflowY: "auto",
  zIndex: 50,
};

const itemStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "0.6rem 1rem",
  cursor: "pointer",
  borderBottom: "1px solid var(--border)",
};
