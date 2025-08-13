import math
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

# ---------------- Config básica ----------------
st.set_page_config(page_title="COTIZACION COURIER CHINA", page_icon="🧮", layout="wide")

# ---------------- Estilos mínimos ----------------
st.markdown("""
<style>
.small-note { font-size: 0.9rem; color:#444; }
.box {
  padding: 1rem; border-radius: 10px; background: #f5f8ff; border: 1px solid #cfe3ff;
}
.tbl-caption { font-weight:700; margin-bottom: .5rem; }
</style>
""", unsafe_allow_html=True)

# ---------------- Título ----------------
st.markdown("<h2 style='text-align:center;background:#14a0ff;color:white;padding:.6rem;border-radius:8px;'>COTIZACION COURIER CHINA:</h2>", unsafe_allow_html=True)

with st.container():
    st.markdown(
        "<div class='box'>"
        "<b>Estimado cliente:</b><br>"
        "A continuación encontrará cotización desde nuestro depósito en Guangzhou hasta nuestras oficinas en Ciudad Autónoma de Buenos Aires."
        "<br><br><b>Esta planilla es automática. Ud. SOLO tiene que completar los campos en amarillo:</b>"
        "</div>",
        unsafe_allow_html=True
    )

st.markdown("### No importa el orden")

# ---------------- Parámetros generales ----------------
with st.expander("⚙️ Parámetros (podés dejarlos como están)", expanded=True):
    colp1, colp2, colp3, colp4 = st.columns([1,1,1,1])
    with colp1:
        factor_vol = st.number_input("Factor volumétrico (cm³/kg)", min_value=1000, value=6000, step=100,
                                     help="Usado para calcular peso volumétrico: (Largo×Ancho×Alto)/factor.")
    with colp2:
        tarifa_kg = st.number_input("Tarifa flete internacional según kg (USD/kg)", min_value=0.0, value=23.0, step=0.5)
    with colp3:
        seguro_pct = st.number_input("Seguro a fines aduaneros (%)", min_value=0.0, value=1.0, step=0.1,
                                     help="% del valor de la mercadería (editable).")
    with colp4:
        coef_base_iva = st.number_input("Coeficiente Base IVA (CIF × coef.)", min_value=1.00, value=1.38, step=0.01,
                                        help="Coeficiente multiplicador para determinar la Base IVA.")

# ---------------- Tabla de bultos ----------------
st.markdown("<div class='tbl-caption'>Bultos</div>", unsafe_allow_html=True)

default_rows = [
    {"Cantidad": 1, "Ancho (cm)": 10, "Alto (cm)": 10, "Largo (cm)": 194},
    {"Cantidad": 1, "Ancho (cm)": 40, "Alto (cm)": 28, "Largo (cm)": 48},
    *[{"Cantidad": 0, "Ancho (cm)": 0, "Alto (cm)": 0, "Largo (cm)": 0} for _ in range(6)]
]
df_input = st.data_editor(
    pd.DataFrame(default_rows),
    num_rows="dynamic",
    use_container_width=True,
    key="bultos_editor",
)

# Calculamos peso volumétrico por fila
def row_peso_vol(r):
    qty = max(0, int(r.get("Cantidad", 0)))
    a = float(r.get("Ancho (cm)", 0))
    h = float(r.get("Alto (cm)", 0))
    l = float(r.get("Largo (cm)", 0))
    if qty <= 0 or a <= 0 or h <= 0 or l <= 0 or factor_vol <= 0:
        return 0.0
    return qty * (a * h * l) / factor_vol

df_calc = df_input.copy()
df_calc["Peso vol."] = df_calc.apply(row_peso_vol, axis=1)
total_peso_vol = round(df_calc["Peso vol."].sum(), 2)

st.dataframe(
    df_calc.assign(**{"Peso vol.": df_calc["Peso vol."].round(2)}),
    use_container_width=True
)

right = st.columns([3,1,1,1,1,2])[5]
right.metric("total peso volumétrico (kg)", f"{total_peso_vol:.2f}")

# ---------------- Base imponible ----------------
st.markdown("### Cálculos para la base imponible:")

c1, c2, c3, c4, c5 = st.columns([1.4,1,1,1,1])
with c1:
    valor_mercaderia = st.number_input("Valor de la mercadería (USD)", min_value=0.0, value=519.00, step=1.0)
