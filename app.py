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

# -------------------- Estilos --------------------
st.markdown("""
<style>
:root { color-scheme: light !important; }
html, body, .stApp, [data-testid="stAppViewContainer"],
section.main, [data-testid="stHeader"], [data-testid="stSidebar"]{
  background:#FFFFFF !important; color:#000033 !important;
}
/* Quitar header/márgenes sup. */
:root{ --header-height:0px !important; }
[data-testid="stHeader"], [data-testid="stToolbar"]{ display:none !important; }
[data-testid="stAppViewContainer"]{ padding-top:0 !important; }
section.main{ padding-top:0 !important; }
section.main > div.block-container{ padding-top:.10rem !important; padding-bottom:2rem !important; }
section.main > div.block-container > div:first-child{ margin-top:0 !important; }
div[data-testid="stDecoration"], #MainMenu, footer, header { display:none !important; }

/* Tipografía color base */
div, p, span, label, h1,h2,h3,h4,h5,h6, a, small, strong, em, th, td,
div[data-testid="stMarkdownContainer"] * { color:#000033 !important; }

/* Ancho máximo centrado para secciones (desktop iguales) */
.gt-section{ max-width:1100px; margin:0 auto; }

/* Card */
.soft-card{
  background:#fff; border:1.5px solid #dfe7ef; border-radius:16px;
  padding:18px 20px; box-shadow:0 8px 18px rgba(17,24,39,.07);
}

/* Tarjetas internas */
.gt-card{
  background:#fff; border:1.5px solid #dfe7ef; border-radius:16px;
  padding:16px; box-shadow:0 6px 16px rgba(17,24,39,.06); margin:10px 0 16px;
}
.gt-card h4{ margin:0 0 8px 0; }

/* Inputs texto */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
  background:#fff !important; color:#000033 !important;
  border:1.5px solid #dfe7ef !important; border-radius:16px !important;
  padding:14px 16px !important; box-shadow:none !important;
}
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder { color:#00003399 !important; }

/* NumberInput (± claro) */
div[data-testid="stNumberInput"] > div{
  background:#fff !important; border:1.5px solid #dfe7ef !important;
  border-radius:24px !important; box-shadow:none !important;
}
div[data-testid="stNumberInput"] input{
  background:#fff !important; color:#000033 !important;
  padding:14px 16px !important; height:48px !important; border:none !important;
}
div[data-testid="stNumberInput"] > div > div:nth-child(2){
  background:#ffffff !important; border-left:1.5px solid #dfe7ef !important;
  border-radius:0 24px 24px 0 !important; padding:2px !important;
}
div[data-testid="stNumberInput"] button{
  background:#eef3ff !important; color:#000033 !important;
  border:1px solid #dfe7ef !important; border-radius:12px !important;
  box-shadow:none !important;
}

/* Botones */
div.stButton > button{
  width:100%; background:#ffffff !important; color:#000033 !important;
  border:1.5px solid #dfe7ef !important; border-radius:16px !important;
  padding:14px 18px !important; box-shadow:0 6px 16px rgba(17,24,39,.06) !important;
}
div.stButton > button:hover{ background:#f6f9ff !important; }
#gt-submit-btn button{ width:100% !important; }

/* Pill peso aplicable */
.gt-pill{
  display:inline-flex; align-items:center; gap:.75rem;
  background:#fff; border:1.5px solid #dfe7ef; border-radius:14px;
  padding:10px 14px; box-shadow:0 6px 16px rgba(17,24,39,.06);
}
.gt-pill b{ font-size:18px; }

/* Popup */
.gt-overlay{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:99999;
  display:flex; align-items:center; justify-content:center; }
.gt-modal{ max-width:680px; width:92%; background:#fff; color:#000033;
  border:1.5px solid #dfe7ef; border-radius:18px; padding:28px 24px; }
.gt-actions{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:16px; }
.gt-btn{ display:inline-block; text-align:center; border:1.5px solid #dfe7ef;
  border-radius:16px; background:#eef5ff; color:#000033; padding:14px 16px;
  cursor:pointer; font-size:18px; text-decoration:none; }

/* Grids acciones (desktop fila / mobile apilado) */
@media (min-width: 900px){
  .gt-actions-row{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }
}
@media (max-width: 899px){
  .gt-actions-row{ display:grid; grid-template-columns:1fr; gap:12px; }
}
</style>
""", unsafe_allow_html=True)

# -------------------- Estado --------------------
FACTOR_VOL = 5000

