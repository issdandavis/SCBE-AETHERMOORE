# HuggingFace Datasets

The Datasets library provides efficient access to thousands of datasets with memory-mapped Arrow tables, streaming support, and built-in processing utilities. It integrates tightly with the Transformers training pipeline.

## load_dataset API

The primary entry point for loading datasets from the Hub, local files, or custom scripts:

```python
from datasets import load_dataset

# Load from HuggingFace Hub
dataset = load_dataset("imdb")
print(dataset)
# DatasetDict({
#     train: Dataset({features: ['text', 'label'], num_rows: 25000})
#     test: Dataset({features: ['text', 'label'], num_rows: 25000})
# })

# Load a specific split
train_dataset = load_dataset("imdb", split="train")

# Load a specific configuration
dataset = load_dataset("glue", "mrpc")

# Load from local files
dataset = load_dataset("json", data_files="data/train.jsonl")
dataset = load_dataset("csv", data_files={"train": "train.csv", "test": "test.csv"})
dataset = load_dataset("parquet", data_files="data/*.parquet")

# Load a subset of rows
dataset = load_dataset("imdb", split="train[:1000]")  # First 1000
dataset = load_dataset("imdb", split="train[50%:]")    # Last 50%

# Load from a private repo (requires HF token)
dataset = load_dataset("username/private-dataset", token="hf_xxx")

# Access rows
print(dataset[0])                    # First row as dict
print(dataset["text"][:5])           # First 5 text entries
print(dataset.column_names)          # List column names
print(dataset.features)              # Schema with types
```

## Streaming IterableDataset

Stream large datasets without downloading the entire dataset to disk:

```python
from datasets import load_dataset

# Stream a dataset
dataset = load_dataset("allenai/c4", "en", split="train", streaming=True)

# Iterate over examples
for i, example in enumerate(dataset):
    print(example["text"][:100])
    if i >= 4:
        break

# Take first N examples
subset = dataset.take(100)

# Skip examples
subset = dataset.skip(1000).take(100)

# Shuffle with a buffer
shuffled = dataset.shuffle(seed=42, buffer_size=1000)

# Chain multiple streaming datasets
from datasets import interleave_datasets

en_dataset = load_dataset("mc4", "en", split="train", streaming=True)
fr_dataset = load_dataset("mc4", "fr", split="train", streaming=True)
combined = interleave_datasets([en_dataset, fr_dataset])
```

## Filtered AudioFolder

Load and filter audio datasets from local directories:

```python
from datasets import load_dataset, Audio

# Load audio from a local folder structure
dataset = load_dataset("audiofolder", data_dir="./audio_data")

# Cast audio column to specific sampling rate
dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))

# Filter by metadata
dataset = dataset.filter(lambda x: x["label"] == "positive")

# Filter by duration (requires loading audio)
def filter_by_duration(example):
    audio = example["audio"]
    duration = len(audio["array"]) / audio["sampling_rate"]
    return 1.0 <= duration <= 30.0

dataset = dataset.filter(filter_by_duration)

# Load with metadata file
dataset = load_dataset("audiofolder", data_dir="./audio_data", drop_labels=True)
```

## Parquet Streaming with Filters

Efficiently stream and filter Parquet datasets:

```python
from datasets import load_dataset

# Stream Parquet files
dataset = load_dataset(
    "parquet",
    data_files="s3://bucket/data/*.parquet",
    split="train",
    streaming=True
)

# Stream from HuggingFace Hub with Parquet backend
dataset = load_dataset(
    "bigcode/the-stack",
    data_dir="data/python",
    split="train",
    streaming=True
)

# Filter while streaming (applied lazily)
python_code = dataset.filter(lambda x: x["language"] == "python")
short_code = python_code.filter(lambda x: len(x["content"]) < 10000)

for example in short_code.take(5):
    print(example["content"][:200])

# Load specific Parquet files
dataset = load_dataset(
    "parquet",
    data_files={
        "train": ["data/part-00000.parquet", "data/part-00001.parquet"],
        "test": "data/test.parquet"
    }
)
```

## IterableDataset.map()

Apply transformations to streaming datasets lazily:

```python
from datasets import load_dataset

dataset = load_dataset("imdb", split="train", streaming=True)

# Map a function over the dataset (lazy, applied on iteration)
def tokenize(example):
    example["tokens"] = example["text"].lower().split()[:128]
    example["length"] = len(example["tokens"])
    return example

mapped = dataset.map(tokenize)

for example in mapped.take(3):
    print(f"Length: {example['length']}, First tokens: {example['tokens'][:5]}")

# Batched map for efficiency
def batch_tokenize(examples):
    return {
        "tokens": [text.lower().split()[:128] for text in examples["text"]],
        "length": [len(text.split()[:128]) for text in examples["text"]]
    }

mapped = dataset.map(batch_tokenize, batched=True, batch_size=32)

# Remove columns
mapped = dataset.map(tokenize, remove_columns=["text"])

# Map with multiple workers (non-streaming)
regular_dataset = load_dataset("imdb", split="train")
mapped = regular_dataset.map(tokenize, num_proc=4)

# Chaining operations
processed = (
    dataset
    .filter(lambda x: len(x["text"]) > 100)
    .map(tokenize)
    .shuffle(seed=42, buffer_size=1000)
)

for example in processed.take(5):
    print(example["length"])
```
