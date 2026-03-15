import type { Metadata } from "next";
import Link from "next/link";
import { ErrorBoundary } from "../components/ErrorBoundary";
import "./globals.css";

export const metadata: Metadata = {
  title: "EvoGraph",
  description: "Explore the evolutionary tree of life through mutual information graphs",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header style={headerStyle}>
          <nav style={navStyle} className="container">
            <Link href="/" style={logoStyle}>
              EvoGraph
            </Link>
            <div style={linksStyle}>
              <Link href="/">Home</Link>
              <Link href="/browse">Species</Link>
              <Link href="/graph">Graph</Link>
              <Link href="/stats">Stats</Link>
            </div>
          </nav>
        </header>
        <main className="container" style={{ paddingTop: "2rem", paddingBottom: "3rem" }}>
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </body>
    </html>
  );
}

const headerStyle: React.CSSProperties = {
  borderBottom: "1px solid var(--border)",
  background: "rgba(10, 10, 10, 0.9)",
  backdropFilter: "blur(8px)",
  position: "sticky",
  top: 0,
  zIndex: 100,
};

const navStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  height: "3.5rem",
};

const logoStyle: React.CSSProperties = {
  fontSize: "1.25rem",
  fontWeight: 700,
  color: "var(--accent)",
  textDecoration: "none",
};

const linksStyle: React.CSSProperties = {
  display: "flex",
  gap: "1.5rem",
};
