"""Builder for notebooks/vtc_lift_fast_colab.ipynb -- the ROBUST variant.

The first notebook used unsloth-from-git, whose Colab install wedged for 20+ min. This one drops
unsloth (and trl) entirely: standard transformers.Trainer + peft + bitsandbytes (all install in ~1
min, no source builds), corpus fed via files.upload() (no Drive auth hang). Same honest measurement:
base (LoRA-off) vs trained (LoRA-on) on held-out MBPP, execution-verified. See python/helm/code_lift.py.

    python notebooks/build_vtc_lift_fast_nb.py
"""

from __future__ import annotations

import json
from pathlib import Path


def md(*lines: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": [x if x.endswith("\n") else x + "\n" for x in lines]}


def code(*lines: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": [x if x.endswith("\n") else x + "\n" for x in lines],
    }


CELLS = [
    md(
        "# VTC Capability-Lift (FAST / robust)  -- qwen2.5-coder-1.5B, Colab T4",
        "",
        "Drops unsloth (whose git install wedges on Colab) for **standard `transformers.Trainer` + `peft` +",
        "`bitsandbytes`** -- installs in ~1 min, no source builds. Corpus comes via **upload** (no Drive). Same",
        "honest measurement: base (LoRA-off) vs trained (LoRA-on) on held-out MBPP, **execution-verified**.",
        "",
        "Headline = `newly_solved` (held-out problems the trained model passes that base could not). Expect a",
        "small/null result and report `newly_solved`, `regressed`, and `n` together -- a prior 1.5B run showed",
        "zero lift, MBPP is likely in pretraining, id-disjoint != content-disjoint.",
    ),
    md("## 1. Install (fast -- no unsloth, no source builds)"),
    code(
        "!pip install -q -U peft bitsandbytes accelerate datasets 'transformers>=4.44'",
        "import torch",
        "print('CUDA available:', torch.cuda.is_available())  # must be True (Runtime>Change runtime type>T4)",
    ),
    md("## 2. Harness code + corpus (upload)"),
    code(
        "import os, sys",
        "!git clone --depth 1 https://github.com/issdandavis/SCBE-AETHERMOORE.git scbe || true",
        "sys.path.insert(0, '/content/scbe')",
        "CORPUS_PATH = '/content/vtc_mbpp_refined.jsonl'",
        "if not os.path.exists(CORPUS_PATH):",
        "    from google.colab import files  # the terminal driver feeds this input; or pick the file yourself",
        "    up = files.upload(); CORPUS_PATH = '/content/' + next(iter(up))",
        "os.environ['SCBE_VTC_CORPUS'] = CORPUS_PATH",
        "print('corpus:', CORPUS_PATH)",
    ),
    md("## 3. Config"),
    code(
        "BASE_MODEL = 'Qwen/Qwen2.5-Coder-1.5B-Instruct'",
        "OUT = '/content/vtc-fast-run'",
        "TRAIN_SFT = '/content/train.sft.jsonl'",
        "PUBLIC_K = 1",
        "EVAL_LIMIT = 60      # held-out problems to eval (more = better signal, slower)",
        "MAXLEN = 2048",
        "EPOCHS = 2",
        "MAX_NEW_TOKENS = 512",
    ),
    md("## 4. Honest split (train ids vs disjoint held-out MBPP)"),
    code(
        "from python.helm import public_bench as pb",
        "from python.helm.vtc_split import load_corpus, split_by_task_id, write_train_sft",
        "records = load_corpus(CORPUS_PATH)",
        "problems = pb.pull_mbpp()",
        "split = split_by_task_id(records, problems, public_k=PUBLIC_K)",
        "write_train_sft(split['train_records'], TRAIN_SFT)",
        "eval_problems = split['eval_problems'][:EVAL_LIMIT] if EVAL_LIMIT else split['eval_problems']",
        "assert not (split['train_ids'] & {p['task_id'] for p in eval_problems}), 'train/eval LEAK'",
        "print('train records:', len(split['train_records']), ' held-out eval:', len(eval_problems))",
    ),
    md("## 5. Load 4-bit model + LoRA adapter + generators"),
    code(
        "from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig",
        "from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training",
        "from python.helm.free_generator import strip_to_code",
        "",
        "bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',",
        "                        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)",
        "tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)",
        "if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token",
        "model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, quantization_config=bnb, device_map='auto')",
        "model = prepare_model_for_kbit_training(model)",
        "model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0,",
        "    target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],",
        "    bias='none', task_type='CAUSAL_LM'))",
        "model.print_trainable_parameters()",
        "",
        "def _gen(prompt):",
        "    ids = tokenizer.apply_chat_template([{'role':'user','content':prompt}], tokenize=True,",
        "             add_generation_prompt=True, return_tensors='pt').to(model.device)",
        "    out = model.generate(input_ids=ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,",
        "             pad_token_id=tokenizer.eos_token_id)",
        "    return tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True)",
        "",
        "def make_hf_generator():  # problem -> code",
        "    def gen(problem):",
        "        public = '\\n'.join(list(problem.get('test_list', []))[:PUBLIC_K])",
        "        prompt = ((problem.get('prompt') or problem.get('text') or '').strip()",
        "                  + '\\n\\nWrite a complete Python solution. It must make this example pass:\\n'",
        "                  + public + '\\nReturn ONLY the code.')",
        "        return strip_to_code(_gen(prompt))",
        "    return gen",
        "make_hf_ask = lambda: _gen  # prompt -> str, for the repair loop",
    ),
    md("## 6. Train (QLoRA SFT via transformers.Trainer -- no trl)"),
    code(
        "from datasets import load_dataset",
        "from transformers import Trainer, TrainingArguments, DataCollatorForLanguageModeling",
        "train_ds = load_dataset('json', data_files=TRAIN_SFT, split='train')",
        "def tok(ex):",
        "    text = tokenizer.apply_chat_template(ex['messages'], tokenize=False, add_generation_prompt=False)",
        "    return tokenizer(text, truncation=True, max_length=MAXLEN)",
        "train_tok = train_ds.map(tok, remove_columns=train_ds.column_names)",
        "args = TrainingArguments(output_dir=OUT, per_device_train_batch_size=2, gradient_accumulation_steps=8,",
        "    num_train_epochs=EPOCHS, learning_rate=2e-4, warmup_ratio=0.05, lr_scheduler_type='cosine',",
        "    logging_steps=10, bf16=True, optim='paged_adamw_8bit', report_to='none', save_strategy='no')",
        "Trainer(model=model, args=args, train_dataset=train_tok,",
        "        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False)).train()",
    ),
    md("## 7. Measure: base (LoRA-off) vs trained (LoRA-on), execution-verified"),
    code(
        "from python.helm.code_lift import solve_rate, lift_from_solve, render",
        "model.eval()",
        "gen = make_hf_generator()",
        "print('Evaluating BASE (adapter disabled)...')",
        "with model.disable_adapter():",
        "    base = solve_rate(eval_problems, gen, public_k=PUBLIC_K)",
        "print('Evaluating TRAINED (adapter enabled)...')",
        "trained = solve_rate(eval_problems, gen, public_k=PUBLIC_K)",
        "report = lift_from_solve(base, trained)",
        "print(); print(render(report)); print()",
        "print('newly solved ids:', sorted(report['newly_solved']))",
        "print('regressed ids   :', sorted(report['regressed']))",
    ),
    md(
        "## Notes",
        "- `NET LIFT` is the headline the terminal driver waits for. `newly_solved > 0` is the only thing that",
        "  shows capability lift; `net_lift <= 0` is a real result (clean verified data, no transfer here).",
        "- Determinism: `do_sample=False`, so base and trained are compared on identical greedy decoding.",
    ),
]


def build() -> dict:
    return {
        "cells": CELLS,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "accelerator": "GPU",
            "colab": {"provenance": [], "gpuType": "T4"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("vtc_lift_fast_colab.ipynb")
    out.write_text(json.dumps(build(), indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", out, "with", len(CELLS), "cells")
