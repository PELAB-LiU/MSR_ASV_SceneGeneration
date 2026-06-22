import gzip
import io
import json
import multiprocessing
import pickle
import tarfile
import zipfile
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from typing import Callable, List, Optional, Tuple

ProgressCallback = Callable[[int, int, str], None]

import pandas as pd
from tqdm import tqdm

from concrete_level.trajectory_generation.trajectory_data import TrajectoryData
from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from utils.file_folder_opener import FileFolderOpener, TkinterFileOpener
from utils.file_system_utils import GEN_DATA_FOLDER, get_all_file_paths
from utils.multiprocessing_config import get_spawn_context


def _load_eval_model_from_file(file: str) -> EvaluationData:
    model: EvaluationData = EvaluationData.load_from_json(file)
    model.path = file
    return model


def _parse_eval_json_bytes(item: Tuple[str, bytes]) -> EvaluationData:
    file_name, content = item
    data = EvaluationData.load_from_json_bytes(content)
    data.path = file_name
    return data


def _load_zip_eval_data_from_path(file: str) -> List[EvaluationData]:
    with zipfile.ZipFile(file, "r") as z:
        items = [
            (name, z.read(name)) for name in z.namelist() if name.endswith(".json")
        ]
    return [_parse_eval_json_bytes(item) for item in items]


def _load_tar_eval_data_from_path(file: str) -> List[EvaluationData]:
    items: List[Tuple[str, bytes]] = []
    with tarfile.open(file, "r:gz") as tar:
        for member in tar:
            if member.isfile() and member.name.endswith(".json"):
                f = tar.extractfile(member)
                if f is not None:
                    items.append((member.name, f.read()))
    return [_parse_eval_json_bytes(item) for item in items]


def _load_pkl_gzip_compressed_eval_data_from_path(file: str) -> List[EvaluationData]:
    eval_datas: List[EvaluationData] = []
    with gzip.open(file, "rb") as f:
        loaded = pickle.load(f)
        eval_datas.extend(loaded)
    return eval_datas


class DataParser(ABC):
    RRT_DIR = f"{GEN_DATA_FOLDER}/RRTStar_algo"
    EVAL_DATA_COLUMN_NAMES = list(sorted(asdict(EvaluationData()).keys()))

    TRAJ_COLUMN_NAMES = [
        "trajectories",
        "config_name",
        "measurement_name",
        "rrt_evaluation_times",
        "iter_numbers",
        "overall_eval_time",
        "path",
        "env_path",
        "expand_distance",
        "goal_sample_rate",
        "random_seed",
    ]

    def __init__(
        self,
        column_names: List[str],
        dir: str,
        file_opener: Optional[FileFolderOpener] = None,
    ) -> None:
        self.column_names = column_names
        self.dir = dir
        self._opener = file_opener if file_opener is not None else TkinterFileOpener()

    def get_data_lines(self, files: List[str]) -> List[dict]:
        return [self.load_dict_from_file(file) for file in files]

    @abstractmethod
    def load_dict_from_file(self, file: str) -> dict:
        pass

    def load_df_from_files(self, files: List[str]) -> pd.DataFrame:
        data_lines = self.get_data_lines(files)
        data_lists: List[List[float]] = []

        for data in data_lines:
            measurement_data = []
            error_message = data["error_message"]
            if error_message is not None:
                print(
                    f'WARNING: error in evaluation data {data["timestamp"]}: {error_message}'
                )
                if data["best_scene"] is None:
                    continue
            for column in self.column_names:
                measurement_data.append(data[column])
            data_lists.append(measurement_data)

        return pd.DataFrame(data_lists, columns=self.column_names)

    def load_dirs_merged(self, dirs=None) -> Tuple[pd.DataFrame, List[str]]:
        if dirs is None:
            dirs = []
        files = []
        if len(dirs) == 0:
            dirs = self._opener.ask_open_dirs(initialdir=self.dir)
        for dir in dirs:
            files += get_all_file_paths(dir, ["json"])["json"]
            if len(files) == 0:
                continue
        return self.load_df_from_files(files), dirs


