#!/usr/bin/env python3
"""Build a Colab notebook for the agentic-operator coding specialty.

This writes a notebook only. It does not execute training.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FILES = [
    "t_operator_v1.sft.jsonl",
    "eml_operator_v1.sft.jsonl",
    "operator_agent_bus_extracted_v1_train.sft.jsonl",
    "command_lattice_seed_train.sft.jsonl",
    "geoseal_command_recall_v1.sft.jsonl",
    "geoseal_command_harmony_v1.sft.jsonl",
    "honeycomb_choice_achievement_v1.sft.jsonl",
    "multirep_choice_matrix_v1.sft.jsonl",
]


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def md_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def build_notebook() -> dict:
    files_json = json.dumps(FILES, indent=2)
    return {
        "cells": [
            md_cell(
                "# SCBE Agentic-Operator Coding Specialty\n\n"
                "Purpose: train a narrow LoRA adapter for operator movement, command recall, T/EML reasoning, "
                "GeoSeal command harmony, honeycomb choice scripts, and multi-representation choice objects.\n\n"
                "This notebook is generated locally and should be reviewed before running."
            ),
            code_cell(
                "!pip install -q transformers>=4.49 peft>=0.14 trl>=0.19 bitsandbytes>=0.45 accelerate>=1.3 datasets>=3.3 huggingface_hub"
            ),
            code_cell(
                "from huggingface_hub import login\n"
                "from google.colab import userdata\n"
                "token = userdata.get('HF_TOKEN')\n"
                "assert token, 'Add HF_TOKEN to Colab secrets first'\n"
                "login(token=token)\n"
            ),
            code_cell(
                "import json, random, torch\n"
                "from pathlib import Path\n"
                "from datasets import Dataset, load_dataset\n"
                "from huggingface_hub import hf_hub_download\n"
                "from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig\n"
                "from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training\n"
                "from trl import SFTConfig, SFTTrainer\n\n"
                "BASE_MODEL = 'Qwen/Qwen2.5-Coder-0.5B-Instruct'\n"
                "HF_DATASET_REPO = 'issdandavis/scbe-coding-agent-sft-stage6-repair-v7'\n"
                "HF_REPO = 'issdandavis/scbe-agentic-operator-coder-qwen-colab-v1'\n"
                f"FILES = {files_json}\n"
                "MAX_RECORDS = 1800\n"
                "MAX_STEPS = 180\n"
                "MAX_LEN = 768\n"
            ),
            code_cell(
                "records = []\n"
                "for name in FILES:\n"
                "    path = Path(hf_hub_download(repo_id=HF_DATASET_REPO, filename=name, repo_type='dataset', token=token))\n"
                "    ds = load_dataset('json', data_files=str(path), split='train')\n"
                "    count = 0\n"
                "    cols = ds.column_names\n"
                "    for row in ds:\n"
                "        rec = None\n"
                "        if 'messages' in cols and row.get('messages'):\n"
                "            rec = {'messages': row['messages']}\n"
                "        elif 'instruction' in cols:\n"
                "            u = row.get('instruction', '')\n"
                "            a = row.get('response') or row.get('output') or row.get('positive', '')\n"
                "            if u and a:\n"
                "                rec = {'messages': [{'role': 'user', 'content': u}, {'role': 'assistant', 'content': a}]}\n"
                "        if rec:\n"
                "            records.append(rec); count += 1\n"
                "    print('LOAD', name, count)\n"
                "random.seed(42)\n"
                "if len(records) > MAX_RECORDS:\n"
                "    records = random.sample(records, MAX_RECORDS)\n"
                "print('records', len(records))\n"
            ),
            code_cell(
                "tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True, token=token)\n"
                "if tokenizer.pad_token is None:\n"
                "    tokenizer.pad_token = tokenizer.eos_token\n"
                "bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)\n"
                "model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, quantization_config=bnb, device_map='auto', token=token)\n"
                "model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)\n"
                "model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias='none', task_type='CAUSAL_LM', target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj']))\n"
                "model.print_trainable_parameters()\n"
            ),
            code_cell(
                "dataset = Dataset.from_list(records)\n"
                "trainer = SFTTrainer(\n"
                "    model=model,\n"
                "    processing_class=tokenizer,\n"
                "    train_dataset=dataset,\n"
                "    args=SFTConfig(\n"
                "        output_dir='/content/scbe-agentic-operator-coder', hub_model_id=HF_REPO, push_to_hub=True,\n"
                "        learning_rate=6e-5, per_device_train_batch_size=1, gradient_accumulation_steps=16,\n"
                "        num_train_epochs=1, max_steps=MAX_STEPS, warmup_ratio=0.03, weight_decay=0.01,\n"
                "        max_grad_norm=0.3, lr_scheduler_type='cosine', logging_steps=10, save_strategy='steps',\n"
                "        save_steps=60, save_total_limit=2, max_length=MAX_LEN, packing=False, dataset_num_proc=1,\n"
                "        report_to='none', fp16=True, optim='adamw_torch', gradient_checkpointing=True,\n"
                "        gradient_checkpointing_kwargs={'use_reentrant': False},\n"
                "    ),\n"
                ")\n"
                "trainer.train()\n"
                "trainer.save_model()\n"
                "trainer.push_to_hub()\n"
            ),
        ],
        "metadata": {
            "accelerator": "GPU",
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="artifacts/colab/operator_agentic_coder_specialty_v1.ipynb")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_notebook(), indent=2), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
