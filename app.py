# app.py
import re
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

# ---------- Config y estilos ----------
st.set_page_config(page_title="Cotización GlobalTrip", page_icon="🧮", layout="wide")
st.markdown("""
<style>
  :root {
    --gt-surface:#f9fbff; --gt-border:#e6eef7; --gt-text:#0b2540; --gt-muted:#5d6b7c;
    --gt-primary:#e9f5ff; --gt-primary-border:#c6e3f7; --gt-primary-hover:#dff0ff;
  }
  .hero{ background:linear-gradient(90deg, #eef7ff 0%, #fafcff 100%);
         border:1px solid var(--gt-border); border-radius:16px; padding:18px 20px; margin-bottom:14px }
  .hero h1{margin:0; font-size:28px; color:var(--gt-text)}
  .sub{color:var(--gt-muted); margin-top:6px}
  .card{ border:1px solid var(--gt-border); background:#ffffffaa; border-radius:14px; padding:16px; margin-bottom:12px }
  .card h3{margin:0 0 12px 0; color:var(--gt-text)}
  div.stButton > button[kind="primary"]{
    background:var(--gt-primary) !important; color:var(--gt-text) !important;
    border:1px solid var(--gt-primary-border) !important; border-radius: 9999px !important;
    padding: 0.6rem 1rem !important;
  }
  div.stButton > button[kind="primary"]:hover{
    background:var(--gt-primary-hover) !important; border-color:var(--gt-primary-border) !important;
  }
  div.stButton > button{
    background:#f5f7fb !important; color:var(--gt-text) !important;
    border:1px solid var(--gt-border) !important; border-radius: 10px !important;
  }
  div.stButton > button:hover{ background:#eef3fb !important; }
  [data-testid="stMetricValue"]{ color:#ffffff !important; }
  [data-testid="stMetricLabel"]{ color:#ffffff !important; }
</style>
""", unsafe_allow_html=True)

# ---------- Constantes ----------
FACTOR_VOL = 5000
MAX_ROWS   = 20
COLS = {
    "cantidad": "Cantidad de bultos",
    "ancho_cm": "Ancho (cm)",
    "alto_cm":  "Alto (cm)",
    "largo_cm": "Largo (cm)",
}
PESO_VOL_COL   = "peso_vol_kg"
PESO_VOL_LABEL = "Peso vol. (kg) 🔒"

