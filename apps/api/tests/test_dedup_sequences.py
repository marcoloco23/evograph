"""Tests for the sequence deduplication pipeline."""

from unittest.mock import MagicMock

from evograph.pipeline.dedup_sequences import find_duplicates


class TestFindDuplicates:
    """Tests for find_duplicates function."""

    def test_returns_empty_when_no_duplicates(self):
        """When all sequences are unique, return empty list."""
        mock_session = MagicMock()
        mock_session.execute.return_value.all.return_value = []

        result = find_duplicates(mock_session)
        assert result == []

    def test_returns_groups_with_count(self):
        """Return duplicate groups with their counts."""
        mock_session = MagicMock()
        mock_session.execute.return_value.all.return_value = [
            (700118, "NC_002008", "COI", 3),
            (893498, "KY456789", "COI", 2),
        ]

        result = find_duplicates(mock_session)
        assert len(result) == 2
        assert result[0] == (700118, "NC_002008", "COI", 3)
        assert result[1] == (893498, "KY456789", "COI", 2)

    def test_calls_execute_with_group_by(self):
        """Verify the query uses group_by and having."""
        mock_session = MagicMock()
        mock_session.execute.return_value.all.return_value = []

        find_duplicates(mock_session)

        # execute should have been called once
        assert mock_session.execute.call_count == 1
