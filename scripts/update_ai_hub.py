#!/usr/bin/env python3
"""Update the SCBE-AETHERMOORE AI Hub Space with latest training data reference.

This creates a Gradio app that serves as the AI's home - a living reference
for lore, systems, relationships, timelines, and technical architecture.
Any AI can query this space to get grounded in the SCBE-AETHERMOORE universe.
"""
import os
import json
import argparse
from huggingface_hub import HfApi, login

GRADIO_APP = '''
import gradio as gr
from datasets import load_dataset
import json

DATASET_ID = "{dataset_id}"

def load_training_data():
    """Load the training dataset from HF."""
    try:
        ds = load_dataset(DATASET_ID, split="train")
        return ds
    except Exception:
        return None

def search_knowledge(query, category="all"):
    """Search the SCBE-AETHERMOORE knowledge base."""
    ds = load_training_data()
    if ds is None:
        return "Dataset not yet populated. Run the Notion export pipeline first."
    results = []
    query_lower = query.lower()
    for record in ds:
        title = record.get("title", "").lower()
        text = record.get("text", "").lower()
        cats = record.get("categories", [])
        if category != "all" and category not in cats:
            continue
        if query_lower in title or query_lower in text:
            results.append(f"### {{record.get(\\"title\\", \\"Untitled\\")}}\\n"
                          f"**Categories**: {{\\", \\".join(cats)}}\\n\\n"
                          f"{{record.get(\\"text\\", \\"\\")[:500]}}...")
    if not results:
        return f"No results found for \\"{{query}}\\" in category \\"{{category}}\\"."
    return "\\n\\n---\\n\\n".join(results[:10])

def get_stats():
    """Get dataset statistics."""
    ds = load_training_data()
    if ds is None:
        return "Dataset not yet populated."
    total = len(ds)
    cats = {{}}
    for record in ds:
        for cat in record.get("categories", []):
            cats[cat] = cats.get(cat, 0) + 1
    stats = f"Total records: {{total}}\\n\\nCategory breakdown:\\n"
    for cat, count in sorted(cats.items()):
        stats += f"  - {{cat}}: {{count}}\\n"
    return stats

with gr.Blocks(title="SCBE-AETHERMOORE AI Hub", theme=gr.themes.Soft()) as app:
    gr.Markdown("""# SCBE-AETHERMOORE AI Hub
    ### The Living Reference for AI Training & Knowledge
    
    This is the central knowledge base for the SCBE-AETHERMOORE universe.
    AI agents can query here for lore, technical systems, relationship
    dynamics, timelines, and architectural references.
    """)
    
    with gr.Tab("Search Knowledge"):
        query_input = gr.Textbox(label="Search Query", placeholder="e.g. Sacred Tongue, fleet coordination, Polly...")
        category_input = gr.Dropdown(
            choices=["all", "technical", "lore", "relationships", "timelines", "general"],
            value="all", label="Category Filter"
        )
        search_btn = gr.Button("Search", variant="primary")
        results_output = gr.Markdown(label="Results")
        search_btn.click(search_knowledge, inputs=[query_input, category_input], outputs=results_output)
    
    with gr.Tab("Dataset Stats"):
        stats_btn = gr.Button("Load Stats")
        stats_output = gr.Markdown()
        stats_btn.click(get_stats, outputs=stats_output)
    
    gr.Markdown(f"""---
    *Connected to dataset: [{dataset_id}](https://huggingface.co/datasets/{dataset_id})*
    *Powered by the Notion-to-Dataset Pipeline*
    """)

app.launch()
'''

REQUIREMENTS = """gradio>=4.0
datasets
huggingface-hub
"""


def main():
    parser = argparse.ArgumentParser(description='Update AI Hub Space')
    parser.add_argument('--dataset', required=True, help='HF dataset repo id')
    parser.add_argument('--space', required=True, help='HF space repo id')
    args = parser.parse_args()

    token = os.environ.get('HF_TOKEN')
    if not token:
        raise ValueError('HF_TOKEN environment variable required')

    login(token=token)
    api = HfApi()

    # Generate app.py with dataset reference
    app_code = GRADIO_APP.format(dataset_id=args.dataset)

    print(f'Updating Space {args.space} with dataset reference {args.dataset}...')

    # Upload app.py
    api.upload_file(
        path_or_fileobj=app_code.encode(),
        path_in_repo='app.py',
        repo_id=args.space,
        repo_type='space',
        commit_message=f'Update AI Hub with latest dataset reference'
    )

    # Upload requirements.txt
    api.upload_file(
        path_or_fileobj=REQUIREMENTS.encode(),
        path_in_repo='requirements.txt',
        repo_id=args.space,
        repo_type='space',
        commit_message='Update requirements'
    )

    print(f'AI Hub Space updated: https://huggingface.co/spaces/{args.space}')


if __name__ == '__main__':
    main()
