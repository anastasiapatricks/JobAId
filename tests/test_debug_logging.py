"""Tests for the debug() function in utils/__init__.py."""

import json
import logging
from unittest.mock import patch

from utils import debug


class TestDebugFunction:
    """Test structured debug logging and conditional print."""

    def test_always_logs_via_logging(self, caplog):
        with caplog.at_level(logging.INFO, logger="jobaid.debug"):
            debug("test msg")

        records = [r for r in caplog.records if r.name == "jobaid.debug"]
        assert len(records) == 1
        data = json.loads(records[0].message)
        assert data["event"] == "debug"
        assert data["message"] == "test msg"

    def test_colored_print_when_debug_true(self):
        with patch("utils.print") as mock_print, patch.dict(
            "os.environ", {"DEBUG": "true"}
        ):
            debug("hello")
            mock_print.assert_called_once()

    def test_no_print_when_debug_false(self):
        with patch("utils.print") as mock_print, patch.dict(
            "os.environ", {"DEBUG": "false"}
        ):
            debug("hello")
            mock_print.assert_not_called()

    def test_prefix_in_log_entry(self, caplog):
        with caplog.at_level(logging.INFO, logger="jobaid.debug"):
            debug("msg", prefix="CUSTOM")

        records = [r for r in caplog.records if r.name == "jobaid.debug"]
        data = json.loads(records[0].message)
        assert data["prefix"] == "CUSTOM"
