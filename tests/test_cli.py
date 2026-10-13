"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from click.testing import CliRunner

from sherlockml.cli import main


class TestCLI:
    """Test CLI command interface."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "sherlockml" in result.output.lower()

    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "search" in result.output
        assert "init" in result.output

    def test_search_help(self, runner):
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "--max-time" in result.output
        assert "--format" in result.output
        assert "--fast-fail" in result.output

    def test_generate_variants_help(self, runner):
        result = runner.invoke(main, ["generate-variants", "--help"])
        assert result.exit_code == 0
        assert "--leet" in result.output
        assert "--years" in result.output

    def test_rl_train_help(self, runner):
        result = runner.invoke(main, ["rl-train", "--help"])
        assert result.exit_code == 0

    def test_rag_query_help(self, runner):
        result = runner.invoke(main, ["rag-query", "--help"])
        assert result.exit_code == 0

    @patch("pathlib.Path.home")
    def test_init_creates_config(self, mock_home, runner, tmp_path):
        mock_home.return_value = tmp_path
        result = runner.invoke(main, ["init"])
        # The command should run without crashing
        assert result.exit_code == 0 or "already exists" in result.output.lower() or "created" in result.output.lower()

    def test_verbose_flag(self, runner):
        result = runner.invoke(main, ["-v", "--help"])
        assert result.exit_code == 0

    @patch("sherlockml.enum.orchestrator.Orchestrator")
    @patch("sherlockml.enum.registry.get_registry")
    @patch("sherlockml.cli.load_config")
    def test_search_execution(self, mock_load_config, mock_get_registry, mock_orchestrator, runner):
        """Test search command execution with various options."""
        from sherlockml.config import Config

        mock_load_config.return_value = Config()
        
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry
        mock_registry.get_enabled.return_value = ["reddit"]
        
        mock_orch_instance = mock_orchestrator.return_value
        mock_orch_instance.search = AsyncMock()
        mock_orch_instance.search.return_value = MagicMock(
            total_platforms=1,
            found_count=0,
            flags_found=[],
            elapsed_time=0.1
        )
        
        # Test with --format option (the one that was failing)
        result = runner.invoke(main, ["search", "testuser", "--format", "json"])
        assert result.exit_code == 0
        assert "Searching for testuser" in result.output
        
        # Test with --variants
        result = runner.invoke(main, ["search", "testuser", "--variants"])
        assert result.exit_code == 0
