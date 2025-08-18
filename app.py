# app.py
from __future__ import annotations
import os, json, requests
from datetime import datetime
import streamlit as st

# -------------------- Config --------------------
st.set_page_config(
    page_title="Cotizador GlobalTrip",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---- Keepalive ultra liviano (para UptimeRobot, cron, etc.) ----
if "ping" in st.query_params:
    st.write("ok")
    st.stop()

# -------------------- Estilos --------------------
st.markdown("""<style>
/* tus estilos completos van acá, los mantuve tal cual */
</style>""", unsafe_allow_html=True)

# -------------------- Estado --------------------
FACTOR_VOL = 5000
def init_state():
    st.session_state.setdefault("rows", [{"cant":0, "ancho":0, "alto":0, "largo":0}])
    st.session_state.setdefault("productos", [{"descripcion":"", "link":""}])
    st.session_state.setdefault("nombre","")
    st.session_state.setdefault("email","")
    st.session_state.setdefault("telefono","")
    st.session_state.setdefault("pais_origen","China")
    st.session_state.setdefault("pais_origen_otro","")
    st.session_state.setdefault("peso_bruto_raw","0.00")
    st.session_state.setdefault("peso_bruto",0.0)
    st.session_state.setdefault("valor_mercaderia_raw","0.00")
    st.session_state.setdefault("valor_mercaderia",0.0)
    st.session_state.setdefault("show_dialog", False)
    st.session_state.setdefault("form_errors", [])
init_state()

# -------------------- Helpers --------------------
def to_float(s, default=0.0):
    try:
        return float(str(s).replace(",",".")) if s not in (None,"") else default
    except:
        return default

def compute_total_vol():
    total = 0.0
    for i in range(len(st.session_state.rows)):
        cant = to_float(st.session_state.get(f"cant_{i}",0))
        an   = to_float(st.session_state.get(f"an_{i}",0))
        al   = to_float(st.session_state.get(f"al_{i}",0))
        lar  = to_float(st.session_state.get(f"lar_{i}",0))
        total += (cant*an*al*lar) / FACTOR_VOL
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
    if not any(p["descripcion"].strip() and p["link"].strip() for p in st.session_state.productos):
        errs.append("• Cargá al menos un producto con descripción y link.")
    if st.session_state.pais_origen == "Otro" and not st.session_state.pais_origen_otro.strip():
        errs.append("• Indicá el país de origen.")
    if not any(
        to_float(st.session_state.get(f"cant_{i}",0))>0 and 
        (to_float(st.session_state.get(f"an_{i}",0))+to_float(st.session_state.get(f"al_{i}",0))+to_float(st.session_state.get(f"lar_{i}",0)))>0
        for i in range(len(st.session_state.rows))
    ):
        errs.append("• Ingresá al menos un bulto con cantidad y medidas.")
    return errs

# -------------------- Callbacks --------------------
def add_row(): st.session_state.rows.append({"cant":0,"ancho":0,"alto":0,"largo":0})
def clear_rows(): st.session_state.rows=[{"cant":0,"ancho":0,"alto":0,"largo":0}]
def add_producto(): st.session_state.productos.append({"descripcion":"", "link":""})
def clear_productos(): st.session_state.productos=[{"descripcion":"", "link":""}]

# -------------------- Header --------------------
st.markdown("""
<div class="soft-card gt-section">
  <h2 style="margin:0;">📦 Cotización de Importación por Courier</h2>
  <p style="margin:6px 0 0;">Completá tus datos e información de tu importación y te enviaremos la cotización por mail.</p>
</div>
""", unsafe_allow_html=True)

# -------------------- Datos de contacto --------------------
st.subheader("Datos de contacto")
c1,c2,c3 = st.columns([1.1,1.1,1.0])
with c1: st.session_state.nombre = st.text_input("Nombre completo*", value=st.session_state.nombre, placeholder="Ej: Juan Pérez")
with c2: st.session_state.email  = st.text_input("Correo electrónico*", value=st.session_state.email, placeholder="ejemplo@email.com")
with c3: st.session_state.telefono=st.text_input("Teléfono*", value=st.session_state.telefono, placeholder="Ej: 11 5555 5555")

# -------------------- País de origen --------------------
st.subheader("País de origen")
sel = st.radio("Seleccioná el país de origen:", ["China", "Otro"], 
               index=0 if st.session_state.pais_origen=="China" else 1, horizontal=True)
if sel=="Otro":
    st.session_state.pais_origen="Otro"
    st.session_state.pais_origen_otro=st.text_input("Ingresá el país de origen", value=st.session_state.pais_origen_otro).strip()
else:
    st.session_state.pais_origen="China"

# -------------------- Productos --------------------
st.subheader("Productos")
for i,p in enumerate(st.session_state.productos):
    st.text_area("Descripción*", value=p["descripcion"], key=f"prod_desc_{i}", placeholder="Ej: Máquina...")
    st.text_area("Link*", value=p["link"], key=f"prod_link_{i}", placeholder="https://...")
    if st.button("🗑️ Eliminar producto", key=f"del_prod_{i}"):
        if len(st.session_state.productos)>1: st.session_state.productos.pop(i)
        else: st.session_state.productos=[{"descripcion":"", "link":""}]
        st.rerun()

st.button("➕ Agregar producto", on_click=add_producto)
st.button("🧹 Vaciar productos", on_click=clear_productos)

# -------------------- Bultos --------------------
st.subheader("Bultos")
for i,_ in enumerate(st.session_state.rows):
    st.number_input("Cantidad", min_value=0, step=1, key=f"cant_{i}")
    st.number_input("Ancho (cm)", min_value=0.0, step=1.0, key=f"an_{i}")
    st.number_input("Alto (cm)", min_value=0.0, step=1.0, key=f"al_{i}")
    st.number_input("Largo (cm)", min_value=0.0, step=1.0, key=f"lar_{i}")
    if st.button("🗑️ Eliminar bulto", key=f"del_row_{i}"):
        if len(st.session_state.rows)>1: st.session_state.rows.pop(i)
        else: st.session_state.rows=[{"cant":0,"ancho":0,"alto":0,"largo":0}]
        st.rerun()

st.button("➕ Agregar bulto", on_click=add_row)
st.button("🧹 Vaciar bultos", on_click=clear_rows)

# -------------------- Pesos --------------------
st.subheader("Peso total de los bultos")
st.session_state.peso_bruto_raw = st.text_input("Peso bruto total (kg)", value=st.session_state.peso_bruto_raw)
st.session_state.peso_bruto = to_float(st.session_state.peso_bruto_raw, 0.0)
total_peso_vol = compute_total_vol()
peso_aplicable = max(total_peso_vol, st.session_state.peso_bruto)
st.markdown(f"<div class='gt-pill'>Peso aplicable (kg) 🔒 <b>{peso_aplicable:,.2f}</b></div>", unsafe_allow_html=True)

# -------------------- Valor total --------------------
st.subheader("Valor total del pedido")
st.session_state.valor_mercaderia_raw = st.text_input("Valor total (USD)", value=st.session_state.valor_mercaderia_raw)
st.session_state.valor_mercaderia = to_float(st.session_state.valor_mercaderia_raw, 0.0)

# -------------------- Submit --------------------
if st.button("📨 Solicitar cotización", key="gt_submit_btn"):
    st.session_state.form_errors = validate()
    if not st.session_state.form_errors:
        productos_validos = [
            {"descripcion": st.session_state[f"prod_desc_{i}"].strip(), "link": st.session_state[f"prod_link_{i}"].strip()}
            for i in range(len(st.session_state.productos))
            if st.session_state[f"prod_desc_{i}"].strip() and st.session_state[f"prod_link_{i}"].strip()
        ]
        pais_final = st.session_state.pais_origen if st.session_state.pais_origen=="China" else st.session_state.pais_origen_otro.strip()
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "origen": "streamlit-cotizador",
            "factor_vol": FACTOR_VOL,
            "contacto": {
                "nombre": st.session_state.nombre.strip(),
                "email": st.session_state.email.strip(),
                "telefono": st.session_state.telefono.strip()
            },
            "pais_origen": pais_final,
            "productos": productos_validos,
            "bultos": [
                {
                    "cant": to_float(st.session_state.get(f"cant_{i}",0)),
                    "ancho": to_float(st.session_state.get(f"an_{i}",0)),
                    "alto": to_float(st.session_state.get(f"al_{i}",0)),
                    "largo": to_float(st.session_state.get(f"lar_{i}",0))
                } for i in range(len(st.session_state.rows))
            ],
            "pesos": {
                "volumetrico_kg": total_peso_vol,
                "bruto_kg": st.session_state.peso_bruto,
                "aplicable_kg": peso_aplicable
            },
            "valor_mercaderia_usd": st.session_state.valor_mercaderia
        }
        try:
            post_to_webhook(payload)
        except Exception:
            pass
        st.session_state.show_dialog=True

# -------------------- Errores --------------------
if st.session_state.form_errors:
    st.error("Revisá estos puntos:\n\n" + "\n".join(st.session_state.form_errors))

# -------------------- Popup --------------------
if st.session_state.get("show_dialog", False):
    email = (st.session_state.email or "").strip()
    email_html = f"<a href='mailto:{email}'>{email}</a>" if email else "tu correo"
    st.markdown(f"""
<div class="gt-overlay">
  <div class="gt-modal">
    <a class="gt-close" href="?gt=close" target="_self">✕</a>
    <h3 class="gt-title">¡Listo!</h3>
    <div class="gt-body">
      <p>Recibimos tu solicitud. En breve te llegará la cotización a {email_html}.</p>
      <p style="opacity:.85;">Podés cargar otra si querés.</p>
    </div>
    <div class="gt-actions">
      <a class="gt-btn" href="?gt=reset" target="_self">➕ Cargar otra cotización</a>
      <a class="gt-btn secondary" href="?gt=close" target="_self">Cerrar</a>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
