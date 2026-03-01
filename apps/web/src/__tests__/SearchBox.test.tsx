import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SearchBox from "../components/SearchBox";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("../lib/api", () => ({
  searchTaxa: jest.fn(),
}));

import { searchTaxa } from "../lib/api";
const mockSearchTaxa = searchTaxa as jest.MockedFunction<typeof searchTaxa>;

describe("SearchBox", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSearchTaxa.mockResolvedValue({ items: [], total: 0, limit: 20 });
  });

  it("renders the search input", () => {
    render(<SearchBox />);
    const input = screen.getByPlaceholderText(/search taxa/i);
    expect(input).toBeInTheDocument();
  });

  it("does not search with fewer than 2 characters", async () => {
    const user = userEvent.setup();
    render(<SearchBox />);
    const input = screen.getByPlaceholderText(/search taxa/i);
    await user.type(input, "a");
    // Wait a bit to ensure debounce doesn't fire
    await new Promise((r) => setTimeout(r, 400));
    expect(mockSearchTaxa).not.toHaveBeenCalled();
  });

  it("calls searchTaxa after debounce for 2+ characters", async () => {
    const user = userEvent.setup();
    mockSearchTaxa.mockResolvedValue({
      items: [{ ott_id: 1, name: "Corvus", rank: "genus", child_count: 5, image_url: null }],
      total: 1,
      limit: 20,
    });
    render(<SearchBox />);
    const input = screen.getByPlaceholderText(/search taxa/i);
    await user.type(input, "cor");

    await waitFor(() => expect(mockSearchTaxa).toHaveBeenCalledWith("cor"), {
      timeout: 1000,
    });
  });

  it("shows dropdown results", async () => {
    const user = userEvent.setup();
    mockSearchTaxa.mockResolvedValue({
      items: [
        { ott_id: 187411, name: "Corvidae", rank: "family", child_count: 10, image_url: null },
        { ott_id: 369568, name: "Corvus", rank: "genus", child_count: 5, image_url: null },
      ],
      total: 2,
      limit: 20,
    });
    render(<SearchBox />);
    const input = screen.getByPlaceholderText(/search taxa/i);
    await user.type(input, "corv");

    await waitFor(() => {
      expect(screen.getByText("Corvidae")).toBeInTheDocument();
      expect(screen.getByText("Corvus")).toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it("navigates on result selection", async () => {
    const user = userEvent.setup();
    mockSearchTaxa.mockResolvedValue({
      items: [{ ott_id: 187411, name: "Corvidae", rank: "family", child_count: 10, image_url: null }],
      total: 1,
      limit: 20,
    });
    render(<SearchBox />);
    const input = screen.getByPlaceholderText(/search taxa/i);
    await user.type(input, "corv");

    await waitFor(() => expect(screen.getByText("Corvidae")).toBeInTheDocument(), {
      timeout: 1000,
    });

    // mousedown triggers navigation
    await user.pointer({ target: screen.getByText("Corvidae"), keys: "[MouseLeft]" });

    expect(mockPush).toHaveBeenCalledWith("/taxa/187411");
  });

  it("has combobox ARIA role", () => {
    render(<SearchBox />);
    const input = screen.getByRole("combobox");
    expect(input).toBeInTheDocument();
  });

  it("navigates with arrow keys and Enter", async () => {
    const user = userEvent.setup();
    mockSearchTaxa.mockResolvedValue({
      items: [
        { ott_id: 187411, name: "Corvidae", rank: "family", child_count: 10, image_url: null },
        { ott_id: 369568, name: "Corvus", rank: "genus", child_count: 5, image_url: null },
      ],
      total: 2,
      limit: 20,
    });
    render(<SearchBox />);
    const input = screen.getByPlaceholderText(/search taxa/i);
    await user.type(input, "corv");

    await waitFor(() => expect(screen.getByText("Corvidae")).toBeInTheDocument(), {
      timeout: 1000,
    });

    // ArrowDown selects first item
    await user.keyboard("{ArrowDown}");
    const firstOption = screen.getByText("Corvidae").closest("li");
    expect(firstOption?.getAttribute("aria-selected")).toBe("true");

    // ArrowDown again selects second item
    await user.keyboard("{ArrowDown}");
    const secondOption = screen.getByText("Corvus").closest("li");
    expect(secondOption?.getAttribute("aria-selected")).toBe("true");

    // Enter navigates to selected item
    await user.keyboard("{Enter}");
    expect(mockPush).toHaveBeenCalledWith("/taxa/369568");
  });

  it("closes dropdown with Escape", async () => {
    const user = userEvent.setup();
    mockSearchTaxa.mockResolvedValue({
      items: [{ ott_id: 187411, name: "Corvidae", rank: "family", child_count: 10, image_url: null }],
      total: 1,
      limit: 20,
    });
    render(<SearchBox />);
    const input = screen.getByPlaceholderText(/search taxa/i);
    await user.type(input, "corv");

    await waitFor(() => expect(screen.getByText("Corvidae")).toBeInTheDocument(), {
      timeout: 1000,
    });

    await user.keyboard("{Escape}");

    // Dropdown should be closed — listbox should no longer be visible
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
