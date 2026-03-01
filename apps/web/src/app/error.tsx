"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div style={{ textAlign: "center", paddingTop: "4rem" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.5rem" }}>
        Something went wrong
      </h1>
      <p style={{ color: "#aaa", marginBottom: "2rem", maxWidth: 480, margin: "0 auto 2rem" }}>
        {error.message || "An unexpected error occurred while loading this page."}
      </p>
      <button
        onClick={reset}
        style={{
          padding: "0.6rem 1.5rem",
          background: "var(--accent)",
          color: "#000",
          border: "none",
          borderRadius: "var(--radius)",
          fontWeight: 600,
          fontSize: "0.95rem",
          cursor: "pointer",
        }}
      >
        Try again
      </button>
    </div>
  );
}