class EvalDataParser(DataParser):
    def __init__(self, file_opener: Optional[FileFolderOpener] = None) -> None:
        super().__init__(
            self.EVAL_DATA_COLUMN_NAMES, GEN_DATA_FOLDER, file_opener=file_opener
        )

    def load_data_models(self) -> List[EvaluationData]:
        files = self._opener.ask_open_files(initialdir=self.dir)
        return self.load_data_models_from_files(files)

    def load_data_models_from_files(
        self,
        files: List[str],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[EvaluationData]:
        if not files:
            return []
        if progress_callback is None:
            with ProcessPoolExecutor(mp_context=get_spawn_context()) as executor:
                results = list(
                    tqdm(
                        executor.map(_load_eval_model_from_file, files),
                        total=len(files),
                        desc="Loading files",
                    )
                )
            return results
        results: List[EvaluationData] = []
        total = len(files)
        for index, file in enumerate(files):
            progress_callback(
                index,
                total,
                f"Loading JSON evaluation record {index + 1}/{total}",
            )
            results.append(_load_eval_model_from_file(file))
        progress_callback(total, total, f"Finished loading {total} JSON file(s)")
        return results

    def load_dirs_merged_as_models(
        self,
        dirs=None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[EvaluationData]:
        if dirs is None:
            dirs = []
        files = []
        if len(dirs) == 0:
            dirs = self._opener.ask_open_dirs(initialdir=self.dir)
        for dir in dirs:
            files += get_all_file_paths(dir, ["json"])["json"]
            if len(files) == 0:
                continue
        return self.load_data_models_from_files(
            files,
            progress_callback=progress_callback,
        )

    def load_dict_from_file(self, file: str) -> dict:
        dict = EvaluationData.load_dict_from_json_file(file)
        dict["path"] = file
        return dict

    def load_model_from_file(self, file: str) -> EvaluationData:
        model: EvaluationData = EvaluationData.load_from_json(file)
        model.path = file
        return model

    def load_pkl_gzip_compressed_eval_data(
        self,
        file_path: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[EvaluationData]:
        if file_path is None:
            files = self._opener.ask_open_files(
                initialdir=self.dir, filetypes=[("pkl.gz files", "*.pkl.gz")]
            )
        else:
            files = [file_path]
        eval_datas: List[EvaluationData] = []
        total_files = len(files)
        for file_index, file in enumerate(files):
            if progress_callback is not None:
                progress_callback(
                    file_index,
                    max(total_files, 1),
                    f"Decompressing archive ({file_index + 1}/{total_files})…",
                )
            with gzip.open(file, "rb") as handle:
                if progress_callback is not None:
                    progress_callback(
                        file_index,
                        max(total_files, 1),
                        "Loading pickled evaluation records (may take several minutes)…",
                    )
                eval_datas.extend(pickle.load(handle))
            if progress_callback is not None:
                progress_callback(
                    file_index + 1,
                    max(total_files, 1),
                    f"Loaded {len(eval_datas)} evaluation record(s) from pickle",
                )
        return eval_datas

    def load_zip_eval_data(self, file: str) -> List[EvaluationData]:

        return _load_zip_eval_data_from_path(file)

    def load_multiple_zip_eval_data(self) -> List[EvaluationData]:
        files = self._opener.ask_open_files(
            initialdir=self.dir,
            filetypes=[("zip files", "*.zip")],
        )

        with ProcessPoolExecutor(mp_context=get_spawn_context()) as executor:
            results = list(
                tqdm(
                    executor.map(_load_zip_eval_data_from_path, files),
                    total=len(files),
                    desc="Loading files",
                )
            )
        return [item for sublist in results for item in sublist]

    def load_multiple_tar_eval_data(self) -> List[EvaluationData]:
        files = self._opener.ask_open_files(
            initialdir=self.dir,
            filetypes=[("tar.gz files", "*.tar.gz")],
        )
        with ProcessPoolExecutor(mp_context=get_spawn_context()) as executor:
            results = list(
                tqdm(
                    executor.map(_load_tar_eval_data_from_path, files),
                    total=len(files),
                    desc="Loading tar.gz files",
                )
            )
        return [item for sublist in results for item in sublist]

    def _parse_json_bytes(self, item):
        file_name, content = item
        data = EvaluationData.load_from_json_bytes(content)
        data.path = file_name
        return data

    def load_tar_eval_data(self, file: str) -> List[EvaluationData]:
        return _load_tar_eval_data_from_path(file)

    def load_eval_data_complex(
        self,
        dirs=None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[EvaluationData]:
        if dirs is None:
            dirs = []
        jsons: List[str] = []
        zips: List[str] = []
        gz_tars: List[str] = []
        pkl_gzs: List[str] = []
        if len(dirs) == 0:
            dirs = self._opener.ask_open_dirs(initialdir=self.dir)
        for dir in dirs:
            files = get_all_file_paths(dir, ["json", "zip", "tar.gz", "pkl.gz"])
            jsons += files["json"]
            zips += files["zip"]
            gz_tars += files["tar.gz"]
            pkl_gzs += files["pkl.gz"]

        if progress_callback is not None:
            return self._load_eval_data_complex_with_progress(
                jsons,
                zips,
                gz_tars,
                pkl_gzs,
                progress_callback,
            )

        results: List[List[EvaluationData]] = []
        spawn_pool = get_spawn_context().Pool(multiprocessing.cpu_count() - 2 or 1)
        with spawn_pool as executor:
            if zips:
                results.extend(
                    tqdm(
                        executor.imap_unordered(_load_zip_eval_data_from_path, zips),
                        total=len(zips),
                        desc="Loading zip files",
                    )
                )
            if gz_tars:
                results.extend(
                    tqdm(
                        executor.imap_unordered(_load_tar_eval_data_from_path, gz_tars),
                        total=len(gz_tars),
                        desc="Loading tar.gz files",
                    )
                )
            if jsons:
                json_models = list(
                    tqdm(
                        executor.imap_unordered(_load_eval_model_from_file, jsons),
                        total=len(jsons),
                        desc="Loading json files",
                    )
                )
                results.append(json_models)
            if pkl_gzs:
                results.extend(
                    tqdm(
                        executor.imap_unordered(
                            _load_pkl_gzip_compressed_eval_data_from_path, pkl_gzs
                        ),
                        total=len(pkl_gzs),
                        desc="Loading pkl.gz files",
                    )
                )
        return [item for sublist in results for item in sublist]

    def _load_eval_data_complex_with_progress(
        self,
        jsons: List[str],
        zips: List[str],
        gz_tars: List[str],
        pkl_gzs: List[str],
        progress_callback: ProgressCallback,
    ) -> List[EvaluationData]:
        tasks: List[Tuple[str, str]] = []
        for path in jsons:
            tasks.append(("json", path))
        for path in zips:
            tasks.append(("zip", path))
        for path in gz_tars:
            tasks.append(("tar.gz", path))
        for path in pkl_gzs:
            tasks.append(("pkl.gz", path))

        eval_datas: List[EvaluationData] = []
        total = max(len(tasks), 1)
        for index, (kind, path) in enumerate(tasks):
            progress_callback(
                index,
                total,
                f"Loading {kind} file {index + 1}/{total}",
            )
            if kind == "json":
                eval_datas.append(_load_eval_model_from_file(path))
            elif kind == "zip":
                eval_datas.extend(_load_zip_eval_data_from_path(path))
            elif kind == "tar.gz":
                eval_datas.extend(_load_tar_eval_data_from_path(path))
            else:
                eval_datas.extend(_load_pkl_gzip_compressed_eval_data_from_path(path))
        progress_callback(total, total, f"Finished loading {len(eval_datas)} record(s)")
        return eval_datas

    def dump_eval_datas_to_gz(
        self, eval_datas: List[EvaluationData], file=None
    ) -> None:
        if file is None:
            file = self._opener.ask_save_file(
                initialdir=self.dir, filetypes=[("gz files", "*.gz")]
            )
        if file is None:
            print("No file selected")
            exit()
        with gzip.open(file, "wb") as f:
            pickle.dump(eval_datas, f, protocol=pickle.HIGHEST_PROTOCOL)


class TrajDataParser(DataParser):
    def __init__(self, file_opener: Optional[FileFolderOpener] = None) -> None:
        super().__init__(self.TRAJ_COLUMN_NAMES, self.RRT_DIR, file_opener=file_opener)

    def load_data_models(self) -> List[TrajectoryData]:
        files = self._opener.ask_open_files(initialdir=self.dir)
        return self.load_models_from_files(files)

    def load_models_from_files(self, files: List[str]) -> List[TrajectoryData]:
        data_models = [self.load_model_from_file(file) for file in files]
        return [model for model in data_models]

    def load_dict_from_file(self, file: str) -> dict:
        dict = TrajectoryData.load_dict_from_json(file)
        dict["path"] = file
        return dict

    def load_model_from_file(self, file: str) -> TrajectoryData:
        model: EvaluationData = TrajectoryData.load_from_json(file)
        model.path = file
        return model
