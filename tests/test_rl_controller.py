"""Tests for RL controller (Thompson Sampling)."""

import json
from pathlib import Path

import pytest

from sherlockml.ml.rl_controller import PlatformStats, RLController


class TestPlatformStats:
    """Test PlatformStats dataclass."""

    def test_success_rate_no_searches(self):
        stats = PlatformStats(
            name="github", successes=0, failures=0,
            total_searches=0, avg_response_time=0.0, last_updated="",
        )
        assert stats.success_rate == 0.5  # Prior

    def test_success_rate_with_data(self):
        stats = PlatformStats(
            name="github", successes=8, failures=2,
            total_searches=10, avg_response_time=0.5, last_updated="",
        )
        assert stats.success_rate == 0.8

    def test_thompson_sample_is_bounded(self):
        stats = PlatformStats(
            name="github", successes=5, failures=5,
            total_searches=10, avg_response_time=0.5, last_updated="",
        )
        samples = [stats.thompson_sample for _ in range(100)]
        assert all(0.0 <= s <= 1.0 for s in samples)


class TestRLController:
    """Test RL controller operations."""

    @pytest.fixture
    def controller(self, tmp_path):
        """Create a fresh RL controller."""
        db_path = tmp_path / "test_rl.db"
        rl = RLController(db_path=db_path)
        yield rl
        rl.close()

    def test_init_creates_db(self, tmp_path):
        db_path = tmp_path / "test.db"
        rl = RLController(db_path=db_path)
        assert db_path.exists()
        rl.close()

    def test_get_stats_unknown_platform(self, controller):
        stats = controller.get_stats("unknown_platform")
        assert stats.name == "unknown_platform"
        assert stats.successes == 0
        assert stats.total_searches == 0

    def test_update_success(self, controller):
        controller.update("github", flag_found=True, response_time=0.5)
        stats = controller.get_stats("github")
        assert stats.successes >= 1
        assert stats.total_searches >= 1

    def test_update_failure(self, controller):
        controller.update("twitter", flag_found=False, response_time=1.0)
        stats = controller.get_stats("twitter")
        assert stats.failures >= 1

    def test_update_with_context(self, controller):
        controller.update(
            "github", flag_found=True,
            context={"ctf": "exampleCTF", "category": "osint"},
        )
        stats = controller.get_stats("github")
        assert stats.successes >= 1

    def test_select_platforms_all_fit(self, controller):
        available = ["github", "twitter", "reddit"]
        selected = controller.select_platforms(available, n=5)
        assert set(selected) == set(available)

    def test_select_platforms_subset(self, controller):
        # Seed some data so Thompson sampling has something to work with
        for _ in range(5):
            controller.update("github", flag_found=True)
            controller.update("twitter", flag_found=False)
            controller.update("reddit", flag_found=False)

        available = ["github", "twitter", "reddit"]
        selected = controller.select_platforms(available, n=2)
        assert len(selected) == 2

    def test_select_platforms_empty(self, controller):
        assert controller.select_platforms([], n=5) == []

    def test_get_all_stats(self, controller):
        controller.update("github", flag_found=True)
        controller.update("twitter", flag_found=False)
        all_stats = controller.get_all_stats()
        assert len(all_stats) == 2

    def test_export_weights(self, controller):
        controller.update("github", flag_found=True)
        controller.update("twitter", flag_found=False)
        weights = controller.export_weights()
        assert "github" in weights
        assert "twitter" in weights
        assert 0.0 <= weights["github"] <= 1.0

    def test_reset(self, controller):
        controller.update("github", flag_found=True)
        controller.reset()
        stats = controller.get_stats("github")
        assert stats.total_searches == 0

    def test_train_from_dataset(self, controller, tmp_path):
        dataset = [
            {"platforms": {"github": True, "twitter": False}},
            {"platforms": {"github": True, "reddit": True}},
        ]
        dataset_path = tmp_path / "train.json"
        dataset_path.write_text(json.dumps(dataset))

        result = controller.train(dataset_path, epochs=2)
        assert result["epochs"] == 2
        assert result["entries"] == 2
        assert result["total_updates"] > 0

    def test_context_manager(self, tmp_path):
        db_path = tmp_path / "ctx.db"
        with RLController(db_path=db_path) as rl:
            rl.update("github", flag_found=True)
        # Connection should be closed but file should exist
        assert db_path.exists()
