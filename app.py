# app.py
# Streamlit 1.30+ recommended

import os
import json
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st

# -------------------- Page & Theme --------------------
st.set_page_config(
    page_title="Cotización de Envío por Courier",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------- Styles (azul del botón) --------------------
st.markdown(
    """
    <style>
      :root{
        --brand:#1F6FFF;          /* azul principal (igual al botón) */
        --brand-soft:#E9F0FF;     /* versión suave para fondos */
        --ink:#0E1B2B;            /* texto principal oscuro */
      }

      /* Ocultar menú de 3 puntos / fork / footer */
      #MainMenu, footer, header [data-testid="baseButton-header"],
      .stDeployButton, [data-testid="stToolbar"] {display:none !important;}

      /* Títulos, subtítulos y labels en azul */
      h1, h2, h3, h4, h5, h6,
      [data-testid="stWidgetLabel"] p,
      [data-testid="stRadio"] label,
      [data-testid="stMarkdownContainer"] p.section-title {
        color: var(--brand) !important;
      }

      /* Caja hero */
      .hero{
        background: var(--brand-soft);
        border: 1px solid #d9e6ff;
        padding: 20px 24px;
        border-radius: 14px;
        margin-bottom: 8px;
      }

      /* Inputs */
      div[data-testid="stTextInput"] input,
      div[data-testid="stNumberInput"] input,
      div[data-testid="stTextArea"] textarea{
        background:#232833; color:#fff;
        border:1px solid #2d3647;
        border-radius:12px;
      }
      div[data-testid="stTextInput"] input::placeholder,
      div[data-testid="stNumberInput"] input::placeholder,
      div[data-testid="stTextArea"] textarea::placeholder{
        color:#5C8BFF !important;   /* placeholder azul suave */
      }

      /* Data editor en claro con encabezado celestito */
      div[data-testid="stDataFrame"] thead tr th{
        background: var(--brand-soft) !important;
        color: var(--ink) !important;
        border-bottom: 1px solid #d9e6ff !important;
      }
      div[data-testid="stDataFrame"] tbody tr td{
        background: #11161f !important;
        color: #ffffff !important;
      }
      div[data-testid="stDataFrame"] tbody tr td:last-child{
        font-variant-numeric: tabular-nums;
      }

      /* Botón principal – pastel */
      .stButton>button{
        background:#ffffff;
        color:#0E1B2B;
        border:1px solid #cfe0ff;
        border-radius:20px;
        padding:14px 22px;
        box-shadow: 0 10px 30px rgba(31,111,255,0.10);
        font-weight:600;
      }
      .stButton>button:hover{
        border-color:#9bbcff;
        box-shadow: 0 12px 40px rgba(31,111,255,0.18);
      }

      /* Tarjetas de KPIs (peso vol, aplicable) */
      .kpi{
        border-radius:14px; padding:18px 20px; border:1px solid #e7eefc;
        background:#fff;
      }
      .kpi.lock{ background:#fff; }
      .kpi .label{ color:var(--brand); font-weight:600; }
      .kpi .value{ font-size:36px; font-weight:700; color:#0E1B2B; }

      /* Bloques de sección */
      .section{ margin-top: 18px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- Helpers --------------------
FACTOR_VOLUMETRICO = 5000  # cm³ / kg

def new_table(rows:int=10) -> pd.DataFrame:
    df = pd.DataFrame({
        "Cantidad de bultos": np.zeros(rows, dtype=int),
        "Ancho (cm)": np.zeros(rows, dtype=int),
        "Alto (cm)": np.zeros(rows, dtype=int),
        "Largo (cm)": np.zeros(rows, dtype=int),
        "Peso vol. (kg)": np.zeros(rows, dtype=float),
    })
    return df

def recalc_volumen():
    """Callback para recalcular peso volumétrico dentro del editor."""
    df = pd.DataFrame(st.session_state.bultos_editor)
    # Asegurar tipos
    for c in ["Cantidad de bultos", "Ancho (cm)", "Alto (cm)", "Largo (cm)"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    vol_unit = (df["Ancho (cm)"] * df["Alto (cm)"] * df["Largo (cm)"]) / FACTOR_VOLUMETRICO
    df["Peso vol. (kg)"] = np.round(vol_unit * df["Cantidad de bultos"], 2)

    st.session_state.bultos_df = df

def reset_form():
    st.session_state.bultos_df = new_table()
    st.session_state.nombre = ""
    st.session_state.email = ""
    st.session_state.telefono = ""
    st.session_state.es_cliente = "No"
    st.session_state.desc = ""
    st.session_state.link = ""
    st.session_state.peso_bruto = 0.0
    st.session_state.valor_merc = 0.0
    st.session_state.show_thanks = False

# -------------------- Session Boot --------------------
if "bultos_df" not in st.session_state:
    reset_form()

# -------------------- HERO --------------------
st.markdown(
    """
    <div class="hero">
      <h2>📦 Cotización de Envío por Courier</h2>
      <p class="section-title">Completá tus datos y medidas. Te mandamos la cotización por email.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------- Contacto & producto --------------------
st.markdown('<p class="section-title">Datos de contacto y del producto</p>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([2.2, 2.2, 1.5, 1.3])

with c1:
    st.session_state.nombre = st.text_input("Nombre completo*", st.session_state.nombre, placeholder="Ej: Juan Pérez")
with c2:
    st.session_state.email = st.text_input("Correo electrónico*", st.session_state.email, placeholder="ejemplo@email.com")
with c3:
    st.session_state.telefono = st.text_input("Teléfono*", st.session_state.telefono, placeholder="Ej: 11 5555 5555")
with c4:
    st.session_state.es_cliente = st.radio("¿Cliente/alumno de Global Trip?", ["No", "Sí"], index=0 if st.session_state.es_cliente=="No" else 1, horizontal=True)

st.session_state.desc = st.text_area("Descripción del producto*", st.session_state.desc, placeholder='Ej: "Máquina selladora de bolsas"', height=110)
st.session_state.link = st.text_input("Link del producto o ficha técnica (Alibaba, Amazon, etc.)*", st.session_state.link, placeholder="https://...")

st.markdown('<div class="section"></div>', unsafe_allow_html=True)

# -------------------- Tabla de bultos (una sola) --------------------
st.markdown('<p class="section-title">Bultos</p>', unsafe_allow_html=True)
st.caption("Tip: usá el botón “+” al final de la tabla para agregar más bultos. Ingresá por bulto: cantidad y dimensiones en cm. El peso volumétrico se calcula solo.")

edited = st.data_editor(
    st.session_state.bultos_df,
    key="bultos_editor",
    use_container_width=True,
    num_rows="dynamic",
    on_change=recalc_volumen,
    column_config={
        "Cantidad de bultos": st.column_config.NumberColumn("Cantidad de bultos", min_value=0, step=1, help="Solo números enteros"),
        "Ancho (cm)": st.column_config.NumberColumn("Ancho (cm)", min_value=0, step=1),
        "Alto (cm)": st.column_config.NumberColumn("Alto (cm)", min_value=0, step=1),
        "Largo (cm)": st.column_config.NumberColumn("Largo (cm)", min_value=0, step=1),
        "Peso vol. (kg)": st.column_config.NumberColumn("Peso vol. (kg)", format="%.2f", disabled=True),
    },
)

# Garantizar cálculo actualizado también en primer render
recalc_volumen()
df_calc = st.session_state.bultos_df.copy()

total_peso_vol = float(np.round(df_calc["Peso vol. (kg)"].sum(), 2))

# -------------------- Pesos y valor --------------------
st.markdown('<div class="section"></div>', unsafe_allow_html=True)
k1, k2, k3 = st.columns([1.1, 1.1, 1.1])

with k1:
    st.markdown('<div class="kpi lock"><div class="label">Peso volumétrico (kg) 🔒</div><div class="value">'
                f'{total_peso_vol:,.2f}</div></div>', unsafe_allow_html=True)

with k2:
    st.session_state.peso_bruto = st.number_input(" ", value=float(st.session_state.peso_bruto), min_value=0.0, step=1.0,
                                                  help="Peso bruto total del envío (kg)")
    # pintar campo como chip oscuro
    st.markdown(
        f"""
        <div class="kpi" style="background:#232833;border:1px solid #2d3647;color:#fff;margin-top:-74px;">
          <div class="label" style="color:#9bbcff">Peso bruto (kg)</div>
          <div class="value" style="color:#fff">{st.session_state.peso_bruto:,.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k3:
    peso_aplicable = max(total_peso_vol, float(st.session_state.peso_bruto))
    st.markdown('<div class="kpi lock"><div class="label">Peso aplicable (kg) 🔒</div><div class="value">'
                f'{peso_aplicable:,.2f}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="section"></div>', unsafe_allow_html=True)
st.markdown('<p class="section-title">Valor de la mercadería</p>', unsafe_allow_html=True)
st.session_state.valor_merc = st.number_input("Valor de la mercadería (USD)", value=float(st.session_state.valor_merc), min_value=0.0, step=10.0)

st.markdown('<div class="section"></div>', unsafe_allow_html=True)

# -------------------- Envío (webhook) --------------------
def send_payload():
    url = st.secrets.get("N8N_WEBHOOK_URL", os.getenv("N8N_WEBHOOK_URL", "")).strip()
    payload = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "origen": "streamlit-cotizador",
        "contacto": {
            "nombre": st.session_state.nombre.strip(),
            "email": st.session_state.email.strip(),
            "telefono": st.session_state.telefono.strip(),
            "es_cliente": st.session_state.es_cliente,
        },
        "producto": {
            "descripcion": st.session_state.desc.strip(),
            "link": st.session_state.link.strip(),
        },
        "bultos": json.loads(df_calc.to_json(orient="records")),
        "peso_vol_total": total_peso_vol,
        "peso_bruto": st.session_state.peso_bruto,
        "peso_aplicable": peso_aplicable,
        "valor_mercaderia_usd": st.session_state.valor_merc,
        "factor_vol": FACTOR_VOLUMETRICO,
    }

    if not url:
        st.error("No se encontró la URL de webhook. Configurá **N8N_WEBHOOK_URL** en *Secrets*.")
        return False

    try:
        r = requests.post(url, json=payload, timeout=12)
        if r.ok:
            return True
        st.error(f"El servidor respondió {r.status_code}.")
    except Exception as e:
        st.error(f"No se pudo enviar: {e}")
    return False

c_submit = st.columns([1, 6, 1])[0]
with c_submit:
    if st.button("📨 Solicitar cotización"):
        ok = send_payload()
        if ok:
            st.session_state.show_thanks = True

# -------------------- “Popup” de gracias --------------------
if st.session_state.get("show_thanks"):
    st.success("¡Gracias! En breve recibirás tu cotización por email.")
    cc1, cc2 = st.columns([1,1])
    with cc1:
        if st.button("🆕 Cargar otra cotización"):
            reset_form()
            st.experimental_rerun()
    with cc2:
        if st.button("Cerrar"):
            st.session_state.show_thanks = False