with c2:
    peso_bruto = st.number_input("Peso bruto (kg)", min_value=0.0, value=20.20, step=0.1)
with c3:
    peso_volumetrico = st.number_input("Peso volumétrico (kg) (auto)", min_value=0.0, value=float(total_peso_vol), step=0.01, disabled=True)
with c4:
    # Peso aplicable = mayor entre bruto y volumétrico
    peso_aplicable = max(peso_bruto, total_peso_vol)
    st.number_input("Peso aplicable (kg)", value=float(peso_aplicable), step=0.01, disabled=True)
with c5:
    st.write("")

# Flete y seguro (con valores por defecto calculados pero editables)
flete_sugerido = round(tarifa_kg * peso_aplicable, 2)
seguro_sugerido = round(valor_mercaderia * (seguro_pct / 100.0), 2)

c6, c7, c8, c9 = st.columns([1.4,1,1,1])
with c6:
    flete_aduanero = st.number_input("Flete a fines aduaneros (USD)", min_value=0.0, value=flete_sugerido, step=0.1,
                                     help="Editable. Por defecto: tarifa × peso aplicable.")
with c7:
    seguro_aduanero = st.number_input("Seguro a fines aduaneros (USD)", min_value=0.0, value=seguro_sugerido, step=0.1,
                                      help="Editable. Por defecto: % sobre mercadería.")
with c8:
    valor_cif = valor_mercaderia + flete_aduanero + seguro_aduanero
    st.number_input("Valor CIF (USD)", value=float(round(valor_cif, 2)), step=0.01, disabled=True)
with c9:
    base_iva = valor_cif * coef_base_iva
    st.number_input("Base IVA (USD)", value=float(round(base_iva, 2)), step=0.01, disabled=True)

# ---------------- ENVIAR A n8n ----------------
st.markdown("---")
st.markdown("### Enviar cotización")

# Leer secrets (configurá en Streamlit Cloud → Settings → Secrets)
n8n_url = st.secrets.get("N8N_WEBHOOK_URL", "")
n8n_token = st.secrets.get("N8N_TOKEN", "")

payload = {
    "timestamp": datetime.utcnow().isoformat(),
    "origen": "streamlit-cotizador",
    "bultos": df_input.to_dict(orient="records"),
    "factor_vol": factor_vol,
    "total_peso_vol": total_peso_vol,
    "peso_bruto": peso_bruto,
    "peso_aplicable": peso_aplicable,
    "parametros": {
        "tarifa_kg": tarifa_kg,
        "seguro_pct": seguro_pct,
        "coef_base_iva": coef_base_iva
    },
    "valores": {
        "valor_mercaderia": valor_mercaderia,
        "flete_aduanero": flete_aduanero,
        "seguro_aduanero": seguro_aduanero,
        "valor_cif": round(valor_cif, 2),
        "base_iva": round(base_iva, 2),
    }
}

col_send1, col_send2 = st.columns([1,3])
with col_send1:
    enviar = st.button("📨 ENVIAR", type="primary", use_container_width=True)
with col_send2:
    st.markdown(
        "<span class='small-note'>Configura <b>N8N_WEBHOOK_URL</b> (y opcional <b>N8N_TOKEN</b>) en <i>Secrets</i>. "
        "El botón enviará este cálculo como JSON.</span>",
        unsafe_allow_html=True
    )

if enviar:
    if not n8n_url:
        st.error("Falta configurar N8N_WEBHOOK_URL en *Secrets*.")
    else:
        headers = {"Content-Type": "application/json"}
        if n8n_token:
            headers["Authorization"] = f"Bearer {n8n_token}"
        try:
            r = requests.post(n8n_url, json=payload, headers=headers, timeout=20)
            if 200 <= r.status_code < 300:
                st.success("Enviado a n8n correctamente ✅")
                with st.expander("Payload enviado (debug)"):
                    st.json(payload)
                with st.expander("Respuesta de n8n (debug)"):
                    st.code(r.text)
            else:
                st.error(f"n8n devolvió estado {r.status_code}.")
                st.code(r.text)
        except Exception as e:
            st.error(f"Error enviando a n8n: {e}")
