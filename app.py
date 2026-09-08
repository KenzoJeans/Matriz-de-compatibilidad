import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y TEMA OSCURO (CUSTOM CSS)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Matriz de Compatibilidad Química",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS para forzar Tema Oscuro Elegante y Tarjetas de Alto Contraste
DARK_THEME_CSS = """
<style>
    /* Fondo principal y colores de texto */
    .stApp {
        background-color: #0e1117;
        color: #e6edf3;
    }
    
    /* Barra lateral */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Tarjetas KPI de resumen */
    .kpi-card {
        padding: 18px;
        border-radius: 12px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .kpi-incompatible {
        background-color: rgba(255, 77, 79, 0.15);
        border: 1px solid #ff4d4f;
        color: #ff4d4f;
    }
    .kpi-compatible {
        background-color: rgba(39, 201, 63, 0.15);
        border: 1px solid #27c93f;
        color: #27c93f;
    }
    .kpi-total {
        background-color: rgba(88, 166, 255, 0.15);
        border: 1px solid #58a6ff;
        color: #58a6ff;
    }

    /* Tarjetas de resultados individuales */
    .card-incompatible {
        background-color: rgba(255, 77, 79, 0.12);
        border-left: 6px solid #ff4d4f;
        border-top: 1px solid #30363d;
        border-right: 1px solid #30363d;
        border-bottom: 1px solid #30363d;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    .card-compatible {
        background-color: rgba(39, 201, 63, 0.05);
        border-left: 6px solid #27c93f;
        border-top: 1px solid #21262d;
        border-right: 1px solid #21262d;
        border-bottom: 1px solid #21262d;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    .card-precaucion {
        background-color: rgba(234, 179, 8, 0.12);
        border-left: 6px solid #eab308;
        border-top: 1px solid #30363d;
        border-right: 1px solid #30363d;
        border-bottom: 1px solid #30363d;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
    }

    /* Insignias o Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: bold;
        display: inline-block;
    }
    .badge-danger {
        background-color: #ff4d4f;
        color: #ffffff;
    }
    .badge-success {
        background-color: #27c93f;
        color: #0d1117;
    }
    .badge-warning {
        background-color: #eab308;
        color: #0d1117;
    }

    /* Ajustes de encabezados */
    h1, h2, h3, h4 {
        color: #ffffff !important;
    }
</style>
"""
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. CARGA DE DATOS DESDE GOOGLE SHEETS
# ---------------------------------------------------------
SHEET_ID = "13iz4k7x-fvdN3yLzLgVOkhIss8P6yCv-"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=600)
def cargar_datos():
    try:
        df = pd.read_csv(CSV_URL)
        # Limpieza de espacios en blanco
        df["Quimico_1"] = df["Quimico_1"].astype(str).str.strip()
        df["Quimico_2"] = df["Quimico_2"].astype(str).str.strip()
        df["Compatibilidad"] = df["Compatibilidad"].astype(str).str.strip()
        df["Notas"] = df["Notas"].fillna("").astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error al cargar la base de datos desde Google Sheets: {e}")
        return pd.DataFrame()

df = cargar_datos()

if df.empty:
    st.stop()

# ---------------------------------------------------------
# 3. INTERFAZ Y BARRA LATERAL
# ---------------------------------------------------------
st.title("🧪 Evaluador de Compatibilidad Química")
st.caption("Matriz dinámica interactiva para la gestión segura de reactivos")

# Lista de químicos únicos
quimicos_unicos = sorted(list(set(df["Quimico_1"].unique()).union(set(df["Quimico_2"].unique()))))

st.sidebar.header("⚙️ Panel de Selección")
sustancia_seleccionada = st.sidebar.selectbox(
    "1. Selecciona la Sustancia Química:",
    quimicos_unicos,
    index=0
)

filtro_estado = st.sidebar.radio(
    "2. Filtrar sustancias comparadas:",
    ["Mostrar Todas", "Solo Incompatibles 🔴", "Solo Compatibles 🟢"]
)

busqueda_texto = st.sidebar.text_input("3. Buscar por nombre:", "")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Las sustancias **INCOMPATIBLES** siempre aparecen de primeras resaltadas en rojo.")

# ---------------------------------------------------------
# 4. FILTRADO Y ORDENAMIENTO (INCOMPATIBLES DE PRIMERAS)
# ---------------------------------------------------------
df_foco = df[df["Quimico_1"] == sustancia_seleccionada].copy()

if df_foco.empty:
    df_foco = df[df["Quimico_2"] == sustancia_seleccionada].copy()
    df_foco = df_foco.rename(columns={"Quimico_1": "Quimico_2", "Quimico_2": "Quimico_1"})

