import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorBoundary } from "../components/ErrorBoundary";

// Suppress React error boundary console.error noise in test output
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: unknown[]) => {
    const msg = typeof args[0] === "string" ? args[0] : "";
    if (msg.includes("ErrorBoundary") || msg.includes("The above error")) return;
    originalError(...args);
  };
});
afterAll(() => {
  console.error = originalError;
});

function ThrowingChild({ message }: { message: string }): React.JSX.Element {
  throw new Error(message);
}

function GoodChild() {
  return <div>All good</div>;
}

describe("ErrorBoundary", () => {
  it("renders children when no error occurs", () => {
    render(
      <ErrorBoundary>
        <GoodChild />
      </ErrorBoundary>
    );
    expect(screen.getByText("All good")).toBeInTheDocument();
  });

  it("shows fallback UI when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild message="Test crash" />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Test crash")).toBeInTheDocument();
  });

  it("shows custom fallback when provided", () => {
    render(
      <ErrorBoundary fallback={<div>Custom error</div>}>
        <ThrowingChild message="Oops" />
      </ErrorBoundary>
    );
    expect(screen.getByText("Custom error")).toBeInTheDocument();
  });

  it("recovers when Try again is clicked", () => {
    let shouldThrow = true;

    function MaybeThrow() {
      if (shouldThrow) throw new Error("Boom");
      return <div>Recovered</div>;
    }

    const { rerender } = render(
      <ErrorBoundary>
        <MaybeThrow />
      </ErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Fix the error condition then click retry
    shouldThrow = false;
    fireEvent.click(screen.getByText("Try again"));

    rerender(
      <ErrorBoundary>
        <MaybeThrow />
      </ErrorBoundary>
    );

    expect(screen.getByText("Recovered")).toBeInTheDocument();
  });

  it("renders a Try again button in default fallback", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild message="Fail" />
      </ErrorBoundary>
    );
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
