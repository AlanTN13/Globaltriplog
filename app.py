# app.py
from __future__ import annotations
import os, json, requests
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# -------------------- Config --------------------
st.set_page_config(page_title="Cotizador GlobalTrip", page_icon="📦", layout="wide")

# -------------------- Estilos (fondo claro + texto #000033, SIEMPRE) --------------------
st.markdown("""
<style id="force-light">
:root { color-scheme: light !important; }
html, body, .stApp, [data-testid="stAppViewContainer"],
section.main, [data-testid="stHeader"], [data-testid="stSidebar"]{
  background:#FFFFFF !important; color:#000033 !important;
}
/* TODO el texto */
body, .stApp, div, p, span, label, h1,h2,h3,h4,h5,h6, a, small, strong, em, th, td,
div[data-testid="stMarkdownContainer"] * { color:#000033 !important; }
a { text-decoration:none; }

/* Tarjeta hero */
.soft-card{
  background:#fff; border:1.5px solid #dfe7ef;
  border-radius:16px; padding:18px 20px; box-shadow:0 8px 18px rgba(17,24,39,.07);
}

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea{
  background:#fff !important; color:#000033 !important;
  border:1.5px solid #dfe7ef !important; border-radius:16px !important; padding:14px 16px !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus{
  outline:none !important; border-color:#000033 !important; box-shadow:0 0 0 3px rgba(0,0,51,.2) !important;
}
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder{ color:#000033 !important; opacity:.55 !important; }

/* Radio chips */
div[data-testid="stRadio"] label{
  background:#fff; border:1.5px solid #dfe7ef; border-radius:14px;
  padding:8px 12px; margin-right:8px; color:#000033 !important;
}

/* Métricas */
div[data-testid="stMetric"]{
  background:#fff; border:1.5px solid #dfe7ef; border-radius:16px; padding:18px 20px; box-shadow:0 8px 18px rgba(17,24,39,.07);
}
div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"]{ color:#000033 !important; }

/* Botón */
div.stButton > button{
  border:1.5px solid #dfe7ef; border-radius:16px;
  background:#fff; color:#000033; padding:14px 18px; box-shadow:0 10px 22px rgba(17,24,39,.09);
}

/* Data editor claro */
[data-testid="stDataFrame"]{
  background:#fff; border:1.5px solid #dfe7ef; border-radius:16px; box-shadow:0 8px 18px rgba(17,24,39,.07); overflow:hidden;
}
[data-testid="stDataFrame"] div[role="grid"]{ background:#fff; }
[data-testid="stDataFrame"] div[role="columnheader"]{
  background:#eef3ff !important; color:#000033 !important; border-bottom:1px solid #dfe7ef !important;
}
[data-testid="stDataFrame"] div[role="cell"]{
  background:#fff !important; color:#000033 !important; border-color:#dfe7ef !important;
}

/* Modal nativo */
[data-testid="stModal"] > div {
  background:#fff !important; color:#000033 !important;
  border:1.5px solid #dfe7ef !important; border-radius:18px !important;
  box-shadow:0 18px 40px rgba(17,24,39,.25) !important;
}

/* Fallback overlay (si no hay st.modal) */
.gt-overlay{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:9999; display:flex; align-items:center; justify-content:center; }
.gt-modal{ max-width:640px; width:92%; background:#fff; color:#000033; border:1.5px solid #dfe7ef; border-radius:18px; padding:22px; box-shadow:0 18px 40px rgba(17,24,39,.25); }
.gt-actions{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:14px; }
.gt-btn{ display:inline-block; text-align:center; border:1.5px solid #dfe7ef; border-radius:16px; background:#f0f7ff; color:#000033; padding:12px 16px; cursor:pointer; }
</style>
""", unsafe_allow_html=True)

# -------------------- Constantes --------------------
FACTOR_VOL = 5000   # cm^3 -> kg
DEFAULT_ROWS = 10

# -------------------- Estado --------------------
def init_state():
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame({
            "Cantidad de bultos": [0]*DEFAULT_ROWS,
            "Ancho (cm)": [0]*DEFAULT_ROWS,
            "Alto (cm)": [0]*DEFAULT_ROWS,
            "Largo (cm)": [0]*DEFAULT_ROWS,
            "Peso vol. (kg)": [0.00]*DEFAULT_ROWS,
        })
    st.session_state.setdefault("nombre","")
    st.session_state.setdefault("email","")
    st.session_state.setdefault("telefono","")
    st.session_state.setdefault("es_cliente","No")
    st.session_state.setdefault("descripcion","")
    st.session_state.setdefault("link","")
    st.session_state.setdefault("peso_bruto_raw","0.00")
    st.session_state.setdefault("peso_bruto",0.0)
    st.session_state.setdefault("valor_mercaderia_raw","0.00")
    st.session_state.setdefault("valor_mercaderia",0.0)
    st.session_state.setdefault("show_modal", False)

