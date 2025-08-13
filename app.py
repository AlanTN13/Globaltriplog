import math
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# ---------- Config ----------
st.set_page_config(
    page_title="GlobalTrip | Cotizador",
    page_icon="🌍",
    layout="wide"
)

# ---------- Estilos (Montserrat + colores) ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');

:root{
  --gt-primary:#3366CC;
  --gt-dark:#003B6F;
  --gt-light:#F5F7FA;
  --gt-success:#2EBD85;
  --gt-warn:#FFB020;
  --gt-error:#E45858;
}

html, body, [class*="css"]  {
  font-family: 'Montserrat', sans-serif !important;
}

.block-container{
  padding-top: 2.2rem;
  padding-bottom: 3rem;
}

.gt-hero{
  background: linear-gradient(120deg, var(--gt-dark) 0%, var(--gt-primary) 60%);
  border-radius: 18px;
  padding: 34px 28px;
  color: #fff;
  box-shadow: 0 6px 24px rgba(0,0,0,.18);
}

.gt-badge{
  display:inline-flex; gap:.5rem; align-items:center;
  background: rgba(255,255,255,.14);
  padding: .35rem .65rem; border-radius: 999px; font-size:.85rem;
}

.gt-card{
  background: #fff; border: 1px solid #E7ECF2; border-radius: 14px;
  padding: 22px; box-shadow: 0 2px 10px rgba(0,0,0,.04);
}

