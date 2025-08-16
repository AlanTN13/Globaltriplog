from __future__ import annotations
import streamlit as st

# -------------------- Config --------------------
st.set_page_config(
    page_title="Ejemplo Productos",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------- Estilos --------------------
st.markdown("""
<style>
:root { color-scheme: light !important; }
html, body, .stApp, [data-testid="stAppViewContainer"],
section.main, [data-testid="stHeader"], [data-testid="stSidebar"]{ background:#FFF !important; color:#000033 !important; }

/* Quitar header/márgenes sup. */
:root{ --header-height:0px !important; }
[data-testid="stHeader"], [data-testid="stToolbar"]{ display:none !important; }
[data-testid="stAppViewContainer"]{ padding-top:0 !important; }
section.main{ padding-top:0 !important; }
section.main > div.block-container{ padding-top:.25rem !important; padding-bottom:1rem !important; }

/* Tarjetas */
.gt-card {
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    background: #fafafa;
}

/* Afinar margen entre caption y primera tarjeta */
.gt-section .stCaption + div .gt-card {
    margin-top: 4px !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------- UI --------------------
st.caption("Lista de productos")
with st.container():
    st.markdown('<div class="gt-card">Producto 1 - Descripción</div>', unsafe_allow_html=True)
    st.markdown('<div class="gt-card">Producto 2 - Descripción</div>', unsafe_allow_html=True)
    st.markdown('<div class="gt-card">Producto 3 - Descripción</div>', unsafe_allow_html=True)
