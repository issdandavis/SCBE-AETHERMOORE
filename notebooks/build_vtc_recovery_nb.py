"""Builder for notebooks/vtc_recovery_colab.ipynb -- the RECOVERY-lift variant.

Single-shot solve-lift on the VTC corpus came out ~null (3B: NET LIFT -2). The thesis the corpus's
repair/manager traces actually target is RECOVERY: does training raise the rate of solving a held-out
problem only AFTER the first attempt failed? This notebook measures that via solve_rate_with_repair
(the write->run->got-vs-expected->fix loop) for base vs trained, execution-verified, and reports
recovery_lift + the single-shot NET LIFT. Small/1.5B because the loop is rounds x slower.
See python/helm/code_lift.py (solve_rate_with_repair, recovery_lift).

    python notebooks/build_vtc_recovery_nb.py
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
        "# VTC RECOVERY-Lift  -- qwen2.5-coder-1.5B, Colab T4",
        "",
        "The VTC thesis is not really 'does it solve more single-shot' (that was ~null) -- it's **does training on",
        "the verified REPAIR traces teach the model to RECOVER: solve a held-out problem only AFTER its first try",
        "failed?** This measures exactly that: base (LoRA-off) vs trained (LoRA-on) run through the",
        "write->run->got-vs-expected->fix LOOP on held-out MBPP, execution-verified, and reports the",
        "**RECOVERY LIFT** (the delta in solve-after-failure rate) alongside the single-shot NET LIFT.",
        "",
        "Small + 1.5B on purpose: the repair loop runs up to (rounds+1) generations per problem per side, so",
        "EVAL_LIMIT is 20. Standard `transformers.Trainer` + `peft` + `bitsandbytes` (no unsloth). Honest: expect",
        "a small/noisy number; report base/trained recovery rates and n together.",
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
        "BASE_MODEL = 'Qwen/Qwen2.5-Coder-1.5B-Instruct'  # 1.5B: faster -- the repair loop is rounds x slower",
        "OUT = '/content/vtc-recovery-run'",
        "TRAIN_SFT = '/content/train.sft.jsonl'",
        "PUBLIC_K = 1",
        "EVAL_LIMIT = 40      # the recovery RATE needs a real denominator (# solved); 20 gave only ~2 solves",
        "REPAIR_ROUNDS = 2    # write -> run -> fix, up to this many repair attempts (rounds x slower)",
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
        "import re",
        "from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig",
        "from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training",
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
        "def make_prompt(problem):",
        "    public = '\\n'.join(list(problem.get('test_list', []))[:PUBLIC_K])",
        "    return ((problem.get('prompt') or problem.get('text') or '').strip()",
        "            + '\\n\\nWrite a complete Python solution. It must make this example pass:\\n'",
        "            + public + '\\nReturn ONLY the code.')",
        "",
        "def extract_code(text):",
        "    # robust: largest fenced block; else drop leading prose to the first code line. Handles",
        "    # unclosed ``` (truncated gen) and bare code with no fences -- why base scored 0 before.",
        "    blocks = re.findall(r'```(?:python)?\\s*(.*?)```', text or '', re.S)",
        "    if blocks: return max(blocks, key=len).strip()",
        "    body = re.sub(r'^\\s*```(?:python)?\\s*', '', (text or '').strip())",
        "    lines = body.splitlines()",
        "    for i, ln in enumerate(lines):",
        "        if ln.lstrip().startswith(('def ', 'import ', 'from ', 'class ', '@')):",
        "            return '\\n'.join(lines[i:]).strip()",
        "    return body.strip()",
        "",
        "def _gen(prompt):",
        "    text = tokenizer.apply_chat_template([{'role':'user','content':prompt}], tokenize=False,",
        "             add_generation_prompt=True)",
        "    enc = tokenizer(text, return_tensors='pt').to(model.device)",
        "    out = model.generate(**enc, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,",
        "             pad_token_id=tokenizer.eos_token_id)",
        "    return tokenizer.decode(out[0][enc['input_ids'].shape[1]:], skip_special_tokens=True)",
        "",
        "make_hf_generator = lambda: (lambda problem: extract_code(_gen(make_prompt(problem))))",
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
    md("## 7. RECOVERY-lift: does training help it solve AFTER failing? (the VTC thesis)"),
    code(
        "from python.helm.code_lift import solve_rate_with_repair, recovery_lift, render",
        "from python.helm import public_bench as _pb",
        "model.eval()",
        "",
        "# DIAGNOSTIC: one base generation so a broken eval is visible (extracted code + does it pass public?)",
        "p0 = eval_problems[0]",
        "with model.disable_adapter():",
        "    code0 = extract_code(_gen(make_prompt(p0)))",
        "chk = _pb._verify(code0, p0['test_list'][:PUBLIC_K], [], p0.get('test_imports', []))",
        "print('--- diag task', p0['task_id'], '| public_passed:', chk['public_passed'], '---')",
        "print(code0[:200].replace(chr(10), ' | '))",
        "",
        "ask = make_hf_ask()  # prompt -> str; solve_rate_with_repair runs the write->run->repair LOOP",
        "print('Recovery eval BASE (adapter disabled)...')",
        "with model.disable_adapter():",
        "    base = solve_rate_with_repair(eval_problems, ask, public_k=PUBLIC_K, rounds=REPAIR_ROUNDS)",
        "print('Recovery eval TRAINED (adapter enabled)...')",
        "trained = solve_rate_with_repair(eval_problems, ask, public_k=PUBLIC_K, rounds=REPAIR_ROUNDS)",
        "report = recovery_lift(base, trained)",
        "print(); print(render(report)); print()",
        "print('base   : solved %d/%d, recovered %d (rate %.3f)' % "
        "(base['solved'], base['total'], base['recovered'], base['recovery_rate']))",
        "print('trained: solved %d/%d, recovered %d (rate %.3f)' % "
        "(trained['solved'], trained['total'], trained['recovered'], trained['recovery_rate']))",
    ),
    md(
        "## Notes",
        "- **RECOVERY LIFT** is the headline: did training raise the rate of solving ONLY AFTER a failed first",
        "  attempt? `solve_rate_with_repair` runs the write->run->got-vs-expected->fix loop (up to REPAIR_ROUNDS) --",
        "  this is the behavior VTC's manager/repair traces teach, which single-shot solve-lift cannot see.",
        "- `NET LIFT` (single-shot solve delta) is shown too; the terminal driver waits on it. Recovery is the",
        "  slower, thesis-relevant number. Determinism: `do_sample=False`.",
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
    out = Path(__file__).with_name("vtc_recovery_colab.ipynb")
    out.write_text(json.dumps(build(), indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", out, "with", len(CELLS), "cells")
