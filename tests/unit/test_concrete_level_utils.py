"""Unit tests for utils modules used by the concrete level."""

from __future__ import annotations

import multiprocessing as mp
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from concrete_level.models.actor_state import ActorState
from concrete_level.trajectory_generation.scene_builder import SceneBuilder
from global_config import GlobalConfig
from logical_level.constraint_satisfaction.assignments import Assignments
from logical_level.models.actor_variable import TSVariable
from logical_level.models.values import VesselValues
from utils.archive_utils import create_zip_archive, create_zip_from_directory
from utils.file_folder_opener import (HeadlessFileOpener, TkinterFileOpener,
                                      ZenityFileOpener,
                                      get_artifact_file_opener,
                                      get_default_file_opener)
from utils.file_system_utils import GEN_DATA_FOLDER, get_all_file_paths
from utils.math_utils import compute_start_point, find_center_and_radius
from utils.multiprocessing_config import (configure_spawn_start_method,
                                          get_spawn_context)
from utils.serializable import Serializable
from utils.vessel_types import (ALL_VESSEL_TYPES, CargoShip,
                                UnspecifiedVesselType)


class PointContainer(Serializable):
    x: float
    y: float

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class TestMathUtilsConcrete:
    def test_find_center_and_radius_on_square(self) -> None:
        points = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]])
        center, radius = find_center_and_radius(points)
        assert center == pytest.approx(np.array([1.0, 1.0]))
        assert radius == pytest.approx(np.sqrt(2.0))

    def test_compute_start_point_with_positive_acceleration(self) -> None:
        position = (10.0, 0.0)
        velocity = (1.0, 0.0)
        start = compute_start_point(position, velocity, speed=4.0, acceleration=2.0)
        assert start == pytest.approx((6.0, 0.0))

    def test_compute_start_point_rejects_non_positive_acceleration(self) -> None:
        with pytest.raises(ValueError, match="Acceleration must be positive"):
            compute_start_point((0.0, 0.0), (1.0, 0.0), speed=1.0, acceleration=0.0)

    def test_compute_start_point_diagonal_heading(self) -> None:
        velocity = (1.0 / np.sqrt(2), 1.0 / np.sqrt(2))
        start = compute_start_point((0.0, 0.0), velocity, speed=2.0, acceleration=1.0)
        assert start[0] == pytest.approx(-np.sqrt(2.0))
        assert start[1] == pytest.approx(-np.sqrt(2.0))

    def test_find_center_and_radius_circle_points(self) -> None:
        angles = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        points = np.column_stack([np.cos(angles), np.sin(angles)])
        center, radius = find_center_and_radius(points)
        assert center == pytest.approx(np.array([0.0, 0.0]), abs=1e-10)
        assert radius == pytest.approx(1.0)


class TestActorStateKinematics:
    def test_velocity_vector_from_heading_and_speed(self) -> None:
        state = ActorState(x=0.0, y=0.0, speed=10.0, heading=0.0)
        assert state.v[0] == pytest.approx(10.0)
        assert state.v[1] == pytest.approx(0.0)

    def test_velocity_unit_perpendicular_is_rotated_ninety_degrees(self) -> None:
        state = ActorState(x=0.0, y=0.0, speed=5.0, heading=np.pi / 4)
        perp = state.v_norm_perp
        assert np.dot(state.v_norm, perp) == pytest.approx(0.0)
        assert np.linalg.norm(perp) == pytest.approx(1.0)

    def test_modify_copy_updates_only_specified_fields(self) -> None:
        original = ActorState(x=1.0, y=2.0, speed=3.0, heading=0.5)
        updated = original.modify_copy(speed=6.0)
        assert updated.x == 1.0
        assert updated.y == 2.0
        assert updated.speed == 6.0
        assert updated.heading == 0.5


class TestSceneBuilderVesselTypeResolution:
    def test_unspecified_vessel_type_resolved_via_do_match(self) -> None:
        ts_var = TSVariable(5, UnspecifiedVesselType())
        assignments = Assignments([ts_var])
        length = 100.0
        speed = 5.0
        assignments[ts_var] = VesselValues(
            x=1000.0, y=2000.0, h=np.pi / 3, l=length, sp=speed
        )
        with patch(
            "concrete_level.trajectory_generation.scene_builder.random.choice",
            lambda options: options[0],
        ):
            scene = SceneBuilder.build_from_assignments(assignments)
        vessel = next(a for a in scene.actors if a.is_vessel)
        assert vessel.type in GlobalConfig.VALID_VESSEL_TYPES
        assert ALL_VESSEL_TYPES[vessel.type].do_match(length, speed)
        state = scene[vessel]
        assert state.x == pytest.approx(1000.0)
        assert state.heading == pytest.approx(np.pi / 3)


