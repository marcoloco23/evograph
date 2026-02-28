export interface TaxonSummary {
  ott_id: number;
  name: string;
  rank: string;
  child_count: number;
  image_url: string | null;
}

export interface TaxonDetail extends TaxonSummary {
  parent_ott_id: number | null;
  parent_name: string | null;
  ncbi_tax_id: number | null;
  children: TaxonSummary[];
  has_canonical_sequence: boolean;
  image_url: string | null;
  lineage: TaxonSummary[];
  wikipedia_url: string | null;
}

export interface SequenceOut {
  id: string;
  ott_id: number;
  marker: string;
  source: string;
  accession: string;
  length: number;
  is_canonical: boolean;
  retrieved_at: string | null;
}

export interface GraphNode {
  ott_id: number;
  name: string;
  rank: string;
  image_url: string | null;
}

export interface GraphEdge {
  src: number;
  dst: number;
  kind: "taxonomy" | "mi";
  distance: number | null;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NeighborOut {
  ott_id: number;
  name: string;
  rank: string;
  distance: number;
  mi_norm: number;
}
