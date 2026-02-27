#!/usr/bin/env python3
"""Browser UI for AI Bridge."""

from __future__ import annotations

import streamlit as st

from ai_bridge import run_once, write_log


st.set_page_config(page_title="SCBE AI Bridge", layout="wide")
st.title("SCBE AI Bridge (Browser)")

provider = st.selectbox("Provider", ["hf", "vertex"])
default_model = "Qwen/Qwen2.5-7B-Instruct" if provider == "hf" else "gemini-2.5-flash"
model = st.text_input("Model", value=default_model)
vault = st.text_input("Obsidian Vault Path", value="C:/Users/issda/OneDrive/Documents/DOCCUMENTS/A follder")
prompt = st.text_area("Prompt", height=180)

if st.button("Run"):
    if not prompt.strip():
        st.warning("Prompt is empty")
    else:
        with st.spinner("Calling model..."):
            resp = run_once(provider, model, prompt)
        st.subheader("Response")
        st.write(resp)
        log = write_log(vault, provider, model, prompt, resp)
        st.caption(f"Logged to: {log}")