class TestSerializableConcrete:
    def test_round_trip_primitive_serializable(self) -> None:
        point = PointContainer(3.5, -1.2)
        restored = PointContainer.from_dict(point.to_dict())
        assert restored.x == pytest.approx(3.5)
        assert restored.y == pytest.approx(-1.2)

    def test_actor_state_round_trip_preserves_navigation_state(self) -> None:
        state = ActorState(x=12.5, y=-3.0, speed=7.5, heading=1.2)
        restored = ActorState.from_dict(state.to_dict())
        assert restored.x == state.x
        assert restored.speed == state.speed
        assert restored.v[0] == pytest.approx(state.v[0])


class TestFileSystemUtilsConcrete:
    def test_gen_data_folder_exists(self) -> None:
        assert Path(GEN_DATA_FOLDER).is_dir()

    def test_get_all_file_paths_skips_unknown_extensions(
        self, sample_tree: Path
    ) -> None:
        paths = get_all_file_paths(str(sample_tree), [".pkl.gz"])
        assert len(paths[".pkl.gz"]) == 1


class TestArchiveUtils:
    def test_create_zip_from_directory(
        self, zip_sources: tuple[Path, Path, Path]
    ) -> None:
        source_dir, _, zip_path = zip_sources
        result = create_zip_from_directory(source_dir, zip_path)
        assert result == zip_path
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
        assert any(name.endswith("inner.txt") for name in names)

    def test_create_zip_archive_mixed_sources(
        self, zip_sources: tuple[Path, Path, Path]
    ) -> None:
        source_dir, lone_file, zip_path = zip_sources
        missing = source_dir.parent / "missing.txt"
        create_zip_archive([lone_file, source_dir, missing], zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            names = set(archive.namelist())
        assert "readme.txt" in names
        assert any("inner.txt" in name for name in names)

    def test_create_zip_archive_creates_parent_dirs(self, tmp_path: Path) -> None:
        lone = tmp_path / "only.txt"
        lone.write_text("x", encoding="utf-8")
        zip_path = tmp_path / "nested" / "out.zip"
        create_zip_archive([lone], zip_path)
        assert zip_path.is_file()


class TestMultiprocessingConfig:
    def test_configure_spawn_start_method_is_idempotent(self) -> None:
        configure_spawn_start_method()
        configure_spawn_start_method()

    def test_get_spawn_context_returns_spawn_context(self) -> None:
        context = get_spawn_context()
        assert context.get_start_method() == "spawn"
        assert isinstance(context, mp.context.BaseContext)


class TestFileFolderOpener:
    def test_headless_file_opener_returns_configured_paths(self) -> None:
        opener = HeadlessFileOpener(
            open_dirs=["/data"],
            open_files=["/data/file.json"],
            save_file="/data/out.zip",
        )
        assert opener.ask_open_dirs() == ["/data"]
        assert opener.ask_open_files() == ["/data/file.json"]
        assert opener.ask_save_file() == "/data/out.zip"

    def test_get_artifact_file_opener(self) -> None:
        opener = get_artifact_file_opener(open_files=["a.pkl.gz"])
        assert isinstance(opener, HeadlessFileOpener)
        assert opener.ask_open_files() == ["a.pkl.gz"]

    def test_get_default_file_opener_platform_specific(self) -> None:
        opener = get_default_file_opener()
        import sys

        if sys.platform == "win32":
            assert isinstance(opener, TkinterFileOpener)
        else:
            assert isinstance(opener, ZenityFileOpener)

    def test_zenity_opener_raises_when_zenity_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_run(*_args, **_kwargs):
            raise FileNotFoundError("zenity")

        monkeypatch.setattr("subprocess.run", fake_run)
        opener = ZenityFileOpener()
        with pytest.raises(RuntimeError, match="zenity not found"):
            opener.ask_open_dirs()
