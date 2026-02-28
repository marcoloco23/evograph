import Link from "next/link";
import type { TaxonSummary } from "@/lib/types";

const RANK_COLORS: Record<string, string> = {
  class: "#e57373",
  order: "#ffb74d",
  family: "#fff176",
  subfamily: "#dce775",
  genus: "#81c784",
  species: "#4fc3f7",
  subspecies: "#4dd0e1",
};

export default function TaxonCard({ ott_id, name, rank, child_count, image_url }: TaxonSummary) {
  const isSpecies = rank === "species" || rank === "subspecies";
  const accent = RANK_COLORS[rank] ?? "#888";

  return (
    <Link href={`/taxa/${ott_id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <div className="card taxon-card" style={{ borderLeftColor: accent }}>
        {image_url && (
          <img src={image_url} alt={name} className="taxon-card-img" />
        )}
        <div>
          <div className={isSpecies ? "italic taxon-card-name" : "taxon-card-name"}>
            {name}
          </div>
          <div className="flex gap-sm" style={{ alignItems: "center", marginTop: "0.25rem" }}>
            <span className="badge" style={{ background: accent, color: "#000" }}>{rank}</span>
            {child_count > 0 && (
              <span className="taxon-card-count">{child_count}</span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
