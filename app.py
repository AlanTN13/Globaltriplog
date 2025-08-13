# app.py
from __future__ import annotations
import os, json, math, time, requests
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# -------------------- Config --------------------
st.set_page_config(page_title="Cotizador GlobalTrip", page_icon="📦", layout="wide")

# -------------------- Styles (TODO texto #000033) --------------------
st.markdown("""
<style>
:root{
  --brand: #000033;          /* color pedido */
  --brand-soft: #eaf1ff;
  --soft-bg: #f4f9fb;
  --soft-card: #ffffff;
  --soft-border: #dfe7ef;
  --soft-text: #000033;      /* todo texto oscuro = #000033 */
  --soft-muted: #000033;
  --soft-focus: rgba(0, 0, 51, .2);
}
html, body, [data-testid="stAppViewContainer"] { background: var(--soft-bg) !important; }

/* Ocultar toolbar/menú */
header, div[data-testid="stToolbar"]{ display:none !important; }

/* ======== Forzar que TODO texto sea #000033 ======== */
body, [data-testid="stAppViewContainer"]{
  color: var(--brand) !important;
}
body, [data-testid="stAppViewContainer"] p, span, label, div, li,
h1, h2, h3, h4, h5, h6, a, small, strong, em, th, td,
div[data-testid="stMarkdownContainer"] * {
  color: var(--brand) !important;
}

/* Card del hero */
.soft-card{
  background: var(--soft-card);
  border: 1.5px solid var(--soft-border);
  border-radius: 16px;
  padding: 18px 20px;
  box-shadow: 0 8px 18px rgba(17,24,39,.07);
}

/* Titulares, labels, captions (igualmente ya forzados arriba) */
div[data-testid="stMetricLabel"],
div[data-testid="stCaptionContainer"],
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] label,
div[data-testid="stRadio"] label,
section[aria-label] > div > label,
div[data-baseweb="textarea"] label {
  color: var(--brand) !important;
}

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea{
  background:#fff !important;
  border:1.5px solid var(--soft-border) !important;
  border-radius:16px !important;
  color:var(--brand) !important;
  padding:14px 16px !important;
  box-shadow:0 6px 16px rgba(17,24,39,0.06),
             0 1px 0 rgba(255,255,255,0.55) inset !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus{
  outline:none !important;
  border-color: var(--brand) !important;
  box-shadow:0 0 0 3px var(--soft-focus),
             0 6px 16px rgba(17,24,39,0.06) !important;
}
/* Placeholder exactamente #000033 */
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stNumberInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder{
  color:#000033 !important;
  opacity:1 !important;
}

/* Radio chips */
div[data-testid="stRadio"] label{
  background:#fff;
  border:1.5px solid var(--soft-border);
  border-radius:14px;
  padding:8px 12px;
  margin-right:8px;
  color:var(--brand) !important;
  box-shadow:0 4px 12px rgba(17,24,39,0.05);
}

/* Métricas: valores también en #000033 */
div[data-testid="stMetric"]{
  background:#fff; border:1.5px solid var(--soft-border);
  border-radius:16px; padding:18px 20px;
  box-shadow:0 8px 18px rgba(17,24,39,.07);
}
div[data-testid="stMetricValue"]{ color: var(--brand) !important; }

/* Botón (texto #000033) */
div.stButton > button{
  border:1.5px solid var(--soft-border) !important;
  border-radius:16px !important;
  background:#ffffff !important;
  color:#000033 !important;
  padding:14px 18px !important;
  box-shadow:0 10px 22px rgba(17,24,39,.09) !important;
}
div.stButton > button:hover{
  border-color:#c7d4e2 !important;
  box-shadow:0 12px 26px rgba(17,24,39,.12) !important;
}

/* Data editor claro + texto #000033 */
[data-testid="stDataFrame"]{
  background:#fff !important;
  border:1.5px solid var(--soft-border) !important;
  border-radius:16px !important;
  box-shadow:0 8px 18px rgba(17,24,39,.07) !important;
  overflow:hidden;
}
[data-testid="stDataFrame"] div[role="grid"]{ background:#fff !important; }
[data-testid="stDataFrame"] div[role="columnheader"]{
  background: var(--brand-soft) !important;
  color: var(--brand) !important;
  border-bottom:1px solid var(--soft-border) !important;
}
[data-testid="stDataFrame"] div[role="cell"]{
  background:#fff !important;
  color: var(--brand) !important;
  border-color: var(--soft-border) !important;
}
[data-testid="stDataFrame"] *::selection{ background: var(--soft-focus) !important; }
/* achicar padding filas */
[data-testid="stDataFrame"] .st-emotion-cache-1xarl3l { padding: 6px 10px !important; }
</style>
""", unsafe_allow_html=True)

