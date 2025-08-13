# app.py
import re
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# ============== Config ==============
st.set_page_config(page_title="Cotización GlobalTrip", page_icon="🧮", layout="wide")
st.markdown("""
<style>
  .hero{
    background:linear-gradient(90deg,rgba(11,123,214,.12),rgba(11,123,214,.05));
    border:1px solid rgba(255,255,255,.06);
    border-radius:16px;padding:18px 20px;margin-bottom:14px
  }
  .hero h1{margin:0;font-size:28px}
  .sub{color:#b9c2cf;margin-top:6px}
  .card{border:1px solid rgba(255,255,255,.08); border-radius:14px; padding:14px 14px 4px 14px; margin-bottom:8px;}
  .card h4{margin:0 0 8px 0}
</style>
""", unsafe_allow_html=True)

FACTOR_VOL = 5000  # cm³/kg
MAX_ROWS   = 20

# ============== Helpers ==============
def is_email(x: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", x or ""))

def is_phone(x: str) -> bool:
    x = (x or "").strip().replace(" ", "").replace("-", "")
    return x.isdigit() and 6 <= len(x) <= 20

def is_url(x: str) -> bool:
    return bool(re.match(r"^https?://.+", (x or "").strip()))

def peso_vol_row(q, a, h, l, factor=FACTOR_VOL) -> float:
    try:
        q = int(q); a = float(a); h = float(h); l = float(l)
        if q <= 0 or a <= 0 or h <= 0 or l <= 0: return 0.0
        return round(q * (a * h * l) / factor, 2)
    except Exception:
        return 0.0

def add_peso_vol(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Peso vol. (kg) 🔒"] = df.apply(
        lambda r: peso_vol_row(r["Cantidad de bultos"], r["Ancho (cm)"], r["Alto (cm)"], r["Largo (cm)"]),
        axis=1
    )
    return df

def default_bultos_df(n_rows: int = 8) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Cantidad de bultos": 0, "Ancho (cm)": 0, "Alto (cm)": 0, "Largo (cm)": 0} for _ in range(n_rows)]
    )

def post_to_automation(payload: dict) -> tuple[bool, str]:
    url = st.secrets.get("N8N_WEBHOOK_URL", "")
    token = st.secrets.get("N8N_TOKEN", "")
    if not url:
        return False, "Falta configurar N8N_WEBHOOK_URL en *Settings → Secrets* (TOML)."
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(url, json=payload, headers=headers, timeout=20)
    ok = 200 <= r.status_code < 300
    return ok, r.text or str(r.status_code)

def reset_form_state():
    st.session_state.bultos_df = default_bultos_df()
    st.session_state.peso_bruto = 0.0
    st.session_state.valor_mercaderia = 0.0
    st.session_state.nombre = ""
    st.session_state.email = ""
    st.session_state.telefono = ""
    st.session_state.es_cliente = "No"
    st.session_state.descripcion = ""
    st.session_state.link = ""

# ============== Header ==============
st.markdown("""
<div class="hero">
  <h1>🧮 Cotización de Envío por Courier</h1>
  <div class="sub">Completá tus datos y la información del envío. Te enviaremos la cotización por email.</div>
</div>
""", unsafe_allow_html=True)

# ============== Estado inicial ==============
if "bultos_df" not in st.session_state:
    reset_form_state()

# ============== Info inicial (dos tarjetas lado a lado) ==============
st.markdown("### Información del remitente y del producto")
left, right = st.columns(2, gap="large")