# Mapeo numérico de prioridad: Incompatible (0) > Precaución (1) > Compatible (2)
def obtener_prioridad(val):
    v = str(val).lower()
    if "incompatible" in v:
        return 0
    elif "precauci" in v or "precaución" in v:
        return 1
    elif "compatible" in v:
        return 2
    return 3

df_foco["Prioridad"] = df_foco["Compatibilidad"].apply(obtener_prioridad)

# Ordenamiento crítico: Prioridad 0 (Rojos) de primeras, luego alfabéticamente
df_foco = df_foco.sort_values(by=["Prioridad", "Quimico_2"]).reset_index(drop=True)

# Filtro por búsqueda de texto
if busqueda_texto:
    df_foco = df_foco[df_foco["Quimico_2"].str.contains(busqueda_texto, case=False, na=False)]

# Filtro por selección
if filtro_estado == "Solo Incompatibles 🔴":
    df_foco = df_foco[df_foco["Prioridad"] == 0]
elif filtro_estado == "Solo Compatibles 🟢":
    df_foco = df_foco[df_foco["Prioridad"] == 2]

# ---------------------------------------------------------
# 5. TARJETAS DE MÉTRICAS (KPIs)
# ---------------------------------------------------------
total_evaluados = len(df_foco)
total_incompatibles = len(df_foco[df_foco["Prioridad"] == 0])
total_compatibles = len(df_foco[df_foco["Prioridad"] == 2])

st.markdown(f"### 📍 Evaluando: **{sustancia_seleccionada}**")

col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
with col_kpi1:
    st.markdown(f'<div class="kpi-card kpi-incompatible"><h2>🚨 {total_incompatibles}</h2>INCOMPATIBLES</div>', unsafe_allow_html=True)
with col_kpi2:
    st.markdown(f'<div class="kpi-card kpi-compatible"><h2>✅ {total_compatibles}</h2>COMPATIBLES</div>', unsafe_allow_html=True)
with col_kpi3:
    st.markdown(f'<div class="kpi-card kpi-total"><h2>📊 {total_evaluados}</h2>MOSTRADAS</div>', unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------
# 6. RENDERIZADO VISUAL
# ---------------------------------------------------------
vista_modo = st.radio("Formato de Presentación:", ["🎴 Tarjetas de Alto Contraste", "📊 Tabla Interactiva"], horizontal=True)

if vista_modo == "🎴 Tarjetas de Alto Contraste":
    if df_foco.empty:
        st.warning("No hay resultados con los filtros actuales.")
    else:
        for _, row in df_foco.iterrows():
            q_destino = row["Quimico_2"]
            estado = row["Compatibilidad"]
            notas = row["Notas"]
            prio = row["Prioridad"]

            if prio == 0:
                # Incompatible - ROJO
                card_html = f"""
                <div class="card-incompatible">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #ffffff;">❌ {q_destino}</h4>
                        <span class="badge badge-danger">INCOMPATIBLE</span>
                    </div>
                    {f'<p style="margin-top: 10px; color: #ff8585; font-size: 0.95rem;">⚠️ <b>Observación/Restricción:</b> {notas}</p>' if notas else '<p style="margin-top: 8px; color: #8b949e; font-size: 0.85rem;">Sin observaciones adicionales escritas.</p>'}
                </div>
                """
            elif prio == 1:
                # Precaución - AMARILLO
                card_html = f"""
                <div class="card-precaucion">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #ffffff;">⚠️ {q_destino}</h4>
                        <span class="badge badge-warning">{estado.upper()}</span>
                    </div>
                    {f'<p style="margin-top: 10px; color: #fde047; font-size: 0.95rem;">📌 <b>Nota:</b> {notas}</p>' if notas else ''}
                </div>
                """
            else:
                # Compatible - VERDE
                card_html = f"""
                <div class="card-compatible">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #ffffff;">✅ {q_destino}</h4>
                        <span class="badge badge-success">COMPATIBLE</span>
                    </div>
                    {f'<p style="margin-top: 10px; color: #86efac; font-size: 0.95rem;">📌 <b>Nota:</b> {notas}</p>' if notas else ''}
                </div>
                """
            st.markdown(card_html, unsafe_allow_html=True)

else:
    # Vista en Tabla
    def estilo_filas(val):
        v = str(val).lower()
        if "incompatible" in v:
            return "background-color: #451a1d; color: #ff8585; font-weight: bold;"
        elif "compatible" in v:
            return "background-color: #133820; color: #86efac;"
        return "background-color: #3b2e04; color: #fde047;"

    df_mostrar = df_foco[["Quimico_2", "Compatibilidad", "Notas"]].rename(
        columns={"Quimico_2": "Sustancia Comparada", "Compatibilidad": "Resultado", "Notas": "Observaciones"}
    )

    st.dataframe(
        df_mostrar.style.map(estilo_filas, subset=["Resultado"]),
        use_container_layout=True,
        height=500
    )
