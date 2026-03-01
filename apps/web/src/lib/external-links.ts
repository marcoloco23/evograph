export function wikipediaUrl(name: string): string {
  return `https://en.wikipedia.org/wiki/${name.replace(/ /g, "_")}`;
}

export function inaturalistUrl(name: string): string {
  return `https://www.inaturalist.org/taxa/search?q=${encodeURIComponent(name)}`;
}

export function gbifUrl(name: string): string {
  return `https://www.gbif.org/species/search?q=${encodeURIComponent(name)}`;
}

export function ncbiUrl(ncbiTaxId: number): string {
  return `https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=${ncbiTaxId}`;
}
