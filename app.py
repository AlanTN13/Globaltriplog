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

# -------------------- Estilos (coherencia visual) --------------------
st.markdown("""
<style>
/* ===== Design tokens ===== */
:root{
  --ink:#0e1b3d;
  --muted:#0e1b3db3;
  --bg:#ffffff;
  --border:#e6ebf3;
  --card-shadow:0 6px 16px rgba(17,24,39,.06);
  --radius:14px;

  /* escala espaciados (4/8/12/16/24) */
  --s-1:4px; --s0:8px; --s1:12px; --s2:16px; --s3:24px;
}

/* ===== Reset de layout streamlit ===== */
:root{ --header-height:0 !important; }
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer, header,
div[data-testid="stDecoration"]{ display:none !important; }

html, body, .stApp, [data-testid="stAppViewContainer"], section.main{ background:var(--bg) !important; color:var(--ink) !important; }
[data-testid="stAppViewContainer"]{ padding-top:0 !important; }
section.main{ padding-top:0 !important; }
section.main > div.block-container{ padding-top:var(--s0) !important; padding-bottom:var(--s3) !important; }

/* tipografía y márgenes consistentes */
h1,h2,h3,h4,h5,h6{ color:var(--ink) !important; margin:var(--s0) 0 var(--s0) 0 !important; }
p, label, small, span{ color:var(--ink) !important; margin:0 !important; }
.stCaption, .stMarkdown p, .st-emotion-cache-1629p8f{ color:var(--muted) !important; }

/* ===== Contenedores ===== */
.gt-section{ max-width:1100px; margin:0 auto; }
.soft-card{
  background:var(--bg); border:1.5px solid var(--border); border-radius:var(--radius);
  padding:var(--s2); box-shadow:0 8px 18px rgba(17,24,39,.07);
  margin:var(--s2) 0 var(--s2);
}
.gt-card{
  background:var(--bg); border:1.5px solid var(--border); border-radius:var(--radius);
  padding:var(--s2); box-shadow:var(--card-shadow);
  margin:var(--s1) 0 var(--s1);
}

/* separar bloques y columnas con el mismo gap */
div[data-testid="stVerticalBlock"]{ gap:var(--s2) !important; }
div[data-testid="stHorizontalBlock"]{ gap:var(--s2) !important; }
div[data-testid="column"]{ padding:0 !important; }

/* ===== Inputs ===== */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea{
  background:var(--bg) !important; color:var(--ink) !important;
  border:1.5px solid var(--border) !important; border-radius:var(--radius) !important;
  padding:12px var(--s2) !important; box-shadow:none !important;
}
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder{ color:var(--muted) !important; }

/* NumberInput: misma altura y menos “ruido” */
div[data-testid="stNumberInput"] > div{
  background:var(--bg) !important; border:1.5px solid var(--border) !important;
  border-radius:24px !important; box-shadow:none !important;
}
div[data-testid="stNumberInput"] input{
  background:var(--bg) !important; color:var(--ink) !important;
  height:44px !important; padding:0 var(--s2) !important; border:none !important;
}
div[data-testid="stNumberInput"] > div > div:nth-child(2){
  background:var(--bg) !important; border-left:1.5px solid var(--border) !important;
  border-radius:0 24px 24px 0 !important; padding:2px !important;
}
div[data-testid="stNumberInput"] button{
  background:#eef3ff !important; color:var(--ink) !important;
  border:1px solid var(--border) !important; border-radius:10px !important; box-shadow:none !important;
}

/* ===== Botones ===== */
div.stButton{ margin:0 !important; }
div.stButton > button{
  width:100%; background:#f7faff !important; color:var(--ink) !important;
  border:1.5px solid var(--border) !important; border-radius:var(--radius) !important;
  padding:12px var(--s2) !important; box-shadow:var(--card-shadow) !important;
}
div.stButton > button:hover{ background:#eef3ff !important; }
#gt-submit-btn button{ width:100% !important; }

/* ===== Elementos utilitarios ===== */
hr{ border:none; border-top:1px solid var(--border); margin:var(--s1) 0; }

.gt-pill{
  display:inline-flex; align-items:center; gap:var(--s0);
  background:var(--bg); border:1.5px solid var(--border); border-radius:12px;
  padding:8px var(--s1); box-shadow:var(--card-shadow);
}

/* ===== Filas de acciones (Agregar/Vaciar) ===== */
.gt-actions-row{ display:grid; grid-template-columns:1fr 1fr; gap:var(--s2); margin-top:var(--s1); }
@media (max-width: 899px){ .gt-actions-row{ grid-template-columns:1fr; } }
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
    st.session_state.setdefault("pais_origen","China")   # default China
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
    if st.session_state.pais_origen == "Otro" and not st.session_state.pais_origen_otro.strip():
        errs.append("• Indicá el país de origen.")
    if not any(
        to_float(r["cant"])>0 and (to_float(r["ancho"])+to_float(r["alto"])+to_float(r["largo"]))>0
        for r in st.session_state.rows
    ):
        errs.append("• Ingresá al menos un bulto con cantidad y medidas.")
    return errs

# -------------------- Callbacks --------------------
def add_row(): st.session_state.rows.append({"cant": 0, "ancho": 0, "alto": 0, "largo": 0})
def clear_rows(): st.session_state.rows = [{"cant": 0, "ancho": 0, "alto": 0, "largo": 0}]
def add_producto(): st.session_state.productos.append({"descripcion":"", "link":""})
def clear_productos(): st.session_state.productos = [{"descripcion":"", "link":""}]

# -------------------- Header --------------------
st.markdown("""
<div class="soft-card gt-section">
  <h2 style="margin:0;">📦 Cotización de Envío por Courier</h2>
  <p style="margin:4px 0 0;">Completá tus datos, el producto y sus medidas, y te enviamos la cotización por mail.</p>
</div>
""", unsafe_allow_html=True)
st.write("")

# -------------------- Datos de contacto --------------------
st.markdown('<div class="gt-section">', unsafe_allow_html=True)
st.subheader("Datos de contacto")
c1,c2,c3 = st.columns([1.1,1.1,1.0])
with c1: st.session_state.nombre = st.text_input("Nombre completo*", value=st.session_state.nombre, placeholder="Ej: Juan Pérez")
with c2: st.session_state.email = st.text_input("Correo electrónico*", value=st.session_state.email, placeholder="ejemplo@email.com")
with c3: st.session_state.telefono = st.text_input("Teléfono*", value=st.session_state.telefono, placeholder="Ej: 11 5555 5555")
st.markdown('</div>', unsafe_allow_html=True)

# -------------------- País de origen --------------------
st.markdown('<div class="gt-section">', unsafe_allow_html=True)
st.subheader("País de origen de los productos a cotizar")
sel = st.radio("Seleccioná el país de origen:", ["China", "Otro"],
               index=0 if st.session_state.pais_origen=="China" else 1, horizontal=True)
if sel == "Otro":
    st.session_state.pais_origen = "Otro"
    st.session_state.pais_origen_otro = st.text_input("Ingresá el país de origen", value=st.session_state.pais_origen_otro).strip()
else:
    st.session_state.pais_origen = "China"
st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Productos --------------------
st.markdown('<div class="gt-section">', unsafe_allow_html=True)
st.subheader("Productos")
st.caption("Cargá descripción y link del/los producto(s). Podés agregar varios.")
st.markdown("<hr>", unsafe_allow_html=True)

del_prod_idx = None
for i, p in enumerate(st.session_state.productos):
    st.markdown('<div class="gt-card">', unsafe_allow_html=True)
    st.markdown(f"**Producto {i+1}**")
    pc1, pc2 = st.columns(2)
    with pc1:
        st.session_state.productos[i]["descripcion"] = st.text_area(
            "Descripción*", value=p["descripcion"], key=f"prod_desc_{i}",
            placeholder='Ej: "Máquina selladora de bolsas"', height=96
        )
    with pc2:
        st.session_state.productos[i]["link"] = st.text_area(
            "Link*", value=p["link"], key=f"prod_link_{i}",
            placeholder="https://...", height=96
        )
    col_del, _ = st.columns([1,3])
    with col_del:
        if st.button("🗑️ Eliminar producto", key=f"del_prod_{i}", use_container_width=True):
            del_prod_idx = i
    st.markdown('</div>', unsafe_allow_html=True)
if del_prod_idx is not None:
    st.session_state.productos.pop(del_prod_idx)

st.markdown('<div class="gt-actions-row">', unsafe_allow_html=True)
pA, pB = st.columns(2)
with pA: st.button("➕ Agregar producto", on_click=add_producto, use_container_width=True)
with pB: st.button("🧹 Vaciar productos", on_click=clear_productos, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Bultos --------------------
st.markdown('<div class="gt-section">', unsafe_allow_html=True)
st.subheader("Bultos")
st.caption("Cargá por bulto: **cantidad** y **dimensiones en cm**. Calculamos el **peso volumétrico**.")
st.markdown("<hr>", unsafe_allow_html=True)

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
st.subheader("Peso total de los bultos")
m1, m2 = st.columns([1.2, 1.0])
with m1:
    st.session_state.peso_bruto_raw = st.text_input(
        "Peso bruto total (kg)", value=st.session_state.peso_bruto_raw,
        help="Usá punto o coma para decimales (ej: 1.25)"
    )
    st.session_state.peso_bruto = to_float(st.session_state.peso_bruto_raw, 0.0)
total_peso_vol = compute_total_vol(st.session_state.rows)
peso_aplicable = max(total_peso_vol, st.session_state.peso_bruto)
with m2:
    st.markdown(f"<div class='gt-pill'><span>Peso aplicable (kg) 🔒</span> <b>{peso_aplicable:,.2f}</b></div>", unsafe_allow_html=True)
    st.caption(f"Se toma el mayor entre peso volumétrico ({total_peso_vol:,.2f}) y peso bruto ({st.session_state.peso_bruto:,.2f}).")
st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Valor total --------------------
st.markdown('<div class="gt-section">', unsafe_allow_html=True)
st.subheader("Valor total del pedido")
st.session_state.valor_mercaderia_raw = st.text_input("Valor total (USD)", value=st.session_state.valor_mercaderia_raw, placeholder="Ej: 2500.00")
st.session_state.valor_mercaderia = to_float(st.session_state.valor_mercaderia_raw, 0.0)
st.markdown('</div>', unsafe_allow_html=True)

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
        pais_final = st.session_state.pais_origen if st.session_state.pais_origen == "China" else st.session_state.pais_origen_otro.strip()
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
            "bultos": st.session_state.rows,
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
