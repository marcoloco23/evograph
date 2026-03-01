export interface TaxonSummary {
  ott_id: number;
  name: string;
  rank: string;
  child_count: number;
  image_url: string | null;
  is_extinct?: boolean | null;
}

export interface TaxonDetail extends TaxonSummary {
  parent_ott_id: number | null;
  parent_name: string | null;
  ncbi_tax_id: number | null;
  is_extinct?: boolean | null;
  children: TaxonSummary[];
  total_children: number;
  has_canonical_sequence: boolean;
  image_url: string | null;
  lineage: TaxonSummary[];
  wikipedia_url: string | null;
}

export interface ChildrenPage {
  items: TaxonSummary[];
  total: number;
  offset: number;
  limit: number;
}

export interface SearchPage {
  items: TaxonSummary[];
  total: number;
  limit: number;
}

export interface SequenceOut {
  id: string;
  ott_id: number;
  marker: string;
  source: string;
  accession: string;
  sequence: string;
  length: number;
  is_canonical: boolean;
  retrieved_at: string | null;
}

export interface SequencePage {
  items: SequenceOut[];
  total: number;
  offset: number;
  limit: number;
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

export interface StatsResponse {
  taxa: {
    total: number;
    by_rank: Record<string, number>;
  };
  sequences: {
    total: number;
    by_source: Record<string, number>;
    species_with_sequences: number;
    species_total: number;
    coverage_pct: number;
  };
  edges: {
    total: number;
    distance: {
      min: number;
      max: number;
      avg: number;
    } | null;
  };
}