# ---------- Helpers ----------
def is_email(x: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", x or ""))

def is_phone(x: str) -> bool:
    x = (x or "").strip().replace(" ", "").replace("-", "")
    return x.isdigit() and 6 <= len(x) <= 20

def is_url(x: str) -> bool:
    return bool(re.match(r"^https?://.+", (x or "").strip()))

def peso_vol_row(q, a, h, l, factor=FACTOR_VOL) -> float:
    try:
        q = int(float(q)); a = float(a); h = float(h); l = float(l)
        if q <= 0 or a <= 0 or h <= 0 or l <= 0: return 0.0
        return round(q * (a * h * l) / factor, 2)
    except Exception:
        return 0.0

def default_bultos_df(n_rows: int = 8) -> pd.DataFrame:
    # guardamos como texto para evitar “saltos”
    return pd.DataFrame([{k: "" for k in COLS.keys()} for _ in range(n_rows)])

def post_to_automation(payload: dict) -> tuple[bool, str]:
    url = st.secrets.get("N8N_WEBHOOK_URL", "")
    token = st.secrets.get("N8N_TOKEN", "")
    if not url:
        return False, "Falta N8N_WEBHOOK_URL en Secrets (TOML)."
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(url, json=payload, headers=headers, timeout=20)
    ok = 200 <= r.status_code < 300
    return ok, (r.text or str(r.status_code))

def reset_form_state():
    for k in ["bultos_df","peso_bruto","valor_mercaderia","nombre","email","telefono","es_cliente","descripcion","link"]:
        if k in st.session_state: del st.session_state[k]

def df_for_payload(df_internal: pd.DataFrame) -> list[dict]:
    df = df_internal.rename(columns={**COLS, PESO_VOL_COL: "Peso vol. (kg)"})
    return df.to_dict(orient="records")

# ---------- Modal de gracias ----------
@st.dialog("¡Listo!")
def _thanks_dialog():
    email_destino = st.session_state.get("_last_email", st.session_state.get("email", "tu email"))
    st.write(f"Recibimos tu solicitud. En breve te llegará la cotización a **{email_destino}**.")
    st.caption("¿Querés cargar otra cotización?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Cargar otra cotización", type="primary", use_container_width=True):
            reset_form_state(); st.session_state["show_thanks"] = False; st.rerun()
    with c2:
        if st.button("Cerrar", use_container_width=True):
            st.session_state["show_thanks"] = False; st.rerun()

# ---------- Hero ----------
st.markdown("""
<div class="hero">
  <h1>🧮 Cotización de Envío por Courier</h1>
  <div class="sub">Completá tus datos y medidas. Te mandamos la cotización por email.</div>
</div>
""", unsafe_allow_html=True)

# ---------- Estado inicial ----------
if "bultos_df" not in st.session_state:
    st.session_state.bultos_df = default_bultos_df()
    st.session_state.peso_bruto = 0.0
    st.session_state.valor_mercaderia = 0.0
    st.session_state.nombre = ""
    st.session_state.email = ""
    st.session_state.telefono = ""
    st.session_state.es_cliente = "No"
    st.session_state.descripcion = ""
    st.session_state.link = ""

if st.session_state.get("show_thanks", False):
    _thanks_dialog()

# ---------- Contacto + Producto ----------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### Datos de contacto y del producto")

c1, c2, c3, c4 = st.columns([1.1, 1.1, 0.9, 0.9])
with c1: st.text_input("Nombre completo*", key="nombre", placeholder="Ej: Juan Pérez")
with c2: st.text_input("Correo electrónico*", key="email", placeholder="ejemplo@email.com")
with c3: st.text_input("Teléfono*", key="telefono", placeholder="Ej: 11 5555 5555")
with c4: st.radio("¿Cliente/alumno de Global Trip?", ["No", "Sí"], key="es_cliente", horizontal=True)

st.text_area("Descripción del producto*", key="descripcion",
             placeholder='Ej: "Máquina selladora de bolsas"', height=110)
st.text_input("Link del producto o ficha técnica (Alibaba, Amazon, etc.)*",
              key="link", placeholder="https://...")
st.markdown('</div>', unsafe_allow_html=True)

# ---------- Bultos (rápido) ----------
st.markdown("### Bultos")
st.caption("Tip: usá el botón “+” al final de la tabla para agregar más bultos.")
st.caption("Ingresá por bulto: cantidad y dimensiones en **cm**. El peso volumétrico se calcula solo.")

base_cols = ["cantidad", "ancho_cm", "alto_cm", "largo_cm"]

def _numeric_copy_for_calc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in base_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

raw_df = st.session_state.bultos_df.copy()
calc_df = _numeric_copy_for_calc(raw_df).fillna(0)
peso_vol_series = calc_df.apply(lambda r: peso_vol_row(r["cantidad"], r["ancho_cm"], r["alto_cm"], r["largo_cm"]), axis=1)

show_df = raw_df.copy()
show_df[PESO_VOL_COL] = peso_vol_series

# 👇 OJO: sin 'validate' / 'placeholder' (compatibilidad)
edited = st.data_editor(
    show_df,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    column_order=[*base_cols, PESO_VOL_COL],
    column_config={
        "cantidad": st.column_config.TextColumn(COLS["cantidad"], help="Sólo números enteros"),
        "ancho_cm": st.column_config.TextColumn(COLS["ancho_cm"], help="Sólo números"),
        "alto_cm":  st.column_config.TextColumn(COLS["alto_cm"],  help="Sólo números"),
        "largo_cm": st.column_config.TextColumn(COLS["largo_cm"], help="Sólo números"),
        PESO_VOL_COL: st.column_config.NumberColumn(PESO_VOL_LABEL, disabled=True, step=0.01),
    },
    key="editor_bultos",
)

# Guardamos tal cual (texto) y recalculamos totales con copia numérica
st.session_state.bultos_df = edited[base_cols].copy()

calc_df = _numeric_copy_for_calc(st.session_state.bultos_df).fillna(0)
calc_df[PESO_VOL_COL] = calc_df.apply(
    lambda r: peso_vol_row(r["cantidad"], r["ancho_cm"], r["alto_cm"], r["largo_cm"]),
    axis=1
)
total_peso_vol = round(calc_df[PESO_VOL_COL].sum(), 2)

# ---------- Form submit ----------
with st.form("cotizacion_form"):
    st.markdown("### Pesos")
    p1, p2, p3 = st.columns(3)
    with p1: st.metric("Peso volumétrico (kg) 🔒", f"{total_peso_vol:.2f}")
    with p2:
        st.number_input("Peso bruto (kg)", min_value=0.0,
                        value=float(st.session_state.get("peso_bruto", 0.0)),
                        step=0.1, format="%.2f", key="peso_bruto")
    with p3:
        peso_aplicable = max(st.session_state.peso_bruto, total_peso_vol)
        st.metric("Peso aplicable (kg) 🔒", f"{peso_aplicable:.2f}")
    st.caption("El **peso aplicable** es el mayor entre el volumétrico y el bruto.")

    st.markdown("### Valor de la mercadería")
    st.number_input("Valor de la mercadería (USD)", min_value=0.0,
                    value=float(st.session_state.get("valor_mercaderia", 0.0)),
                    step=1.0, format="%.2f", key="valor_mercaderia")

    submit = st.form_submit_button("📨 Solicitar cotización")

# ---------- Validación + envío ----------
def validar_form() -> list[str]:
    errs = []
    if not st.session_state.nombre or len(st.session_state.nombre.strip()) < 2:
        errs.append("Ingresá tu nombre.")
    if not is_email(st.session_state.email):
        errs.append("Ingresá un email válido.")
    if not is_phone(st.session_state.telefono):
        errs.append("Ingresá un teléfono válido (sólo números, 6–20 dígitos).")
    if not st.session_state.descripcion or len(st.session_state.descripcion.strip()) < 3:
        errs.append("Ingresá una descripción del producto.")
    if not is_url(st.session_state.link):
        errs.append("Ingresá un link válido (debe empezar con http:// o https://).")

    valid_rows = calc_df[
        (calc_df["cantidad"] > 0) &
        (calc_df["ancho_cm"] > 0) &
        (calc_df["alto_cm"] > 0) &
        (calc_df["largo_cm"] > 0)
    ]
    if valid_rows.empty:
        errs.append("Agregá al menos un bulto con medidas > 0.")
    if len(calc_df) > MAX_ROWS:
        errs.append(f"Máximo {MAX_ROWS} filas de bultos.")
    return errs

if submit:
    errores = validar_form()
    if errores:
        for e in errores: st.error(e)
    else:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "origen": "streamlit-cotizador",
            "contacto": {
                "nombre": st.session_state.nombre.strip(),
                "email": st.session_state.email.strip(),
                "telefono": st.session_state.telefono.strip(),
                "es_cliente": st.session_state.es_cliente,
            },
            "producto": {
                "descripcion": st.session_state.descripcion.strip(),
                "link": st.session_state.link.strip(),
            },
            "bultos": df_for_payload(calc_df),
            "totales": {
                "peso_vol_total": total_peso_vol,
                "peso_bruto": st.session_state.peso_bruto,
                "peso_aplicable": max(st.session_state.peso_bruto, total_peso_vol),
                "valor_mercaderia": st.session_state.valor_mercaderia,
                "factor_vol": FACTOR_VOL,
            },
        }
        with st.spinner("Enviando…"):
            ok, msg = post_to_automation(payload)
        if ok:
            st.session_state["_last_email"] = st.session_state.email
            st.session_state["show_thanks"] = True
            st.rerun()
        else:
            st.error("No pudimos enviar tu solicitud.")
            st.code(msg)

st.caption("Usamos estos datos sólo para generar tu cotización. No compartimos tu información.")
