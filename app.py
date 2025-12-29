import streamlit as st
import pandas as pd

from agents.negotiation import run_multi_round_negotiation
from agents.arbiter import final_arbitration
from agents.scoring import score_negotiation

from parsing.dependencies import detect_clause_dependencies
from ui.graph import render_dependency_graph

from export.diff import redline_diff

import openai

st.set_page_config(layout="wide")
st.title("AI Contract & SoW Simulator")

openai.api_key = st.secrets["OPENAI_API_KEY"]

def llm_call(prompt, model):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "system", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content

# ======================
# SIDEBAR
# ======================
model = st.sidebar.selectbox("Model", ["gpt-4.1", "gpt-4.1-mini"])
rounds = st.sidebar.slider("Negotiation Rounds", 1, 5, 3)

buyer_objectives = st.sidebar.text_area(
    "Buyer Objectives",
    "Minimise liability; Clear acceptance; Strong remedies"
)

supplier_objectives = st.sidebar.text_area(
    "Supplier Objectives",
    "Cap liability; Flexibility; Limit remedies"
)

# ======================
# INPUT
# ======================
clause_text = st.text_area("Paste clause text")

if st.button("Run Analysis"):

    # --- Multi-round negotiation
    history = run_multi_round_negotiation(
        clause_text,
        buyer_objectives,
        supplier_objectives,
        lambda p: llm_call(p, model),
        rounds
    )

    st.subheader("Negotiation History")
    for h in history:
        st.markdown(f"### Round {h['round']}")
        st.markdown("**Supplier:**")
        st.write(h["supplier"])
        st.markdown("**Buyer:**")
        st.write(h["buyer"])

    # --- Arbitration
    arb_prompt = final_arbitration(history)
    final_clause = llm_call(arb_prompt, model)

    st.subheader("Final Arbiter Clause")
    st.success(final_clause)

    # --- Scoring
    score, reasons = score_negotiation(history, buyer_objectives)
    st.metric("Negotiation Strength Score", score)

    with st.expander("Score Explanation"):
        for r in reasons:
            st.write("-", r)

    # --- Redline export
    if st.button("Export Word Redline"):
        path = redline_diff(clause_text, final_clause)
        with open(path, "rb") as f:
            st.download_button(
                "Download Redline",
                f,
                file_name="AI_Redline.docx"
            )
