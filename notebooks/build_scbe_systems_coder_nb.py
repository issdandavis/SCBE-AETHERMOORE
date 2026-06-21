"""Builder for notebooks/scbe_systems_coder_colab.ipynb -- train a coder model to code in ISSAC'S SYSTEMS.

Unlike coder_qwen_code_primaries_colab.ipynb (which points at SFT files that are NOT committed and so dies
on a fresh clone), this notebook GENERATES the systems-SFT inside the run, from the repo itself, then trains
on the union and measures base-vs-trained on a held-out slice. What it trains on:

  * the Six Tongues as coding primaries (Kor'aelin/Python, Avali/JS, Runethic/Rust, Cassisivadan/
    Mathematica, Umbroth/Haskell, Draumric/Markdown) + encoding mechanics  -- generate_tongue_curriculum_sft
  * the coding SYSTEM itself: every module's docstrings + the docs (the binary<->hex spine, the block/
    polyglot coding, loom, tongues, loomfn ...)                            -- codebase_to_sft
  * an augmented curriculum (inversions/rotations/paraphrases/adversarial) + a HELD-OUT pop-quiz eval
                                                                            -- augment_curriculum_sft
  * any other systems-SFT the repo can mint standalone (chemistry primary, drill, bijective codeflow) --
    each best-effort, a failing generator is skipped, never fatal.

Every record is normalized to the chat {messages} shape regardless of the generator's native format, then
QLoRA-trained on Qwen2.5-Coder-7B (4-bit, fits a T4). Eval: held-out perplexity with the LoRA adapter
DISABLED (base) vs ENABLED (trained) -- a lower trained perplexity is a real, honest signal that the model
fits Issac's systems better, on data it never trained on. Plus sample generations to eyeball.

    python notebooks/build_scbe_systems_coder_nb.py   # writes the .ipynb
"""

from __future__ import annotations

import json
from pathlib import Path

NB = Path(__file__).resolve().parent / "scbe_systems_coder_colab.ipynb"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


