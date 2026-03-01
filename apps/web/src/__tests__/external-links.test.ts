import { wikipediaUrl, inaturalistUrl, gbifUrl, ncbiUrl } from "../lib/external-links";

describe("external-links", () => {
  describe("wikipediaUrl", () => {
    it("replaces spaces with underscores", () => {
      expect(wikipediaUrl("Corvus corax")).toBe(
        "https://en.wikipedia.org/wiki/Corvus_corax"
      );
    });

    it("handles single word", () => {
      expect(wikipediaUrl("Aves")).toBe(
        "https://en.wikipedia.org/wiki/Aves"
      );
    });
  });

  describe("inaturalistUrl", () => {
    it("encodes name for search", () => {
      expect(inaturalistUrl("Corvus corax")).toBe(
        "https://www.inaturalist.org/taxa/search?q=Corvus%20corax"
      );
    });
  });

  describe("gbifUrl", () => {
    it("encodes name for search", () => {
      expect(gbifUrl("Corvus corax")).toBe(
        "https://www.gbif.org/species/search?q=Corvus%20corax"
      );
    });
  });

  describe("ncbiUrl", () => {
    it("builds taxonomy browser URL from tax ID", () => {
      expect(ncbiUrl(56781)).toBe(
        "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=56781"
      );
    });
  });
});