def reset_form():
    st.session_state.update({
        "nombre":"", "email":"", "telefono":"", "es_cliente":"No",
        "descripcion":"", "link":"",
        "peso_bruto_raw":"0.00", "peso_bruto":0.0,
        "valor_mercaderia_raw":"0.00", "valor_mercaderia":0.0,
        "df": pd.DataFrame({
            "Cantidad de bultos": [0]*DEFAULT_ROWS,
            "Ancho (cm)": [0]*DEFAULT_ROWS,
            "Alto (cm)": [0]*DEFAULT_ROWS,
            "Largo (cm)": [0]*DEFAULT_ROWS,
            "Peso vol. (kg)": [0.00]*DEFAULT_ROWS,
        }),
        "show_modal": False
    })

def compute_vol(df: pd.DataFrame):
    calc = df[["Cantidad de bultos","Ancho (cm)","Alto (cm)","Largo (cm)"]].fillna(0).astype(float)
    per_row = (calc["Cantidad de bultos"] * calc["Ancho (cm)"] * calc["Alto (cm)"] * calc["Largo (cm)"]) / FACTOR_VOL
    per_row = per_row.replace([np.inf,-np.inf],0).fillna(0).round(2)
    out = df.copy()
    out["Peso vol. (kg)"] = per_row
    total = float(per_row.sum().round(2))
    return out, total

def post_to_webhook(payload: dict):
    url = st.secrets.get("N8N_WEBHOOK_URL", os.getenv("N8N_WEBHOOK_URL",""))
    token = st.secrets.get("N8N_TOKEN", os.getenv("N8N_TOKEN",""))
    if not url:  # best-effort, no corta el flujo
        return True, "Sin webhook configurado."
    headers = {"Content-Type":"application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        return (r.ok, f"HTTP {r.status_code}")
    except Exception as e:
        return False, str(e)

init_state()

# -------------------- UI --------------------
# Hero
st.markdown("""
<div class="soft-card">
  <h2 style="margin:0;">📦 Cotización de Envío por Courier</h2>
  <p style="margin:6px 0 0;">Completá tus datos y medidas. Te mandamos la cotización por email.</p>
</div>
""", unsafe_allow_html=True)
st.write("")

# Formulario
with st.form("cotizador", clear_on_submit=False):
    st.subheader("Datos de contacto y del producto")
    c1,c2,c3,c4 = st.columns([1.1,1.1,1.0,0.9])
    with c1:
        st.session_state.nombre = st.text_input("Nombre completo*", value=st.session_state.nombre, placeholder="Ej: Juan Pérez")
    with c2:
        st.session_state.email = st.text_input("Correo electrónico*", value=st.session_state.email, placeholder="ejemplo@email.com")
    with c3:
        st.session_state.telefono = st.text_input("Teléfono*", value=st.session_state.telefono, placeholder="Ej: 11 5555 5555")
    with c4:
        st.session_state.es_cliente = st.radio("¿Cliente/alumno de Global Trip?", ["No","Sí"],
                                               index=0 if st.session_state.es_cliente=="No" else 1, horizontal=True)

    st.session_state.descripcion = st.text_area("Descripción del producto*", value=st.session_state.descripcion,
                                                placeholder='Ej: "Máquina selladora de bolsas"')
    st.session_state.link = st.text_input("Link del producto o ficha técnica (Alibaba, Amazon, etc.)*",
                                          value=st.session_state.link, placeholder="https://...")

    st.write("")
    st.subheader("Bultos")
    st.caption("Tip: usá el botón “+” al final de la tabla para agregar más bultos. Ingresá por bulto: cantidad y dimensiones en **cm**. El **peso volumétrico** se calcula solo.")

    col_cfg = {
        "Cantidad de bultos": st.column_config.NumberColumn("Cantidad de bultos", min_value=0, step=1, help="Sólo enteros"),
        "Ancho (cm)": st.column_config.NumberColumn("Ancho (cm)", min_value=0, step=1),
        "Alto (cm)": st.column_config.NumberColumn("Alto (cm)", min_value=0, step=1),
        "Largo (cm)": st.column_config.NumberColumn("Largo (cm)", min_value=0, step=1),
        "Peso vol. (kg)": st.column_config.NumberColumn("Peso vol. (kg)", step=0.01, disabled=True, help="Auto"),
    }
    edited = st.data_editor(st.session_state.df, key="bultos_editor", num_rows="dynamic",
                            use_container_width=True, hide_index=True, column_config=col_cfg)
    st.session_state.df, total_peso_vol = compute_vol(edited)

    st.write("")
    st.subheader("Pesos")
    m1, mMid, m2 = st.columns([1.1,1.1,1.1])
    with m1:
        st.metric("Peso volumétrico (kg) 🔒", f"{total_peso_vol:,.2f}")
    with mMid:
        st.session_state.peso_bruto_raw = st.text_input("Peso bruto (kg)", value=st.session_state.peso_bruto_raw,
                                                        help="Usá punto o coma para decimales (ej: 1.25)")
        try:
            st.session_state.peso_bruto = max(0.0, float(st.session_state.peso_bruto_raw.replace(",", ".")))
        except Exception:
            pass
    with m2:
        peso_aplicable = max(total_peso_vol, float(st.session_state.peso_bruto))
        st.metric("Peso aplicable (kg) 🔒", f"{peso_aplicable:,.2f}")

    st.subheader("Valor de la mercadería")
    st.session_state.valor_mercaderia_raw = st.text_input("Valor de la mercadería (USD)", value=st.session_state.valor_mercaderia_raw)
    try:
        st.session_state.valor_mercaderia = max(0.0, float(st.session_state.valor_mercaderia_raw.replace(",", ".")))
    except Exception:
        pass

    st.write("")
    submitted = st.form_submit_button("📨 Solicitar cotización")

# -------------------- Submit --------------------
if submitted:
    errores = []
    if not st.session_state.nombre.strip(): errores.append("• Nombre es obligatorio.")
    if not st.session_state.email.strip() or "@" not in st.session_state.email: errores.append("• Email válido es obligatorio.")
    if not st.session_state.telefono.strip(): errores.append("• Teléfono es obligatorio.")
    if not st.session_state.descripcion.strip(): errores.append("• Descripción del producto es obligatoria.")
    if not st.session_state.link.strip(): errores.append("• Link del producto/ficha técnica es obligatorio.")
    df_ok = st.session_state.df.fillna(0)
    if (df_ok[["Cantidad de bultos","Ancho (cm)","Alto (cm)","Largo (cm)"]].sum().sum() <= 0):
        errores.append("• Ingresá al menos un bulto con cantidad y medidas.")

    if errores:
        st.error("Revisá estos puntos:\n\n" + "\n".join(errores))
    else:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "origen": "streamlit-cotizador",
            "factor_vol": FACTOR_VOL,
            "contacto": {
                "nombre": st.session_state.nombre.strip(),
                "email": st.session_state.email.strip(),
                "telefono": st.session_state.telefono.strip(),
                "es_cliente": st.session_state.es_cliente
            },
            "producto": {
                "descripcion": st.session_state.descripcion.strip(),
                "link": st.session_state.link.strip()
            },
            "bultos": st.session_state.df.replace([np.inf,-np.inf],0).fillna(0).to_dict(orient="records"),
            "pesos": {
                "volumetrico_kg": total_peso_vol,
                "bruto_kg": float(st.session_state.peso_bruto),
                "aplicable_kg": max(total_peso_vol, float(st.session_state.peso_bruto))
            },
            "valor_mercaderia_usd": float(st.session_state.valor_mercaderia)
        }
        post_to_webhook(payload)
        st.session_state.show_modal = True

