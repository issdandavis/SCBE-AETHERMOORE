from __future__ import annotations

from pathlib import Path

from scripts.system import kaggle_notebook_smoke as smoke


class _FakeCuda:
    def __init__(self, *, available: bool, name: str = "Tesla T4", count: int = 1) -> None:
        self._available = available
        self._name = name
        self._count = count if available else 0

    def is_available(self) -> bool:
        return self._available

    def device_count(self) -> int:
        return self._count

    def get_device_name(self, index: int) -> str:
        assert index == 0
        return self._name


class _FakeTorch:
    class version:
        cuda = "12.1"

    def __init__(self, *, gpu: bool) -> None:
        self.cuda = _FakeCuda(available=gpu)


class _FakeDataset:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows)

    def select(self, indices):
        return _FakeDataset([self._rows[index] for index in indices])


class _FakeTensor:
    def __init__(self, value: float = 1.0) -> None:
        self.value = value

    def to(self, device: str):
        return self

    def detach(self):
        return self

    def cpu(self):
        return self

    def item(self) -> float:
        return self.value

    def backward(self) -> None:
        return None


class _FakeTokenizer:
    pad_token = None
    eos_token = "<eos>"

    def __call__(self, texts, return_tensors=None, padding=None, truncation=None, max_length=None):
        assert texts
        return {"input_ids": _FakeTensor(), "attention_mask": _FakeTensor()}


class _FakeModel:
    def to(self, device: str):
        return self

    def train(self) -> None:
        return None

    def parameters(self):
        return []

    def __call__(self, **kwargs):
        return type("_Output", (), {"loss": _FakeTensor(0.25)})()


class _FakeOptimizer:
    def step(self) -> None:
        return None

    def zero_grad(self) -> None:
        return None


def test_detect_runtime_recognizes_kaggle_env() -> None:
    result = smoke.detect_runtime(
        environ={
            "KAGGLE_KERNEL_RUN_TYPE": "Interactive",
            "KAGGLE_URL_BASE": "https://www.kaggle.com",
        }
    )

    assert result["is_kaggle"] is True
    assert result["run_type"] == "Interactive"


def test_probe_dependencies_reports_missing_modules() -> None:
    def fake_importer(name: str):
        if name == "datasets":
            raise ModuleNotFoundError("datasets missing")
        return object()

    result = smoke.probe_dependencies(importer=fake_importer, module_names=("torch", "datasets"))

    assert result["ok"] is False
    assert result["loaded"] == ["torch"]
    assert result["missing"][0]["module"] == "datasets"


def test_probe_dataset_access_returns_preview_rows() -> None:
    rows = [
        {"text": "alpha row", "meta": {"track": "core"}},
        {"instruction": "beta", "response": "gamma"},
    ]

    def fake_loader(repo_id: str, *, data_files: str | None = None, split: str = "train"):
        assert repo_id == "repo/demo"
        assert data_files == "train.jsonl"
        assert split == "train"
        return _FakeDataset(rows)

    result = smoke.probe_dataset_access(
        dataset_repo="repo/demo",
        data_file="train.jsonl",
        split="train",
        sample_size=2,
        load_dataset_fn=fake_loader,
    )

    assert result["ok"] is True
    assert result["row_count"] == 2
    assert result["sample_rows"][0]["text"] == "alpha row"


def test_probe_micro_train_runs_single_step_with_fake_components() -> None:
    rows = [{"text": "SCBE training sample text"}]

    result = smoke.probe_micro_train(
        rows=rows,
        model_id="repo/model",
        torch_module=_FakeTorch(gpu=False),
        tokenizer_loader=lambda model_id: _FakeTokenizer(),
        model_loader=lambda model_id: _FakeModel(),
        optimizer_factory=lambda params: _FakeOptimizer(),
    )

    assert result["ok"] is True
    assert result["loss"] == 0.25
    assert result["sample_count"] == 1


def test_run_kaggle_preflight_fails_without_gpu_even_if_other_gates_pass(tmp_path: Path) -> None:
    def fake_importer(name: str):
        if name == "torch":
            return _FakeTorch(gpu=False)
        return object()

    def fake_loader(repo_id: str, *, data_files: str | None = None, split: str = "train"):
        return _FakeDataset([{"text": "sample row"}])

    report = smoke.run_kaggle_preflight(
        dataset_repo="repo/demo",
        data_file="train.jsonl",
        output_dir=tmp_path / "artifacts",
        require_gpu=True,
        require_micro_train=False,
        importer=fake_importer,
        load_dataset_fn=fake_loader,
        environ={"KAGGLE_KERNEL_RUN_TYPE": "Interactive"},
    )

    assert report["status"] == "failed"
    assert "runtime:no_gpu" in report["failures"]
    assert Path(report["report_path"]).exists()


def test_run_kaggle_preflight_passes_with_gpu_and_micro_train(tmp_path: Path) -> None:
    def fake_importer(name: str):
        if name == "torch":
            return _FakeTorch(gpu=True)
        return object()

    def fake_loader(repo_id: str, *, data_files: str | None = None, split: str = "train"):
        return _FakeDataset([{"text": "sample row"}])

    report = smoke.run_kaggle_preflight(
        dataset_repo="repo/demo",
        data_file="train.jsonl",
        output_dir=tmp_path / "artifacts",
        require_kaggle=True,
        require_gpu=True,
        require_micro_train=True,
        importer=fake_importer,
        load_dataset_fn=fake_loader,
        torch_module=_FakeTorch(gpu=True),
        tokenizer_loader=lambda model_id: _FakeTokenizer(),
        model_loader=lambda model_id: _FakeModel(),
        optimizer_factory=lambda params: _FakeOptimizer(),
        environ={
            "KAGGLE_KERNEL_RUN_TYPE": "Interactive",
            "KAGGLE_URL_BASE": "https://www.kaggle.com",
        },
    )

    assert report["status"] == "passed"
    assert report["failures"] == []
    assert report["micro_train"]["ok"] is True
