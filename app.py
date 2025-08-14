# app.py
from __future__ import annotations
import os, json, requests
from datetime import datetime

import numpy as np
import streamlit as st

# -------------------- Config --------------------
st.set_page_config(page_title="Cotizador GlobalTrip", page_icon="📦", layout="wide")

# -------------------- Estilos (claro forzado + #000033) --------------------
st.markdown("""
<style>
/* Fuerza modo claro en toda la app */
:root { color-scheme: light !important; }
html, body, .stApp, [data-testid="stAppViewContainer"],
section.main, [data-testid="stHeader"], [data-testid="stSidebar"]{
  background:#FFFFFF !important; color:#000033 !important;
}

/* Texto siempre #000033 */
div, p, span, label, h1,h2,h3,h4,h5,h6, a, small, strong, em, th, td,
div[data-testid="stMarkdownContainer"] * { color:#000033 !important; }

/* Card */
.soft-card{
  background:#fff; border:1.5px solid #dfe7ef; border-radius:16px;
  padding:18px 20px; box-shadow:0 8px 18px rgba(17,24,39,.07);
}

/* Inputs base (desktop & mobile) */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
  background:#fff !important; color:#000033 !important;
  border:1.5px solid #dfe7ef !important; border-radius:16px !important;
  padding:14px 16px !important; box-shadow:none !important;
}
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder { color:#00003399 !important; }

/* ---- NumberInput: caja + stepper (claro) ---- */
div[data-testid="stNumberInput"] > div{
  background:#fff !important; border:1.5px solid #dfe7ef !important;
  border-radius:16px !important; box-shadow:none !important;
}
div[data-testid="stNumberInput"] input{
  background:#fff !important; color:#000033 !important;
  padding:14px 16px !important; height:48px !important;
}
/* Sufijo con + / - */
div[data-testid="stNumberInput"] > div > div:nth-child(2){
  background:#fff !important; border-left:1.5px solid #dfe7ef !important;
  border-radius:0 16px 16px 0 !important;
}
/* Botoncitos + / - */
div[data-testid="stNumberInput"] button{
  background:#eef3ff !important; color:#000033 !important;
  border:1px solid #dfe7ef !important; border-radius:10px !important;
}

/* iOS / Safari: evita “auto-dark” y autofill gris */
input, textarea, select{
  -webkit-text-fill-color:#000033 !important;
  background:#fff !important; color:#000033 !important; caret-color:#000033 !important;
}
input:-webkit-autofill{
  -webkit-box-shadow:0 0 0 1000px #fff inset !important;
  -webkit-text-fill-color:#000033 !important;
}

/* Botón enviar */
#gt-submit-btn button{
  width:100% !important; background:#f3f5fb !important; color:#000033 !important;
  border:2px solid #000033 !important; border-radius:16px !important; padding:14px 18px !important;
  box-shadow:0 4px 10px rgba(0,16,64,.08) !important;
}
#gt-submit-btn button:hover{ background:#eef3ff !important; }

/* Popup (sin iframe/JS) */
.gt-overlay{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:99999;
  display:flex; align-items:center; justify-content:center; }
.gt-modal{ max-width:680px; width:92%; background:#fff; color:#000033;
  border:1.5px solid #dfe7ef; border-radius:18px; padding:28px 24px;
  box-shadow:0 18px 40px rgba(17,24,39,.25); }
.gt-modal h3{ margin:0 0 8px 0; font-size:30px; font-weight:800; }
.gt-actions{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:16px; }
.gt-btn{ display:inline-block; text-align:center; border:1.5px solid #dfe7ef;
  border-radius:16px; background:#eef5ff; color:#000033; padding:14px 16px;
  cursor:pointer; font-size:18px; text-decoration:none; }

/* Mobile tweaks */
@media (max-width: 640px){
  .soft-card{ padding:16px; }
  div[data-testid="stNumberInput"] input{ font-size:18px !important; }
}
</style>

""", unsafe_allow_html=True)

# -------------------- Constantes --------------------
FACTOR_VOL = 5000

# -------------------- Estado --------------------
def init_state():
    st.session_state.setdefault("rows", [{"cant":0, "ancho":0, "alto":0, "largo":0}])
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
    st.session_state.setdefault("show_dialog", False)
    st.session_state.setdefault("form_errors", [])

