import { render, screen } from "@testing-library/react";
import {
  SkeletonLine,
  SkeletonCircle,
  SkeletonCard,
  TaxonDetailSkeleton,
  GraphPageSkeleton,
} from "../components/Skeleton";

describe("SkeletonLine", () => {
  it("renders with default dimensions", () => {
    const { container } = render(<SkeletonLine />);
    const el = container.querySelector(".skeleton");
    expect(el).toBeInTheDocument();
    expect(el).toHaveStyle({ width: "100%", height: "1rem" });
  });

  it("renders with custom dimensions", () => {
    const { container } = render(<SkeletonLine width="200px" height="2rem" />);
    const el = container.querySelector(".skeleton");
    expect(el).toHaveStyle({ width: "200px", height: "2rem" });
  });
});

describe("SkeletonCircle", () => {
  it("renders with default size", () => {
    const { container } = render(<SkeletonCircle />);
    const el = container.querySelector(".skeleton");
    expect(el).toBeInTheDocument();
    expect(el).toHaveStyle({ width: "44px", height: "44px", borderRadius: "50%" });
  });

  it("renders with custom size", () => {
    const { container } = render(<SkeletonCircle size={80} />);
    const el = container.querySelector(".skeleton");
    expect(el).toHaveStyle({ width: "80px", height: "80px" });
  });
});

describe("SkeletonCard", () => {
  it("renders circle and lines", () => {
    const { container } = render(<SkeletonCard />);
    const skeletons = container.querySelectorAll(".skeleton");
    // 1 circle + 2 lines
    expect(skeletons.length).toBe(3);
  });
});

describe("TaxonDetailSkeleton", () => {
  it("renders without crashing", () => {
    const { container } = render(<TaxonDetailSkeleton />);
    const skeletons = container.querySelectorAll(".skeleton");
    expect(skeletons.length).toBeGreaterThan(5);
  });

  it("renders hero section placeholder", () => {
    const { container } = render(<TaxonDetailSkeleton />);
    const hero = container.querySelector(".hero-section");
    expect(hero).toBeInTheDocument();
  });
});

describe("GraphPageSkeleton", () => {
  it("renders without crashing", () => {
    const { container } = render(<GraphPageSkeleton />);
    const skeletons = container.querySelectorAll(".skeleton");
    expect(skeletons.length).toBeGreaterThan(2);
  });
});
