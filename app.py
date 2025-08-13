# app.py
import pandas as pd
import requests
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Cotización Courier China", page_icon="🧮", layout="wide")

# ----------------- Parámetros -----------------
FACTOR_VOL = 5000  # cm³/kg  → da 3.88 y 10.75 como en tu planilla

st.markdown("<h2 style='text-align:center;background:#14a0ff;color:white;padding:.6rem;border-radius:8px;'>COTIZACION COURIER CHINA</h2>", unsafe_allow_html=True)
st.caption("Esta planilla es automática. Ud. **solo** completa los campos amarillos.")

# ----------------- Helpers -----------------
def calc_peso_vol_row(r):
    try:
        q = max(0, int(r.get("Cantidad", 0)))
        a = float(r.get("Ancho (cm)", 0))
        h = float(r.get("Alto (cm)", 0))
        l = float(r.get("Largo (cm)", 0))
        if q <= 0 or a <= 0 or h <= 0 or l <= 0:
            return 0.0
        return round(q * (a * h * l) / FACTOR_VOL, 2)
    except Exception:
        return 0.0

# ----------------- Bultos (una sola grilla) -----------------
if "bultos_df" not in st.session_state:
    st.session_state.bultos_df = pd.DataFrame(
        [
            {"Cantidad": 1, "Ancho (cm)": 10, "Alto (cm)": 10, "Largo (cm)": 194},
            {"Cantidad": 1, "Ancho (cm)": 40, "Alto (cm)": 28, "Largo (cm)": 48},
            *[{"Cantidad": 0, "Ancho (cm)": 0, "Alto (cm)": 0, "Largo (cm)": 0} for _ in range(6)]
        ]
    )

# calcular antes de mostrar
df_to_show = st.session_state.bultos_df.copy()
df_to_show["Peso vol."] = df_to_show.apply(calc_peso_vol_row, axis=1)

st.markdown("### Bultos")
edited = st.data_editor(
    df_to_show,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Peso vol.": st.column_config.NumberColumn("Peso vol.", step=0.01, disabled=True)
    },
    key="bultos_editor",
)

# recalcular después de editar y guardar en sesión
edited = edited.drop(columns=["Peso vol."], errors="ignore")
edited["Peso vol."] = edited.apply(calc_peso_vol_row, axis=1)
st.session_state.bultos_df = edited

total_peso_vol = round(edited["Peso vol."].sum(), 2)
st.metric("Total peso volumétrico (kg)", f"{total_peso_vol:.2f}")

st.divider()

# ----------------- Base imponible (solo 2 campos editables) -----------------
st.markdown("### Cálculos para la base imponible:")
c1, c2, c3, c4 = st.columns([1,1,1,1])
with c1:
    valor_merc = st.number_input("Valor de la mercadería (USD)", min_value=0.0, value=519.00, step=1.0)
with c2:
    peso_bruto = st.number_input("Peso bruto (kg)", min_value=0.0, value=20.20, step=0.1)
with c3:
    st.number_input("Peso volumétrico (kg)", value=float(total_peso_vol), step=0.01, disabled=True)
with c4:
    peso_aplicable = max(peso_bruto, total_peso_vol)
    st.number_input("Peso aplicable (kg)", value=float(peso_aplicable), step=0.01, disabled=True)

st.divider()

# ----------------- Enviar a n8n -----------------
st.markdown("### Enviar cotización")
n8n_url = st.secrets.get("N8N_WEBHOOK_URL", "")
n8n_token = st.secrets.get("N8N_TOKEN", "")

payload = {
    "timestamp": datetime.utcnow().isoformat(),
    "origen": "streamlit-cotizador",
    "factor_vol": FACTOR_VOL,
    "bultos": edited.to_dict(orient="records"),
    "totales": {
        "peso_vol_total": total_peso_vol,
        "peso_bruto": peso_bruto,
        "peso_aplicable": peso_aplicable,
        "valor_mercaderia": valor_merc,
    }
}

if st.button("📨 ENVIAR", type="primary"):
    if not n8n_url:
        st.error("Falta configurar N8N_WEBHOOK_URL en Settings → Secrets (TOML).")
    else:
        headers = {"Content-Type": "application/json"}
        if n8n_token:
            headers["Authorization"] = f"Bearer {n8n_token}"
        try:
            r = requests.post(n8n_url, json=payload, headers=headers, timeout=20)
            if 200 <= r.status_code < 300:
                st.success("Enviado a n8n correctamente ✅")
                with st.expander("Payload enviado"):
                    st.json(payload)
                with st.expander("Respuesta de n8n"):
                    st.code(r.text)
            else:
                st.error(f"n8n devolvió estado {r.status_code}.")
                st.code(r.text)
        except Exception as e:
            st.error(f"Error enviando a n8n: {e}")