def reset_form():
    st.session_state.update({
        "rows":[{"cant":0, "ancho":0, "alto":0, "largo":0}],
        "nombre":"", "email":"", "telefono":"", "es_cliente":"No",
        "descripcion":"", "link":"",
        "peso_bruto_raw":"0.00", "peso_bruto":0.0,
        "valor_mercaderia_raw":"0.00", "valor_mercaderia":0.0,
        "show_dialog": False, "form_errors":[]
    })

init_state()

# -------------------- QS helpers (manejo ?gt=...) --------------------
def get_qs():
    try: return dict(st.query_params)
    except: return {}
def set_qs(**kwargs):
    try:
        st.query_params.clear()
        for k,v in kwargs.items(): st.query_params[k] = v
    except: pass
def rerun():
    try: st.rerun()
    except: st.experimental_rerun()

_qs = get_qs()
if _qs.get("gt","") == "reset":
    reset_form(); set_qs(); rerun()
elif _qs.get("gt","") == "close":
    st.session_state.show_dialog = False; set_qs(); rerun()

# -------------------- Helpers --------------------
def to_float(s, default=0.0):
    try: return float(str(s).replace(",",".")) if s not in (None,"") else default
    except: return default

def compute_total_vol(rows):
    total = 0.0
    for r in rows:
        total += (to_float(r["cant"])*to_float(r["ancho"])*to_float(r["alto"])*to_float(r["largo"])) / FACTOR_VOL
    return round(total, 2)

