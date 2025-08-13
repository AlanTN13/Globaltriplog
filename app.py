import pandas as pd
import numpy as np
import streamlit as st

# ----- Brand -----
PRIMARY = "#0B3A66"     # Azul GlobalTrip
ACCENT   = "#FFB703"     # Detalle cálido (botones / resaltes)

st.set_page_config(page_title="GlobalTrip — Cotización Courier", page_icon="📦", layout="wide")

# ----- Estilos rápidos -----
st.markdown(f"""
<style>
:root {{
  --primary: {PRIMARY};
  --accent: {ACCENT};
}}
.block-container {{ padding-top: 1.2rem; }}
h1, h2, h3, h4 {{ color: var(--primary); font-weight: 700; }}
.stButton>button {{ background: var(--primary); border: 0; color: #fff; }}
.stButton>button:hover {{ filter: brightness(1.05); }}
div[data-testid="stHeader"] {{ background: transparent; }}
</style>
""", unsafe_allow_html=True)

# ----- Hero -----
col_logo, col_title = st.columns([1,3], gap="large")
with col_logo:
    st.image("https://raw.githubusercontent.com/AlanTN13/globaltriplog/main/.devcontainer/GlobalTrip-logo.png", width=140)  # Cambiá si querés
with col_title:
    st.title("Cotización de Envío por Courier")
    st.caption("Ingresá los datos de tus bultos. Nosotros nos encargamos del resto.")

st.divider()

# ----- Panel lateral (parámetros generales) -----
with st.sidebar:
    st.subheader("Parámetros")
    origen  = st.selectbox("Origen", ["China", "USA", "Europa", "Otro"], index=0)
    destino = st.selectbox("Destino", ["Argentina", "Chile", "Uruguay", "Paraguay", "Otro"], index=0)
    moneda  = st.selectbox("Moneda", ["USD", "ARS", "EUR"], index=0)

    st.subheader("Reglas de cálculo")
    factor_vol = st.number_input("Factor volumétrico (cm³/kg)", value=5000, min_value=1000, step=100)
    min_fact_kg = st.number_input("Mínimo facturable (kg)", value=0.50, min_value=0.0, step=0.1)

# ----- Tabla editable tipo Excel -----
st.subheader("📦 Detalle de bultos")

# columnas base
cols = ["Cant.", "Ancho (cm)", "Alto (cm)", "Largo (cm)", "Peso real (kg)"]
defaults = pd.DataFrame({
    "Cant.": [1, 1, 0, 0, 0, 0, 0, 0],
    "Ancho (cm)": [10, 40, 0, 0, 0, 0, 0, 0],
    "Alto (cm)":  [10, 28, 0, 0, 0, 0, 0, 0],
    "Largo (cm)": [194, 48, 0, 0, 0, 0, 0, 0],
    "Peso real (kg)": [3.88, 10.75, 0, 0, 0, 0, 0, 0],
})

edited = st.data_editor(
    defaults,
    key="tabla_bultos",
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Cant.": st.column_config.NumberColumn(min_value=0, step=1, width="small"),
        "Ancho (cm)": st.column_config.NumberColumn(min_value=0.0, step=0.5),
        "Alto (cm)":  st.column_config.NumberColumn(min_value=0.0, step=0.5),
        "Largo (cm)": st.column_config.NumberColumn(min_value=0.0, step=0.5),
        "Peso real (kg)": st.column_config.NumberColumn(min_value=0.0, step=0.1),
    }
)

# ----- Cálculos simples (como tu hoja) -----
df = edited.copy().fillna(0)

# peso volumétrico por pieza = (ancho*alto*largo)/factor_vol
vol_por_pieza = (df["Ancho (cm)"] * df["Alto (cm)"] * df["Largo (cm)"]) / factor_vol
df["Peso vol. (kg)"] = np.round(vol_por_pieza * df["Cant."], 2)

# totales
peso_real_total = np.round((df["Peso real (kg)"] * df["Cant."]).sum(), 2)
peso_vol_total  = np.round(df["Peso vol. (kg)"].sum(), 2)
peso_facturable = max(peso_real_total, peso_vol_total, min_fact_kg)

st.subheader("📊 Resumen de pesos")
c1, c2, c3 = st.columns(3)
c1.metric("Peso real total", f"{peso_real_total:.2f} kg")
c2.metric("Peso volumétrico total", f"{peso_vol_total:.2f} kg")
c3.metric("Peso facturable", f"{peso_facturable:.2f} kg")

# Mostrar tabla con columna calculada
st.dataframe(df, use_container_width=True)

st.divider()

# ----- Datos comerciales básicos (opcional) -----
st.subheader("💲 Parámetros económicos (opcional)")
c1, c2, c3 = st.columns(3)
valor_merc = c1.number_input("Valor de la mercadería (USD)", value=500.0, min_value=0.0, step=10.0)
tarifa_kg   = c2.number_input("Tarifa por kg (USD/kg)", value=8.0, min_value=0.0, step=0.5)
seguro_pct  = c3.number_input("Seguro % sobre CIF (0-100)", value=0.8, min_value=0.0, step=0.1)

# Estimación súper simple (puedes reemplazar luego por tu backend)
# Flete básico
flete = np.round(peso_facturable * tarifa_kg, 2)
# Seguro aproximado
cif_aprox = valor_merc + flete
seguro = np.round(cif_aprox * (seguro_pct/100.0), 2)
# Otros fijos (ejemplo)
handling = 25.00
almacen = 2.40

estimacion = pd.DataFrame({
    "Concepto": ["Flete", "Seguro", "Handling", "Almacenaje (estimado)", "Otros"],
    "Monto (USD)": [flete, seguro, handling, almacen, 15.00],
})

st.subheader("🧾 Cotización estimada")
st.dataframe(estimacion, use_container_width=True)
total_final = np.round(estimacion["Monto (USD)"].sum(), 2)
st.markdown(f"### Total final: **${total_final:.2f} {moneda}**")
st.caption("Valores estimados. La cotización final puede variar según inspección, normativa y recargos.")

st.divider()

# ----- Envío / captura (para “calcular por atrás”) -----
st.subheader("📨 ¿Querés que te enviemos el PDF / respuesta?")
email = st.text_input("Email de contacto", placeholder="tu@empresa.com")

colA, colB = st.columns([1,1])
with colA:
    enviar = st.button("Enviar consulta")
with colB:
    limpiar = st.button("Limpiar todo")

if enviar:
    payload = {
        "origen": origen,
        "destino": destino,
        "moneda": moneda,
        "factor_volumetrico": factor_vol,
        "min_facturable": min_fact_kg,
        "tabla": df.to_dict(orient="records"),
        "resumen": {
            "peso_real_total": float(peso_real_total),
            "peso_vol_total": float(peso_vol_total),
            "peso_facturable": float(peso_facturable),
        },
        "economico": {
            "valor_mercaderia": float(valor_merc),
            "tarifa_kg": float(tarifa_kg),
            "seguro_pct": float(seguro_pct),
            "estimacion": estimacion.to_dict(orient="records"),
            "total_final": float(total_final)
        },
        "email": email,
    }
    # Aquí después podés: guardar en Google Sheets, mandar a un webhook, o enviar email.
    # Por ahora mostramos un “OK” y el JSON si querés copiarlo.
    st.success("Consulta enviada. ¡Te contactamos a la brevedad!")
    with st.expander("Ver JSON enviado"):
        st.json(payload)

if limpiar:
    st.session_state.pop("tabla_bultos", None)
    st.rerun()

# Footer
st.markdown("---")
st.caption("© GlobalTrip. Todos los derechos reservados.")
