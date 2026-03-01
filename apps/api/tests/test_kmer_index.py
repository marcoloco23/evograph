"""Tests for k-mer index service."""

import numpy as np

from evograph.services.kmer_index import (
    KMER_DIM,
    build_faiss_index,
    load_index,
    query_candidates,
    save_index,
    sequence_to_kmer_vector,
)


class TestSequenceToKmerVector:
    def test_returns_correct_shape(self):
        vec = sequence_to_kmer_vector("ACGTACGTACGT")
        assert vec.shape == (KMER_DIM,)
        assert vec.dtype == np.float32

    def test_normalized_to_unit_vector(self):
        vec = sequence_to_kmer_vector("ACGTACGTACGTACGTACGTACGT")
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-5

    def test_empty_sequence_returns_zero_vector(self):
        vec = sequence_to_kmer_vector("")
        assert np.all(vec == 0)

    def test_short_sequence_below_k(self):
        vec = sequence_to_kmer_vector("ACGT")  # k=6, so no k-mers
        assert np.all(vec == 0)

    def test_ignores_non_acgt_bases(self):
        # N's in the sequence should be skipped (k-mers containing N are not in vocab)
        vec_clean = sequence_to_kmer_vector("ACGTACGTACGT")
        vec_with_n = sequence_to_kmer_vector("ACGTNACGTACGT")
        # Different because N breaks k-mer counting
        assert not np.array_equal(vec_clean, vec_with_n)

    def test_identical_sequences_same_vector(self):
        seq = "ACGTACGTACGTACGTACGT"
        v1 = sequence_to_kmer_vector(seq)
        v2 = sequence_to_kmer_vector(seq)
        np.testing.assert_array_equal(v1, v2)

    def test_case_insensitive(self):
        v1 = sequence_to_kmer_vector("ACGTACGTACGT")
        v2 = sequence_to_kmer_vector("acgtacgtacgt")
        np.testing.assert_array_equal(v1, v2)


class TestBuildFaissIndex:
    def test_builds_index(self):
        sequences = {
            1: "ACGTACGTACGTACGTACGT",
            2: "TGCATGCATGCATGCATGCA",
            3: "ACGTACGTACGTACGTACGT",
        }
        index, ott_ids = build_faiss_index(sequences)
        assert index.ntotal == 3
        assert ott_ids == [1, 2, 3]

    def test_query_finds_identical(self):
        sequences = {
            1: "ACGTACGTACGTACGTACGT",
            2: "TGCATGCATGCATGCATGCA",
            3: "ACGTACGTACGTACGTACGT",  # same as 1
        }
        index, ott_ids = build_faiss_index(sequences)

        query_vec = sequence_to_kmer_vector("ACGTACGTACGTACGTACGT")
        results = query_candidates(index, ott_ids, query_vec, n_candidates=3)

        # First two results should be ott_ids 1 and 3 (identical sequences)
        result_ids = [r[0] for r in results]
        assert 1 in result_ids[:2]
        assert 3 in result_ids[:2]


class TestSaveLoadIndex:
    def test_roundtrip(self, tmp_path):
        sequences = {
            10: "ACGTACGTACGTACGTACGT",
            20: "TGCATGCATGCATGCATGCA",
        }
        index, ott_ids = build_faiss_index(sequences)

        save_index(index, ott_ids, directory=tmp_path)
        loaded = load_index(directory=tmp_path)

        assert loaded is not None
        loaded_index, loaded_ids = loaded
        assert loaded_index.ntotal == 2
        assert loaded_ids == [10, 20]

    def test_load_nonexistent_returns_none(self, tmp_path):
        result = load_index(directory=tmp_path / "nonexistent")
        assert result is None