def post_to_webhook(payload: dict):
    url = st.secrets.get("N8N_WEBHOOK_URL", os.getenv("N8N_WEBHOOK_URL",""))
    token = st.secrets.get("N8N_TOKEN", os.getenv("N8N_TOKEN",""))
    if not url: return True, "Sin webhook configurado."
    headers = {"Content-Type":"application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        return (r.ok, f"HTTP {r.status_code}")
    except Exception as e:
        return False, str(e)

def validate():
    errs = []
    if not st.session_state.nombre.strip(): errs.append("• Nombre es obligatorio.")
    if not st.session_state.email.strip() or "@" not in st.session_state.email: errs.append("• Email válido es obligatorio.")
    if not st.session_state.telefono.strip(): errs.append("• Teléfono es obligatorio.")
    if not st.session_state.descripcion.strip(): errs.append("• Descripción del producto es obligatoria.")
    if not st.session_state.link.strip(): errs.append("• Link del producto/ficha técnica es obligatorio.")
    hay_medidas = any(to_float(r["cant"])>0 and (to_float(r["ancho"])+to_float(r["alto"])+to_float(r["largo"]))>0
                      for r in st.session_state.rows)
    if not hay_medidas: errs.append("• Ingresá al menos un bulto con **cantidad** y **medidas**.")
    return errs

# -------------------- UI --------------------
st.markdown("""
<div class="soft-card">
  <h2 style="margin:0;">📦 Cotización de Envío por Courier</h2>
  <p style="margin:6px 0 0;">Completá tus datos y medidas. Te mandamos la cotización por email.</p>
</div>
""", unsafe_allow_html=True)
st.write("")

st.subheader("Datos de contacto y del producto")
c1,c2,c3,c4 = st.columns([1.1,1.1,1.0,0.9])
with c1:
    nombre_input = st.text_input("Nombre completo*", value=st.session_state.nombre,
                                 placeholder="Ej: Juan Pérez", key="nombre_input")
    st.session_state.nombre = nombre_input
with c2:
    email_input = st.text_input("Correo electrónico*", value=st.session_state.email,
                                placeholder="ejemplo@email.com", key="email_input")
    st.session_state.email = email_input
with c3:
    tel_input = st.text_input("Teléfono*", value=st.session_state.telefono,
                              placeholder="Ej: 11 5555 5555", key="tel_input")
    st.session_state.telefono = tel_input
with c4:
    st.session_state.es_cliente = st.radio("¿Cliente/alumno de Global Trip?", ["No","Sí"],
                                           index=0 if st.session_state.es_cliente=="No" else 1, horizontal=True)

st.session_state.descripcion = st.text_area("Descripción del producto*", value=st.session_state.descripcion,
                                            placeholder='Ej: "Máquina selladora de bolsas"', key="desc_input")
st.session_state.link = st.text_input("Link del producto o ficha técnica (Alibaba, Amazon, etc.)*",
                                      value=st.session_state.link, placeholder="https://...", key="link_input")

st.write("")
# --------- BULTOS (labels sobre cada input, responsive) ---------
st.subheader("Bultos")
st.caption("Cargá por bulto: **cantidad** y **dimensiones en cm**. Calculamos el **peso volumétrico**.")

# Filas de bultos (cada campo con su label)
for i, r in enumerate(st.session_state.rows):
    cols = st.columns([0.9, 1, 1, 1, 0.8])

    with cols[0]:
        st.session_state.rows[i]["cant"] = st.number_input(
            "Cantidad", min_value=0, step=1, value=int(r["cant"]), key=f"cant_{i}"
        )
    with cols[1]:
        st.session_state.rows[i]["ancho"] = st.number_input(
            "Ancho (cm)", min_value=0.0, step=1.0, value=float(r["ancho"]), key=f"an_{i}"
        )
    with cols[2]:
        st.session_state.rows[i]["alto"] = st.number_input(
            "Alto (cm)", min_value=0.0, step=1.0, value=float(r["alto"]), key=f"al_{i}"
        )
    with cols[3]:
        st.session_state.rows[i]["largo"] = st.number_input(
            "Largo (cm)", min_value=0.0, step=1.0, value=float(r["largo"]), key=f"lar_{i}"
        )
    with cols[4]:
        if st.button("🗑️ Eliminar", key=f"del_{i}"):
            st.session_state.rows.pop(i)
            st.stop()

cc1, cc2 = st.columns([1, 1])
with cc1:
    if st.button("➕ Agregar bulto"):
        st.session_state.rows.append({"cant": 0, "ancho": 0, "alto": 0, "largo": 0})
with cc2:
    if st.button("🧹 Vaciar tabla"):
        st.session_state.rows = [{"cant": 0, "ancho": 0, "alto": 0, "largo": 0}]

# Pesos
st.write("")
st.subheader("Pesos")
m1, mMid, m2 = st.columns([1.1, 1.1, 1.1])
total_peso_vol = compute_total_vol(st.session_state.rows)
with m1:
    st.metric("Peso volumétrico (kg) 🔒", f"{total_peso_vol:,.2f}")
with mMid:
    st.session_state.peso_bruto_raw = st.text_input("Peso bruto (kg)", value=st.session_state.peso_bruto_raw,
                                                    help="Usá punto o coma para decimales (ej: 1.25)", key="pb_input")
    st.session_state.peso_bruto = to_float(st.session_state.peso_bruto_raw, 0.0)
with m2:
    peso_aplicable = max(total_peso_vol, st.session_state.peso_bruto)
    st.metric("Peso aplicable (kg) 🔒", f"{peso_aplicable:,.2f}")

# Valor mercadería
st.subheader("Valor de la mercadería")
st.session_state.valor_mercaderia_raw = st.text_input("Valor de la mercadería (USD)",
                                                      value=st.session_state.valor_mercaderia_raw, key="vm_input")
st.session_state.valor_mercaderia = to_float(st.session_state.valor_mercaderia_raw, 0.0)

# Submit
st.write("")
st.markdown('<div id="gt-submit-btn">', unsafe_allow_html=True)
submit_clicked = st.button("📨 Solicitar cotización", use_container_width=True, key="gt_submit_btn")
st.markdown('</div>', unsafe_allow_html=True)

if submit_clicked:
    st.session_state.form_errors = validate()
    if not st.session_state.form_errors:
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
            "bultos": st.session_state.rows,
            "pesos": {
                "volumetrico_kg": total_peso_vol,
                "bruto_kg": st.session_state.peso_bruto,
                "aplicable_kg": peso_aplicable
            },
            "valor_mercaderia_usd": st.session_state.valor_mercaderia
        }
        # Envío best-effort si hubiera webhook
        try: post_to_webhook(payload)
        except: pass
        st.session_state.show_dialog = True

# Errores debajo del botón
if st.session_state.form_errors:
    st.markdown('<div id="gt-errors">', unsafe_allow_html=True)
    st.error("Revisá estos puntos:\n\n" + "\n".join(st.session_state.form_errors))
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Popup SIN iframe/JS --------------------
if st.session_state.get("show_dialog", False):
    email = (st.session_state.email or "").strip()
    email_html = f"<a href='mailto:{email}'>{email}</a>" if email else "tu correo"
    st.markdown(f"""
<div class="gt-overlay">
  <div class="gt-modal">
    <h3>¡Listo!</h3>
    <p>Recibimos tu solicitud. En breve te llegará la cotización a {email_html}.</p>
    <p style="opacity:.75;">Podés cargar otra si querés.</p>
    <div class="gt-actions">
      <a class="gt-btn" href="?gt=reset" target="_self">➕ Cargar otra cotización</a>
      <a class="gt-btn" href="?gt=close" target="_self">Cerrar</a>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

