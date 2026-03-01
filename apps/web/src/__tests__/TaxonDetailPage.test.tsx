import { render, screen, waitFor } from "@testing-library/react";
import TaxonDetailPage from "../app/taxa/[ottId]/page";

const mockTaxon = {
  ott_id: 187411,
  name: "Corvidae",
  rank: "family",
  child_count: 3,
  image_url: null,
  parent_ott_id: 1041547,
  parent_name: "Passeriformes",
  ncbi_tax_id: null,
  children: [
    { ott_id: 369568, name: "Corvus", rank: "genus", child_count: 2, image_url: null },
  ],
  total_children: 1,
  has_canonical_sequence: false,
  lineage: [
    { ott_id: 81461, name: "Aves", rank: "class", child_count: 0, image_url: null },
    { ott_id: 1041547, name: "Passeriformes", rank: "order", child_count: 0, image_url: null },
  ],
  wikipedia_url: null,
};

jest.mock("next/navigation", () => ({
  useParams: () => ({ ottId: "187411" }),
}));

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

jest.mock("next/dynamic", () => {
  return function mockDynamic() {
    return function MockComponent() {
      return <div data-testid="mock-graph">Graph</div>;
    };
  };
});

jest.mock("../lib/api", () => ({
  getTaxon: jest.fn(),
  getNeighbors: jest.fn(),
  getSubtreeGraph: jest.fn(),
  getChildren: jest.fn(),
}));

import { getTaxon, getNeighbors, getSubtreeGraph } from "../lib/api";

describe("TaxonDetailPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (getTaxon as jest.Mock).mockResolvedValue(mockTaxon);
    (getNeighbors as jest.Mock).mockResolvedValue([]);
    (getSubtreeGraph as jest.Mock).mockResolvedValue({ nodes: [], edges: [] });
  });

  it("shows loading skeleton initially", () => {
    const { container } = render(<TaxonDetailPage />);
    const skeletons = container.querySelectorAll(".skeleton");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders taxon name after loading", async () => {
    render(<TaxonDetailPage />);
    await waitFor(() => {
      // Name appears in both breadcrumb and hero title
      const matches = screen.getAllByText("Corvidae");
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders rank badge", async () => {
    render(<TaxonDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("family")).toBeInTheDocument();
    });
  });

  it("renders breadcrumb lineage", async () => {
    render(<TaxonDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Aves")).toBeInTheDocument();
      expect(screen.getByText("Passeriformes")).toBeInTheDocument();
    });
  });

  it("renders children", async () => {
    render(<TaxonDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Corvus")).toBeInTheDocument();
    });
  });

  it("shows external links", async () => {
    render(<TaxonDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Wikipedia")).toBeInTheDocument();
      expect(screen.getByText("iNaturalist")).toBeInTheDocument();
      expect(screen.getByText("GBIF")).toBeInTheDocument();
    });
  });

  it("shows OTT ID", async () => {
    render(<TaxonDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("OTT 187411")).toBeInTheDocument();
    });
  });

  it("shows error on API failure", async () => {
    (getTaxon as jest.Mock).mockRejectedValue(new Error("Network error"));
    render(<TaxonDetailPage />);
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });
});