def init_state():
    st.session_state.setdefault("rows", [{"cant":0, "ancho":0, "alto":0, "largo":0}])
    st.session_state.setdefault("productos", [{"descripcion":"", "link":""}])
    st.session_state.setdefault("nombre","")
    st.session_state.setdefault("email","")
    st.session_state.setdefault("telefono","")
    st.session_state.setdefault("peso_bruto_raw","0.00")
    st.session_state.setdefault("peso_bruto",0.0)
    st.session_state.setdefault("valor_mercaderia_raw","0.00")
    st.session_state.setdefault("valor_mercaderia",0.0)
    st.session_state.setdefault("show_dialog", False)
    st.session_state.setdefault("form_errors", [])
init_state()

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
    if not any(p["descripcion"].strip() and p["link"].strip() for p in st.session_state.productos):
        errs.append("• Cargá al menos un producto con descripción y link.")
    if not any(
        to_float(r["cant"])>0 and (to_float(r["ancho"])+to_float(r["alto"])+to_float(r["largo"]))>0
        for r in st.session_state.rows
    ):
        errs.append("• Ingresá al menos un bulto con cantidad y medidas.")
    return errs

# -------------------- Callbacks simples --------------------
def add_row(): st.session_state.rows.append({"cant": 0, "ancho": 0, "alto": 0, "largo": 0})
def clear_rows(): st.session_state.rows = [{"cant": 0, "ancho": 0, "alto": 0, "largo": 0}]
def add_producto(): st.session_state.productos.append({"descripcion":"", "link":""})
def clear_productos(): st.session_state.productos = [{"descripcion":"", "link":""}]

# -------------------- Header --------------------
st.markdown("""
<div class="soft-card gt-section">
  <h2 style="margin:0;">📦 Cotización de Envío por Courier</h2>
  <p style="margin:6px 0 0;">Completá tus datos, el producto y sus medidas, y te enviamos la cotización por mail.</p>
</div>
""", unsafe_allow_html=True)
st.write("")

# -------------------- Datos de contacto --------------------
with st.container():
    st.markdown('<div class="gt-section">', unsafe_allow_html=True)
    st.subheader("Datos de contacto")
    c1,c2,c3 = st.columns([1.1,1.1,1.0])
    with c1: st.session_state.nombre = st.text_input("Nombre completo*", value=st.session_state.nombre, placeholder="Ej: Juan Pérez")
    with c2: st.session_state.email = st.text_input("Correo electrónico*", value=st.session_state.email, placeholder="ejemplo@email.com")
    with c3: st.session_state.telefono = st.text_input("Teléfono*", value=st.session_state.telefono, placeholder="Ej: 11 5555 5555")
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Productos (tarjetas) --------------------
st.markdown('<div class="gt-section">', unsafe_allow_html=True)
st.subheader("Productos")
st.caption("Cargá descripción y link del/los producto(s). Podés agregar varios.")

# manejar eliminación por índice tras el loop
del_prod_idx = None
for i, p in enumerate(st.session_state.productos):
    st.markdown('<div class="gt-card">', unsafe_allow_html=True)
    st.markdown(f"**Producto {i+1}**")
    pc1, pc2 = st.columns([1, 1])
    with pc1:
        st.session_state.productos[i]["descripcion"] = st.text_area(
            "Descripción*", value=p["descripcion"], key=f"prod_desc_{i}",
            placeholder='Ej: "Máquina selladora de bolsas"', height=120
        )
    with pc2:
        st.session_state.productos[i]["link"] = st.text_input(
            "Link*", value=p["link"], key=f"prod_link_{i}", placeholder="https://..."
        )
    col_del, _ = st.columns([1,3])
    with col_del:
        if st.button("🗑️ Eliminar producto", key=f"del_prod_{i}", use_container_width=True):
            del_prod_idx = i
    st.markdown('</div>', unsafe_allow_html=True)

if del_prod_idx is not None:
    st.session_state.productos.pop(del_prod_idx)

