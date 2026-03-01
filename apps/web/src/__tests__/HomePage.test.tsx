import { render, screen } from "@testing-library/react";
import HomePage from "../app/page";

// Mock the SearchBox component since it uses useRouter
jest.mock("../components/SearchBox", () => {
  return function MockSearchBox() {
    return <input data-testid="search-box" placeholder="Search taxa..." />;
  };
});

// Mock next/link
jest.mock("next/link", () => {
  return function MockLink({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  };
});

describe("HomePage", () => {
  it("renders the main heading", () => {
    render(<HomePage />);
    expect(screen.getByText("Explore the Tree of Life")).toBeInTheDocument();
  });

  it("renders the search box", () => {
    render(<HomePage />);
    expect(screen.getByTestId("search-box")).toBeInTheDocument();
  });

  it("renders the graph explorer link", () => {
    render(<HomePage />);
    const link = screen.getByText("Open Graph Explorer");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "/graph");
  });

  it("renders quick explore links for all taxa", () => {
    render(<HomePage />);
    expect(screen.getByText("Aves")).toBeInTheDocument();
    expect(screen.getByText("Passeriformes")).toBeInTheDocument();
    expect(screen.getByText("Corvidae")).toBeInTheDocument();
    expect(screen.getByText("Columbidae")).toBeInTheDocument();
    expect(screen.getByText("Strigiformes")).toBeInTheDocument();
    expect(screen.getByText("Psittaciformes")).toBeInTheDocument();
  });

  it("renders rank badges for quick links", () => {
    render(<HomePage />);
    const badges = screen.getAllByText("class");
    expect(badges.length).toBeGreaterThanOrEqual(1);
    const familyBadges = screen.getAllByText("family");
    expect(familyBadges.length).toBe(2); // Corvidae + Columbidae
  });

  it("links quick explore items to correct taxon pages", () => {
    render(<HomePage />);
    const avesLink = screen.getByText("Aves").closest("a");
    expect(avesLink).toHaveAttribute("href", "/taxa/81461");
  });
});
