import re
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# =============== Tema ==================
st.set_page_config(page_title="Cotización GlobalTrip", page_icon="🧮", layout="wide")

st.markdown("""
<style>
  .hero{background:linear-gradient(90deg,rgba(11,123,214,.12),rgba(11,123,214,.05));
        border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:18px 20px;margin-bottom:14px}
  .hero h1{margin:0;font-size:28px}
  .sub{color:#b9c2cf;margin-top:6px}
  /* lectura más clara para campos bloqueados */
  .readonly input[disabled]{opacity:.55; cursor:not-allowed; background:#1b1f2a!important;}
  .readonly label{opacity:.8}
</style>
""", unsafe_allow_html=True)

# =============== Negocio ==================
FACTOR_VOL = 5000   # cm³/kg
MAX_ROWS   = 20

# =============== Helpers ==================
def is_email(x: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", x or ""))

def is_phone(x: str) -> bool:
    x = (x or "").strip().replace(" ", "").replace("-", "")
    return x.isdigit() and 6 <= len(x) <= 20

def peso_vol_row(q, a, h, l, factor=FACTOR_VOL) -> float:
    try:
        q = int(q); a = float(a); h = float(h); l = float(l)
        if q <= 0 or a <= 0 or h <= 0 or l <= 0: return 0.0
        return round(q * (a * h * l) / factor, 2)
    except:  # noqa
        return 0.0

def add_peso_vol(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Peso vol. (kg) 🔒"] = df.apply(
        lambda r: peso_vol_row(r["Cantidad de bultos"], r["Ancho (cm)"], r["Alto (cm)"], r["Largo (cm)"]),
        axis=1
    )
    return df

def post_to_n8n(payload: dict) -> tuple[bool, str]:
    url = st.secrets.get("N8N_WEBHOOK_URL", "")
    token = st.secrets.get("N8N_TOKEN", "")
    if not url:
        return False, "Falta configurar N8N_WEBHOOK_URL en *Secrets* (TOML)."
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(url, json=payload, headers=headers, timeout=20)
    ok = 200 <= r.status_code < 300
    return ok, r.text or str(r.status_code)

# =============== Estado inicial tabla ==================
if "bultos_df" not in st.session_state:
    st.session_state.bultos_df = pd.DataFrame(
        [
            {"Cantidad de bultos": 1, "Ancho (cm)": 10, "Alto (cm)": 10, "Largo (cm)": 194, "Valor de la mercadería (USD)": 519.0},
            {"Cantidad de bultos": 1, "Ancho (cm)": 40, "Alto (cm)": 28, "Largo (cm)": 48,  "Valor de la mercadería (USD)": 0.0},
            *[{"Cantidad de bultos": 0, "Ancho (cm)": 0, "Alto (cm)": 0, "Largo (cm)": 0, "Valor de la mercadería (USD)": 0.0} for _ in range(6)]
        ]
    )

# =============== Header ==================
st.markdown("""
<div class="hero">
  <h1>🧮 Cotización de Envío por Courier</h1>
  <div class="sub">Completá tus datos y la información del envío. Te enviaremos la cotización por email.</div>
</div>
""", unsafe_allow_html=True)

# =============== FORM ==================
with st.form("cotizacion_form"):
    # --- Datos de contacto ---
    st.markdown("### Datos de contacto")
    c1, c2, c3 = st.columns([1.1, 1.1, 0.9])
    with c1:
        nombre = st.text_input("Nombre completo*", placeholder="Ej: Juan Pérez")
    with c2:
        email = st.text_input("Correo electrónico*", placeholder="ejemplo@email.com")
    with c3:
        telefono = st.text_input("Teléfono*", placeholder="Ej: 11 5555 5555")

    es_cliente = st.radio("¿Sos alumno o cliente de Global Trip?", ["Sí", "No"], horizontal=True)

    # --- Bultos (tabla única) ---
    st.markdown("### Bultos")
    st.caption("Ingresá por bulto: cantidad, dimensiones en **cm**, y valor de mercadería en **USD**.")
    df_show = st.session_state.bultos_df.copy()
    df_show = add_peso_vol(df_show)  # calcula Peso vol. antes de mostrar

    edited = st.data_editor(
        df_show,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Cantidad de bultos": st.column_config.NumberColumn("Cantidad de bultos", step=1, min_value=0),
            "Ancho (cm)": st.column_config.NumberColumn("Ancho (cm)", step=1, min_value=0),
            "Alto (cm)":  st.column_config.NumberColumn("Alto (cm)",  step=1, min_value=0),
            "Largo (cm)": st.column_config.NumberColumn("Largo (cm)", step=1, min_value=0),
            "Valor de la mercadería (USD)": st.column_config.NumberColumn("Valor de la mercadería (USD)", step=1.0, min_value=0.0),
            "Peso vol. (kg) 🔒": st.column_config.NumberColumn("Peso vol. (kg) 🔒", step=0.01, disabled=True, help="Se calcula automáticamente"),
        },
        key="editor_bultos",
    )

    # normalizo y recalculo
    edited = edited.copy()
    edited["Cantidad de bultos"] = edited["Cantidad de bultos"].fillna(0).astype(int)
    for col in ["Ancho (cm)", "Alto (cm)", "Largo (cm)", "Valor de la mercadería (USD)"]:
        edited[col] = edited[col].fillna(0).astype(float)
    edited = add_peso_vol(edited)
    st.session_state.bultos_df = edited

    total_peso_vol   = round(edited["Peso vol. (kg) 🔒"].sum(), 2)
    total_valor_merc = round(float(edited["Valor de la mercadería (USD)"].sum()), 2)

    # --- Pesos (solo bruto editable) ---
    st.markdown("### Pesos")
    colA, colB, colC = st.columns(3)
    with colB:
        # Editable
        peso_bruto = st.number_input("Peso bruto (kg)", min_value=0.0, value=0.0, step=0.1)
    peso_aplicable = max(peso_bruto, total_peso_vol)
    with colA:
        # No editable (más claro)
        with st.container():
            st.markdown('<div class="readonly">', unsafe_allow_html=True)
            st.number_input("Peso volumétrico (kg) 🔒", value=float(total_peso_vol), step=0.01, disabled=True)
            st.markdown('</div>', unsafe_allow_html=True)
    with colC:
        with st.container():
            st.markdown('<div class="readonly">', unsafe_allow_html=True)
            st.number_input("Peso aplicable (kg) 🔒", value=float(peso_aplicable), step=0.01, disabled=True,
                            help="Máximo entre peso bruto y volumétrico")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- Enviar ---
    submit = st.form_submit_button("📨 Solicitar cotización")

