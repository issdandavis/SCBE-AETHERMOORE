# Hugging Face Hub
> Source: Context7 MCP | Category: science
> Fetched: 2026-04-04

### Load and Push Models using ModelHubMixin

Source: https://github.com/huggingface/huggingface_hub/blob/main/docs/source/en/guides/integrations.md

This approach leverages the `ModelHubMixin` class, allowing models to be loaded using `MyModel.from_pretrained(...)` and pushed via `model.push_to_hub(...)`. It reduces maintenance as many Hub interactions are handled by the `huggingface_hub` library.

```python
from huggingface_hub import ModelHubMixin

class MyModel(ModelHubMixin):
    def __init__(self, config=None):
        self.config = config

    @classmethod
    def from_pretrained(cls, model_id):
        print(f"Loading model {model_id}")
        return cls()

    def push_to_hub(self, repo_id):
        print(f"Pushing model to {repo_id}")

model = MyModel.from_pretrained("bert-base-uncased")
model.push_to_hub("my-bert-model")
```

---

### Implement push_to_hub for Model Uploading

Source: https://github.com/huggingface/huggingface_hub/blob/main/docs/source/en/guides/integrations.md

Shows how to create a repository, save model artifacts to a temporary directory, and upload them to the Hub using the HfApi. This approach ensures atomic commits by uploading a folder of files.

```python
def push_to_hub(model: MyModelClass, repo_name: str) -> None:
   api = HfApi()
   repo_id = api.create_repo(repo_name, exist_ok=True)

   with TemporaryDirectory() as tmpdir:
      tmpdir = Path(tmpdir)
      save_model(model, tmpdir / "model.safetensors")
      card = generate_model_card(model)
      (tmpdir / "README.md").write_text(card)
      return api.upload_folder(repo_id=repo_id, folder_path=tmpdir)
```

---

### Implement from_pretrained for Model Loading

Source: https://github.com/huggingface/huggingface_hub/blob/main/docs/source/en/guides/integrations.md

Demonstrates how to implement a custom from_pretrained method to download model files from the Hub using hf_hub_download and load them into a specific model class.

```python
def from_pretrained(model_id: str) -> MyModelClass:
   cached_model = hf_hub_download(
      repo_id=repo_id,
      filename="model.pkl",
      library_name="fastai",
      library_version=get_fastai_version(),
   )
   return load_model(cached_model)
```

---

### Upload Files to Hugging Face Hub (Python)

Source: https://context7.com/huggingface/huggingface_hub/llms.txt

Upload files and folders to the Hugging Face Hub using `HfApi`. Supports uploading single files, entire directories, and large folders with resilience and multi-threading.

```python
from huggingface_hub import HfApi, CommitOperationAdd, CommitOperationDelete

api = HfApi()

# Upload a single file
api.upload_file(
    path_or_fileobj="/path/to/local/README.md",
    path_in_repo="README.md",
    repo_id="username/my-model",
    repo_type="model"
)

# Upload from bytes or file-like object
api.upload_file(
    path_or_fileobj=b"Model configuration content",
    path_in_repo="config.txt",
    repo_id="username/my-model"
)

# Upload an entire folder
api.upload_folder(
    folder_path="/path/to/local/folder",
    repo_id="username/my-cool-space",
    repo_type="space",
    ignore_patterns=["*.log", "__pycache__/**"]
)

# Non-blocking upload (returns Future)
future = api.upload_folder(
    repo_id="username/my-model",
    folder_path="checkpoints",
    run_as_future=True
)
result = future.result()

# Upload large folders (resilient, multi-threaded, resumable)
api.upload_large_folder(
    repo_id="username/large-dataset",
    repo_type="dataset",
    folder_path="/path/to/large/folder"
)

# Low-level commit with multiple operations
operations = [
    CommitOperationAdd(path_in_repo="model.safetensors", path_or_fileobj="/local/model.safetensors"),
    CommitOperationAdd(path_in_repo="config.json", path_or_fileobj="/local/config.json"),
    CommitOperationDelete(path_in_repo="old-model.bin"),
]
api.create_commit(
    repo_id="username/my-model",
    operations=operations,
    commit_message="Update model weights and remove old version"
)
```

---

### Download an entire repository from Hugging Face Hub

Source: https://github.com/huggingface/huggingface_hub/blob/main/README.md

Downloads all files from a specified repository on the Hugging Face Hub using the `snapshot_download` function.

```python
from huggingface_hub import snapshot_download

snapshot_download("stabilityai/stable-diffusion-2-1")
```
