import Link from "next/link";
import type { TaxonSummary } from "@/lib/types";

interface TaxonCardProps extends TaxonSummary {
  image_url?: string | null;
}

export default function TaxonCard({ ott_id, name, rank, image_url }: TaxonCardProps) {
  const isSpecies = rank === "species" || rank === "subspecies";

  return (
    <Link href={`/taxa/${ott_id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <div className="card" style={cardStyle}>
        {image_url && (
          <img
            src={image_url}
            alt={name}
            style={imageStyle}
          />
        )}
        <div>
          <div style={isSpecies ? { fontStyle: "italic", fontSize: "1.05rem" } : { fontSize: "1.05rem" }}>
            {name}
          </div>
          <span className="badge" style={{ marginTop: "0.35rem" }}>{rank}</span>
        </div>
      </div>
    </Link>
  );
}

const cardStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.75rem",
  cursor: "pointer",
  transition: "border-color 0.15s",
};

const imageStyle: React.CSSProperties = {
  width: 48,
  height: 48,
  borderRadius: "50%",
  objectFit: "cover",
  background: "#222",
};
