"use client";

import React from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error" style={{ margin: "2rem 0" }}>
          <h2 style={{ margin: "0 0 0.5rem", fontSize: "1.1rem" }}>
            Something went wrong
          </h2>
          <p style={{ margin: "0 0 1rem", color: "#ccc", fontSize: "0.9rem" }}>
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              padding: "0.4rem 1rem",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              background: "var(--bg-card)",
              color: "var(--fg)",
              cursor: "pointer",
              fontSize: "0.85rem",
            }}
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
