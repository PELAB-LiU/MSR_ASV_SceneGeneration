"""Unit tests for shared / cross-cutting utils modules."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import matplotlib.colors as mcolors
import pytest

import utils.file_system_utils as file_system_utils
from utils.artifact_config import (ArtifactConfig, download_zenodo_dataset,
                                   fetch_zenodo_record,
                                   list_zenodo_measurement_files,
                                   resolve_zenodo_pkl,
                                   zenodo_record_id_from_doi)
from utils.cached_property import CachedProperty
from utils.colors import lighten_color, mix_colors
from utils.console_utils import configure_utf8_stdio


class TestColors:
    def test_mix_colors_default_weights(self) -> None:
        mixed = mix_colors("red", "blue")
        assert mixed.startswith("#")
        assert mixed == mix_colors("red", "blue", weight1=0.5, weight2=0.5)

    def test_mix_colors_custom_weights(self) -> None:
        mixed = mix_colors("white", "black", weight1=0.0, weight2=1.0)
        assert mixed == "#000000"

    def test_lighten_color_valid_name(self) -> None:
        light = lighten_color("blue", amount=0.5)
        base = mcolors.to_rgb("blue")
        result = mcolors.to_rgb(light)
        assert all(result[i] >= base[i] for i in range(3))

    def test_lighten_color_invalid_name_returns_input(self) -> None:
        assert lighten_color("not-a-real-color-name") == "not-a-real-color-name"


class TestCachedProperty:
    def test_cached_property_computes_value(self) -> None:
        class Counter:
            def __init__(self) -> None:
                self.calls = 0
                self.value = 1

            @CachedProperty
            def doubled(self) -> int:
                self.calls += 1
                return self.value * 2

        counter = Counter()
        assert counter.doubled == 2
        assert counter.calls == 1

    def test_cached_property_on_class_returns_descriptor(self) -> None:
        class Holder:
            @CachedProperty
            def x(self) -> int:
                return 1

        assert isinstance(Holder.__dict__["x"], CachedProperty)


class TestConsoleUtils:
    def test_configure_utf8_stdio_sets_env_and_does_not_crash(self) -> None:
        configure_utf8_stdio()
        assert os.environ.get("PYTHONIOENCODING") == "utf-8"
        assert os.environ.get("PYTHONUTF8") == "1"


class TestFileSystemUtilsShared:
    def test_ensure_directories_skips_when_already_initialized(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(file_system_utils, "_initialized", True)
        mkdir = MagicMock()
        monkeypatch.setattr(Path, "mkdir", mkdir)
        file_system_utils.ensure_directories()
        mkdir.assert_not_called()

    def test_ensure_directories_initializes_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        created: list[str] = []

        def fake_mkdir(self, parents=True, exist_ok=True):
            created.append(str(self))

        monkeypatch.setattr(file_system_utils, "_initialized", False)
        monkeypatch.setattr(Path, "mkdir", fake_mkdir)
        file_system_utils.ensure_directories()
        assert file_system_utils._initialized is True
        assert created
        created.clear()
        file_system_utils.ensure_directories()
        assert created == []


class TestArtifactConfig:
    def test_from_env_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ARTIFACT_DATA_DIR", raising=False)
        monkeypatch.delenv("ARTIFACT_OUTPUT_DIR", raising=False)
        config = ArtifactConfig.from_env()
        assert config.data_dir == Path("data")
        assert config.output_dir == Path("output")
        assert config.jobs_dir == Path("output") / "jobs"

    def test_from_env_custom_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ARTIFACT_DATA_DIR", "/tmp/data")
        monkeypatch.setenv("ARTIFACT_OUTPUT_DIR", "/tmp/out")
        config = ArtifactConfig.from_env()
        assert config.data_dir == Path("/tmp/data")
        assert config.output_dir == Path("/tmp/out")

    def test_ensure_dirs_creates_expected_subfolders(self, tmp_path: Path) -> None:
        config = ArtifactConfig(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            zenodo_record_doi="10.5281/zenodo.123",
            jobs_dir=tmp_path / "output" / "jobs",
        )
        config.ensure_dirs()
        assert (config.data_dir / "full").is_dir()
        assert (config.data_dir / "uploads").is_dir()
        assert config.jobs_dir.is_dir()

    @pytest.mark.parametrize(
        "doi,expected",
        [
            ("https://zenodo.org/records/20792734", "20792734"),
            ("10.5281/zenodo.20792734", "20792734"),
            ("https://doi.org/10.5281/zenodo.20792734", "20792734"),
            ("20792734", "20792734"),
        ],
    )
    def test_zenodo_record_id_from_doi(self, doi: str, expected: str) -> None:
        assert zenodo_record_id_from_doi(doi) == expected

    def test_fetch_zenodo_record(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "1", "files": []}
        mock_response.raise_for_status = MagicMock()
        with patch("utils.artifact_config.requests.get", return_value=mock_response):
            record = fetch_zenodo_record("20792734")
        assert record["id"] == "1"

    def test_download_zenodo_dataset_writes_files(self, tmp_path: Path) -> None:
        config = ArtifactConfig(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            zenodo_record_doi="10.5281/zenodo.99",
            jobs_dir=tmp_path / "output" / "jobs",
        )
        record = {
            "files": [
                {
                    "key": "main_measurements.pkl.gz",
                    "links": {"self": "http://example.com/file"},
                }
            ]
        }
        chunks = [b"abc", b"def"]

        def fake_get(url, stream=True, timeout=300):
            assert url == "http://example.com/file"
            response = MagicMock()
            response.raise_for_status = MagicMock()
            response.iter_content = MagicMock(return_value=iter(chunks))
            response.__enter__ = MagicMock(return_value=response)
            response.__exit__ = MagicMock(return_value=False)
            return response

        logs: list[str] = []

        with patch("utils.artifact_config.fetch_zenodo_record", return_value=record):
            with patch("utils.artifact_config.requests.get", side_effect=fake_get):
                target = download_zenodo_dataset(config, log_callback=logs.append)
        saved = target / "main_measurements.pkl.gz"
        assert saved.read_bytes() == b"abcdef"
        assert any("Downloading" in line for line in logs)

    def test_download_zenodo_dataset_raises_when_no_files(self, tmp_path: Path) -> None:
        config = ArtifactConfig(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            zenodo_record_doi="10.5281/zenodo.99",
            jobs_dir=tmp_path / "output" / "jobs",
        )
        with patch(
            "utils.artifact_config.fetch_zenodo_record", return_value={"files": []}
        ):
            with pytest.raises(RuntimeError, match="No files found"):
                download_zenodo_dataset(config)

    def test_resolve_zenodo_pkl_prefers_main_file(self, tmp_path: Path) -> None:
        config = ArtifactConfig(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            zenodo_record_doi="10.5281/zenodo.1",
            jobs_dir=tmp_path / "jobs",
        )
        full = config.data_dir / "full"
        full.mkdir(parents=True)
        preferred = full / "main_measurements.pkl.gz"
        preferred.write_bytes(b"1")
        other = full / "msr_measurements_for_full_coverage.pkl.gz"
        other.write_bytes(b"2")
        assert resolve_zenodo_pkl(config) == preferred

    def test_resolve_zenodo_pkl_by_filename(self, tmp_path: Path) -> None:
        config = ArtifactConfig(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            zenodo_record_doi="10.5281/zenodo.1",
            jobs_dir=tmp_path / "jobs",
        )
        full = config.data_dir / "full"
        full.mkdir(parents=True)
        main = full / "main_measurements.pkl.gz"
        main.write_bytes(b"1")
        msr = full / "msr_measurements_for_full_coverage.pkl.gz"
        msr.write_bytes(b"2")
        assert resolve_zenodo_pkl(config, filename=msr.name) == msr

    def test_list_zenodo_measurement_files(self, tmp_path: Path) -> None:
        config = ArtifactConfig(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            zenodo_record_doi="10.5281/zenodo.1",
            jobs_dir=tmp_path / "jobs",
        )
        full = config.data_dir / "full"
        full.mkdir(parents=True)
        main = full / "main_measurements.pkl.gz"
        main.write_bytes(b"1")
        assert list_zenodo_measurement_files(config) == [main]

    def test_resolve_zenodo_pkl_returns_none_when_missing(self, tmp_path: Path) -> None:
        config = ArtifactConfig(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            zenodo_record_doi="10.5281/zenodo.1",
            jobs_dir=tmp_path / "jobs",
        )
        assert resolve_zenodo_pkl(config) is None