# -------------------- Constantes --------------------
FACTOR_VOL = 5000   # cm->kg
DEFAULT_ROWS = 10

# -------------------- Helpers --------------------
def init_state():
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame({
            "Cantidad de bultos": [0]*DEFAULT_ROWS,
            "Ancho (cm)": [0]*DEFAULT_ROWS,
            "Alto (cm)": [0]*DEFAULT_ROWS,
            "Largo (cm)": [0]*DEFAULT_ROWS,
            "Peso vol. (kg)": [0.00]*DEFAULT_ROWS,
        })
    for k, v in {
        "nombre":"", "email":"", "telefono":"",
        "es_cliente":"No", "descripcion":"", "link":"",
        "peso_bruto":0.0, "valor_mercaderia":0.0,
        "last_submit_ok":False, "show_dialog":False
    }.items():
        st.session_state.setdefault(k, v)

def compute_vol(df: pd.DataFrame):
    calc = df[["Cantidad de bultos","Ancho (cm)","Alto (cm)","Largo (cm)"]].fillna(0).astype(float)
    per_row = (calc["Cantidad de bultos"] * calc["Ancho (cm)"] * calc["Alto (cm)"] * calc["Largo (cm)"]) / FACTOR_VOL
    per_row = per_row.replace([np.inf,-np.inf],0).fillna(0).round(2)
    out = df.copy()
    out["Peso vol. (kg)"] = per_row
    total = float(per_row.sum().round(2))
    return out, total

def reset_form():
    st.session_state.nombre = ""
    st.session_state.email = ""
    st.session_state.telefono = ""
    st.session_state.es_cliente = "No"
    st.session_state.descripcion = ""
    st.session_state.link = ""
    st.session_state.peso_bruto = 0.0
    st.session_state.valor_mercaderia = 0.0
    st.session_state.df = pd.DataFrame({
        "Cantidad de bultos": [0]*DEFAULT_ROWS,
        "Ancho (cm)": [0]*DEFAULT_ROWS,
        "Alto (cm)": [0]*DEFAULT_ROWS,
        "Largo (cm)": [0]*DEFAULT_ROWS,
        "Peso vol. (kg)": [0.00]*DEFAULT_ROWS,
    })

