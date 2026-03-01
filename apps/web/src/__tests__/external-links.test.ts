import { wikipediaUrl, inaturalistUrl, ebirdUrl } from "../lib/external-links";

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

  describe("ebirdUrl", () => {
    it("encodes name for search", () => {
      expect(ebirdUrl("Corvus corax")).toBe(
        "https://ebird.org/species/search?q=Corvus%20corax"
      );
    });
  });
});
