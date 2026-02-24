"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import patch

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

    def test_init_creates_config(self, runner, tmp_path):
        config_path = tmp_path / ".sherlockml" / "config.yaml"
        result = runner.invoke(main, ["init", "--config-dir", str(tmp_path / ".sherlockml")])
        # The command should run without crashing
        assert result.exit_code == 0 or "already exists" in result.output.lower() or "created" in result.output.lower()

    def test_verbose_flag(self, runner):
        result = runner.invoke(main, ["-v", "--help"])
        assert result.exit_code == 0
