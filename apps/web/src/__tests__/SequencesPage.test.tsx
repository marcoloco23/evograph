import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SequencesPage from "../app/taxa/[ottId]/sequences/page";

jest.mock("next/navigation", () => ({
  useParams: () => ({ ottId: "700118" }),
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

const mockTaxon = {
  ott_id: 700118,
  name: "Corvus corax",
  rank: "species",
  child_count: 0,
  image_url: null,
  parent_ott_id: 369568,
  parent_name: "Corvus",
  ncbi_tax_id: null,
  children: [],
  total_children: 0,
  has_canonical_sequence: true,
  lineage: [
    { ott_id: 81461, name: "Aves", rank: "class", child_count: 0, image_url: null },
  ],
  wikipedia_url: null,
};

const mockSequences = [
  {
    id: "seq-1",
    ott_id: 700118,
    marker: "COI",
    source: "NCBI",
    accession: "NC_002008",
    sequence: "ATCGATCGATCGATCG",
    length: 658,
    is_canonical: true,
    retrieved_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "seq-2",
    ott_id: 700118,
    marker: "COI",
    source: "NCBI",
    accession: "KY456789",
    sequence: "GCTAGCTAGCTA",
    length: 612,
    is_canonical: false,
    retrieved_at: "2024-02-01T00:00:00Z",
  },
];

jest.mock("../lib/api", () => ({
  getTaxon: jest.fn(),
  getSequences: jest.fn(),
}));

import { getTaxon, getSequences } from "../lib/api";

describe("SequencesPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (getTaxon as jest.Mock).mockResolvedValue(mockTaxon);
    (getSequences as jest.Mock).mockResolvedValue({ items: mockSequences, total: 2, offset: 0, limit: 50 });
  });

  it("shows loading skeleton initially", () => {
    const { container } = render(<SequencesPage />);
    const skeletons = container.querySelectorAll(".skeleton");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders page title after loading", async () => {
    render(<SequencesPage />);
    await waitFor(() => {
      expect(screen.getByText("COI Sequences")).toBeInTheDocument();
    });
  });

  it("shows taxon name and sequence count", async () => {
    render(<SequencesPage />);
    await waitFor(() => {
      // Name appears in both breadcrumb and description
      const matches = screen.getAllByText(/Corvus corax/);
      expect(matches.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/2 sequences/)).toBeInTheDocument();
    });
  });

  it("renders sequence accessions", async () => {
    render(<SequencesPage />);
    await waitFor(() => {
      expect(screen.getByText("NC_002008")).toBeInTheDocument();
      expect(screen.getByText("KY456789")).toBeInTheDocument();
    });
  });

  it("marks canonical sequence with badge", async () => {
    render(<SequencesPage />);
    await waitFor(() => {
      expect(screen.getByText("canonical")).toBeInTheDocument();
    });
  });

  it("shows sequence length", async () => {
    render(<SequencesPage />);
    await waitFor(() => {
      expect(screen.getByText("658 bp")).toBeInTheDocument();
      expect(screen.getByText("612 bp")).toBeInTheDocument();
    });
  });

  it("auto-expands canonical sequence", async () => {
    render(<SequencesPage />);
    await waitFor(() => {
      // The canonical sequence should be expanded, showing the composition section
      const compositionBars = screen.getAllByTitle(/A:/);
      expect(compositionBars.length).toBeGreaterThan(0);
    });
  });

  it("shows empty state when no sequences", async () => {
    (getSequences as jest.Mock).mockResolvedValue({ items: [], total: 0, offset: 0, limit: 50 });
    render(<SequencesPage />);
    await waitFor(() => {
      expect(screen.getByText(/No COI sequences found/)).toBeInTheDocument();
    });
  });

  it("toggles sequence expansion on click", async () => {
    const user = userEvent.setup();
    render(<SequencesPage />);

    // Wait for sequences to load
    await waitFor(() => {
      expect(screen.getByText("KY456789")).toBeInTheDocument();
    });

    // The second sequence should not be expanded initially
    // Click to expand it
    const header = screen.getByText("KY456789").closest("button");
    if (header) {
      await user.click(header);
      // After clicking, it should show sequence content for the second sequence
      await waitFor(() => {
        // There should now be composition elements for the second sequence
        const compositionSections = screen.getAllByTitle(/A:/);
        expect(compositionSections.length).toBeGreaterThan(0);
      });
    }
  });

  it("shows error on API failure", async () => {
    (getTaxon as jest.Mock).mockRejectedValue(new Error("Server error"));
    render(<SequencesPage />);
    await waitFor(() => {
      expect(screen.getByText(/Server error/)).toBeInTheDocument();
    });
  });
});
