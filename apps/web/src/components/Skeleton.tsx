"use client";

/**
 * Reusable skeleton primitives for loading states.
 */

export function SkeletonLine({
  width = "100%",
  height = "1rem",
}: {
  width?: string;
  height?: string;
}) {
  return (
    <div
      className="skeleton"
      style={{ width, height, borderRadius: "var(--radius)" }}
    />
  );
}

export function SkeletonCircle({ size = 44 }: { size?: number }) {
  return (
    <div
      className="skeleton"
      style={{ width: size, height: size, borderRadius: "50%", flexShrink: 0 }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="card" style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
      <SkeletonCircle />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.4rem" }}>
        <SkeletonLine width="60%" height="0.9rem" />
        <SkeletonLine width="35%" height="0.7rem" />
      </div>
    </div>
  );
}

/** Full-page loading skeleton for taxon detail. */
export function TaxonDetailSkeleton() {
  return (
    <div>
      {/* Breadcrumb skeleton */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem" }}>
        <SkeletonLine width="60px" height="0.85rem" />
        <SkeletonLine width="80px" height="0.85rem" />
        <SkeletonLine width="100px" height="0.85rem" />
      </div>

      {/* Hero section skeleton */}
      <div className="hero-section">
        <div
          className="skeleton"
          style={{ width: 160, height: 160, borderRadius: "var(--radius)", flexShrink: 0 }}
        />
        <div className="hero-info" style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
          <SkeletonLine width="280px" height="1.75rem" />
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <SkeletonLine width="60px" height="1.5rem" />
            <SkeletonLine width="80px" height="0.85rem" />
          </div>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
            <SkeletonLine width="80px" height="1.6rem" />
            <SkeletonLine width="80px" height="1.6rem" />
            <SkeletonLine width="60px" height="1.6rem" />
          </div>
        </div>
      </div>

      {/* Stats bar skeleton */}
      <div style={{ marginBottom: "1.5rem" }}>
        <SkeletonLine width="100%" height="2.5rem" />
      </div>

      {/* Grid skeleton */}
      <div className="detail-grid">
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <SkeletonLine width="120px" height="1.1rem" />
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <div>
          <SkeletonLine width="120px" height="1.1rem" />
          <div
            className="skeleton"
            style={{ width: "100%", height: 300, borderRadius: "var(--radius)", marginTop: "0.75rem" }}
          />
        </div>
      </div>
    </div>
  );
}

/** Loading skeleton for the graph page. */
export function GraphPageSkeleton() {
  return (
    <div>
      <SkeletonLine width="280px" height="1.5rem" />
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.75rem", marginBottom: "0.75rem" }}>
        <SkeletonLine width="60%" height="0.85rem" />
        <SkeletonLine width="120px" height="0.75rem" />
      </div>
      <div
        className="skeleton"
        style={{ width: "100%", height: "78vh", borderRadius: "12px" }}
      />
    </div>
  );
}
