import pandas as pd
import numpy as np
import streamlit as st
import requests
import json
from datetime import datetime

# ===== Brand Colors =====
PRIMARY = "#0B3A66"  # Azul GlobalTrip
ACCENT = "#FFB703"   # Detalle cálido

st.set_page_config(
    page_title="GlobalTrip – Cotización Courier",
    page_icon="📦",
    layout="wide"
)

# ===== Estilos =====
st.markdown(f"""
<style>
:root {{
    --primary: {PRIMARY};
    --accent: {ACCENT};
}}
.block-container {{ padding-top: 1.2rem; }}
h1, h2, h3, h4 {{ color: var(--primary); font-weight: 700; }}
.stButton>button {{
    background-color: var(--primary);
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 5px;
}}
.stButton>button:hover {{
    background-color: var(--accent);
    color: black;
}}
</style>
""", unsafe_allow_html=True)

# ===== Título =====
st.title("📦 GlobalTrip – Cotización Courier")
st.write("Complete los datos del envío para obtener una cotización.")

# ===== Formulario =====
with st.form("cotizacion_form"):
    id_envio = st.text_input("ID de Envío", "CUR-2025-000312")
    fecha = st.date_input("Fecha", datetime.now())
    es_alumno = st.checkbox("Es Alumno", value=True)
    nombre = st.text_input("Nombre", "Carlos Vázquez")
    mail = st.text_input("Email", "carlos.vazquez@gmail.com")
    descripcion = st.text_area("Descripción del Producto", "Máquina selladora al vacío de alimentos + repuestos")
    valor = st.number_input("Valor mercadería (USD)", value=135)
    
    st.subheader("Bultos")
    bultos = []
    for i in range(2):  # ejemplo con 2 bultos
        st.markdown(f"**Bulto {i+1}**")
        cantidad = st.number_input(f"Cantidad bulto {i+1}", value=1, min_value=1)
        alto = st.number_input(f"Alto (cm) bulto {i+1}", value=25 if i==0 else 15)
        ancho = st.number_input(f"Ancho (cm) bulto {i+1}", value=35 if i==0 else 25)
        largo = st.number_input(f"Largo (cm) bulto {i+1}", value=40 if i==0 else 30)
        peso = st.number_input(f"Peso (kg) bulto {i+1}", value=4.2 if i==0 else 2.0)
        bultos.append({
            "cantidad": cantidad,
            "alto_cm": alto,
            "ancho_cm": ancho,
            "largo_cm": largo,
            "peso_kg": peso
        })

    peso_bruto = st.number_input("Peso bruto (kg)", value=6.2)
    categoria = st.text_input("Categoría", "Electrodomésticos de cocina")
    link = st.text_input("Link del producto", "https://www.aliexpress.com/item/1005006021453217.html")

    contiene_liquido = st.checkbox("Contiene líquido", value=False)
    contiene_aerosol = st.checkbox("Contiene aerosol", value=False)
    contiene_quimicos = st.checkbox("Contiene químicos", value=False)

    contacto_alimentos = st.selectbox("Contacto con alimentos", ["Sí", "No"], index=0)
    uso_salud = st.selectbox("Uso para salud", ["Sí", "No"], index=1)
    observaciones = st.text_area("Observaciones", "El segundo bulto contiene bolsas de repuesto.")
    ciudad_retiro = st.text_input("Ciudad de Retiro", "Guangzhou")
    ciudad_entrega = st.text_input("Ciudad de Entrega", "CABA")
    courier = st.text_input("Courier", "DHL")

    enviado = st.form_submit_button("Enviar cotización")

if enviado:
    payload = {
        "ID": id_envio,
        "Fecha": fecha.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
        "Es Alumno": es_alumno,
        "Nombre": nombre,
        "Mail": mail,
        "Descripcion_Producto": descripcion,
        "Valor mercadería": valor,
        "Bultos": bultos,
        "Peso bruto": peso_bruto,
        "Categoria": categoria,
        "Link_Producto": link,
        "Contiene": {
            "liquido": contiene_liquido,
            "aerosol": contiene_aerosol,
            "quimicos": contiene_quimicos
        },
        "Contacto_Alimentos": contacto_alimentos,
        "Uso_Salud": uso_salud,
        "Observaciones": observaciones,
        "Ciudad_Retiro": ciudad_retiro,
        "Ciudad_Entrega": ciudad_entrega,
        "Courier": courier
    }

    try:
        url = "https://nexops.app.n8n.cloud/webhook-test/57ed992b-929f-49dd-8a11-4983bb7d6643"
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            st.success("✅ Datos enviados correctamente")
            st.json(payload)
        else:
            st.error(f"❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        st.error(f"Error enviando datos: {e}")

