import type { TaxonSummary, TaxonDetail, GraphResponse, NeighborOut } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function searchTaxa(query: string, limit = 20) {
  return getJSON<TaxonSummary[]>(
    `/v1/search?q=${encodeURIComponent(query)}&limit=${limit}`
  );
}

export function getTaxon(ottId: number) {
  return getJSON<TaxonDetail>(`/v1/taxa/${ottId}`);
}

export function getSubtreeGraph(ottId: number, depth = 1) {
  return getJSON<GraphResponse>(`/v1/graph/subtree/${ottId}?depth=${depth}`);
}

export function getMiNetwork() {
  return getJSON<GraphResponse>(`/v1/graph/mi-network`);
}

export function getNeighbors(ottId: number, k = 15) {
  return getJSON<NeighborOut[]>(`/v1/graph/neighbors/${ottId}?k=${k}`);
}