CELLS = [
    md(
        "# SCBE Systems Coder — QLoRA on Issac's coding systems\n\n"
        "Trains `Qwen2.5-Coder-7B-Instruct` (4-bit QLoRA, fits a T4) to code in **your** systems, not\n"
        "generic Python. The training corpus is **generated from this repo at run time** so it always\n"
        "exists and always matches the current code:\n\n"
        "- **Six Tongues → primary languages** + encoding mechanics (tongue curriculum)\n"
        "- **the coding system itself** — the binary↔hex spine, the block/polyglot emitter, loom, loomfn,\n"
        "  tongues — mined from every module's docstrings + the docs (codebase→SFT)\n"
        "- an **augmented curriculum** (inversions / rotations / paraphrases / adversarial) + a **held-out\n"
        "  pop-quiz** used as the eval set\n"
        "- any other systems-SFT the repo can mint standalone (chemistry, drill, bijective codeflow) —\n"
        "  best-effort\n\n"
        "**Honest eval:** held-out perplexity with the adapter OFF (base) vs ON (trained). Lower trained\n"
        "perplexity on data it never saw = it genuinely fits your systems better. Sample generations are\n"
        "printed so you can read what it writes."
    ),
    code(
        '!pip install -q "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"\n'
        "!pip install -q --no-deps xformers trl peft accelerate bitsandbytes triton\n"
        "!pip install -q datasets huggingface_hub\n"
        "print('deps installed')"
    ),
    code(
        "import os\n"
        "# HF login is OPTIONAL (only needed to push the adapter). Skipped silently if no token.\n"
        "try:\n"
        "    from google.colab import userdata\n"
        "    os.environ['HF_TOKEN'] = userdata.get('HF_TOKEN')\n"
        "except Exception:\n"
        "    pass\n"
        "if os.environ.get('HF_TOKEN'):\n"
        "    from huggingface_hub import login\n"
        "    login(token=os.environ['HF_TOKEN'])\n"
        "    print('HF login ok')\n"
        "else:\n"
        "    print('no HF_TOKEN — training stays local to Colab (fine)')"
    ),
    code(
        "!git clone --depth 1 https://github.com/issdandavis/SCBE-AETHERMOORE.git scbe\n"
        "%cd /content/scbe\n"
        "!nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv"
    ),
    md(
        "## 1. Generate the systems-SFT from the repo\n"
        "Each generator is best-effort — a failing one is skipped, never fatal. Whatever lands in\n"
        "`training-data/sft/*.jsonl` becomes the corpus."
    ),
    code(
        "import subprocess, sys, glob, os, shutil\n"
        "os.makedirs('training-data/sft', exist_ok=True)\n"
        "\n"
        "def run(script):\n"
        "    try:\n"
        "        r = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=900)\n"
        "        tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or ['']\n"
        "        print('%-4s %-46s %s' % ('OK' if r.returncode == 0 else 'WARN', script, tail[0][:78]))\n"
        "        return r.returncode == 0\n"
        "    except Exception as e:\n"
        "        print('WARN %-46s %s' % (script, type(e).__name__)); return False\n"
        "\n"
        "# 1) generators with no input deps first (tongue -> sft/, codebase -> training-data/ parent), then\n"
        "#    optional ones. Each best-effort: a failing generator is skipped, never fatal.\n"
        "for script in ['scripts/generate_tongue_curriculum_sft.py', 'scripts/codebase_to_sft.py',\n"
        "               'scripts/build_chemistry_codebase_sft.py',  # chem from chem code+docs+notes (self-contained)\n"
        "               'scripts/generate_collegiate_curriculum_sft.py', 'scripts/build_chemistry_primary_sft.py']:\n"
        "    if os.path.exists(script):\n"
        "        run(script)\n"
        "    else:\n"
        "        print('SKIP  %-46s (missing script)' % script)\n"
        "\n"
        "# 2) codebase_to_sft writes to training-data/ (parent); relocate any top-level shard into sft/ so the\n"
        "#    augmenter AND the loader see everything in one place.\n"
        "for f in glob.glob('training-data/*.jsonl'):\n"
        "    dst = os.path.join('training-data/sft', os.path.basename(f))\n"
        "    if os.path.abspath(f) != os.path.abspath(dst):\n"
        "        shutil.move(f, dst)\n"
        "\n"
        "# 3) augment now globs training-data/sft/*.jsonl -> writes training-data/curriculum/ (gym train +\n"
        "#    the held-out phase3_pop_quiz eval + aug_* shards).\n"
        "if os.path.exists('scripts/augment_curriculum_sft.py'):\n"
        "    run('scripts/augment_curriculum_sft.py')\n"
        "\n"
        "files = sorted(glob.glob('training-data/sft/**/*.jsonl', recursive=True)\n"
        "               + glob.glob('training-data/curriculum/**/*.jsonl', recursive=True))\n"
        "print('\\nSFT files present:', len(files))\n"
        "for f in files:\n"
        "    n = sum(1 for _ in open(f, encoding='utf-8'))\n"
        "    print('  %6d  %s' % (n, f))"
    ),
    md(
        "## 2. Load + normalize every record to chat `messages`, hold out the eval set\n"
        "Generators emit different shapes (`messages`, `instruction`/`response`, `text`, ...). One\n"
        "normalizer handles all. The held-out **pop-quiz** (if present) is the eval; otherwise an 8% split."
    ),
    code(
        "import glob, json, random\n"
        "random.seed(42)\n"
        "SYSTEM_PROMPT = (\n"
        "    \"You are an SCBE-AETHERMOORE governance-aware coding assistant. You understand the Six \"\n"
        "    \"Sacred Tongues as coding primaries (Kor'aelin/Python, Avali/JavaScript, Runethic/Rust, \"\n"
        "    \"Cassisivadan/Mathematica, Umbroth/Haskell, Draumric/Markdown), the binary<->hex spine, the \"\n"
        "    \"block/polyglot emitter, and bijective edit propagation. Write clean, correct, SCBE-style code.\"\n"
        ")\n"
        "\n"
        "def to_messages(rec):\n"
        "    if isinstance(rec.get('messages'), list) and rec['messages']:\n"
        "        msgs = rec['messages']\n"
        "        if not any(m.get('role') == 'system' for m in msgs):\n"
        "            msgs = [{'role': 'system', 'content': SYSTEM_PROMPT}] + msgs\n"
        "        return msgs\n"
        "    user = rec.get('instruction') or rec.get('prompt') or rec.get('question') or rec.get('input')\n"
        "    asst = rec.get('response') or rec.get('output') or rec.get('completion') or rec.get('answer')\n"
        "    if user and asst:\n"
        "        extra = rec.get('input') if rec.get('instruction') else None\n"
        "        u = user + ('\\n\\n' + extra if extra and extra != user else '')\n"
        "        return [{'role': 'system', 'content': SYSTEM_PROMPT},\n"
        "                {'role': 'user', 'content': u}, {'role': 'assistant', 'content': asst}]\n"
        "    if rec.get('text'):\n"
        "        return None  # handled as raw text below\n"
        "    return None\n"
        "\n"
        "EVAL_GLOBS = ('phase3_pop_quiz', 'holdout', '_eval')\n"
        "train_recs, eval_recs, raw_text = [], [], []\n"
        "_all = (glob.glob('training-data/sft/**/*.jsonl', recursive=True)\n"
        "        + glob.glob('training-data/curriculum/**/*.jsonl', recursive=True))\n"
        "for f in sorted(_all):\n"
        "    base = os.path.basename(f)\n"
        "    if base.startswith('aug_'):\n"
        "        continue  # raw augmentation components -- already split into phase2 (train) + phase3 (quiz)\n"
        "    is_eval = any(k in base for k in EVAL_GLOBS)\n"
        "    for line in open(f, encoding='utf-8'):\n"
        "        line = line.strip()\n"
        "        if not line:\n"
        "            continue\n"
        "        try:\n"
        "            rec = json.loads(line)\n"
        "        except Exception:\n"
        "            continue\n"
        "        msgs = to_messages(rec)\n"
        "        if msgs is None and rec.get('text'):\n"
        "            (eval_recs if is_eval else train_recs).append({'text': rec['text']}); continue\n"
        "        if msgs is None:\n"
        "            continue\n"
        "        (eval_recs if is_eval else train_recs).append({'messages': msgs})\n"
        "\n"
        "# de-dup train by content; if no dedicated eval file, carve 8% of train as held-out\n"
        "seen, uniq = set(), []\n"
        "for r in train_recs:\n"
        "    key = json.dumps(r, sort_keys=True)\n"
        "    if key not in seen:\n"
        "        seen.add(key); uniq.append(r)\n"
        "train_recs = uniq\n"
        "if not eval_recs:\n"
        "    random.shuffle(train_recs)\n"
        "    cut = max(1, int(len(train_recs) * 0.08))\n"
        "    eval_recs, train_recs = train_recs[:cut], train_recs[cut:]\n"
        "# eval must be disjoint from train\n"
        "train_keys = {json.dumps(r, sort_keys=True) for r in train_recs}\n"
        "eval_recs = [r for r in eval_recs if json.dumps(r, sort_keys=True) not in train_keys]\n"
        "print('train records:', len(train_recs), ' held-out eval:', len(eval_recs))\n"
        "print('sample:', json.dumps(train_recs[0])[:400])"
    ),
    md("## 3. Load Qwen2.5-Coder-7B (4-bit) + LoRA"),
    code(
        "from unsloth import FastLanguageModel\n"
        "from datasets import Dataset\n"
        "BASE_MODEL = 'Qwen/Qwen2.5-Coder-7B-Instruct'\n"
        "MAX_SEQ_LENGTH = 2048  # 7B 4-bit QLoRA fits a 16GB T4 at 2048 under unsloth; raise on L4/A100\n"
        "model, tokenizer = FastLanguageModel.from_pretrained(\n"
        "    model_name=BASE_MODEL, max_seq_length=MAX_SEQ_LENGTH, dtype=None, load_in_4bit=True)\n"
        "model = FastLanguageModel.get_peft_model(\n"
        "    model, r=32, lora_alpha=64, lora_dropout=0,\n"
        "    target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],\n"
        "    bias='none', use_gradient_checkpointing='unsloth', random_state=42)\n"
        "\n"
        "def render(rec):\n"
        "    if 'text' in rec:\n"
        "        return {'text': rec['text']}\n"
        "    return {'text': tokenizer.apply_chat_template(rec['messages'], tokenize=False, add_generation_prompt=False)}\n"
        "\n"
        "train_ds = Dataset.from_list(train_recs).map(render, remove_columns=['messages'] if 'messages' in train_recs[0] else ['text'])\n"
        "eval_ds = Dataset.from_list(eval_recs).map(render, remove_columns=['messages'] if 'messages' in eval_recs[0] else ['text'])\n"
        "print('rendered train/eval:', len(train_ds), len(eval_ds))"
    ),
    md("## 4. Held-out perplexity BEFORE training (adapter disabled = base)"),
    code(
        "import math, torch\n"
        "\n"
        "def held_out_loss(model, tokenizer, ds, n=64, max_len=2048):\n"
        "    model.eval()\n"
        "    losses = []\n"
        "    rows = ds.select(range(min(n, len(ds))))\n"
        "    with torch.no_grad():\n"
        "        for ex in rows:\n"
        "            ids = tokenizer(ex['text'], return_tensors='pt', truncation=True, max_length=max_len).to(model.device)\n"
        "            out = model(**ids, labels=ids['input_ids'])\n"
        "            if not math.isnan(float(out.loss)):\n"
        "                losses.append(float(out.loss))\n"
        "    mean = sum(losses) / len(losses) if losses else float('nan')\n"
        "    return mean, math.exp(mean) if losses else float('nan')\n"
        "\n"
        "with model.disable_adapter():\n"
        "    base_loss, base_ppl = held_out_loss(model, tokenizer, eval_ds)\n"
        "print('BASE   held-out loss %.4f  perplexity %.2f' % (base_loss, base_ppl))"
    ),
    md("## 5. Train the LoRA adapter on your systems"),
    code(
        "from transformers import TrainingArguments\n"
        "from trl import SFTTrainer\n"
        "FastLanguageModel.for_training(model)\n"
        "trainer = SFTTrainer(\n"
        "    model=model, tokenizer=tokenizer, train_dataset=train_ds,\n"
        "    dataset_text_field='text', max_seq_length=MAX_SEQ_LENGTH, packing=True,\n"
        "    args=TrainingArguments(\n"
        "        output_dir='/content/scbe/training/runs/systems-coder', report_to='none',\n"
        "        num_train_epochs=2, warmup_ratio=0.05, per_device_train_batch_size=2,\n"
        "        gradient_accumulation_steps=8, learning_rate=2e-4, optim='adamw_8bit',\n"
        "        weight_decay=0.01, lr_scheduler_type='cosine', logging_steps=20,\n"
        "        save_strategy='no', seed=42))\n"
        "stats = trainer.train()\n"
        "model.save_pretrained('/content/scbe/training/runs/systems-coder/lora')\n"
        "tokenizer.save_pretrained('/content/scbe/training/runs/systems-coder/lora')\n"
        "print('train loss:', float(getattr(stats, 'training_loss', 0.0)))"
    ),
    md("## 6. Held-out perplexity AFTER training + the headline delta"),
    code(
        "FastLanguageModel.for_inference(model)\n"
        "trained_loss, trained_ppl = held_out_loss(model, tokenizer, eval_ds)\n"
        "print('TRAINED held-out loss %.4f  perplexity %.2f' % (trained_loss, trained_ppl))\n"
        "print()\n"
        "print('==== SYSTEMS FIT (held-out, never trained on) ====')\n"
        "print('  base    perplexity : %.2f' % base_ppl)\n"
        "print('  trained perplexity : %.2f' % trained_ppl)\n"
        "delta = base_ppl - trained_ppl\n"
        "pct = 100.0 * delta / base_ppl if base_ppl and not math.isnan(base_ppl) else float('nan')\n"
        "print('  PPL IMPROVEMENT    : %+.2f  (%.1f%% lower = fits your systems better)' % (delta, pct))\n"
        "print('  NET LIFT %+.4f loss' % (base_loss - trained_loss))  # terminal driver waits on 'NET LIFT'"
    ),
    md("## 7. Read what it writes — sample generations in your systems"),
    code(
        "PROMPTS = [\n"
        "    'In SCBE, what are the Six Sacred Tongues and which programming language is each the coding primary for?',\n"
        "    'Write a Python function that round-trips a byte through the binary<->hex spine and asserts it is bijective.',\n"
        "    'Explain the block/polyglot emitter: how one CA-opcode core emits the same program into multiple languages.',\n"
        "]\n"
        "for q in PROMPTS:\n"
        "    msgs = [{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':q}]\n"
        "    text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)\n"
        "    ids = tokenizer(text, return_tensors='pt').to(model.device)\n"
        "    out = model.generate(**ids, max_new_tokens=256, do_sample=False, pad_token_id=tokenizer.eos_token_id)\n"
        "    print('Q:', q)\n"
        "    print(tokenizer.decode(out[0][ids['input_ids'].shape[1]:], skip_special_tokens=True)[:600])\n"
        "    print('-' * 80)"
    ),
    md(
        "## Notes\n"
        "- Corpus is generated from the repo, so it tracks your systems as they change — re-run to refresh.\n"
        "- `NET LIFT` (loss delta) is the line the terminal driver waits on; perplexity drop is the headline.\n"
        "- To push the adapter: set `HF_TOKEN` and add a `model.push_to_hub('issdandavis/scbe-systems-coder')`\n"
        "  cell. Default stays local until you like the result.\n"
        "- Perplexity measures *fit*, not execution-correctness. For an execution-verified code eval, pair\n"
        "  this with `python/helm/pitfall_eval.py` and the polyglot/loomfn verifiers in a follow-up cell."
    ),
]


def main() -> int:
    nb = {
        "cells": CELLS,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": [], "gpuType": "T4"},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 0,
    }
    NB.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote %s (%d cells)" % (NB, len(CELLS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
