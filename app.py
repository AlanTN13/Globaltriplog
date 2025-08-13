import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="GlobalTripLog",
    page_icon="🌍",
    layout="wide"
)

# Encabezado
st.title("🌍 GlobalTripLog")
st.subheader("Calculadora y Dashboard Interactivo")

# Sidebar para navegación
menu = st.sidebar.selectbox(
    "Navegación",
    ["Inicio", "Calculadora", "Contacto"]
)

if menu == "Inicio":
    st.write("Bienvenido a la aplicación de GlobalTripLog.")
    st.image("https://via.placeholder.com/800x300.png?text=Imagen+de+Portada", use_column_width=True)

elif menu == "Calculadora":
    st.write("Calcula tus costos y tiempos de envío.")
    
    peso = st.number_input("Peso del paquete (kg)", min_value=0.0, step=0.1)
    valor = st.number_input("Valor declarado (USD)", min_value=0.0, step=1.0)

    if st.button("Calcular"):
        impuesto = valor * 0.5  # Ejemplo: 50% de impuesto
        costo_total = valor + impuesto
        st.success(f"El costo total estimado es: USD {costo_total:.2f}")

elif menu == "Contacto":
    st.write("Formulario de contacto")
    nombre = st.text_input("Nombre")
    email = st.text_input("Email")
    mensaje = st.text_area("Mensaje")
    if st.button("Enviar"):
        st.success("Gracias por tu mensaje. Te contactaremos pronto.")

# Footer
st.markdown("---")
st.caption("© 2025 GlobalTripLog - Todos los derechos reservados")
