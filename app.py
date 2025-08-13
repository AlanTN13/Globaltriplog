# app.py — GlobalTrip | Cotizador Courier
import os
import time
import json
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st

# ---------- Config ----------
st.set_page_config(page_title="Cotización de Envío por Courier", page_icon="📦", layout="wide")

PASTEL_PRIMARY = "#6fb3b8"     # verde agua suave
PASTEL_ACCENT  = "#e8f4f5"     # fondo cards
LOCK_ICON = "🔒"
VOL_FACTOR = 5000   # cm3 -> kg
MAX_ROWS = 10

# Oculta barra superior / menú / footer del viewer
st.markdown("""
<style>
  [data-testid="stToolbar"], header, footer, .stDeployButton, .viewerBadge_container__1QSob {display: none !important;}
  .stApp {background: #f7fbfc;}
  .stButton>button {background: #fff; color:#1b1f23; border:1px solid #cbd5e1; border-radius:10px;}
  .stButton>button:hover {background:#f1f5f9; border-color:#94a3b8;}
  .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
  .card {background: %s; border:1px solid #dfe7ea; border-radius:16px; padding:18px;}
  .metric {background:#fff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 16px; font-size:26px; font-weight:600; color:#111827;}
  .label {font-size:13px; color:#4b5563; margin-bottom:6px;}
  .muted {color:#6b7280; font-size:13px;}
  .section-title {font-size:28px; font-weight:700; margin: 0 0 12px 0;}
  .subtle-hr {height:10px; background:#e8eef0; border-radius:999px; border:none; margin:10px 0 18px 0;}
  div[data-testid="stHorizontalBlock"] > div {align-items: end;}
</style>
""" % PASTEL_ACCENT, unsafe_allow_html=True)

# ---------- Helpers ----------
def init_state():
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame({
            "Cantidad de bultos": [0]*MAX_ROWS,
            "Ancho (cm)":         [0]*MAX_ROWS,
            "Alto (cm)":          [0]*MAX_ROWS,
            "Largo (cm)":         [0]*MAX_ROWS,
            f"Peso vol. (kg) {LOCK_ICON}": [0.0]*MAX_ROWS,
        })
    for k, v in {
        "nombre": "", "email":"", "telefono":"", "es_cliente": "No",
        "desc_producto":"", "link_producto":"", "peso_bruto": 0.0,
        "valor_mercaderia": 0.0, "show_modal": False
    }.items():
        st.session_state.setdefault(k, v)

def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    for col in ["Cantidad de bultos","Ancho (cm)","Alto (cm)","Largo (cm)"]:
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0).clip(lower=0)
    # peso_vol por fila = cantidad * (A*B*C/factor)
    work[f"Peso vol. (kg) {LOCK_ICON}"] = (
        work["Cantidad de bultos"] * (work["Ancho (cm)"] * work["Alto (cm)"] * work["Largo (cm)"] / VOL_FACTOR)
    ).round(2)
    return work

def totals(work: pd.DataFrame, peso_bruto: float):
    total_vol = float(work[f"Peso vol. (kg) {LOCK_ICON}"].sum().round(2))
    peso_apl  = float(max(total_vol, float(peso_bruto or 0)))
    return total_vol, peso_apl

def metric_box(label: str, value: float):
    st.markdown(f'<div class="label">{label}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric">{value:,.2f}</div>', unsafe_allow_html=True)

def reset_form():
    st.session_state.df.iloc[:, :] = 0
    st.session_state.nombre = ""
    st.session_state.email = ""
    st.session_state.telefono = ""
    st.session_state.es_cliente = "No"
    st.session_state.desc_producto = ""
    st.session_state.link_producto = ""
    st.session_state.peso_bruto = 0.0
    st.session_state.valor_mercaderia = 0.0

# ---------- UI ----------
init_state()

