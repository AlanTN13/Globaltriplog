import pandas as pd
import requests
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Cotización Courier China", page_icon="🧮", layout="wide")

# ---------- Parámetros fijos mínimos ----------
FACTOR_VOL = 6000  # cm³/kg para peso volumétrico

st.markdown("<h2 style='text-align:center;background:#14a0ff;color:white;padding:.6rem;border-radius:8px;'>COTIZACION COURIER CHINA</h2>", unsafe_allow_html=True)
st.caption("Esta planilla es automática. Ud. **solo** completa los campos amarillos.")

# ---------- Tabla única: Bultos (con Peso vol. calculado) ----------
st.markdown("### Bultos")

# filas por defecto
rows = [
    {"Cantidad": 1, "Ancho (cm)": 10, "Alto (cm)": 10, "Largo (cm)": 194, "Peso vol.": 0.0},
    {"Cantidad": 1, "Ancho (cm)": 40, "Alto (cm)": 28, "Largo (cm)": 48,  "Peso vol.": 0.0},
    *[{"Cantidad": 0, "Ancho (cm)": 0, "Alto (cm)": 0, "Largo (cm)": 0, "Peso vol.": 0.0} for _ in range(6)]
]
df_default = pd.DataFrame(rows)

def calc_peso_vol(r):
    q = max(0, int(r["Cantidad"]))
    a, h, l = float(r["Ancho (cm)"]), float(r["Alto (cm)"]), float(r["Largo (cm)"])
    if q <= 0 or a <= 0 or h <= 0 or l <= 0: return 0.0
    return round(q * (a * h * l) / FACTOR_VOL, 2)

# Editor (marcamos Peso vol. como deshabilitado)
edited = st.data_editor(
    df_default,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Peso vol.": st.column_config.NumberColumn("Peso vol.", step=0.01, disabled=True)
    },
    key="bultos_editor",
)

# Recalcular Peso vol. y total
edited["Peso vol."] = edited.apply(calc_peso_vol, axis=1)
total_peso_vol = round(edited["Peso vol."].sum(), 2)
st.metric("Total peso volumétrico (kg)", f"{total_peso_vol:.2f}")

st.divider()

# ---------- Base imponible (solo dos campos editables) ----------
st.markdown("### Cálculos para la base imponible:")

col1, col2, col3, col4 = st.columns([1,1,1,1])
with col1:
    valor_merc = st.number_input("Valor de la mercadería (USD)", min_value=0.0, value=519.00, step=1.0)
with col2:
    peso_bruto = st.number_input("Peso bruto (kg)", min_value=0.0, value=20.20, step=0.1)
with col3:
    st.number_input("Peso volumétrico (kg)", value=float(total_peso_vol), step=0.01, disabled=True)
with col4:
    peso_aplicable = max(peso_bruto, total_peso_vol)
    st.number_input("Peso aplicable (kg)", value=float(peso_aplicable), step=0.01, disabled=True)

st.divider()

# ---------- Enviar a n8n ----------
st.markdown("### Enviar cotización")
n8n_url = st.secrets.get("N8N_WEBHOOK_URL", "")
n8n_token = st.secrets.get("N8N_TOKEN", "")

payload = {
    "timestamp": datetime.utcnow().isoformat(),
    "origen": "streamlit-cotizador",
    "bultos": edited.to_dict(orient="records"),
    "factor_vol": FACTOR_VOL,
    "totales": {
        "peso_vol_total": total_peso_vol,
        "peso_bruto": peso_bruto,
        "peso_aplicable": peso_aplicable,
        "valor_mercaderia": valor_merc,
    }
}

enviar = st.button("📨 ENVIAR", type="primary")
if enviar:
    if not n8n_url:
        st.error("Falta configurar N8N_WEBHOOK_URL en *Settings → Secrets* (TOML).")
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
