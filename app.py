import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="GlobalTripLog - Cotizador", page_icon="🧮", layout="centered")

st.title("🧮 Cotizador GlobalTripLog")
st.caption("Calcula costos estimados de importación basados en valor declarado, peso real y volumétrico.")

# Sidebar - Parámetros configurables
st.sidebar.header("⚙️ Configuración")
moneda = st.sidebar.selectbox("Moneda base", ["USD", "ARS"], index=0)
tc = st.sidebar.number_input("Tipo de cambio (ARS por USD)", min_value=0.0, value=1000.0, step=1.0)
tarifa_kg = st.sidebar.number_input("Tarifa por kg (moneda base)", min_value=0.0, value=8.0, step=0.5)
cargo_fijo = st.sidebar.number_input("Cargo fijo (moneda base)", min_value=0.0, value=5.0, step=1.0)
factor_vol = st.sidebar.number_input("Factor volumétrico (cm³/kg)", min_value=1000, value=5000, step=100)

st.sidebar.subheader("Impuestos")
umbral = st.sidebar.number_input("Umbral libre (USD)", min_value=0.0, value=50.0, step=5.0)
alicuota = st.sidebar.number_input("Alícuota (%)", min_value=0.0, value=50.0, step=1.0)
recargos = st.sidebar.number_input("Otros recargos (%)", min_value=0.0, value=0.0, step=1.0)
tasas_fijas = st.sidebar.number_input("Tasas fijas (moneda base)", min_value=0.0, value=0.0, step=1.0)

# Inputs de usuario
col1, col2 = st.columns(2)
with col1:
    valor_usd = st.number_input("Valor mercadería (USD)", min_value=0.0, value=120.0, step=1.0)
    peso_real = st.number_input("Peso real (kg)", min_value=0.0, value=1.8, step=0.1)
with col2:
    largo = st.number_input("Largo (cm)", min_value=0.0, value=40.0, step=1.0)
    ancho = st.number_input("Ancho (cm)", min_value=0.0, value=35.0, step=1.0)
    alto  = st.number_input("Alto (cm)", min_value=0.0, value=25.0, step=1.0)

# Cálculos
volumen = largo * ancho * alto
peso_vol = volumen / factor_vol
peso_fact = max(peso_real, peso_vol)

costo_envio_base = cargo_fijo + tarifa_kg * peso_fact
costo_envio_usd = costo_envio_base if moneda == "USD" else costo_envio_base / tc

excedente = max(0.0, valor_usd - umbral)
imp_principal = (excedente + costo_envio_usd) * (alicuota / 100.0)
otros_recargos = (valor_usd + costo_envio_usd) * (recargos / 100.0)
tasas_usd = tasas_fijas if moneda == "USD" else tasas_fijas / tc

subtotal_usd = valor_usd + costo_envio_usd
impuestos_usd = imp_principal + otros_recargos + tasas_usd
total_usd = subtotal_usd + impuestos_usd

# Funciones de conversión
def usd_a_base(x): 
    return x if moneda == "USD" else x * tc

# Tabla de resultados
df = pd.DataFrame({
    "Concepto": [
        "Valor mercadería",
        "Envío",
        "Impuesto principal",
        "Otros recargos",
        "Tasas fijas",
        "TOTAL"
    ],
    "USD": [
        valor_usd,
        costo_envio_usd,
        imp_principal,
        otros_recargos,
        tasas_usd,
        total_usd
    ],
    "ARS": [
        usd_a_base(valor_usd),
        usd_a_base(costo_envio_usd),
        usd_a_base(imp_principal),
        usd_a_base(otros_recargos),
        usd_a_base(tasas_usd),
        usd_a_base(total_usd)
    ]
})

df["USD"] = df["USD"].round(2)
df["ARS"] = df["ARS"].round(2)

st.subheader("📦 Resumen")
st.write(f"Peso real: **{peso_real:.2f} kg** · Peso volumétrico: **{peso_vol:.2f} kg** · Peso facturable: **{peso_fact:.2f} kg**")

st.dataframe(df, use_container_width=True)

st.success(f"**Total estimado:** {round(total_usd, 2)} USD  |  {round(usd_a_base(total_usd), 2)} ARS")

# Exportar CSV
st.markdown("### 📤 Exportar cotización")
nombre_archivo = f"cotizacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Descargar CSV", csv, file_name=nombre_archivo, mime="text/csv")
