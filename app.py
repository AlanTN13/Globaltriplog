import json
import datetime as dt
import uuid
import requests
import streamlit as st

# ====== Brand ======
PRIMARY = "#0B3A66"   # azul GlobalTrip aprox
ACCENT   = "#FFB703"   # acento cálido

st.set_page_config(page_title="GlobalTrip — Cotización Courier", page_icon="📦", layout="wide")

# ====== Estilos ======
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
:root {{
  --primary: {PRIMARY};
  --accent:  {ACCENT};
}}
html, body, [class*="st-"] {{
  font-family: 'Poppins', system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}}
h1,h2,h3,h4 {{ color: var(--primary); font-weight:700; }}
.stButton>button {{
  background: var(--primary); color:#fff; border:0; border-radius:10px; padding:0.6rem 1.1rem; font-weight:600;
}}
.stButton>button:hover {{ filter: brightness(1.08); }}
.stTextInput>div>div>input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] input {{
  border-radius:10px !important;
}}
.badge {{
  display:inline-block; background: #e7f0ff; color: var(--primary);
  padding:.25rem .6rem; border-radius:999px; font-size:.8rem; font-weight:600
}}
.card {{ border:1px solid #eaeaea; border-radius:16px; padding:1.1rem; background:#fff; }}
.footer-note {{ color:#6b7280; font-size:.85rem }}
</style>
""", unsafe_allow_html=True)

# ====== Encabezado ======
col_logo, col_title, col_cta = st.columns([1,2,1], gap="large")
with col_title:
    st.markdown("### <span class='badge'>GlobalTrip</span>", unsafe_allow_html=True)
    st.markdown("## Cotización de Envío por Courier")
    st.caption("Completá los datos de tu producto y te respondemos por mail con la **cotización final**. No calculamos en vivo.")
with col_cta:
    st.markdown("<div style='text-align:right'>📞 +54 11 1234 5678<br>✉️ hola@globaltriplog.com</div>", unsafe_allow_html=True)

st.divider()

# ====== Datos del solicitante ======
st.markdown("### Datos del solicitante")
c1, c2, c3 = st.columns([1.3,1.3,1])
with c1:
    nombre = st.text_input("Nombre completo*", placeholder="Ej: Carlos Vázquez")
with c2:
    mail = st.text_input("Email*", placeholder="tu@empresa.com")
with c3:
    es_alumno = st.toggle("¿Es alumno GlobalTrip?", value=False)

# ====== Producto ======
st.markdown("### Información del producto")
c4, c5 = st.columns([2,1])
with c4:
    descripcion = st.text_input("Descripción del producto*", placeholder="Ej: Máquina selladora al vacío + repuestos")
with c5:
    valor_mercaderia = st.number_input("Valor mercadería (USD)*", min_value=0.0, step=1.0)

link_producto = st.text_input("Link del producto (opcional)", placeholder="https://...")

# ====== Bultos dinámicos ======
st.markdown("### Bultos")
st.caption("Ingresá medidas en **centímetros** y peso en **kilogramos**.")

if "rows" not in st.session_state:
    st.session_state.rows = 1

def add_row():
    st.session_state.rows += 1
def del_row():
    st.session_state.rows = max(1, st.session_state.rows - 1)

a1, a2 = st.columns([1,1])
with a1: st.button("➕ Agregar fila", use_container_width=True, on_click=add_row)
with a2: st.button("➖ Quitar fila", use_container_width=True, on_click=del_row)

bultos = []
grid_header = st.columns([0.6,1,1,1,1])
for c, lbl in zip(grid_header, ["Cant.", "Alto (cm)", "Ancho (cm)", "Largo (cm)", "Peso (kg)"]):
    c.markdown(f"**{lbl}**")

for i in range(st.session_state.rows):
    c_q, c_h, c_w, c_l, c_wt = st.columns([0.6,1,1,1,1])
    cant = c_q.number_input(f"cant_{i}", min_value=1, value=1, step=1, label_visibility="collapsed")
    alto = c_h.number_input(f"alto_{i}", min_value=0.0, value=10.0, step=1.0, label_visibility="collapsed")
    ancho = c_w.number_input(f"ancho_{i}", min_value=0.0, value=10.0, step=1.0, label_visibility="collapsed")
    largo = c_l.number_input(f"largo_{i}", min_value=0.0, value=10.0, step=1.0, label_visibility="collapsed")
    peso  = c_wt.number_input(f"peso_{i}",  min_value=0.0, value=1.0, step=0.1, label_visibility="collapsed")
    bultos.append({
        "cantidad": int(cant),
        "alto_cm": float(alto),
        "ancho_cm": float(ancho),
        "largo_cm": float(largo),
        "peso_kg": float(peso)
    })

# ====== Declaraciones ======
st.markdown("### Declaraciones")
c_liq, c_ali, c_salud = st.columns(3)
with c_liq:
    liquido = st.toggle("Contiene líquido", value=False)
    aerosol = st.toggle("Contiene aerosol", value=False)
    quimicos = st.toggle("Contiene químicos", value=False)
with c_ali:
    contacto_alimentos = st.selectbox("¿Contacto con alimentos?", ["No", "Sí"])
with c_salud:
    uso_salud = st.selectbox("¿Uso de salud?", ["No", "Sí"])

observaciones = st.text_area("Observaciones (opcional)", placeholder="Información adicional relevante…")

# ====== Logística ======
st.markdown("### Logística")
c_or, c_de, c_cour = st.columns(3)
with c_or:
    ciudad_retiro = st.selectbox("Ciudad de retiro", ["Guangzhou", "Shenzhen", "Shanghai", "Otra"])
with c_de:
    ciudad_entrega = st.selectbox("Ciudad de entrega", ["CABA", "GBA", "Córdoba", "Rosario", "Otra"])
with c_cour:
    courier = st.selectbox("Courier preferido", ["DHL", "UPS", "FedEx", "Sin preferencia"])

st.divider()

# ====== Armado del payload ======
now = dt.datetime.now().astimezone()
payload = {
    "ID": f"CUR-{now.strftime('%Y')}-{str(uuid.uuid4())[:6].upper()}",
    "Fecha": now.isoformat(timespec="seconds"),
    "Es Alumno": bool(es_alumno),
    "Nombre": nombre.strip(),
    "Mail": mail.strip(),
    "Descripcion_Producto": descripcion.strip(),
    "Valor mercadería": float(valor_mercaderia or 0),
    "Bultos": bultos,
    "Peso bruto": float(sum(b["peso_kg"] * b["cantidad"] for b in bultos)),
    "Categoria": "",
    "Link_Producto": link_producto.strip(),
    "Contiene": {
        "liquido": liquido,
        "aerosol": aerosol,
        "quimicos": quimicos
    },
    "Contacto_Alimentos": "Sí" if contacto_alimentos == "Sí" else "No",
    "Uso_Salud": "Sí" if uso_salud == "Sí" else "No",
    "Observaciones": observaciones.strip(),
    "Ciudad_Retiro": ciudad_retiro,
    "Ciudad_Entrega": ciudad_entrega,
    "Courier": courier
}

# ====== Webhook / envío ======
st.markdown("### Envío")
st.caption("Revisá el resumen y enviá tu consulta. Te respondemos por mail con la cotización final.")
with st.expander("Ver JSON que se enviará", expanded=False):
    st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")

# Secret (recomendado en Streamlit Cloud)
webhook_secret = st.secrets.get("webhook_url", "")
# Campo opcional visible solo si no hay secret
if not webhook_secret:
    webhook_secret = st.text_input("Webhook (temporal, si no está en secrets)", placeholder="https://.../webhook", type="password")

col_send, col_dl = st.columns([1,1])
with col_send:
    send = st.button("📨 Enviar solicitud", use_container_width=True)
with col_dl:
    st.download_button("⬇️ Descargar JSON", data=json.dumps(payload, ensure_ascii=False, indent=2),
                       file_name=f"{payload['ID']}.json", mime="application/json", use_container_width=True)

if send:
    # validaciones mínimas
    missing = []
    if not nombre: missing.append("Nombre")
    if not mail: missing.append("Email")
    if not descripcion: missing.append("Descripción")
    if not valor_mercaderia: missing.append("Valor mercadería")

    if missing:
        st.error(f"Completá: {', '.join(missing)}.")
    elif not webhook_secret:
        st.error("Configurá el *webhook* (en **Secrets** de Streamlit Cloud) o pegalo temporalmente arriba.")
    else:
        try:
            resp = requests.post(webhook_secret, json=payload, timeout=15)
            if 200 <= resp.status_code < 300:
                st.success("¡Enviado! Te contactaremos al mail con la cotización final.")
            else:
                st.error(f"El servidor respondió {resp.status_code}. Revisá el endpoint.")
        except Exception as e:
            st.error(f"No pudimos enviar la solicitud: {e}")

st.markdown("<br><div class='footer-note'>© 2025 GlobalTrip. Todos los derechos reservados.</div>", unsafe_allow_html=True)
