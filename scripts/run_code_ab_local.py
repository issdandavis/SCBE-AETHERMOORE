#!/usr/bin/env python3
"""Run the code A/B comparison LOCALLY on CPU. No Kaggle. No Colab. Just works."""
import json, os, time, random, sys
sys.stdout.reconfigure(encoding='utf-8')
random.seed(42)

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer

BASE_MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
MAX_STEPS = 50  # Fast comparison

print('='*60)
print('CODE A/B TEST (LOCAL CPU)')
print(f'Model: {BASE_MODEL}')
print(f'Steps: {MAX_STEPS}')
print(f'PyTorch: {torch.__version__}')
print('='*60)

def load_local(path):
    records = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.strip(): continue
            try:
                rec = json.loads(line)
                msgs = rec.get('messages', [])
                if len(msgs) >= 2:
                    parts = []
                    for m in msgs:
                        r = m.get('role', '')
                        c = m.get('content', '')
                        if r and c:
                            parts.append(f'<|im_start|>{r}\n{c}<|im_end|>')
                    if parts:
                        t = '\n'.join(parts)
                        if len(t) > 50:
                            records.append({'text': t})
            except: continue
    print(f'{os.path.basename(path)}: {len(records)} samples')
    return Dataset.from_list(records[:3000])

def train(dataset, name):
    print(f'\nTraining {name}...')
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    tok.pad_token = tok.eos_token
    tok.padding_side = 'right'
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, torch_dtype=torch.float32, trust_remote_code=True)
    lora = LoraConfig(r=4, lora_alpha=8, lora_dropout=0.05, bias='none', task_type='CAUSAL_LM', target_modules=['q_proj', 'v_proj'])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    def tok_fn(ex):
        return tok(ex['text'], truncation=True, max_length=256, padding='max_length')

    ds = dataset.map(tok_fn, batched=True, remove_columns=['text'])
    ds = ds.map(lambda x: {'labels': x['input_ids'].copy()}, batched=True)

    args = TrainingArguments(
        output_dir=f'./output/{name}', num_train_epochs=1,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=2e-4, weight_decay=0.01, lr_scheduler_type='cosine',
        logging_steps=10, save_strategy='no', max_grad_norm=0.3,
        report_to='none', max_steps=MAX_STEPS,
    )
    trainer = Trainer(model=model, args=args, train_dataset=ds)
    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0

    loss = 'unknown'
    for e in reversed(trainer.state.log_history):
        if 'loss' in e:
            loss = round(e['loss'], 4)
            break

    del model, trainer
    print(f'{name}: {elapsed:.0f}s, loss={loss}')
    return elapsed, loss

# Load local data
a_data = load_local('training-data/code_baseline_l3.jsonl')
b_data = load_local('training-data/code_full_multiview.jsonl')

# Train both
a_time, a_loss = train(a_data, 'baseline')
b_time, b_loss = train(b_data, 'triangulated')

# Results
print(f'\n{"="*60}')
print('RESULTS')
print(f'{"="*60}')
print(f'Baseline (L3):       loss={a_loss} ({a_time:.0f}s)')
print(f'Triangulated (L0-3): loss={b_loss} ({b_time:.0f}s)')
try:
    d = float(b_loss) - float(a_loss)
    pct = abs(d) / float(a_loss) * 100
    print(f'Delta: {d:+.4f} ({pct:.1f}%)')
    if d < 0: print('TRIANGULATED WINS')
    else: print('BASELINE WINS')
except: pass

# Save results
results = {
    'experiment': 'Code A/B local CPU',
    'model': BASE_MODEL,
    'max_steps': MAX_STEPS,
    'baseline': {'loss': a_loss, 'time': a_time},
    'triangulated': {'loss': b_loss, 'time': b_time},
}
with open('artifacts/code_ab_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f'\nSaved to artifacts/code_ab_results.json')
