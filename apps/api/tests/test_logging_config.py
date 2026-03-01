"""Tests for logging configuration."""

import json
import logging
from unittest.mock import patch

from evograph.logging_config import JSONFormatter, configure_logging


class TestJSONFormatter:
    def test_formats_as_valid_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert parsed["message"] == "hello world"
        assert "timestamp" in parsed

    def test_includes_exception_info(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="something failed",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]


class TestConfigureLogging:
    def test_configure_text_format(self):
        with patch("evograph.logging_config.settings") as mock_settings:
            mock_settings.log_level = "info"
            mock_settings.log_format = "text"
            configure_logging()

            root = logging.getLogger()
            assert root.level == logging.INFO
            assert len(root.handlers) == 1
            assert not isinstance(root.handlers[0].formatter, JSONFormatter)

    def test_configure_json_format(self):
        with patch("evograph.logging_config.settings") as mock_settings:
            mock_settings.log_level = "warning"
            mock_settings.log_format = "json"
            configure_logging()

            root = logging.getLogger()
            assert root.level == logging.WARNING
            assert len(root.handlers) == 1
            assert isinstance(root.handlers[0].formatter, JSONFormatter)

    def test_configure_debug_level(self):
        with patch("evograph.logging_config.settings") as mock_settings:
            mock_settings.log_level = "debug"
            mock_settings.log_format = "text"
            configure_logging()

            root = logging.getLogger()
            assert root.level == logging.DEBUG
