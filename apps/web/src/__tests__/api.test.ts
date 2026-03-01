import { getJSON, searchTaxa, getTaxon, getSubtreeGraph, getNeighbors, getChildren, getSequences, getStats } from "../lib/api";

// Mock global fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("API client", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("getJSON", () => {
    it("fetches from API base URL", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: "test" }),
      });

      const result = await getJSON("/v1/test");
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/v1/test"),
        { cache: "no-store" }
      );
      expect(result).toEqual({ data: "test" });
    });

    it("throws on non-ok response", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
      });

      await expect(getJSON("/v1/missing")).rejects.toThrow("API error: 404 Not Found");
    });
  });

  describe("searchTaxa", () => {
    it("encodes query parameter", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await searchTaxa("Corvus corax");
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/v1/search?q=Corvus%20corax&limit=20"),
        expect.anything()
      );
    });

    it("accepts custom limit", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await searchTaxa("test", 5);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("limit=5"),
        expect.anything()
      );
    });
  });

  describe("getTaxon", () => {
    it("fetches correct endpoint", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ ott_id: 123 }),
      });

      await getTaxon(123);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/v1/taxa/123"),
        expect.anything()
      );
    });
  });

  describe("getSubtreeGraph", () => {
    it("includes depth parameter", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ nodes: [], edges: [] }),
      });

      await getSubtreeGraph(123, 3);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/v1/graph/subtree/123?depth=3"),
        expect.anything()
      );
    });
  });

  describe("getNeighbors", () => {
    it("includes k parameter", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await getNeighbors(123, 10);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/v1/graph/neighbors/123?k=10"),
        expect.anything()
      );
    });
  });

  describe("getChildren", () => {
    it("includes pagination parameters", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0, offset: 50, limit: 25 }),
      });

      await getChildren(123, 50, 25);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/v1/taxa/123/children?offset=50&limit=25"),
        expect.anything()
      );
    });
  });

  describe("getSequences", () => {
    it("fetches correct endpoint", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await getSequences(123);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/v1/taxa/123/sequences"),
        expect.anything()
      );
    });
  });

  describe("getStats", () => {
    it("fetches stats endpoint", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ taxa: {}, sequences: {}, edges: {} }),
      });

      await getStats();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/v1/stats"),
        expect.anything()
      );
    });
  });
});
