import { render, screen } from "@testing-library/react";
import TaxonCard from "../components/TaxonCard";

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

describe("TaxonCard", () => {
  const defaultProps = {
    ott_id: 700118,
    name: "Corvus corax",
    rank: "species",
    child_count: 0,
    image_url: null,
  };

  it("renders taxon name", () => {
    render(<TaxonCard {...defaultProps} />);
    expect(screen.getByText("Corvus corax")).toBeInTheDocument();
  });

  it("renders rank badge", () => {
    render(<TaxonCard {...defaultProps} />);
    expect(screen.getByText("species")).toBeInTheDocument();
  });

  it("links to correct taxon page", () => {
    render(<TaxonCard {...defaultProps} />);
    const link = screen.getByText("Corvus corax").closest("a");
    expect(link).toHaveAttribute("href", "/taxa/700118");
  });

  it("shows child count when > 0", () => {
    render(<TaxonCard {...defaultProps} child_count={42} />);
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("hides child count when 0", () => {
    render(<TaxonCard {...defaultProps} child_count={0} />);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("renders image when provided", () => {
    render(<TaxonCard {...defaultProps} image_url="https://example.com/raven.jpg" />);
    const img = screen.getByAltText("Corvus corax");
    expect(img).toHaveAttribute("src", "https://example.com/raven.jpg");
  });

  it("italicizes species names", () => {
    const { container } = render(<TaxonCard {...defaultProps} />);
    const nameEl = container.querySelector(".italic");
    expect(nameEl).toBeInTheDocument();
  });

  it("does not italicize non-species names", () => {
    const { container } = render(
      <TaxonCard {...defaultProps} name="Corvidae" rank="family" />
    );
    const nameEl = container.querySelector(".italic");
    expect(nameEl).not.toBeInTheDocument();
  });
});