# =============== Validación + Envío ==================
def validar_form() -> list[str]:
    errs = []
    if not nombre or len(nombre.strip()) < 2:
        errs.append("Ingresá tu nombre.")
    if not is_email(email):
        errs.append("Ingresá un email válido.")
    if not is_phone(telefono):
        errs.append("Ingresá un teléfono válido (sólo números, 6–20 dígitos).")
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
        for e in errores:
            st.error(e)
    else:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "origen": "streamlit-cotizador",
            "contacto": {
                "nombre": nombre.strip(),
                "email": email.strip(),
                "telefono": telefono.strip(),
                "es_cliente": es_cliente,
            },
            "bultos": edited.to_dict(orient="records"),
            "totales": {
                "peso_vol_total": total_peso_vol,
                "valor_mercaderia_total": total_valor_merc,
                "peso_bruto": peso_bruto,
                "peso_aplicable": peso_aplicable,
                "factor_vol": FACTOR_VOL,
            },
        }
        with st.spinner("Enviando…"):
            ok, msg = post_to_n8n(payload)
        if ok:
            st.success("✅ ¡Gracias! En breve recibirás tu cotización por email.")
            with st.expander("Payload enviado (debug)"):
                st.json(payload)
        else:
            st.error("No pudimos enviar tu solicitud.")
            st.code(msg)