.gt-muted{ color:#6B7A90; }

.gt-pipe{ height: 22px; width: 2px; background: rgba(255,255,255,.35); display:inline-block; margin:0 .65rem; }

.stButton>button{
  background: var(--gt-primary) !important;
  color:#fff !important;
  border: 0 !important;
  border-radius: 10px !important;
  padding: .6rem 1.1rem !important;
  font-weight: 700 !important;
  box-shadow: 0 6px 16px rgba(51,102,204,.28) !important;
}
.stButton>button:hover{ filter:brightness(1.05); transform: translateY(-1px); }
.stButton>button:active{ transform: translateY(0); }

[data-testid="stHeader"] { display:none; } /* limpia header default */
</style>
""", unsafe_allow_html=True)

# ---------- Encabezado ----------
col_logo, col_title, col_cta = st.columns([1,3,2], vertical_alignment="center")
with col_logo:
    # Usá la ruta raw de tu logo en GitHub o súbelo a /assets y referenciarlo
    st.image(
        "https://raw.githubusercontent.com/AlanTN13/Globaltriplog/main/assets/globaltrip_logo.png",
        width=120
    )
with col_title:
    st.markdown(f"""
    <div class="gt-hero">
      <div class="gt-badge">🚀 Cotizador Express <span class="gt-pipe"></span> v{datetime.now():%Y.%m.%d}</div>
      <h1 style="margin:.4rem 0 0 0;">GlobalTrip</h1>
      <p style="margin:.35rem 0 0 0; opacity:.92;">Calculá tu envío internacional con precisión volumétrica y costos estimados en segundos.</p>
    </div>
    """, unsafe_allow_html=True)

with col_cta:
    st.markdown("<div class='gt-card'>", unsafe_allow_html=True)
    st.markdown("**Soporte**\n\n¿Necesitás ayuda? Escribinos:")
    st.markdown("✉️ **ops@globaltriplog.com**")
    st.markdown("📞 **+54 11 1234 5678**")
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# ---------- Sidebar (parámetros generales) ----------
with st.sidebar:
    st.markdown("### Parámetros")
    origen = st.selectbox("Origen", ["China", "USA", "Europa"], index=0)
    destino = st.selectbox("Destino", ["Argentina"], index=0)
    moneda = st.selectbox("Moneda", ["USD", "ARS"], index=0)

    st.divider()
    st.markdown("### Reglas de cálculo")
    # Factor volumétrico usado habitualmente por courier (cm)
    factor_vol = st.number_input("Factor volumétrico (cm³/kg)", value=5000, step=100)
    # Mínimo facturable por pieza o envío (opcional)
    minimo_kg = st.number_input("Mínimo facturable (kg)", value=0.5, step=0.1)

    st.divider()
    st.caption("💡 Tip: Podés duplicar filas en la tabla para múltiples bultos.")

# ---------- Formulario de bultos ----------
st.markdown("### 📦 Detalle de bultos")
st.markdown(
    "<div class='gt-muted'>Ingresá medidas en centímetros y peso real en kilogramos. El sistema calcula el peso volumétrico por pieza y total.</div>",
    unsafe_allow_html=True
)

n = st.number_input("Cantidad de filas", min_value=1, max_value=20, value=3)
rows = []
cols = st.columns([1,1,1,1,1,1])
with cols[0]: st.markdown("**Cant.**")
with cols[1]: st.markdown("**Ancho (cm)**")
with cols[2]: st.markdown("**Alto (cm)**")
with cols[3]: st.markdown("**Largo (cm)**")
with cols[4]: st.markdown("**Peso real (kg)**")
with cols[5]: st.markdown("**Peso vol. (kg)**")

total_peso_real = 0.0
total_peso_vol = 0.0

for i in range(int(n)):
    c0, c1, c2, c3, c4, c5 = st.columns([1,1,1,1,1,1])
    with c0:
        cant = st.number_input(f"cant_{i}", min_value=0, value=1, label_visibility="collapsed")
    with c1:
        ancho = st.number_input(f"an_{i}", min_value=0.0, value=10.0, step=0.1, label_visibility="collapsed")
    with c2:
        alto = st.number_input(f"al_{i}", min_value=0.0, value=10.0, step=0.1, label_visibility="collapsed")
    with c3:
        largo = st.number_input(f"la_{i}", min_value=0.0, value=10.0, step=0.1, label_visibility="collapsed")
    with c4:
        peso_r = st.number_input(f"pr_{i}", min_value=0.0, value=1.0, step=0.1, label_visibility="collapsed")

    # peso volumétrico por pieza (cm*cm*cm / factor)
    peso_v = (ancho * alto * largo) / factor_vol if factor_vol > 0 else 0.0
    # aplica mínimo por pieza si corresponde
    peso_v = max(peso_v, minimo_kg)
    with c5:
        st.write(f"**{peso_v:.2f}**")

    total_peso_real += cant * peso_r
    total_peso_vol += cant * peso_v
    rows.append({
        "cant": cant, "ancho": ancho, "alto": alto, "largo": largo,
        "peso_real": peso_r, "peso_vol": peso_v
    })

df = pd.DataFrame(rows)

# ---------- Tarifa y costos ----------
st.markdown("### 💵 Parámetros económicos")
c1, c2, c3 = st.columns(3)
with c1:
    valor_merc = st.number_input("Valor de la mercadería (USD)", value=500.0, step=50.0)
with c2:
    tarifa_kg = st.number_input("Tarifa por kg (USD/kg)", value=8.0, step=0.5)
with c3:
    seguro_pct = st.number_input("Seguro % sobre CIF (0-100)", value=0.8, step=0.1)

# Pesos de facturación
peso_facturable = max(total_peso_real, total_peso_vol)

# Componentes de costo (ejemplo simplificado)
flete = tarifa_kg * peso_facturable
# CIF ~ valor mercadería + flete (simplificado; podrías sumar otros)
cif = valor_merc + flete
seguro = cif * (seguro_pct / 100.0)
handling = 25.0
almacen = 0.80 * max(1, math.ceil(peso_facturable))  # ejemplo
otros = 15.0

total_final = flete + seguro + handling + almacen + otros

# ---------- Resumen ----------
left, right = st.columns([1.2, 1])
with left:
    st.markdown("### 📊 Resumen de pesos")
    st.markdown("<div class='gt-card'>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Peso real total", f"{total_peso_real:.2f} kg")
    m2.metric("Peso volumétrico total", f"{total_peso_vol:.2f} kg")
    m3.metric("Peso facturable", f"{peso_facturable:.2f} kg")
    st.dataframe(
        df.rename(columns={
            "cant":"Cant.", "ancho":"Ancho", "alto":"Alto", "largo":"Largo",
            "peso_real":"Peso real (kg)", "peso_vol":"Peso vol. (kg)"
        }),
        use_container_width=True, hide_index=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("### 💳 Cotización estimada")
    st.markdown("<div class='gt-card'>", unsafe_allow_html=True)
    st.write("**Conceptos**")
    concepts = pd.DataFrame([
        ["Flete", f"${flete:,.2f}"],
        ["Seguro", f"${seguro:,.2f}"],
        ["Handling", f"${handling:,.2f}"],
        ["Almacenaje (estimado)", f"${almacen:,.2f}"],
        ["Otros", f"${otros:,.2f}"],
    ], columns=["Concepto","Monto (USD)"])
    st.table(concepts)
    st.markdown("---")
    st.markdown(f"### Total final: **${total_final:,.2f} USD**")
    st.caption("Valores estimados. La cotización final puede variar según inspección, normativa y recargos.")

    st.markdown("</div>", unsafe_allow_html=True)

st.write("")
st.markdown("###### ¿Querés que te enviemos el PDF de la cotización?")
c_mail, c_btn = st.columns([3,1])
with c_mail:
    email = st.text_input("Email de contacto", label_visibility="collapsed", placeholder="tu@empresa.com")
with c_btn:
    if st.button("Solicitar envío PDF"):
        if email.strip():
            st.success("¡Listo! Te vamos a enviar el detalle al correo ingresado. 🙌")
        else:
            st.error("Ingresá un email válido, por favor.")

# ---------- Footer ----------
st.write("")
st.markdown(
    f"<div class='gt-muted'>© {datetime.now():%Y} GlobalTrip. Todos los derechos reservados.</div>",
    unsafe_allow_html=True
)