def post_to_webhook(payload: dict):
    url = st.secrets.get("N8N_WEBHOOK_URL", os.getenv("N8N_WEBHOOK_URL",""))
    token = st.secrets.get("N8N_TOKEN", os.getenv("N8N_TOKEN",""))
    if not url:
        return False, "Falta configurar N8N_WEBHOOK_URL en Secrets."
    headers = {"Content-Type":"application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        if r.ok: return True, "Enviado correctamente."
        return False, f"n8n devolvió estado {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return False, f"Error de red: {e}"

# -------------------- App --------------------
init_state()

# Hero
st.markdown("""
<div class="soft-card">
  <h2 style="margin:0;">📦 Cotización de Envío por Courier</h2>
  <p style="margin:6px 0 0;">Completá tus datos y medidas. Te mandamos la cotización por email.</p>
</div>
""", unsafe_allow_html=True)
st.write("")

# Contacto + Producto
st.subheader("Datos de contacto y del producto")
c1,c2,c3,c4 = st.columns([1.1,1.1,1.0,0.9])
with c1:
    st.session_state.nombre = st.text_input("Nombre completo*", value=st.session_state.nombre, placeholder="Ej: Juan Pérez")
with c2:
    st.session_state.email = st.text_input("Correo electrónico*", value=st.session_state.email, placeholder="ejemplo@email.com")
with c3:
    st.session_state.telefono = st.text_input("Teléfono*", value=st.session_state.telefono, placeholder="Ej: 11 5555 5555")
with c4:
    st.session_state.es_cliente = st.radio("¿Cliente/alumno de Global Trip?", options=["No","Sí"], horizontal=True,
                                           index=0 if st.session_state.es_cliente=="No" else 1)

st.session_state.descripcion = st.text_area("Descripción del producto*", value=st.session_state.descripcion,
                                            placeholder='Ej: "Máquina selladora de bolsas"')
st.session_state.link = st.text_input("Link del producto o ficha técnica (Alibaba, Amazon, etc.)*",
                                      value=st.session_state.link, placeholder="https://...")

st.write("")
st.subheader("Bultos")
st.caption("Tip: usá el botón “+” al final de la tabla para agregar más bultos. Ingresá por bulto: cantidad y dimensiones en **cm**. El **peso volumétrico** se calcula solo.")

# Editor ÚNICO
col_cfg = {
    "Cantidad de bultos": st.column_config.NumberColumn("Cantidad de bultos", min_value=0, step=1, help="Sólo números enteros"),
    "Ancho (cm)": st.column_config.NumberColumn("Ancho (cm)", min_value=0, step=1),
    "Alto (cm)": st.column_config.NumberColumn("Alto (cm)", min_value=0, step=1),
    "Largo (cm)": st.column_config.NumberColumn("Largo (cm)", min_value=0, step=1),
    "Peso vol. (kg)": st.column_config.NumberColumn("Peso vol. (kg)", step=0.01, disabled=True, help="Se calcula automáticamente"),
}

edited = st.data_editor(
    st.session_state.df,
    key="bultos_editor",
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config=col_cfg
)

st.session_state.df, total_peso_vol = compute_vol(edited)

# Pesos
st.write("")
st.subheader("Pesos")
m1, mMid, m2 = st.columns([1.1, 1.1, 1.1])
with m1:
    st.metric("Peso volumétrico (kg) 🔒", f"{total_peso_vol:,.2f}")
with mMid:
    st.session_state.peso_bruto = st.number_input("Peso bruto (kg)", min_value=0.0, step=0.5, value=float(st.session_state.peso_bruto))
with m2:
    peso_aplicable = max(total_peso_vol, float(st.session_state.peso_bruto))
    st.metric("Peso aplicable (kg) 🔒", f"{peso_aplicable:,.2f}")

# Valor mercadería
st.subheader("Valor de la mercadería")
st.session_state.valor_mercaderia = st.number_input("Valor de la mercadería (USD)", min_value=0.0, step=1.0,
                                                    value=float(st.session_state.valor_mercaderia))

# Enviar
st.write("")
btn = st.button("📨 Solicitar cotización", use_container_width=False)

if btn:
    errores = []
    if not st.session_state.nombre.strip(): errores.append("• Nombre es obligatorio.")
    if not st.session_state.email.strip() or "@" not in st.session_state.email: errores.append("• Email válido es obligatorio.")
    if not st.session_state.telefono.strip(): errores.append("• Teléfono es obligatorio.")
    if not st.session_state.descripcion.strip(): errores.append("• Descripción del producto es obligatoria.")
    if not st.session_state.link.strip(): errores.append("• Link del producto/ficha técnica es obligatorio.")
    df_ok = st.session_state.df.fillna(0)
    tiene_bultos = (df_ok[["Cantidad de bultos","Ancho (cm)","Alto (cm)","Largo (cm)"]].sum().sum() > 0)
    if not tiene_bultos: errores.append("• Ingresá al menos un bulto con cantidad y medidas.")

    if errores:
        st.error("Revisá estos puntos:\n\n" + "\n".join(errores))
    else:
        rows_list = st.session_state.df.replace([np.inf,-np.inf],0).fillna(0).to_dict(orient="records")
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "origen": "streamlit-cotizador",
            "factor_vol": FACTOR_VOL,
            "contacto": {
                "nombre": st.session_state.nombre.strip(),
                "email": st.session_state.email.strip(),
                "telefono": st.session_state.telefono.strip(),
                "es_cliente": st.session_state.es_cliente
            },
            "producto": {
                "descripcion": st.session_state.descripcion.strip(),
                "link": st.session_state.link.strip()
            },
            "bultos": rows_list,
            "pesos": {
                "volumetrico_kg": total_peso_vol,
                "bruto_kg": float(st.session_state.peso_bruto),
                "aplicable_kg": peso_aplicable
            },
            "valor_mercaderia_usd": float(st.session_state.valor_mercaderia)
        }
        ok, msg = post_to_webhook(payload)
        if ok:
            st.session_state.last_submit_ok = True
            st.session_state.show_dialog = True
        else:
            st.session_state.last_submit_ok = False
            st.error(msg)

# Popup post-submit
if st.session_state.get("show_dialog", False):
    st.success("¡Gracias! En breve recibirás tu cotización por email.")
    cA, cB = st.columns([1,1])
    with cA:
        if st.button("➕ Cargar otra cotización", type="primary"):
            reset_form()
            st.session_state.show_dialog = False
            st.experimental_rerun()
    with cB:
        if st.button("Cerrar"):
            st.session_state.show_dialog = False
            st.experimental_rerun()
