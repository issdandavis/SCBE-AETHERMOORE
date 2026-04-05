# Hugging Face Tokenizers
> Source: Context7 MCP | Category: science
> Fetched: 2026-04-04

### Train BPE Tokenizer from Files (Python)

Source: https://context7.com/huggingface/tokenizers/llms.txt

Shows how to train a BPE tokenizer using a list of text files. It includes initializing the tokenizer with a pre-tokenizer, configuring the BpeTrainer with various parameters, training the tokenizer, and saving the trained model.

```python
from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import Whitespace

# Initialize tokenizer with pre-tokenizer
tokenizer = Tokenizer(BPE(unk_token="[UNK]"))
tokenizer.pre_tokenizer = Whitespace()

# Configure trainer
trainer = BpeTrainer(
    vocab_size=30000,
    min_frequency=2,
    show_progress=True,
    special_tokens=["[UNK]", "[CLS]", "[SEP]", "[PAD]", "[MASK]"],
    limit_alphabet=1000,
    continuing_subword_prefix="##"
)

# Train on files
files = ["wiki.train.raw", "wiki.valid.raw", "wiki.test.raw"]
tokenizer.train(files, trainer)

# Save trained tokenizer
tokenizer.save("tokenizer.json", pretty=True)
```

---

### Python: Training ByteLevel BPE Tokenizer

Source: https://context7.com/huggingface/tokenizers/llms.txt

Demonstrates training a ByteLevel BPE tokenizer, similar to GPT-2. It allows adding a prefix space to tokens.

```python
from tokenizers import ByteLevelBPETokenizer

tokenizer = ByteLevelBPETokenizer(add_prefix_space=True)
tokenizer.train(
    files=["file1.txt"],
    vocab_size=10000,
    min_frequency=2,
    special_tokens=["<s>", "<pad>", "</s>"]
)
encoded = tokenizer.encode("Training ByteLevel BPE is very easy")
print(encoded.tokens)  # ['Training', 'Byte', 'Level', 'BPE', ...]
```

---

### Build Custom Byte-Level BPE Tokenizer (Python)

Source: https://github.com/huggingface/tokenizers/blob/main/bindings/python/README.md

Demonstrates building a custom byte-level BPE tokenizer by composing different components (model, pre-tokenizer, decoder, post-processor), training it with a `BpeTrainer`, and using it for encoding.

```python
from tokenizers import Tokenizer, models, pre_tokenizers, decoders, trainers, processors

tokenizer = Tokenizer(models.BPE())
tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
tokenizer.decoder = decoders.ByteLevel()
tokenizer.post_processor = processors.ByteLevel(trim_offsets=True)

trainer = trainers.BpeTrainer(
    vocab_size=20000,
    min_frequency=2,
    initial_alphabet=pre_tokenizers.ByteLevel.alphabet()
)
tokenizer.train([
    "./path/to/dataset/1.txt",
    "./path/to/dataset/2.txt",
    "./path/to/dataset/3.txt"
], trainer=trainer)
```

---

### Encode Text with Tokenizer (Python, Rust, JS)

Source: https://github.com/huggingface/tokenizers/blob/main/docs/source-doc-builder/quicktour.mdx

Demonstrates how to use the `Tokenizer.encode` method to process text through the entire tokenizer pipeline.

```python
from tokenizers import Tokenizer

tokenizer = Tokenizer.from_file("path/to/your/tokenizer.json")

text = "Here is some text to encode."
encoding = tokenizer.encode(text)

print(encoding.tokens)
print(encoding.ids)
print(encoding.offsets)
print(encoding.attention_mask)
print(encoding.special_tokens_mask)
print(encoding.overflowing)
```

```rust
use tokenizers::Tokenizer;

let mut tokenizer = Tokenizer::from_file("path/to/your/tokenizer.json").unwrap();
let text = "Here is some text to encode.";
let encoding = tokenizer.encode(text, true).unwrap();

println!("{:?}", encoding.get_tokens());
println!("{:?}", encoding.get_ids());
```

```js
const { Tokenizer } = require("tokenizers");
const tokenizer = Tokenizer.fromFile("path/to/your/tokenizer.json");

const text = "Here is some text to encode.";
const encoding = tokenizer.encode(text);
console.log(encoding.tokens);
console.log(encoding.ids);
```

---

### Train Tokenizer

Source: https://github.com/huggingface/tokenizers/blob/main/docs/source-doc-builder/quicktour.mdx

Trains the tokenizer using the specified trainer and a list of files. The training process learns merge rules based on the corpus in the provided files until the desired vocabulary size is reached.

```python
files = ["path/to/your/wikitext.txt"]
tokenizer.train(files, trainer)
```
