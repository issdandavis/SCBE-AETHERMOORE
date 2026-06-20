"""Builder for notebooks/vtc_lift_qwen15_colab.ipynb.

A notebook is hard to review in a diff, so the source of truth is this script: run it to regenerate the
.ipynb. The notebook itself measures whether QLoRA fine-tuning on the VTC corpus produces capability
lift (base vs trained, execution-verified on held-out MBPP) -- see python/helm/code_lift.py + vtc_split.py.

    python notebooks/build_vtc_lift_nb.py
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
        "# VTC Capability-Lift Harness  (qwen2.5-coder-1.5B, free Colab T4)",
        "",
        "**The one question the VTC corpus has not yet answered:** does fine-tuning on the execution-verified",
        "trajectories actually make a model *more capable* -- not just produce clean training data?",
        "",
        "This notebook measures it honestly:",
        "1. **Split** the corpus by MBPP `task_id`; eval ONLY on problems whose id is NOT in training (disjoint).",
        "2. **QLoRA fine-tune** `Qwen/Qwen2.5-Coder-1.5B-Instruct` on the verified trajectories.",
        "3. **Eval base vs trained** on held-out problems, *execution-verified* against hidden tests",
        "   (LoRA-off vs LoRA-on on the SAME model, so the delta is the adapter, not prompt drift).",
        "",
        "**Headline number = `newly_solved`:** held-out problems the TRAINED model passes that the BASE could not.",
        "",
        "### Honest caveats (read before believing any number)",
        "- MBPP is on GitHub and almost certainly in Qwen's pretraining; a 'solve' may be memorization, and the corpus",
        "  was harvested FROM MBPP, so `newly_solved` upper-bounds novel capability -- it is not proof.",
        "- A prior real 1.5B run here showed **zero** capability lift while verification never lied. Expect a small",
        "  or null result and report it honestly -- a 1-2 problem swing on a small eval is within noise.",
        "- `regressed` (base solved, trained broke) is always shown; net lift is never just the positive.",
        "- Eval runs model-generated code in a subprocess -- fine on a throwaway Colab VM, not for untrusted output.",
    ),
    md("## 1. Install (unsloth brings peft/trl/bitsandbytes)"),
    code(
        '!pip install -q "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"',
        '!pip install -q --no-deps "trl<0.9.0" peft accelerate bitsandbytes',
    ),
    md(
        "## 2. Get the harness code + the corpus",
        "`python/helm` (vtc_split, code_lift, public_bench, free_generator) comes from the repo. The corpus",
        "`vtc_mbpp_refined.jsonl` is training data (not committed) -- upload it, or set `CORPUS_PATH` to a Drive path.",
    ),
    code(
        "import os, sys",
        "!git clone --depth 1 https://github.com/issdandavis/SCBE-AETHERMOORE.git scbe || true",
        "sys.path.insert(0, '/content/scbe')",
        "",
        "CORPUS_PATH = '/content/vtc_mbpp_refined.jsonl'  # <- or point at a Drive path",
        "if not os.path.exists(CORPUS_PATH):",
        "    try:",
        "        from google.colab import files",
        "        print('Upload vtc_mbpp_refined.jsonl (the verified-trajectory corpus):')",
        "        up = files.upload()",
        "        CORPUS_PATH = '/content/' + next(iter(up))",
        "    except Exception as e:",
        "        raise SystemExit('No corpus: upload vtc_mbpp_refined.jsonl or set CORPUS_PATH. (%s)' % e)",
        "os.environ['SCBE_VTC_CORPUS'] = CORPUS_PATH",
        "print('corpus:', CORPUS_PATH)",
    ),
    md("## 3. Config (1.5B fits a free T4 comfortably; 7B OOMs)"),
    code(
        "BASE_MODEL   = 'Qwen/Qwen2.5-Coder-1.5B-Instruct'  # corpus models were 1.5b/3b; 1.5B = safe free-T4 pick",
        "OUTPUT_DIR   = '/content/vtc-lift-run'",
        "TRAIN_SFT    = '/content/train.sft.jsonl'",
        "PUBLIC_K     = 1        # asserts the model sees; the rest are HIDDEN at eval time",
        "EVAL_LIMIT   = 80       # held-out problems to eval (more = better signal, slower). None = all ~266",
        "MAX_SEQ_LENGTH = 2048",
        "LORA_RANK, LORA_ALPHA = 16, 32",
        "LEARNING_RATE, NUM_EPOCHS = 2e-4, 2",
        "BATCH_SIZE, GRAD_ACCUM = 2, 8",
        "MAX_NEW_TOKENS = 512",
    ),
    md("## 4. Honest split: train ids vs disjoint held-out MBPP"),
    code(
        "from python.helm import public_bench as pb",
        "from python.helm.vtc_split import load_corpus, split_by_task_id, write_train_sft",
        "",
        "records  = load_corpus(CORPUS_PATH)",
        "problems = pb.pull_mbpp()  # full MBPP-sanitized (427); cached after first pull",
        "split = split_by_task_id(records, problems, public_k=PUBLIC_K)",
        "write_train_sft(split['train_records'], TRAIN_SFT)",
        "",
        "eval_problems = split['eval_problems']",
        "if EVAL_LIMIT:",
        "    eval_problems = eval_problems[:EVAL_LIMIT]",
        "assert not (split['train_ids'] & {p['task_id'] for p in eval_problems}), 'train/eval LEAK'",
        "print('train records :', len(split['train_records']))",
        "print('held-out eval :', len(eval_problems), '(of', len(split['eval_problems']), 'disjoint problems)')",
    ),
    md("## 5. Load base model + QLoRA adapter + the in-process generator"),
    code(
        "from unsloth import FastLanguageModel",
        "from python.helm.free_generator import strip_to_code",
        "",
        "model, tokenizer = FastLanguageModel.from_pretrained(",
        "    model_name=BASE_MODEL, max_seq_length=MAX_SEQ_LENGTH, dtype=None, load_in_4bit=True)",
        "model = FastLanguageModel.get_peft_model(",
        "    model, r=LORA_RANK, lora_alpha=LORA_ALPHA, lora_dropout=0,",
        "    target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],",
        "    bias='none', use_gradient_checkpointing='unsloth', random_state=42)",
        "",
        "def make_hf_generator(model, tokenizer, public_k=1, max_new_tokens=512):",
        '    """problem -> code, mirroring free_generator\'s prompt but calling the in-process checkpoint."""',
        "    def gen(problem):",
        "        public = '\\n'.join(list(problem.get('test_list', []))[:public_k])",
        "        prompt = ((problem.get('prompt') or problem.get('text') or '').strip()",
        "                  + '\\n\\nWrite a complete Python solution. It must make this example pass:\\n'",
        "                  + public + '\\nReturn ONLY the code.')",
        "        ids = tokenizer.apply_chat_template([{'role':'user','content':prompt}],",
        "                  tokenize=True, add_generation_prompt=True, return_tensors='pt').to(model.device)",
        "        out = model.generate(input_ids=ids, max_new_tokens=max_new_tokens, do_sample=False,",
        "                             pad_token_id=tokenizer.eos_token_id)",
        "        return strip_to_code(tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True))",
        "    return gen",
    ),
    md("## 6. Train (QLoRA SFT on the verified trajectories)"),
    code(
        "from datasets import load_dataset",
        "from transformers import TrainingArguments",
        "from trl import SFTTrainer",
        "",
        "train_ds = load_dataset('json', data_files=TRAIN_SFT, split='train')",
        "def convert(ex):",
        "    out = tokenizer.apply_chat_template(ex['messages'], tokenize=False, add_generation_prompt=False)",
        "    return {'text': out}",
        "train_ds = train_ds.map(convert, remove_columns=train_ds.column_names)",
        "print('train rows:', len(train_ds))",
        "",
        "trainer = SFTTrainer(",
        "    model=model, tokenizer=tokenizer, train_dataset=train_ds,",
        "    dataset_text_field='text', max_seq_length=MAX_SEQ_LENGTH, packing=True,",
        "    args=TrainingArguments(",
        "        output_dir=OUTPUT_DIR, report_to='none', num_train_epochs=NUM_EPOCHS,",
        "        per_device_train_batch_size=BATCH_SIZE, gradient_accumulation_steps=GRAD_ACCUM,",
        "        warmup_ratio=0.05, learning_rate=LEARNING_RATE, optim='adamw_8bit',",
        "        weight_decay=0.01, lr_scheduler_type='cosine', logging_steps=10, seed=42))",
        "trainer.train()",
        "model.save_pretrained(OUTPUT_DIR + '/lora'); tokenizer.save_pretrained(OUTPUT_DIR + '/lora')",
    ),
    md("## 7. The measurement: base (LoRA-off) vs trained (LoRA-on), execution-verified"),
    code(
        "from python.helm.code_lift import solve_rate, lift_from_solve, render",
        "FastLanguageModel.for_inference(model)",
        "gen = make_hf_generator(model, tokenizer, public_k=PUBLIC_K, max_new_tokens=MAX_NEW_TOKENS)",
        "",
        "print('Evaluating BASE (adapter disabled) over', len(eval_problems), 'held-out problems...')",
        "with model.disable_adapter():",
        "    base = solve_rate(eval_problems, gen, public_k=PUBLIC_K)",
        "print('Evaluating TRAINED (adapter enabled)...')",
        "trained = solve_rate(eval_problems, gen, public_k=PUBLIC_K)",
        "",
        "report = lift_from_solve(base, trained)",
        "print(); print(render(report)); print()",
        "print('newly solved ids:', sorted(report['newly_solved']))",
        "print('regressed ids   :', sorted(report['regressed']))",
    ),
    md(
        "## Notes (hold the honest line)",
        "- `newly_solved > 0` is the only thing that shows capability lift -- and even then, see the memorization",
        "  caveat above: id-disjoint != content-disjoint. Report the number, the `regressed` set, and `n` together.",
        "- If `net_lift <= 0`, that is a real, publishable result: the corpus produces clean verified data but this",
        "  fine-tune did not raise held-out capability. The verifier not lying is itself the contribution.",
        "- To strengthen signal: raise `EVAL_LIMIT` to all ~266, train more epochs, or try the 3B base on a paid GPU.",
        "- Determinism: `do_sample=False` so base and trained are compared on identical greedy decoding.",
    ),
]


def build() -> dict:
    return {
        "cells": CELLS,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "accelerator": "GPU",
            "colab": {"provenance": []},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("vtc_lift_qwen15_colab.ipynb")
    out.write_text(json.dumps(build(), indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", out, "with", len(CELLS), "cells")
