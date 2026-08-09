"""Tema visual institucional para la aplicación Streamlit de Grupo CEO."""
from __future__ import annotations

import streamlit as st


CEO_COLORS = {
    "navy": "#001D2C",
    "teal": "#008672",
    "green": "#0D3B2E",
    "lime": "#6DB16A",
    "ink": "#1A1A1A",
    "paper": "#F4FAF6",
    "soft": "#EAF3E8",
    "white": "#FFFFFF",
    "muted": "#667570",
}


def apply_ceo_theme() -> None:
    """Aplica tipografía, color y jerarquías del manual de estilo CEO."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

        :root {
            --ceo-navy: #001D2C;
            --ceo-teal: #008672;
            --ceo-green: #0D3B2E;
            --ceo-lime: #6DB16A;
            --ceo-ink: #1A1A1A;
            --ceo-paper: #F4FAF6;
            --ceo-soft: #EAF3E8;
            --ceo-white: #FFFFFF;
            --ceo-muted: #667570;
        }

        html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] * {
            font-family: "Source Sans 3", Arial, sans-serif !important;
        }
        [data-testid="stAppViewContainer"] {
            background: var(--ceo-paper) !important;
            color: var(--ceo-ink) !important;
        }
        h1, h2, h3, h4, h5, h6,
        [data-testid="stMetricValue"],
        [data-testid="stMetricLabel"],
        button, label, .stTabs [data-baseweb="tab"] {
            font-family: "Montserrat", Arial, sans-serif !important;
        }
        h1, h2 { color: var(--ceo-green) !important; letter-spacing: -0.02em !important; }
        h3, h4 { color: var(--ceo-teal) !important; }
        p, li, [data-testid="stCaptionContainer"] { line-height: 1.55 !important; }

        [data-testid="stSidebar"] {
            background: var(--ceo-navy) !important;
            border-right: 1px solid rgba(255,255,255,.08) !important;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div {
            color: var(--ceo-white) !important;
        }
        [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.18) !important; }

        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
            background: var(--ceo-teal) !important;
            border: 1px solid var(--ceo-teal) !important;
            color: var(--ceo-white) !important;
            border-radius: 8px !important;
            min-height: 42px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {
            background: var(--ceo-green) !important;
            border-color: var(--ceo-green) !important;
        }
        [data-testid="stSidebar"] .stButton > button {
            background: rgba(0,134,114,.88) !important;
            border-color: rgba(255,255,255,.18) !important;
        }

        [data-testid="stMetric"] {
            background: var(--ceo-white) !important;
            border: 1px solid #D7E8DF !important;
            border-top: 3px solid var(--ceo-teal) !important;
            border-radius: 10px !important;
            padding: 14px 16px !important;
            box-shadow: 0 4px 14px rgba(0,29,44,.05) !important;
        }
        [data-testid="stMetricValue"] { color: var(--ceo-green) !important; }
        [data-testid="stMetricLabel"] { color: var(--ceo-muted) !important; }

        [data-testid="stDataFrame"], [data-testid="stTable"],
        [data-testid="stForm"], [data-testid="stExpander"] {
            background: var(--ceo-white) !important;
            border: 1px solid #D7E8DF !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 14px rgba(0,29,44,.04) !important;
        }
        [data-testid="stForm"] { padding: 18px !important; }

        .stTabs [data-baseweb="tab-list"] { gap: 8px !important; }
        .stTabs [data-baseweb="tab"] {
            background: var(--ceo-soft) !important;
            border-radius: 8px 8px 0 0 !important;
            color: var(--ceo-green) !important;
            padding: 10px 16px !important;
        }
        .stTabs [aria-selected="true"] {
            background: var(--ceo-white) !important;
            border-bottom: 3px solid var(--ceo-teal) !important;
        }

        div[data-baseweb="select"] > div,
        .stTextInput input, .stTextArea textarea, .stNumberInput input {
            background: var(--ceo-white) !important;
            border-color: #BFD8CB !important;
            border-radius: 8px !important;
            color: var(--ceo-ink) !important;
        }

        .ceo-section-header {
            background: linear-gradient(120deg, #EAF3E8 0%, #D7EDE4 100%);
            border-left: 5px solid var(--ceo-teal);
            border-radius: 10px;
            padding: 18px 22px;
            margin: 4px 0 18px 0;
        }
        .ceo-section-header h2 { margin: 0 0 4px 0 !important; }
        .ceo-section-header p { margin: 0 !important; color: #49645A !important; }

        .ceo-candidate-card {
            background: var(--ceo-white);
            border: 1px solid #D7E8DF;
            border-left: 5px solid var(--ceo-teal);
            border-radius: 10px;
            padding: 18px 20px;
            margin: 10px 0 16px 0;
            box-shadow: 0 5px 16px rgba(0,29,44,.05);
        }
        .ceo-kicker {
            color: var(--ceo-teal);
            font-family: "Montserrat", Arial, sans-serif !important;
            font-size: .76rem;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .ceo-muted { color: var(--ceo-muted) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
