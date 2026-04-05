# HuggingFace Transformers

The Transformers library provides state-of-the-art pretrained models for NLP, computer vision, and audio tasks. It supports PyTorch, TensorFlow, and JAX backends with a unified API for model loading, tokenization, and inference.

## AutoModel Loading with dtype and device_map

Load pretrained models with automatic architecture detection, precision control, and device placement:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Load model with specific dtype
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")

# Load with 8-bit quantization
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    load_in_8bit=True,
    device_map="auto"
)

# Load with 4-bit quantization (QLoRA-ready)
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    quantization_config=bnb_config,
    device_map="auto"
)

# Custom device map for multi-GPU
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-70B",
    torch_dtype=torch.bfloat16,
    device_map="balanced"  # Distribute across available GPUs
)
```

## Pipeline Creation

High-level inference API that handles tokenization, model forward pass, and post-processing:

```python
from transformers import pipeline

# Text generation
generator = pipeline("text-generation", model="gpt2")
result = generator("Once upon a time", max_new_tokens=50, do_sample=True, temperature=0.7)
print(result[0]["generated_text"])

# Sentiment analysis
classifier = pipeline("sentiment-analysis")
result = classifier("I love this library!")
print(result)  # [{'label': 'POSITIVE', 'score': 0.9998}]

# Named entity recognition
ner = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")
result = ner("My name is John and I work at Google in New York.")
for entity in result:
    print(f"{entity['word']}: {entity['entity_group']} ({entity['score']:.4f})")

# Question answering
qa = pipeline("question-answering")
result = qa(question="What is SCBE?", context="SCBE is an AI safety governance framework.")
print(result["answer"])

# Zero-shot classification
classifier = pipeline("zero-shot-classification")
result = classifier(
    "This is a tutorial about machine learning",
    candidate_labels=["education", "politics", "business"]
)
print(result["labels"][0], result["scores"][0])

# Pipeline with specific device
generator = pipeline("text-generation", model="gpt2", device=0)  # GPU 0
```

## Tokenization

Convert text to model input tensors and back:

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("gpt2")

# Basic tokenization
tokens = tokenizer("Hello, world!")
print(tokens)
# {'input_ids': [15496, 11, 995, 0], 'attention_mask': [1, 1, 1, 1]}

# Batch tokenization with padding
texts = ["Short text.", "This is a much longer piece of text for comparison."]
tokens = tokenizer(
    texts,
    padding=True,
    truncation=True,
    max_length=128,
    return_tensors="pt"  # Return PyTorch tensors
)

# Decode back to text
decoded = tokenizer.decode(tokens["input_ids"][0], skip_special_tokens=True)

# Inspect individual tokens
token_ids = tokenizer.encode("Hello, world!")
tokens_list = tokenizer.convert_ids_to_tokens(token_ids)
print(tokens_list)  # ['Hello', ',', 'Ġworld', '!']

# Chat template tokenization
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is AI safety?"}
]
chat_input = tokenizer.apply_chat_template(messages, tokenize=True, return_tensors="pt")
```

## Fine-Tune Causal LM with Trainer

Train a causal language model using the Trainer API:

```python
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from datasets import load_dataset

# Load model and tokenizer
model_name = "gpt2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(model_name)

# Load and tokenize dataset
dataset = load_dataset("wikitext", "wikitext-2-raw-v1")

def tokenize_function(examples):
    return tokenizer(examples["text"], truncation=True, max_length=512)

tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"])

# Data collator for causal LM (predicts next token)
data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

# Training arguments
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=8,
    learning_rate=2e-5,
    weight_decay=0.01,
    warmup_steps=100,
    logging_steps=50,
    eval_strategy="steps",
    eval_steps=500,
    save_strategy="steps",
    save_steps=500,
    bf16=True,
    report_to="wandb",
)

# Create Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["validation"],
    data_collator=data_collator,
)

# Train
trainer.train()

# Save
trainer.save_model("./fine-tuned-gpt2")
tokenizer.save_pretrained("./fine-tuned-gpt2")
```

## Sequence Classification Fine-Tuning

Fine-tune a model for text classification tasks:

```python
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
)
from datasets import load_dataset
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

# Load model with classification head
model_name = "bert-base-uncased"
num_labels = 2

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=num_labels
)

# Load dataset
dataset = load_dataset("imdb")

def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        padding="max_length",
        truncation=True,
        max_length=256
    )

tokenized_dataset = dataset.map(tokenize_function, batched=True)

# Compute metrics
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1": f1_score(labels, predictions, average="weighted"),
    }

# Training arguments
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=64,
    learning_rate=5e-5,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["test"],
    compute_metrics=compute_metrics,
)

trainer.train()
eval_results = trainer.evaluate()
print(f"Accuracy: {eval_results['eval_accuracy']:.4f}")
print(f"F1: {eval_results['eval_f1']:.4f}")
```
