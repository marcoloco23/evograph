"""Taxonomy-based candidate neighbor selection."""

from collections import defaultdict


def build_family_index(
    taxa: list,
) -> tuple[dict[int, int], dict[int, list[int]]]:
    """Build species-to-family and family-to-species mappings.

    Args:
        taxa: list of Taxon ORM objects with .ott_id, .rank, .parent_ott_id

    Returns:
        Tuple of (species_to_family, family_to_species) where:
        - species_to_family maps species ott_id -> family ott_id
        - family_to_species maps family ott_id -> list of species ott_ids
    """
    # Build parent lookup: ott_id -> Taxon object
    by_ott: dict[int, object] = {t.ott_id: t for t in taxa}

    species_to_family: dict[int, int] = {}
    family_to_species: dict[int, list[int]] = defaultdict(list)

    for taxon in taxa:
        if taxon.rank != "species":
            continue

        # Walk up the parent chain to find the enclosing family
        current = taxon
        family_id: int | None = None
        seen: set[int] = set()

        while current is not None:
            if current.ott_id in seen:
                break  # cycle guard
            seen.add(current.ott_id)

            if current.rank == "family":
                family_id = current.ott_id
                break

            parent_id = getattr(current, "parent_ott_id", None)
            if parent_id is None:
                break
            current = by_ott.get(parent_id)

        if family_id is not None:
            species_to_family[taxon.ott_id] = family_id
            family_to_species[family_id].append(taxon.ott_id)

    return species_to_family, dict(family_to_species)
