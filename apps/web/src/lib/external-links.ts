export function wikipediaUrl(name: string): string {
  return `https://en.wikipedia.org/wiki/${name.replace(/ /g, "_")}`;
}

export function inaturalistUrl(name: string): string {
  return `https://www.inaturalist.org/taxa/search?q=${encodeURIComponent(name)}`;
}

export function ebirdUrl(name: string): string {
  return `https://ebird.org/species/search?q=${encodeURIComponent(name)}`;
}
