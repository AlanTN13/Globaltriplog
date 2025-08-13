# ---------- Tabla única: Bultos (con Peso vol. calculado en la misma grilla) ----------
FACTOR_VOL = 5000  # cm³/kg

def calc_peso_vol_row(r):
    try:
        q = max(0, int(r.get("Cantidad", 0)))
        a = float(r.get("Ancho (cm)", 0))
        h = float(r.get("Alto (cm)", 0))
        l = float(r.get("Largo (cm)", 0))
        if q <= 0 or a <= 0 or h <= 0 or l <= 0:
            return 0.0
        return round(q * (a * h * l) / FACTOR_VOL, 2)
    except Exception:
        return 0.0

# inicializo una sola vez
if "bultos_df" not in st.session_state:
    st.session_state.bultos_df = pd.DataFrame(
        [
            {"Cantidad": 1, "Ancho (cm)": 10, "Alto (cm)": 10, "Largo (cm)": 194},
            {"Cantidad": 1, "Ancho (cm)": 40, "Alto (cm)": 28, "Largo (cm)": 48},
            *[{"Cantidad": 0, "Ancho (cm)": 0, "Alto (cm)": 0, "Largo (cm)": 0} for _ in range(6)]
        ]
    )

# SIEMPRE calculo 'Peso vol.' antes de renderizar el editor
df_to_show = st.session_state.bultos_df.copy()
df_to_show["Peso vol."] = df_to_show.apply(calc_peso_vol_row, axis=1)

st.markdown("### Bultos")
edited = st.data_editor(
    df_to_show,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Peso vol.": st.column_config.NumberColumn("Peso vol.", step=0.01, disabled=True)
    },
    key="bultos_editor",
)

# El usuario pudo cambiar cantidad/dimensiones: recalculo y guardo en sesión
edited = edited.drop(columns=["Peso vol."], errors="ignore")
edited["Peso vol."] = edited.apply(calc_peso_vol_row, axis=1)
st.session_state.bultos_df = edited

total_peso_vol = round(edited["Peso vol."].sum(), 2)
st.metric("Total peso volumétrico (kg)", f"{total_peso_vol:.2f}")
