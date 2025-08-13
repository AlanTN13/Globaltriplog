# app.py
import re
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# ================== Config básica ==================
st.set_page_config(page_title="Cotización GlobalTrip", page_icon="🧮", layout="wide")

st.markdown("""
<style>
  .hero{background:linear-gradient(90deg,rgba(11,123,214,.12),rgba(11,123,214,.05));
        border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:18px 20px;margin-bottom:14px}
  .hero h1{margin:0;font-size:28px}
  .sub{color:#b9c2cf;margin-top:6px}
</style>
""", unsafe_allow_html=True)

# ================== Parámetros negocio ==================
FACTOR_VOL = 5000   # cm³/kg (coincide con tu planilla)
MAX_ROWS   = 20

# ================== Helpers ==================
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
    except:
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
        return False, "Falta configurar N8N_WEBHOOK_URL en *Settings → Secrets* (TOML)."
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(url, json=payload, headers=headers, timeout=20)
    ok = 200 <= r.status_code < 300
    return ok, r.text or str(r.status_code)

# ================== Header ==================
st.markdown("""
<div class="hero">
  <h1>🧮 Cotización de Envío por Courier</h1>
  <div class="sub">Completá tus datos y la información del envío. Te enviaremos la cotización por email.</div>
</div>
""", unsafe_allow_html=True)

# ================== Estado inicial tabla ==================
if "bultos_df" not in st.session_state:
    st.session_state.bultos_df = pd.DataFrame(
        [
            {"Cantidad de bultos": 1, "Ancho (cm)": 10, "Alto (cm)": 10, "Largo (cm)": 194},
            {"Cantidad de bultos": 1, "Ancho (cm)": 40, "Alto (cm)": 28, "Largo (cm)": 48},
            *[{"Cantidad de bultos": 0, "Ancho (cm)": 0, "Alto (cm)": 0, "Largo (cm)": 0} for _ in range(6)]
        ]
    )

# ================== FORM ==================
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

    # --- Bultos (tabla única; todo editable salvo Peso vol.) ---
    st.markdown("### Bultos")
    st.caption("Ingresá por bulto: cantidad y dimensiones en **cm**. El peso volumétrico se calcula solo.")
    df_show = add_peso_vol(st.session_state.bultos_df.copy())

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
            "Peso vol. (kg) 🔒": st.column_config.NumberColumn("Peso vol. (kg) 🔒", step=0.01, disabled=True, help="Se calcula automáticamente"),
        },
        key="editor_bultos",
    )

    # normalizo y recalculo
    edited = edited.copy()
    edited["Cantidad de bultos"] = edited["Cantidad de bultos"].fillna(0).astype(int)
    for col in ["Ancho (cm)", "Alto (cm)", "Largo (cm)"]:
        edited[col] = edited[col].fillna(0).astype(float)
    edited = add_peso_vol(edited)
    st.session_state.bultos_df = edited

    total_peso_vol = round(edited["Peso vol. (kg) 🔒"].sum(), 2)

    # --- Pesos (alineados: métricas bloqueadas + input editable) ---
    st.markdown("### Pesos")
    p1, p2, p3 = st.columns(3)
    with p1:
        st.metric("Peso volumétrico (kg) 🔒", f"{total_peso_vol:.2f}")
    with p2:
        peso_bruto = st.number_input(
            "Peso bruto (kg)",
            min_value=0.0,
            value=float(st.session_state.get("peso_bruto", 0.0)),
            step=0.1,
            format="%.2f",
            key="peso_bruto_input",
        )
        st.session_state.peso_bruto = peso_bruto
    with p3:
        peso_aplicable = max(peso_bruto, total_peso_vol)
        st.metric("Peso aplicable (kg) 🔒", f"{peso_aplicable:.2f}")

    # --- Valor general de la compra ---
    st.markdown("### Valor de la mercadería")
    valor_mercaderia = st.number_input(
        "Valor de la mercadería (USD)",
        min_value=0.0,
        value=float(st.session_state.get("valor_mercaderia", 0.0)),
        step=1.0,
        format="%.2f",
        key="valor_mercaderia_input",
    )
    st.session_state.valor_mercaderia = valor_mercaderia

    # --- Enviar ---
    submit = st.form_submit_button("📨 Solicitar cotización")

# ================== Validación + Envío ==================
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
                "peso_bruto": st.session_state.get("peso_bruto", 0.0),
                "peso_aplicable": max(st.session_state.get("peso_bruto", 0.0), total_peso_vol),
                "valor_mercaderia": st.session_state.get("valor_mercaderia", 0.0),
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