with left:
    st.markdown('<div class="card"><h4>Datos de contacto</h4>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        st.text_input("Nombre completo*", key="nombre", placeholder="Ej: Juan Pérez")
    with c2:
        st.text_input("Correo electrónico*", key="email", placeholder="ejemplo@email.com")
    c3, c4 = st.columns([1, 1])
    with c3:
        st.text_input("Teléfono*", key="telefono", placeholder="Ej: 11 5555 5555")
    with c4:
        st.radio("¿Cliente/alumno de Global Trip?", ["No", "Sí"], key="es_cliente", horizontal=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card"><h4>Datos del producto</h4>', unsafe_allow_html=True)
    st.text_area("Descripción del producto*", key="descripcion",
                 placeholder='Ej: "Máquina selladora de bolsas"', height=110)
    st.text_input("Link del producto o ficha técnica (Alibaba, Amazon, etc.)*",
                  key="link", placeholder="https://...")
    st.markdown('</div>', unsafe_allow_html=True)

# ============== BULTOS (fuera del form para recalcular en vivo) ==============
st.markdown("### Bultos")
st.caption("Ingresá por bulto: cantidad y dimensiones en **cm**. El peso volumétrico se calcula solo.")

bultos_to_show = add_peso_vol(st.session_state.bultos_df.copy())
edited = st.data_editor(
    bultos_to_show,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    column_config={
        "Cantidad de bultos": st.column_config.NumberColumn("Cantidad de bultos", step=1, min_value=0),
        "Ancho (cm)":       st.column_config.NumberColumn("Ancho (cm)", step=1, min_value=0),
        "Alto (cm)":        st.column_config.NumberColumn("Alto (cm)",  step=1, min_value=0),
        "Largo (cm)":       st.column_config.NumberColumn("Largo (cm)", step=1, min_value=0),
        "Peso vol. (kg) 🔒": st.column_config.NumberColumn("Peso vol. (kg) ", step=0.01, disabled=True,
                                                          help="Se calcula automáticamente"),
    },
    key="editor_bultos",
)
edited = edited.copy()
edited["Cantidad de bultos"] = edited["Cantidad de bultos"].fillna(0).astype(int)
for col in ["Ancho (cm)", "Alto (cm)", "Largo (cm)"]:
    edited[col] = edited[col].fillna(0).astype(float)
st.session_state.bultos_df = edited
edited_calc = add_peso_vol(edited)
total_peso_vol = round(edited_calc["Peso vol. (kg) "].sum(), 2)

# ============== FORM (submit) ==============
with st.form("cotizacion_form"):
    st.markdown("### Pesos")
    p1, p2, p3 = st.columns(3)
    with p1:
        st.metric("Peso volumétrico (kg) ", f"{total_peso_vol:.2f}")
    with p2:
        st.number_input("Peso bruto (kg)", min_value=0.0,
                        value=float(st.session_state.get("peso_bruto", 0.0)),
                        step=0.1, format="%.2f", key="peso_bruto")
    with p3:
        peso_aplicable = max(st.session_state.peso_bruto, total_peso_vol)
        st.metric("Peso aplicable (kg) ", f"{peso_aplicable:.2f}")

    st.markdown("### Valor de la mercadería")
    st.number_input("Valor de la mercadería (USD)", min_value=0.0,
                    value=float(st.session_state.get("valor_mercaderia", 0.0)),
                    step=1.0, format="%.2f", key="valor_mercaderia")

    submit = st.form_submit_button("📨 Solicitar cotización")

# ============== Validación + Envío ==============
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
    valid_rows = edited[
        (edited["Cantidad de bultos"] > 0) &
        (edited["Ancho (cm)"] > 0) &
        (edited["Alto (cm)"] > 0) &
        (edited["Largo (cm)"] > 0)
    ]
    if valid_rows.empty:
        errs.append("Agregá al menos un bulto con medidas > 0.")
    if len(edited) > MAX_ROWS:
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
                "es_cliente": st.session_state.es_cliente,   # "No" o "Sí"
            },
            "producto": {
                "descripcion": st.session_state.descripcion.strip(),
                "link": st.session_state.link.strip(),
            },
            "bultos": edited_calc.to_dict(orient="records"),
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
            st.success("✅ ¡Gracias! En breve recibirás tu cotización por email.")
            # Debug sólo si ?debug=1
            debug_flag = False
            try:
                debug_flag = st.query_params.get("debug", ["0"])[0] == "1"
            except Exception:
                try:
                    debug_flag = st.experimental_get_query_params().get("debug", ["0"])[0] == "1"
                except Exception:
                    debug_flag = False
            if debug_flag:
                with st.expander("Payload enviado (debug)"):
                    st.json(payload)
            reset_form_state()
            st.rerun()
        else:
            st.error("No pudimos enviar tu solicitud.")
            st.code(msg)
