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

  it("renders MI neighbors with NMI similarity", async () => {
    const neighbors = [
      {
        ott_id: 100001,
        name: "Pica pica",
        rank: "species",
        distance: 0.15,
        mi_norm: 0.85,
        align_len: 542,
        shared_rank: "family",
      },
    ];
    (getNeighbors as jest.Mock).mockResolvedValue(neighbors);
    render(<TaxonDetailPage />);
    await waitFor(() => {
      expect(screen.getByText(/85% NMI/)).toBeInTheDocument();
      expect(screen.getByText(/542 cols/)).toBeInTheDocument();
      expect(screen.getByText("Pica pica")).toBeInTheDocument();
    });
  });

  it("shows taxonomic coherence summary for neighbors", async () => {
    const neighbors = [
      { ott_id: 1, name: "Species A", rank: "species", distance: 0.1, mi_norm: 0.9, align_len: 600, shared_rank: "genus" },
      { ott_id: 2, name: "Species B", rank: "species", distance: 0.2, mi_norm: 0.8, align_len: 550, shared_rank: "family" },
      { ott_id: 3, name: "Species C", rank: "species", distance: 0.4, mi_norm: 0.6, align_len: 500, shared_rank: "order" },
    ];
    (getNeighbors as jest.Mock).mockResolvedValue(neighbors);
    render(<TaxonDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Taxonomic coherence:")).toBeInTheDocument();
      expect(screen.getByText("1 same genus")).toBeInTheDocument();
      expect(screen.getByText("1 same family")).toBeInTheDocument();
      expect(screen.getByText("1 cross-family")).toBeInTheDocument();
    });
  });
});
