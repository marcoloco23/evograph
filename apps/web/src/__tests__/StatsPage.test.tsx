import { render, screen, waitFor } from "@testing-library/react";
import StatsPage from "../app/stats/page";

const mockStats = {
  taxa: {
    total: 27853,
    by_rank: {
      species: 18000,
      genus: 5000,
      family: 200,
      order: 40,
      class: 1,
    },
  },
  sequences: {
    total: 350,
    by_source: { NCBI: 300, BOLD: 50 },
    species_with_sequences: 167,
    species_total: 18000,
    coverage_pct: 0.9,
  },
  edges: {
    total: 1787,
    distance: { min: 0.01, max: 0.95, avg: 0.42 },
  },
};

jest.mock("../lib/api", () => ({
  getStats: jest.fn(),
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

import { getStats } from "../lib/api";
const mockGetStats = getStats as jest.MockedFunction<typeof getStats>;

describe("StatsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows loading skeleton initially", () => {
    mockGetStats.mockReturnValue(new Promise(() => {}));
    render(<StatsPage />);
    expect(screen.getByText("Database Stats")).toBeInTheDocument();
  });

  it("renders stats after loading", async () => {
    mockGetStats.mockResolvedValue(mockStats);
    render(<StatsPage />);

    await waitFor(() => {
      expect(screen.getByText("27,853")).toBeInTheDocument();
    });
    expect(screen.getByText("Total Taxa")).toBeInTheDocument();
    expect(screen.getByText("350")).toBeInTheDocument();
    expect(screen.getByText("Total Sequences")).toBeInTheDocument();
    expect(screen.getByText("1,787")).toBeInTheDocument();
    expect(screen.getByText("MI Edges")).toBeInTheDocument();
  });

  it("shows sequence coverage percentage", async () => {
    mockGetStats.mockResolvedValue(mockStats);
    render(<StatsPage />);

    await waitFor(() => {
      expect(screen.getByText("0.9%")).toBeInTheDocument();
    });
    expect(screen.getByText("Sequence Coverage")).toBeInTheDocument();
    expect(screen.getByText("167 / 18000 species")).toBeInTheDocument();
  });

  it("shows sources breakdown", async () => {
    mockGetStats.mockResolvedValue(mockStats);
    render(<StatsPage />);

    await waitFor(() => {
      expect(screen.getByText("NCBI")).toBeInTheDocument();
    });
    expect(screen.getByText("300")).toBeInTheDocument();
    expect(screen.getByText("BOLD")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
  });

  it("shows distance distribution", async () => {
    mockGetStats.mockResolvedValue(mockStats);
    render(<StatsPage />);

    await waitFor(() => {
      expect(screen.getByText("MI Distance Distribution")).toBeInTheDocument();
    });
    expect(screen.getByText("0.0100")).toBeInTheDocument();
    expect(screen.getByText("0.9500")).toBeInTheDocument();
    expect(screen.getByText("0.4200")).toBeInTheDocument();
  });

  it("shows error state", async () => {
    mockGetStats.mockRejectedValue(new Error("Network error"));
    render(<StatsPage />);

    await waitFor(() => {
      expect(screen.getByText("Failed to load stats: Network error")).toBeInTheDocument();
    });
  });

  it("renders rank breakdown with labels", async () => {
    mockGetStats.mockResolvedValue(mockStats);
    render(<StatsPage />);

    await waitFor(() => {
      expect(screen.getByText("Taxa by Rank")).toBeInTheDocument();
    });
  });
});
