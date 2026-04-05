# Gradio
> Source: Context7 MCP | Category: code
> Fetched: 2026-04-04

### Understanding the `Interface` Class

Source: https://github.com/gradio-app/gradio/blob/main/guides/01_getting-started/01_quickstart.md

The `Interface` class is designed to create demos for machine learning models which accept one or more inputs, and return one or more outputs. It has three core arguments:

- `fn` — the function to wrap a user interface around
- `inputs` — the Gradio component(s) to use for the input
- `outputs` — the Gradio component(s) to use for the output

The `fn` argument is very flexible -- you can pass any Python function that you want to wrap with a UI. Gradio includes more than 30 built-in components (such as `gr.Textbox()`, `gr.Image()`, and `gr.HTML()`) that are designed for machine learning applications.

For the `inputs` and `outputs` arguments, you can pass in the name of components as a string (`"textbox"`) or an instance of the class (`gr.Textbox()`).

---

### Create Hello World Interface

Source: https://github.com/gradio-app/gradio/blob/main/demo/hello_world/run.ipynb

```python
import gradio as gr


def greet(name):
    return "Hello " + name + "!"


demo = gr.Interface(fn=greet, inputs="textbox", outputs="textbox", api_name="predict")

if __name__ == "__main__":
    demo.launch()
```

---

### NER Demo using Tuples

Source: https://github.com/gradio-app/gradio/blob/main/guides/11_other-tutorials/named-entity-recognition.md

Illustrates building a Gradio interface for an NER model that outputs data as a list of tuples, handled by Gradio's `HighlightedText` component.

```python
import gradio as gr

def spacy_ner(text):
    return [('This', 'DET'), ('is', 'VERB'), ('an', 'DET'), ('example', 'NOUN'), ('sentence', 'NOUN'), ('.', None)]

app = gr.Interface(fn=spacy_ner, inputs="text", outputs=gr.HighlightedText())
app.launch()
```

---

### Full-Context ASR Demo

Source: https://github.com/gradio-app/gradio/blob/main/guides/07_streaming/05_real-time-speech-recognition.md

Builds a Gradio interface for an ASR model. Takes audio input from the user's microphone and outputs transcribed text.

```python
import gradio as gr
import numpy as np

def transcribe(audio):
    if audio is None:
        return ""
    audio_float32 = audio.astype(np.float32)
    return p(audio_float32)['text']

input_audio = gr.Audio(source="microphone", type="numpy")
output_text = gr.Textbox(label="Transcription")

interface = gr.Interface(fn=transcribe, inputs=input_audio, outputs=output_text)
```

---

### Translation Interface

Source: https://github.com/gradio-app/gradio/blob/main/demo/translation/run.ipynb

Initializes the NLLB-200 sequence-to-sequence model and creates a Gradio interface for translation.

```python
import gradio as gr
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import torch

model = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M")
tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
device = 0 if torch.cuda.is_available() else -1
LANGS = ["ace_Arab", "eng_Latn", "fra_Latn", "spa_Latn"]

def translate(text, src_lang, tgt_lang):
    translation_pipeline = pipeline("translation", model=model, tokenizer=tokenizer,
                                     src_lang=src_lang, tgt_lang=tgt_lang,
                                     max_length=400, device=device)
    result = translation_pipeline(text)
    return result[0]['translation_text']

demo = gr.Interface(
    fn=translate,
    inputs=[
        gr.components.Textbox(label="Text"),
        gr.components.Dropdown(label="Source Language", choices=LANGS),
        gr.components.Dropdown(label="Target Language", choices=LANGS),
    ],
    outputs=["text"],
    examples=[["Building a translation demo with Gradio is so easy!", "eng_Latn", "spa_Latn"]],
    cache_examples=False,
    title="Translation Demo",
    description="Simplified version of the NLLB-Translator space",
    api_name="predict"
)

demo.launch()
```