with st.container():
    st.markdown(
        f"""
        <div class="card">
          <h1 style="margin:0; font-size:28px;">📦 Cotización de Envío por Courier</h1>
          <div class="muted">Completá tus datos y medidas. Te mandamos la cotización por email.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="subtle-hr">', unsafe_allow_html=True)

# Datos de contacto + producto
st.markdown('<div class="section-title">Datos de contacto y del producto</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([1.1, 1.1, 1.0, 1.0])
with c1:
    st.session_state.nombre = st.text_input("Nombre completo*", value=st.session_state.nombre, placeholder="Ej: Juan Pérez")
with c2:
    st.session_state.email = st.text_input("Correo electrónico*", value=st.session_state.email, placeholder="ejemplo@email.com")
with c3:
    st.session_state.telefono = st.text_input("Teléfono*", value=st.session_state.telefono, placeholder="Ej: 11 5555 5555")
with c4:
    st.session_state.es_cliente = st.radio("¿Cliente/alumno de Global Trip?", ["No","Sí"], index=0 if st.session_state.es_cliente=="No" else 1, horizontal=True)

st.session_state.desc_producto = st.text_area("Descripción del producto*", value=st.session_state.desc_producto, placeholder='Ej: "Máquina selladora de bolsas"')
st.session_state.link_producto = st.text_input("Link del producto o ficha técnica (Alibaba, Amazon, etc.)*", value=st.session_state.link_producto, placeholder="https://...")

# Bultos (tabla única, optimizada)
st.markdown('<div class="section-title">Bultos</div>', unsafe_allow_html=True)
st.caption("Tip: usá el botón “+” al final de la tabla para agregar más bultos. Ingresá por bulto: cantidad y dimensiones en **cm**. El peso volumétrico se calcula solo.")
edited = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Cantidad de bultos": st.column_config.NumberColumn("Cantidad de bultos", min_value=0, step=1, help="Sólo números enteros"),
        "Ancho (cm)":         st.column_config.NumberColumn("Ancho (cm)", min_value=0, step=1),
        "Alto (cm)":          st.column_config.NumberColumn("Alto (cm)", min_value=0, step=1),
        "Largo (cm)":         st.column_config.NumberColumn("Largo (cm)", min_value=0, step=1),
        f"Peso vol. (kg) {LOCK_ICON}": st.column_config.NumberColumn(f"Peso vol. (kg) {LOCK_ICON}", disabled=True, format="%.2f", help="Campo automático"),
    },
    disabled=[f"Peso vol. (kg) {LOCK_ICON}"],
    key="bultos_editor",
)

# Recalcular y persistir (sólo una vez por cambio)
work = sanitize_df(edited)
st.session_state.df = work.copy()

# Pesos
st.markdown('<div class="section-title" style="margin-top:18px;">Pesos</div>', unsafe_allow_html=True)
colA, colB, colC = st.columns([1,1,1])
total_vol, peso_aplicable = totals(work, st.session_state.peso_bruto)

with colA:
    metric_box(f"Peso volumétrico (kg) {LOCK_ICON}", total_vol)
with colB:
    st.session_state.peso_bruto = st.number_input("Peso bruto (kg)", min_value=0.0, step=0.1, value=float(st.session_state.peso_bruto))
with colC:
    metric_box(f"Peso aplicable (kg) {LOCK_ICON}", peso_aplicable)

# Valor mercadería
st.markdown('<div class="section-title" style="margin-top:8px;">Valor de la mercadería</div>', unsafe_allow_html=True)
st.session_state.valor_mercaderia = st.number_input("Valor de la mercadería (USD)", min_value=0.0, step=1.0, value=float(st.session_state.valor_mercaderia))

st.write("")  # respirito

# ---------- Enviar ----------
col_btn, _ = st.columns([1,3])
with col_btn:
    enviar = st.button("📨 Solicitar cotización", use_container_width=True)

def validate_required() -> list:
    missing = []
    if not st.session_state.nombre.strip(): missing.append("Nombre completo")
    if not st.session_state.email.strip(): missing.append("Correo electrónico")
    if not st.session_state.telefono.strip(): missing.append("Teléfono")
    if not st.session_state.desc_producto.strip(): missing.append("Descripción del producto")
    if not st.session_state.link_producto.strip(): missing.append("Link del producto")
    # al menos algún bulto válido (alguna fila con algo > 0)
    valid_row = (work[["Cantidad de bultos","Ancho (cm)","Alto (cm)","Largo (cm)"]].sum(axis=1) > 0).any()
    if not valid_row:
        missing.append("Bultos (completar al menos una fila)")
    return missing

if enviar:
    faltan = validate_required()
    if faltan:
        st.error("Para enviar, te falta completar: " + ", ".join(faltan))
    else:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "origen": "streamlit-cotizador",
            "factor_vol": VOL_FACTOR,
            "contacto": {
                "nombre": st.session_state.nombre.strip(),
                "email": st.session_state.email.strip(),
                "telefono": st.session_state.telefono.strip(),
                "es_cliente": st.session_state.es_cliente,
            },
            "producto": {
                "descripcion": st.session_state.desc_producto.strip(),
                "link": st.session_state.link_producto.strip(),
            },
            "bultos": work.replace({np.nan: 0}).to_dict(orient="records"),
            "totales": {
                "peso_vol_kg": total_vol,
                "peso_bruto_kg": float(st.session_state.peso_bruto or 0.0),
                "peso_aplicable_kg": peso_aplicable,
                "valor_mercaderia_usd": float(st.session_state.valor_mercaderia or 0.0),
            },
        }

        url = st.secrets.get("N8N_WEBHOOK_URL") or os.getenv("N8N_WEBHOOK_URL")
        token = st.secrets.get("N8N_TOKEN") or os.getenv("N8N_TOKEN")
        headers = {"Content-Type": "application/json"}
        if token: headers["Authorization"] = f"Bearer {token}"

        ok = False
        try:
            if not url:
                st.warning("Falta configurar el endpoint (N8N_WEBHOOK_URL).")
            else:
                res = requests.post(url, data=json.dumps(payload), headers=headers, timeout=15)
                ok = res.status_code in (200,201,202)
        except Exception as e:
            st.error(f"No pudimos enviar la solicitud ({e}).")

        if ok:
            st.session_state.show_modal = True
        else:
            st.error("Hubo un problema enviando la cotización. Probá nuevamente.")

# ---------- Modal de confirmación ----------
if st.session_state.get("show_modal"):
    with st.modal("¡Solicitud enviada! 🎉", key="modal_ok"):
        st.write(
            "Gracias por tu solicitud. En breve te enviaremos la cotización a tu email.\n\n"
            "¿Querés **cargar otra cotización**?"
        )
        cA, cB = st.columns(2)
        with cA:
            if st.button("Cargar otra cotización", type="primary", use_container_width=True):
                st.session_state.show_modal = False
                reset_form()
                st.rerun()
        with cB:
            if st.button("Cerrar", use_container_width=True):
                st.session_state.show_modal = False
                st.rerun()
