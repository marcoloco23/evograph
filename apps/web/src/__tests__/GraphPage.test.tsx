import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GraphPage from "../app/graph/page";

jest.mock("next/dynamic", () => {
  return function MockDynamic() {
    return function MockGraphViewSigma() {
      return <div data-testid="graph-sigma">Graph rendered</div>;
    };
  };
});

jest.mock("../lib/api", () => ({
  getMiNetwork: jest.fn(),
}));

import { getMiNetwork } from "../lib/api";
const mockGetMiNetwork = getMiNetwork as jest.MockedFunction<typeof getMiNetwork>;

const mockGraph = {
  nodes: [
    { ott_id: 1, name: "Corvus corax", rank: "species", image_url: null },
    { ott_id: 2, name: "Corvus corone", rank: "species", image_url: null },
    { ott_id: 3, name: "Corvus", rank: "genus", image_url: null },
  ],
  edges: [
    { src: 1, dst: 2, kind: "mi" as const, distance: 0.15, mi_norm: 0.85, align_len: 600 },
    { src: 3, dst: 1, kind: "taxonomy" as const, distance: null, mi_norm: null, align_len: null },
    { src: 3, dst: 2, kind: "taxonomy" as const, distance: null, mi_norm: null, align_len: null },
  ],
};

describe("GraphPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows loading skeleton initially", () => {
    mockGetMiNetwork.mockReturnValue(new Promise(() => {}));
    const { container } = render(<GraphPage />);
    const skeletons = container.querySelectorAll(".skeleton");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders page title", async () => {
    mockGetMiNetwork.mockResolvedValue(mockGraph);
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByText("MI Similarity Network")).toBeInTheDocument();
    });
  });

  it("shows species and edge counts after loading", async () => {
    mockGetMiNetwork.mockResolvedValue(mockGraph);
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByText(/3 species/)).toBeInTheDocument();
      expect(screen.getByText(/1 MI edges/)).toBeInTheDocument();
    });
  });

  it("shows error state on API failure", async () => {
    mockGetMiNetwork.mockRejectedValue(new Error("Network error"));
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });

  it("renders node search box after loading", async () => {
    mockGetMiNetwork.mockResolvedValue(mockGraph);
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Search nodes...")).toBeInTheDocument();
    });
  });

  it("filters nodes in search dropdown", async () => {
    const user = userEvent.setup();
    mockGetMiNetwork.mockResolvedValue(mockGraph);
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Search nodes...")).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText("Search nodes...");
    await user.type(input, "cor");

    await waitFor(() => {
      expect(screen.getByText("Corvus corax")).toBeInTheDocument();
      expect(screen.getByText("Corvus corone")).toBeInTheDocument();
    });
  });

  it("renders description text", async () => {
    mockGetMiNetwork.mockResolvedValue(mockGraph);
    render(<GraphPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/Species with COI barcodes connected by mutual information/)
      ).toBeInTheDocument();
    });
  });

  it("does not show search box while loading", () => {
    mockGetMiNetwork.mockReturnValue(new Promise(() => {}));
    render(<GraphPage />);
    expect(screen.queryByPlaceholderText("Search nodes...")).not.toBeInTheDocument();
  });

  it("shows MI metrics summary after loading", async () => {
    mockGetMiNetwork.mockResolvedValue(mockGraph);
    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByText("Avg NMI")).toBeInTheDocument();
      expect(screen.getByText("Median")).toBeInTheDocument();
      expect(screen.getByText("Range")).toBeInTheDocument();
    });
  });
});
