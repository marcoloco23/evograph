import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import BrowsePage from "../app/browse/page";

const mockSpeciesData = {
  items: [
    {
      ott_id: 700118,
      name: "Corvus corax",
      rank: "species",
      image_url: "https://example.com/corax.jpg",
      is_extinct: false,
      has_sequence: true,
      edge_count: 12,
      family_name: "Corvidae",
      order_name: "Passeriformes",
    },
    {
      ott_id: 893498,
      name: "Corvus corone",
      rank: "species",
      image_url: null,
      is_extinct: false,
      has_sequence: false,
      edge_count: 0,
      family_name: "Corvidae",
      order_name: "Passeriformes",
    },
  ],
  total: 2,
  offset: 0,
  limit: 50,
};

jest.mock("../lib/api", () => ({
  browseSpecies: jest.fn(),
}));

jest.mock("next/link", () => {
  return function MockLink({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) {
    return <a href={href}>{children}</a>;
  };
});

import { browseSpecies } from "../lib/api";
const mockBrowseSpecies = browseSpecies as jest.MockedFunction<typeof browseSpecies>;

describe("BrowsePage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows loading skeleton initially", () => {
    mockBrowseSpecies.mockReturnValue(new Promise(() => {}));
    render(<BrowsePage />);
    expect(screen.getByText("Browse Species")).toBeInTheDocument();
  });

  it("renders species after loading", async () => {
    mockBrowseSpecies.mockResolvedValue(mockSpeciesData);
    render(<BrowsePage />);

    await waitFor(() => {
      expect(screen.getByText("Corvus corax")).toBeInTheDocument();
    });
    expect(screen.getByText("Corvus corone")).toBeInTheDocument();
  });

  it("shows COI badge for species with sequences", async () => {
    mockBrowseSpecies.mockResolvedValue(mockSpeciesData);
    render(<BrowsePage />);

    await waitFor(() => {
      expect(screen.getByText("COI")).toBeInTheDocument();
    });
  });

  it("shows MI edges badge with count", async () => {
    mockBrowseSpecies.mockResolvedValue(mockSpeciesData);
    render(<BrowsePage />);

    await waitFor(() => {
      expect(screen.getByText("12 MI edges")).toBeInTheDocument();
    });
  });

  it("shows total count", async () => {
    mockBrowseSpecies.mockResolvedValue(mockSpeciesData);
    render(<BrowsePage />);

    await waitFor(() => {
      expect(screen.getByText("2 species found")).toBeInTheDocument();
    });
  });

  it("shows error state", async () => {
    mockBrowseSpecies.mockRejectedValue(new Error("Network error"));
    render(<BrowsePage />);

    await waitFor(() => {
      expect(screen.getByText("Failed to load species: Network error")).toBeInTheDocument();
    });
  });

  it("shows empty state when no results", async () => {
    mockBrowseSpecies.mockResolvedValue({
      items: [],
      total: 0,
      offset: 0,
      limit: 50,
    });
    render(<BrowsePage />);

    await waitFor(() => {
      expect(screen.getByText("No species match the current filters.")).toBeInTheDocument();
    });
  });

  it("renders filter buttons", async () => {
    mockBrowseSpecies.mockResolvedValue(mockSpeciesData);
    render(<BrowsePage />);

    expect(screen.getByText("With MI edges")).toBeInTheDocument();
    expect(screen.getByText("With COI")).toBeInTheDocument();
    expect(screen.getByText("All species")).toBeInTheDocument();
  });

  it("renders sort dropdown", async () => {
    mockBrowseSpecies.mockResolvedValue(mockSpeciesData);
    render(<BrowsePage />);

    expect(screen.getByText("Sort: A-Z")).toBeInTheDocument();
    expect(screen.getByText("Sort: Most edges")).toBeInTheDocument();
  });

  it("renders include extinct checkbox", async () => {
    mockBrowseSpecies.mockResolvedValue(mockSpeciesData);
    render(<BrowsePage />);

    expect(screen.getByText("Include extinct")).toBeInTheDocument();
  });

  it("links to taxon detail page", async () => {
    mockBrowseSpecies.mockResolvedValue(mockSpeciesData);
    render(<BrowsePage />);

    await waitFor(() => {
      expect(screen.getByText("Corvus corax")).toBeInTheDocument();
    });

    const link = screen.getByText("Corvus corax").closest("a");
    expect(link).toHaveAttribute("href", "/taxa/700118");
  });

  it("shows pagination for large results", async () => {
    mockBrowseSpecies.mockResolvedValue({
      ...mockSpeciesData,
      total: 150,
    });
    render(<BrowsePage />);

    await waitFor(() => {
      expect(screen.getByText("Previous")).toBeInTheDocument();
    });
    expect(screen.getByText("Next")).toBeInTheDocument();
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  it("shows family and order taxonomy context", async () => {
    mockBrowseSpecies.mockResolvedValue(mockSpeciesData);
    render(<BrowsePage />);

    await waitFor(() => {
      expect(screen.getByText("Corvus corax")).toBeInTheDocument();
    });
    // Both species are in Passeriformes > Corvidae
    const taxonomyLabels = screen.getAllByText("Passeriformes > Corvidae");
    expect(taxonomyLabels.length).toBe(2);
  });

  it("calls API with filter params when clicking filter buttons", async () => {
    mockBrowseSpecies.mockResolvedValue(mockSpeciesData);
    render(<BrowsePage />);

    await waitFor(() => {
      expect(screen.getByText("Corvus corax")).toBeInTheDocument();
    });

    // Click "With COI" filter
    fireEvent.click(screen.getByText("With COI"));

    await waitFor(() => {
      expect(mockBrowseSpecies).toHaveBeenCalledWith(
        expect.objectContaining({ has_sequences: true })
      );
    });
  });
});