# -------------------- Popup post-submit --------------------
if st.session_state.get("show_modal", False):
    email = (st.session_state.email or "").strip()
    email_html = f"<a href='mailto:{email}'>{email}</a>" if email else "tu correo"

    if hasattr(st, "modal"):  # modal nativo
        with st.modal("¡Listo!"):
            st.markdown("Recibimos tu solicitud. En breve te llegará la cotización a " + email_html + ".", unsafe_allow_html=True)
            st.caption("Podés cargar otra si querés.")
            cA, cB = st.columns(2)
            with cA:
                if st.button("➕ Cargar otra cotización", use_container_width=True):
                    reset_form(); st.rerun()
            with cB:
                if st.button("Cerrar", use_container_width=True):
                    st.session_state.show_modal = False; st.rerun()
    else:
        # Fallback con overlay (sin f-strings)
        html = (
            '<div class="gt-overlay">'
              '<div class="gt-modal">'
                '<h3>¡Listo!</h3>'
                '<p>Recibimos tu solicitud. En breve te llegará la cotización a ' + email_html + '.</p>'
                '<p style="opacity:.7;">Podés cargar otra si querés.</p>'
                '<div class="gt-actions">'
                  '<div id="gt-reset" class="gt-btn">➕ Cargar otra cotización</div>'
                  '<div id="gt-close" class="gt-btn">Cerrar</div>'
                '</div>'
              '</div>'
            '</div>'
            '<script>(function(){'
              'function reload(){ window.location.reload(); }'
              'document.getElementById("gt-reset").onclick = function(e){ e.preventDefault(); fetch(window.location.href,{cache:"reload"}).finally(reload); };'
              'document.getElementById("gt-close").onclick  = function(e){ e.preventDefault(); reload(); };'
            '})();</script>'
        )
        components.html(html, height=1, scrolling=False)

