import Link from "next/link";

export default function NotFound() {
  return (
    <div style={{ textAlign: "center", paddingTop: "4rem" }}>
      <h1 style={{ fontSize: "4rem", fontWeight: 700, color: "var(--accent)", margin: 0 }}>
        404
      </h1>
      <p style={{ fontSize: "1.2rem", color: "#aaa", marginTop: "0.5rem" }}>
        Page not found
      </p>
      <p style={{ color: "#666", marginBottom: "2rem" }}>
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link
        href="/"
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
        Go Home
      </Link>
    </div>
  );
}
