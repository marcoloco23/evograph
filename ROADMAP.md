TREE OF LIFE — FULL ROADMAP

We’ll break this into 6 phases:
	1.	MVP (COI + One Clade)
	2.	Scale Across Animalia
	3.	Multi-Marker & Better Distance
	4.	Whole-Genome & Sketching Layer
	5.	Scientific-Grade Phylogenetic Engine
	6.	Platform & Ecosystem

Each phase builds on the previous without refactoring the universe.

⸻

PHASE 1 — MVP (3–6 weeks)

Scope:
	•	One major clade (Aves or Mammalia recommended)
	•	COI barcode only
	•	Canonical sequence per species
	•	Family-level neighbor search
	•	Tree backbone from OpenTree
	•	Interactive web graph

Deliverables:
	•	Taxonomy ingestion pipeline
	•	BOLD ingestion pipeline
	•	Canonical selection logic
	•	Global alignment implementation
	•	MI-derived distance metric
	•	kNN graph construction
	•	REST API
	•	Web graph viewer

Validation criteria:
	•	Most nearest neighbors share genus or family.
	•	Graph visually mirrors known taxonomy.
	•	< 2 sec API response for subtree graph.

This proves:
	•	Data ingestion works
	•	MI distance behaves sensibly
	•	Visualization works
	•	System architecture is stable

⸻

PHASE 2 — Expand Across Animalia (2–3 months)

Now we scale horizontally.

Goals
	•	Entire Animalia taxonomy backbone
	•	COI ingestion at scale
	•	Proper job queue for background computation
	•	Smarter candidate selection (not just same-family)

Key upgrade: k-mer candidate filtering

Instead of family-only candidates:
	1.	Compute k-mer frequency vectors for canonical sequences.
	2.	Build approximate nearest neighbor index (FAISS or Annoy).
	3.	Use that to generate candidate neighbors before alignment.

This allows:
	•	Cross-family detection
	•	Mislabel detection
	•	Better global structure

Also:
	•	Add species-level caching
	•	Precompute subtree graph exports
	•	Pagination on API

Now it’s no longer a demo. It’s a dataset.

⸻

PHASE 3 — Multi-Marker Model (3–6 months)

COI is nice, but it’s a single mitochondrial gene. Evolution is bigger.

Add:
	•	16S
	•	18S
	•	rRNA markers
	•	Whole mitochondrial genomes (where available)

Architectural change

Instead of:

Edge(marker=“COI”)

We move to:

Edge(
marker=“COI”,
method=“mi_alignment”,
distance=…
)

Now edges are typed.

We introduce:

Composite distance:
D_total = weighted sum across markers

This gives more stable phylogenetic structure.

Validation:
	•	Compare clustering to OpenTree backbone
	•	Measure disagreement score

⸻

PHASE 4 — Whole-Genome Sketching (6–12 months)

Now we get serious.

Whole genomes are too large for full alignment.

Solution:
	•	MinHash genome sketches
	•	Jaccard similarity
	•	Approximate mutual information via compression-based distance

Add:
	•	Mash-like genome sketch pipeline
	•	Store genome-level embeddings
	•	Build genome neighbor index

Now Tree of Life supports:
	•	Barcode-based graph
	•	Genome-based graph

Two modes:
	•	Marker graph
	•	Genome graph

⸻

PHASE 5 — Phylogenetic Engine (Research Tier)

This is where it becomes scientifically interesting.

Add:
	•	Maximum likelihood tree reconstruction for selected clades
	•	Bootstrapping confidence
	•	Detect horizontal gene transfer anomalies
	•	Outlier detection (misidentified sequences)

Introduce:

“Conflict Map”
Edges where genetic similarity contradicts taxonomy.

This is where evolutionary biology meets anomaly detection.

⸻

PHASE 6 — Platform Layer

Now we turn it into a public system.

Features:
	•	Node pages with:
	•	Images
	•	Taxonomy
	•	Genetic markers
	•	Neighbor graph
	•	External links (NCBI, BOLD, OpenTree)
	•	Search by:
	•	Species name
	•	DNA sequence (BLAST-like query)
	•	Upload your own sequence → see where it lands in Tree of Life
	•	API for researchers

Add:
	•	Public data snapshots
	•	Citation support
	•	Versioned graph builds

Now it’s infrastructure.

⸻

Long-Term Vision

Tree of Life becomes:

A global evolutionary map
Where taxonomy, genetic similarity, and genome-level information coexist.

Think:

Google Maps × Wikipedia × BLAST × OpenTree.

⸻

Engineering Milestones

Milestone 1
	•	MVP stable
	•	10k–50k species
	•	Graph responsive

Milestone 2
	•	200k+ species
	•	k-mer candidate indexing
	•	Cross-family neighbor detection

Milestone 3
	•	Whole genome support
	•	1M+ nodes
	•	Approximate graph construction

Milestone 4
	•	Continuous ingestion pipeline
	•	Public API
	•	Search-by-sequence

⸻

Critical Architectural Principles
	1.	OTT ID is canonical identity.
	2.	Sequences are immutable + versioned.
	3.	Edges are recomputable artifacts.
	4.	Graph is derived data, not source of truth.
	5.	Always store provenance.

⸻

Scientific Guardrails

This is important.

Mutual information is a similarity proxy.
It is not a phylogenetic model.

So:
	•	Always label edges as “similarity,” not “evolutionary truth.”
	•	Provide transparency on method.
	•	Show taxonomy tree separately from MI overlay.

Never confuse similarity graph with reconstructed phylogeny.

That’s how you stay scientifically honest.

⸻

What This Project Actually Becomes

At small scale:
A beautiful interactive graph.

At medium scale:
A searchable genetic atlas.

At large scale:
A computational map of biodiversity.

At extreme scale:
A dynamic, living index of Earth’s evolutionary information.

⸻

If you want next, we can:
	•	Design the exact production cloud architecture.
	•	Estimate compute cost for 100k species.
	•	Or design the genome-sketch pipeline properly so we don’t accidentally build something quadratic and regret our existence.

The Tree of Life deserves good math.