# app.py
import os
import json
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Cotización GlobalTrip",
    page_icon="🧮",
    layout="wide",
    menu_items={"Get help": None, "Report a Bug": None, "About": None}
)

# Palanca del envío (secreto)
N8N_WEBHOOK_URL = st.secrets.get("N8N_WEBHOOK_URL", "")
N8N_TOKEN = st.secrets.get("N8N_TOKEN", None)

# -----------------------------------------------------------------------------
# ESTILOS (oculta toolbar + look & feel pastel + números de métricas en blanco)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
/* Ocultar toolbar (Fork, Rerun, Settings, 3 puntitos) y header/footer nativos */
div[data-testid="stToolbar"] { display: none !important; }
header { visibility: hidden; height: 0px; }
footer, #MainMenu { visibility: hidden; }

/* Paleta suave */
:root{
  --gt-bg:#f7fbff;
  --gt-card:#ffffff;
  --gt-border:#deebf7;
  --gt-text:#0b2540;
  --gt-muted:#5d6b7c;
  --gt-primary:#eaf5ff;
  --gt-primary-hover:#e2f1ff;
}

/* Fondo general */
[data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg, var(--gt-bg) 0%, #ffffff 55%);
}

/* Hero */
.hero{
  background: linear-gradient(90deg, #f2f8ff 0%, #ffffff 100%);
  border: 1px solid var(--gt-border);
  border-radius: 16px;
  padding: 18px 20px;
  margin-bottom: 16px;
  box-shadow: 0 4px 18px rgba(13, 81, 171, 0.06);
}
.hero h1{ margin:0; font-size:28px; color:var(--gt-text) }
.sub{ color:var(--gt-muted); margin-top:6px }

/* Cards */
.card{
  background: var(--gt-card);
  border: 1px solid var(--gt-border);
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 14px;
  box-shadow: 0 6px 20px rgba(13, 81, 171, 0.06);
}
.card h3{ margin:0 0 12px 0; color:var(--gt-text) }

/* Inputs */
input, textarea {
  background: #f6faff !important;
  border: 1px solid var(--gt-border) !important;
  color: var(--gt-text) !important;
  border-radius: 10px !important;
}
input:focus, textarea:focus {
  outline: none !important;
  border: 1px solid #cfe4fb !important;
  box-shadow: 0 0 0 3px rgba(115, 170, 236, 0.15) !important;
}

/* Botones */
div.stButton > button[kind="primary"]{
  background: var(--gt-primary) !important;
  color: var(--gt-text) !important;
  border: 1px solid var(--gt-border) !important;
  border-radius: 9999px !important;
  padding: 10px 16px !important;
}
div.stButton > button[kind="primary"]:hover{
  background: var(--gt-primary-hover) !important;
}
div.stButton > button{
  background:#f5f7fb !important;
  color:var(--gt-text) !important;
  border:1px solid var(--gt-border) !important;
  border-radius:10px !important;
}

/* Métricas */
[data-testid="stMetricValue"]{ color:#ffffff !important; }
[data-testid="stMetricLabel"]{ color:#ffffff !important; }

/* Tabla (header claro + zebra) */
[data-testid="stDataFrame"] thead tr th {
  background: #f2f7ff !important;
  border-bottom: 1px solid var(--gt-border) !important;
}
[data-testid="stDataFrame"] tbody tr:nth-child(odd) td {
  background: #fbfdff !important;
}

.block-container{ padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# UTILS
# -----------------------------------------------------------------------------
FACTOR_VOL = 5000  # cm -> kg

def nueva_tabla_bultos(n=8):
    """DataFrame base con N filas en 0."""
    df = pd.DataFrame({
        "Cantidad de bultos": np.zeros(n, dtype=int),
        "Ancho (cm)": np.zeros(n, dtype=int),
        "Alto (cm)" : np.zeros(n, dtype=int),
        "Largo (cm)": np.zeros(n, dtype=int),
        "Peso vol. (kg)": np.zeros(n, dtype=float),
    })
    return df

def calcular_peso_vol(df: pd.DataFrame, factor: int = FACTOR_VOL) -> pd.DataFrame:
    """Vectorizado y robusto (sin .apply)."""
    work = df.copy()

    for col in ["Cantidad de bultos", "Ancho (cm)", "Alto (cm)", "Largo (cm)"]:
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0)

    # volumen por bulto (cm3) -> /factor -> kg; multiplicado por cantidad
    work["Peso vol. (kg)"] = (
        (work["Ancho (cm)"] * work["Alto (cm)"] * work["Largo (cm)"]) / factor
    ) * work["Cantidad de bultos"]

    # Redondeo leve, evita drift por retrigger
    work["Peso vol. (kg)"] = np.round(work["Peso vol. (kg)"], 2)

    return work

def reset_form():
    """Resetea todo el formulario."""
    st.session_state.bultos = nueva_tabla_bultos()
    st.session_state.valor_mercaderia = 0.0
    st.session_state.peso_bruto = 0.0
    st.session_state.nombre = ""
    st.session_state.email = ""
    st.session_state.telefono = ""
    st.session_state.es_cliente = False
    st.session_state.prod_desc = ""
    st.session_state.prod_link = ""
    st.session_state.show_success = False

def payload_para_envio(df_calc, peso_vol_total, peso_aplicable):
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "origen": "streamlit-cotizador",
        "contacto": {
            "nombre": st.session_state.nombre.strip(),
            "email": st.session_state.email.strip(),
            "telefono": st.session_state.telefono.strip(),
            "es_cliente": "Sí" if st.session_state.es_cliente else "No",
        },
        "producto": {
            "descripcion": st.session_state.prod_desc.strip(),
            "link": st.session_state.prod_link.strip()
        },
        "factor_vol": FACTOR_VOL,
        "bultos": df_calc.to_dict(orient="records"),
        "pesos": {
            "peso_vol_total": float(peso_vol_total),
            "peso_bruto": float(st.session_state.peso_bruto),
            "peso_aplicable": float(peso_aplicable),
            "valor_mercaderia": float(st.session_state.valor_mercaderia)
        }
    }

# -----------------------------------------------------------------------------
# STATE INIT
# -----------------------------------------------------------------------------
if "bultos" not in st.session_state:
    st.session_state.bultos = nueva_tabla_bultos()
if "valor_mercaderia" not in st.session_state:
    st.session_state.valor_mercaderia = 0.0
if "peso_bruto" not in st.session_state:
    st.session_state.peso_bruto = 0.0
if "nombre" not in st.session_state:
    st.session_state.nombre = ""
if "email" not in st.session_state:
    st.session_state.email = ""
if "telefono" not in st.session_state:
    st.session_state.telefono = ""
if "es_cliente" not in st.session_state:
    st.session_state.es_cliente = False
if "prod_desc" not in st.session_state:
    st.session_state.prod_desc = ""
if "prod_link" not in st.session_state:
    st.session_state.prod_link = ""
if "show_success" not in st.session_state:
    st.session_state.show_success = False

# -----------------------------------------------------------------------------
# HERO
# -----------------------------------------------------------------------------
st.markdown(
    '<div class="hero"><h1>🧮 Cotización de Envío por Courier</h1>'
    '<div class="sub">Completá tus datos y medidas. Te mandamos la cotización por email.</div></div>',
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# DATOS DE CONTACTO + PRODUCTO (2 columnas)
# -----------------------------------------------------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### Información del remitente y del producto")

c1, c2, c3, c4 = st.columns([1.1, 1.1, 1.0, 0.9])
st.session_state.nombre   = c1.text_input("Nombre completo*", value=st.session_state.nombre, placeholder="Ej: Juan Pérez")
st.session_state.email    = c2.text_input("Correo electrónico*", value=st.session_state.email, placeholder="ejemplo@email.com")
st.session_state.telefono = c3.text_input("Teléfono*", value=st.session_state.telefono, placeholder="Ej: 11 5555 5555")
st.session_state.es_cliente = c4.radio("¿Cliente/alumno de Global Trip?", options=["No", "Sí"], horizontal=True) == "Sí"

c5, c6 = st.columns([1.2, 1.0])
st.session_state.prod_desc = c5.text_area("Descripción del producto*", value=st.session_state.prod_desc, placeholder='Ej: "Máquina selladora de bolsas"', height=100)
st.session_state.prod_link = c6.text_input("Link del producto o ficha técnica (Alibaba, Amazon, etc.)*", value=st.session_state.prod_link, placeholder="https://...")

st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TABLA DE BULTOS (optimizda)
# -----------------------------------------------------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### Bultos")
st.caption("Tip: usá el botón “+” al final de la tabla para agregar más bultos. Ingresá por bulto: cantidad y dimensiones en cm. El peso volumétrico se calcula solo.")

# Editor (más liviano con NumberColumn y sin validadores regex)
edited = st.data_editor(
    st.session_state.bultos.drop(columns=["Peso vol. (kg)"]),  # el usuario edita 4 columnas
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    column_config={
        "Cantidad de bultos": st.column_config.NumberColumn(
            "Cantidad de bultos", min_value=0, step=1, help="Sólo enteros ≥ 0"
        ),
        "Ancho (cm)": st.column_config.NumberColumn(
            "Ancho (cm)", min_value=0, step=1, help="cm"
        ),
        "Alto (cm)": st.column_config.NumberColumn(
            "Alto (cm)", min_value=0, step=1, help="cm"
        ),
        "Largo (cm)": st.column_config.NumberColumn(
            "Largo (cm)", min_value=0, step=1, help="cm"
        ),
    },
    key="edit_bultos"
)

# Recalcular en vector
calc = calcular_peso_vol(edited)
st.session_state.bultos = calc  # persistimos (incluye Peso vol. (kg))

# Mostrar una vista con la columna calculada (sólo lectura)
st.dataframe(
    calc,
    hide_index=True,
    use_container_width=True
)
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# PESOS + VALOR MERCADERÍA
# -----------------------------------------------------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### Pesos")

peso_vol_total = float(np.round(calc["Peso vol. (kg)"].sum(), 2))

c7, c8, c9 = st.columns([1, 1, 1])
with c7:
    st.metric("Peso volumétrico (kg)", f"{peso_vol_total:,.2f}")
with c8:
    st.session_state.peso_bruto = st.number_input("Peso bruto (kg)", min_value=0.0, step=0.5, value=st.session_state.peso_bruto)
with c9:
    peso_aplicable = float(np.round(max(peso_vol_total, st.session_state.peso_bruto), 2))
    st.metric("Peso aplicable (kg)", f"{peso_aplicable:,.2f}")

st.markdown("### Valor de la mercadería")
st.session_state.valor_mercaderia = st.number_input(
    "Valor de la mercadería (USD)", min_value=0.0, step=10.0, value=st.session_state.valor_mercaderia
)

st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# ENVIAR
# -----------------------------------------------------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
enviar = st.button("📤 Solicitar cotización", type="primary")
st.markdown('</div>', unsafe_allow_html=True)

if enviar:
    # Validaciones mínimas
    faltan = []
    if not st.session_state.nombre.strip(): faltan.append("Nombre")
    if not st.session_state.email.strip(): faltan.append("Email")
    if not st.session_state.telefono.strip(): faltan.append("Teléfono")
    if not st.session_state.prod_desc.strip(): faltan.append("Descripción de producto")
    if not st.session_state.prod_link.strip(): faltan.append("Link de producto")

    if faltan:
        st.error("Por favor completá: " + ", ".join(faltan))
    elif not N8N_WEBHOOK_URL:
        st.error("No se configuró el endpoint. Agregá N8N_WEBHOOK_URL en Secrets.")
    else:
        data = payload_para_envio(calc, peso_vol_total, peso_aplicable)
        try:
            headers = {"Content-Type": "application/json"}
            if N8N_TOKEN:
                headers["Authorization"] = f"Bearer {N8N_TOKEN}"
            r = requests.post(N8N_WEBHOOK_URL, headers=headers, data=json.dumps(data), timeout=20)
            if 200 <= r.status_code < 300:
                st.session_state.show_success = True
                st.success("¡Gracias! En breve recibirás tu cotización por email.")
            else:
                st.error(f"El servidor respondió {r.status_code}: {r.text}")
        except requests.RequestException as e:
            st.error(f"No se pudo enviar la solicitud: {e}")

# -----------------------------------------------------------------------------
# MODAL DE ÉXITO
# -----------------------------------------------------------------------------
if st.session_state.show_success:
    with st.modal("✅ Enviado"):
        st.write(
            "Tu solicitud fue enviada con éxito. En breve te llegará la cotización por email."
        )
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("➕ Cargar otra cotización"):
                reset_form()
                st.rerun()
        with cc2:
            if st.button("🏠 Volver al inicio"):
                reset_form()
                # simple scroll al top (efecto visual); rerun deja todo limpio
                st.rerun()
