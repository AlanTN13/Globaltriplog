import os
import re
import time
import requests
import pandas as pd
import streamlit as st

# ========= Config mínima (no cambia colores/tema) =========
st.set_page_config(page_title="Cotizador de Envío", page_icon="📦", layout="wide")

DIVISOR_VOLUMETRICO = 5000  # 10x10x20/5000 * cant 10 = 4.00

# =================== Helpers ===================
def parse_num(txt: str) -> float:
    """Convierte texto a float (acepta coma o punto). Vacío o inválido -> 0."""
    s = (txt or "").strip().replace(",", ".")
    if s == "" or not re.match(r"^[+-]?\d*\.?\d*$", s):
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0

def calcular_volumetrico(df: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    safe = df.fillna(0)
    fila = (safe["Ancho (cm)"] * safe["Alto (cm)"] * safe["Largo (cm)"]) / DIVISOR_VOLUMETRICO
    fila = fila * safe["Cantidad de bultos"]
    out = safe.copy()
    out["Peso vol. (kg)"] = fila.round(2)
    return out, float(fila.sum())

def resetear_form():
    st.session_state.df_bultos.loc[:, :] = 0
    st.session_state.df_bultos["Peso vol. (kg)"] = 0.0
    st.session_state.peso_vol_total = 0.0
    st.session_state.peso_bruto_txt = ""
    st.session_state.valor_mercaderia_txt = ""

def get_webhook_url() -> str:
    # 1) Streamlit Secrets, 2) variable de entorno
    try:
        return st.secrets.get("N8N_WEBHOOK_URL", "").strip()  # type: ignore
    except Exception:
        pass
    return os.getenv("N8N_WEBHOOK_URL", "").strip()

# =================== Estado ===================
if "df_bultos" not in st.session_state:
    st.session_state.df_bultos = pd.DataFrame({
        "Cantidad de bultos": [0]*10,
        "Ancho (cm)": [0]*10,
        "Alto (cm)": [0]*10,
        "Largo (cm)": [0]*10,
        "Peso vol. (kg)": [0.0]*10,  # se completa al calcular
    })
if "peso_vol_total" not in st.session_state:
    st.session_state.peso_vol_total = 0.0
if "peso_bruto_txt" not in st.session_state:
    st.session_state.peso_bruto_txt = ""   # texto -> se limpia al escribir
if "valor_mercaderia_txt" not in st.session_state:
    st.session_state.valor_mercaderia_txt = ""
if "mostrar_modal" not in st.session_state:
    st.session_state.mostrar_modal = False

# =================== HERO (ligero, no cambia estilos) ===================
st.title("📦 Cotización de Envío por Courier")
st.caption("Completá tus datos y medidas. Te mandamos la cotización por email.")

# =================== BULTOS ===================
st.header("Bultos")
st.caption(
    'Tip: usá el botón “+” al final de la tabla para agregar más bultos. '
    'Ingresá por bulto: cantidad y dimensiones en cm. El **peso volumétrico** se calcula con el botón.'
)

# Editor (la columna calculada queda bloqueada)
df_edit = st.data_editor(
    st.session_state.df_bultos,
    key="editor_bultos",
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    disabled=["Peso vol. (kg)"],
    column_config={
        "Cantidad de bultos": st.column_config.NumberColumn(min_value=0, step=1, help="Unidades por fila"),
        "Ancho (cm)"       : st.column_config.NumberColumn(min_value=0, step=1),
        "Alto (cm)"        : st.column_config.NumberColumn(min_value=0, step=1),
        "Largo (cm)"       : st.column_config.NumberColumn(min_value=0, step=1),
        "Peso vol. (kg)"   : st.column_config.NumberColumn(format="%.2f", help="Se completa al presionar Calcular"),
    },
)
# Guardamos solo columnas editables (la calculada se pisa al apretar Calcular)
st.session_state.df_bultos.update(df_edit[["Cantidad de bultos","Ancho (cm)","Alto (cm)","Largo (cm)"]])

# Botón calcular (evita recálculo constante)
if st.button("⚖️ Calcular volumétrico"):
    st.session_state.df_bultos, st.session_state.peso_vol_total = calcular_volumetrico(st.session_state.df_bultos)

# =================== PESOS ===================
st.subheader("Pesos")
c1, c2, c3 = st.columns([1, 1, 1.2])
with c1:
    st.metric("Peso volumétrico (kg) 🔒", f"{st.session_state.peso_vol_total:.2f}")

with c2:
    # texto + placeholder -> al tipear se limpia, no se “escribe atrás” del 0.00
    st.session_state.peso_bruto_txt = st.text_input(
        "Peso bruto (kg)", value=st.session_state.peso_bruto_txt, placeholder="0.00",
        help="Peso real total en balanza"
    )

with c3:
    peso_bruto_num = parse_num(st.session_state.peso_bruto_txt)
    peso_aplicable = max(st.session_state.peso_vol_total, peso_bruto_num)
    st.metric("Peso aplicable (kg) 🔒", f"{peso_aplicable:.2f}")

# =================== VALOR MERCADERÍA ===================
st.subheader("Valor de la mercadería")
st.session_state.valor_mercaderia_txt = st.text_input(
    "Valor de la mercadería (USD)", value=st.session_state.valor_mercaderia_txt, placeholder="0.00"
)
valor_merc_num = parse_num(st.session_state.valor_mercaderia_txt)

# =================== CONTACTO Y PRODUCTO ===================
st.subheader("Datos de contacto y del producto")
colL, colR = st.columns(2)
with colL:
    nombre = st.text_input("Nombre completo*")
    email  = st.text_input("Correo electrónico*")
    tel    = st.text_input("Teléfono*")
with colR:
    es_cliente  = st.radio("¿Cliente/alumno de Global Trip?", ["No","Sí"], horizontal=True, index=0)
    descripcion = st.text_area("Descripción del producto*")
    link        = st.text_input("Link del producto o ficha técnica (Alibaba, Amazon, etc.)*")

st.divider()

# =================== SOLICITAR COTIZACIÓN ===================
if st.button("📨 Solicitar cotización", type="primary"):
    st.session_state.mostrar_modal = True

if st.session_state.mostrar_modal:
    with st.modal("Confirmar envío"):
        st.write("Revisá que los datos estén correctos antes de enviar.")
        st.write("**Resumen**")
        st.write(f"- Nombre: {nombre or '—'}")
        st.write(f"- Email: {email or '—'}")
        st.write(f"- Teléfono: {tel or '—'}")
        st.write(f"- ¿Cliente/alumno?: {es_cliente}")
        st.write(f"- Descripción: {descripcion or '—'}")
        st.write(f"- Link: {link or '—'}")
        st.write(f"- Peso volumétrico total: **{st.session_state.peso_vol_total:.2f} kg**")
        st.write(f"- Peso bruto: **{peso_bruto_num:.3f} kg**")
        st.write(f"- Peso aplicable: **{peso_aplicable:.2f} kg**")
        st.write(f"- Valor mercadería: **USD {valor_merc_num:.2f}**")

        b1, b2, b3 = st.columns([1,1,1.2])
        enviar = b1.button("Enviar", key="btn_enviar")
        otra   = b2.button("Solicitar otra cotización", key="btn_otra")
        cerrar = b3.button("Cerrar", key="btn_cerrar")

        if enviar:
            payload = {
                "contacto": {
                    "nombre": nombre, "email": email, "tel": tel, "cliente_alumno": es_cliente
                },
                "producto": {"descripcion": descripcion, "link": link},
                "bultos": st.session_state.df_bultos.fillna(0).to_dict(orient="records"),
                "pesos": {
                    "volumetrico": round(st.session_state.peso_vol_total, 2),
                    "bruto": round(peso_bruto_num, 3),
                    "aplicable": round(peso_aplicable, 2),
                },
                "valor_mercaderia_usd": round(valor_merc_num, 2),
            }

            webhook = get_webhook_url()
            if not webhook:
                st.warning("Falta **N8N_WEBHOOK_URL** en Secrets o variables de entorno.")
            else:
                try:
                    r = requests.post(webhook, json=payload, timeout=15)
                    if r.status_code < 400:
                        st.success("¡Enviado! ✅ Te respondemos por email.")
                        time.sleep(1.0)
                        st.session_state.mostrar_modal = False
                        resetear_form()
                        st.rerun()
                    else:
                        st.error(f"El webhook respondió {r.status_code}. Revisá n8n.")
                except Exception as e:
                    st.error(f"No pude enviar al webhook. Detalle: {e}")

        if otra:
            st.session_state.mostrar_modal = False
            resetear_form()
            st.rerun()

        if cerrar:
            st.session_state.mostrar_modal = False
            st.rerun()