st.markdown('<div class="gt-actions-row">', unsafe_allow_html=True)
cpa, cpb = st.columns(2)
with cpa: st.button("➕ Agregar producto", on_click=add_producto, use_container_width=True)
with cpb: st.button("🧹 Vaciar productos", on_click=clear_productos, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Bultos (tarjetas) --------------------
st.markdown('<div class="gt-section">', unsafe_allow_html=True)
st.subheader("Bultos")
st.caption("Cargá por bulto: **cantidad** y **dimensiones en cm**. Calculamos el **peso volumétrico**.")

del_row_idx = None
for i, r in enumerate(st.session_state.rows):
    st.markdown('<div class="gt-card">', unsafe_allow_html=True)
    st.markdown(f"**Bulto {i+1}**")
    c1, c2, c3, c4 = st.columns([0.9, 1, 1, 1])
    with c1: st.session_state.rows[i]["cant"]  = st.number_input("Cantidad",  min_value=0,   step=1,   value=int(r["cant"]),  key=f"cant_{i}")
    with c2: st.session_state.rows[i]["ancho"] = st.number_input("Ancho (cm)", min_value=0.0, step=1.0, value=float(r["ancho"]), key=f"an_{i}")
    with c3: st.session_state.rows[i]["alto"]  = st.number_input("Alto (cm)",  min_value=0.0, step=1.0, value=float(r["alto"]),  key=f"al_{i}")
    with c4: st.session_state.rows[i]["largo"] = st.number_input("Largo (cm)", min_value=0.0, step=1.0, value=float(r["largo"]), key=f"lar_{i}")
    col_del, _ = st.columns([1,3])
    with col_del:
        if st.button("🗑️ Eliminar bulto", key=f"del_row_{i}", use_container_width=True):
            del_row_idx = i
    st.markdown('</div>', unsafe_allow_html=True)

if del_row_idx is not None:
    st.session_state.rows.pop(del_row_idx)

st.markdown('<div class="gt-actions-row">', unsafe_allow_html=True)
ba, bb = st.columns(2)
with ba: st.button("➕ Agregar bulto", on_click=add_row, use_container_width=True)
with bb: st.button("🧹 Vaciar bultos", on_click=clear_rows, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Pesos --------------------
st.markdown('<div class="gt-section">', unsafe_allow_html=True)
st.subheader("Pesos")
m1, m2 = st.columns([1.2, 1.0])
with m1:
    st.session_state.peso_bruto_raw = st.text_input(
        "Peso bruto total (kg)", value=st.session_state.peso_bruto_raw,
        help="Usá punto o coma para decimales (ej: 1.25)"
    )
    st.session_state.peso_bruto = to_float(st.session_state.peso_bruto_raw, 0.0)

def compute_total_vol(rows):
    total = 0.0
    for r in rows:
        total += (to_float(r["cant"])*to_float(r["ancho"])*to_float(r["alto"])*to_float(r["largo"])) / FACTOR_VOL
    return round(total, 2)

total_peso_vol = compute_total_vol(st.session_state.rows)
peso_aplicable = max(total_peso_vol, st.session_state.peso_bruto)

with m2:
    st.markdown(f"<div class='gt-pill'><span>Peso aplicable (kg) 🔒</span> <b>{peso_aplicable:,.2f}</b></div>", unsafe_allow_html=True)
    st.caption(f"Se toma el mayor entre peso volumétrico ({total_peso_vol:,.2f}) y peso bruto ({st.session_state.peso_bruto:,.2f}).")

# -------------------- Valor mercadería --------------------
st.subheader("Valor de la mercadería")
st.session_state.valor_mercaderia_raw = st.text_input("Valor total (USD)", value=st.session_state.valor_mercaderia_raw)
st.session_state.valor_mercaderia = to_float(st.session_state.valor_mercaderia_raw, 0.0)

# -------------------- Submit --------------------
st.write("")
st.markdown('<div id="gt-submit-btn" class="gt-section">', unsafe_allow_html=True)
submit_clicked = st.button("📨 Solicitar cotización", use_container_width=True, key="gt_submit_btn")
st.markdown('</div>', unsafe_allow_html=True)

if submit_clicked:
    st.session_state.form_errors = validate()
    if not st.session_state.form_errors:
        productos_validos = [
            {"descripcion": p["descripcion"].strip(), "link": p["link"].strip()}
            for p in st.session_state.productos if p["descripcion"].strip() and p["link"].strip()
        ]
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "origen": "streamlit-cotizador",
            "factor_vol": FACTOR_VOL,
            "contacto": {
                "nombre": st.session_state.nombre.strip(),
                "email": st.session_state.email.strip(),
                "telefono": st.session_state.telefono.strip()
            },
            "productos": productos_validos,
            "bultos": st.session_state.rows,
            "pesos": {
                "volumetrico_kg": total_peso_vol,
                "bruto_kg": st.session_state.peso_bruto,
                "aplicable_kg": peso_aplicable
            },
            "valor_mercaderia_usd": st.session_state.valor_mercaderia
        }
        try: post_to_webhook(payload)
        except: pass
        st.session_state.show_dialog = True

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
