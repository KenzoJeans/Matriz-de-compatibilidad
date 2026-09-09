import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import unicodedata
import requests
from io import StringIO
 
# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y TEMA OSCURO (CUSTOM CSS)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Matriz de Compatibilidad Química",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)
 
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
 
    h1, h2, h3, h4 {
        color: #ffffff !important;
    }
</style>
"""
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)
 
# ---------------------------------------------------------
# 2. CARGA DE DATOS DESDE GOOGLE SHEETS
# ---------------------------------------------------------
# FIX 1: apuntar al GID específico de la pestaña "Pares_Compatibilidad".
# Ábrela en el navegador, entra a esa pestaña y copia el número después de
# "gid=" en la URL para reemplazar el valor de abajo.
SHEET_ID = "13iz4k7x-fvdN3yLzLgVOkhIss8P6yCv-"
GID_PARES = "1151033427"  # <-- reemplaza con el gid real de la pestaña Pares_Compatibilidad
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_PARES}"
 
 
def clave_orden_es(texto):
    """Genera una clave de orden alfabético en español (ignora tildes al ordenar,
    pero el texto original se conserva para mostrar en pantalla)."""
    return unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('utf-8').upper()
 
 
@st.cache_data(ttl=600)
def cargar_datos():
    # Google a veces responde 400 a peticiones sin un User-Agent de navegador
    # (lo trata como bot). Hacemos la petición con requests para poder
    # mandar ese header, en vez de dejar que pandas la haga directo.
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        resp = requests.get(CSV_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text))
    except Exception as e:
        st.error(f"Error al cargar la base de datos desde Google Sheets: {e}")
        return pd.DataFrame()
 
    columnas_esperadas = {"Quimico_1", "Quimico_2", "Compatibilidad", "Notas"}
    if not columnas_esperadas.issubset(df.columns):
        st.error(
            "El formato de la hoja no es el esperado. "
            f"Faltan columnas: {columnas_esperadas - set(df.columns)}"
        )
        return pd.DataFrame()
 
    df["Quimico_1"] = df["Quimico_1"].astype(str).str.strip()
    df["Quimico_2"] = df["Quimico_2"].astype(str).str.strip()
    df["Compatibilidad"] = df["Compatibilidad"].astype(str).str.strip()
    df["Notas"] = df["Notas"].fillna("").astype(str).str.strip()
 
    # FIX 2: la matriz original es triangular (cada par solo está registrado en
    # una dirección). La "espejamos" para tener ambas direcciones A→B y B→A,
    # evitando que la mitad del heatmap salga como "Sin Registro".
    df_espejo = df.rename(columns={"Quimico_1": "Quimico_2", "Quimico_2": "Quimico_1"})
    df_completo = pd.concat([df, df_espejo], ignore_index=True)
    df_completo = df_completo.drop_duplicates(subset=["Quimico_1", "Quimico_2"], keep="first")
 
    return df_completo
 
 
df = cargar_datos()
 
if df.empty:
    st.stop()
 
# Lista de químicos únicos, en orden alfabético real en español
quimicos_unicos = sorted(
    set(df["Quimico_1"].unique()).union(set(df["Quimico_2"].unique())),
    key=clave_orden_es
)
 
# ---------------------------------------------------------
# 3. NAVEGACIÓN PRINCIPAL CON PESTAÑAS
# ---------------------------------------------------------
st.title("🧪 Sistema de Compatibilidad Química")
st.caption("Plataforma interactiva para control de almacenamiento de reactivos")
 
col_titulo, col_boton = st.columns([5, 1])
with col_boton:
    if st.button("🔄 Actualizar datos"):
        st.cache_data.clear()
        st.rerun()
 
tab1, tab2 = st.tabs(["🔍 Consulta por Sustancia", "🗺️ Matriz Completa (Mapa de Calor)"])
 
# =========================================================
# PESTAÑA 1: CONSULTA POR SUSTANCIA
# =========================================================
with tab1:
    st.sidebar.header("⚙️ Panel de Control")
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
 
    # Como los datos ya están espejados, basta con filtrar por Quimico_1
    df_foco = df[df["Quimico_1"] == sustancia_seleccionada].copy()
 
    def obtener_prioridad(val):
        v = str(val).lower()
        if "incompatible" in v:
            return 0
        elif "precauci" in v:
            return 1
        elif "compatible" in v:
            return 2
        return 3
 
    df_foco["Prioridad"] = df_foco["Compatibilidad"].apply(obtener_prioridad)
    df_foco = df_foco.sort_values(by=["Prioridad", "Quimico_2"]).reset_index(drop=True)
 
    if busqueda_texto:
        df_foco = df_foco[df_foco["Quimico_2"].str.contains(busqueda_texto, case=False, na=False)]
 
    if filtro_estado == "Solo Incompatibles 🔴":
        df_foco = df_foco[df_foco["Prioridad"] == 0]
    elif filtro_estado == "Solo Compatibles 🟢":
        df_foco = df_foco[df_foco["Prioridad"] == 2]
 
    # Indicadores KPIs
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
 
        try:
            df_estilizado = df_mostrar.style.map(estilo_filas, subset=["Resultado"])
        except AttributeError:
            df_estilizado = df_mostrar.style.applymap(estilo_filas, subset=["Resultado"])
 
        st.dataframe(df_estilizado, use_container_width=True, height=500)
 
 
import numpy as np

# =========================================================
# PESTAÑA 2: MAPA DE CALOR GENERAL (TRIANGULAR CON BÚSQUEDA)
# =========================================================
with tab2:
    st.subheader("🗺️ Matriz Global de Compatibilidad")
    st.caption("Pasa el cursor sobre cualquier casilla para ver los detalles. Usa la rueda del mouse para hacer zoom o arrastra para desplazarte.")

    # ---------------------------------------------------------
    # PANEL DE CONTROL DE ENFOQUE Y BÚSQUEDA
    # ---------------------------------------------------------
    col_busq, col_reset = st.columns([4, 1])
    
    with col_busq:
        quimico_enfoque = st.selectbox(
            "🔎 Buscar y enfocar sustancia en la matriz:",
            ["-- Ver Matriz Completa --"] + quimicos_unicos,
            index=0,
            key="busqueda_matriz"
        )
        
    with col_reset:
        st.write("") # Espaciador para alinear con el selectbox
        st.write("")
        if st.button("🔍 Restablecer Vista Global", use_container_width=True):
            st.session_state["busqueda_matriz"] = "-- Ver Matriz Completa --"
            st.rerun()

    # ---------------------------------------------------------
    # CONSTRUCCIÓN DE LA MATRIZ
    # ---------------------------------------------------------
    matriz_comp = df.pivot_table(index="Quimico_1", columns="Quimico_2", values="Compatibilidad", aggfunc="first")
    matriz_notas = df.pivot_table(index="Quimico_1", columns="Quimico_2", values="Notas", aggfunc="first")

    matriz_comp = matriz_comp.reindex(index=quimicos_unicos, columns=quimicos_unicos).fillna("Sin Registro")
    matriz_notas = matriz_notas.reindex(index=quimicos_unicos, columns=quimicos_unicos).fillna("")

    def mapear_color(val):
        v = str(val).lower()
        if "incompatible" in v:
            return 0
        elif "precauci" in v:
            return 1
        elif "compatible" in v:
            return 2
        return 3

    try:
        z_vals = matriz_comp.map(mapear_color).values.astype(float)
    except AttributeError:
        z_vals = matriz_comp.applymap(mapear_color).values.astype(float)

    # Máscara triangular inferior (i > j)
    n = len(quimicos_unicos)
    mask_superior_o_diagonal = np.triu(np.ones((n, n), dtype=bool))
    z_vals[mask_superior_o_diagonal] = np.nan

    hover_text = []
    for i, row_name in enumerate(matriz_comp.index):
        row_hover = []
        for j, col_name in enumerate(matriz_comp.columns):
            if i <= j:
                row_hover.append("")
                continue

            comp = matriz_comp.iloc[i, j]
            nota = matriz_notas.iloc[i, j]
            nota_str = f"<br><b>Observación:</b> {nota}" if (nota and str(nota).strip() != "") else ""
            row_hover.append(
                f"<b>Químico A:</b> {row_name}<br>"
                f"<b>Químico B:</b> {col_name}<br>"
                f"<b>Resultado:</b> {comp}"
                f"{nota_str}"
            )
        hover_text.append(row_hover)

    colorscale = [
        [0.00, '#ff4d4f'], [0.25, '#ff4d4f'],  # Incompatible
        [0.25, '#eab308'], [0.50, '#eab308'],  # Precaución
        [0.50, '#27c93f'], [0.75, '#27c93f'],  # Compatible
        [0.75, '#1f242d'], [1.00, '#1f242d']   # Sin Registro
    ]

    fig = go.Figure(data=go.Heatmap(
        z=z_vals,
        x=matriz_comp.columns,
        y=matriz_comp.index,
        text=hover_text,
        hoverinfo="text",
        colorscale=colorscale,
        zmin=-0.5,
        zmax=3.5,
        showscale=False,
        xgap=1,
        ygap=1
    ))

    # ---------------------------------------------------------
    # CÁLCULO DE RANGOS DE ZOOM / ENFOQUE DINÁMICO
    # ---------------------------------------------------------
    xaxis_config = dict(
        tickangle=-90,
        side="top",
        tickfont=dict(size=8),
        dtick=1,
        showgrid=False,
        zeroline=False,
        constraintoward='left'  # Alinea el zoom hacia la izquierda
    )
    yaxis_config = dict(
        autorange="reversed",
        tickfont=dict(size=8),
        dtick=1,
        scaleanchor="x",
        scaleratio=1,
        showgrid=False,
        zeroline=False,
        constraintoward='top'   # Alinea el zoom hacia arriba
    )

    if quimico_enfoque != "-- Ver Matriz Completa --":
        idx_q = quimicos_unicos.index(quimico_enfoque)
        
        margen = 3  
        x_min = max(0, idx_q - margen)
        x_max = min(n - 1, idx_q + margen)
        y_min = max(0, idx_q - margen)
        y_max = min(n - 1, idx_q + margen)

        xaxis_config["range"] = [x_min - 0.5, x_max + 0.5]
        yaxis_config["range"] = [y_max + 0.5, y_min - 0.5]

        # Resalte horizontal
        fig.add_shape(
            type="rect",
            x0=-0.5, x1=idx_q - 0.5 if idx_q > 0 else 0.5,
            y0=idx_q - 0.5, y1=idx_q + 0.5,
            line=dict(color="#58a6ff", width=2),
            fillcolor="rgba(88, 166, 255, 0.15)"
        )
        
        # Resalte vertical
        if idx_q < n - 1:
            fig.add_shape(
                type="rect",
                x0=idx_q - 0.5, x1=idx_q + 0.5,
                y0=idx_q + 0.5, y1=n - 0.5,
                line=dict(color="#58a6ff", width=2),
                fillcolor="rgba(88, 166, 255, 0.15)"
            )

    fig.update_layout(
        height=950,
        margin=dict(l=130, r=40, t=180, b=80),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        dragmode="pan",
        font=dict(color="#e6edf3", size=9),
        xaxis=xaxis_config,
        yaxis=yaxis_config
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            'scrollZoom': True,
            'displayModeBar': True,
            # Ocultamos select, lasso y el botón de pantalla completa que causa el fallo en Streamlit
            'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'toggleFullscreen']
        }
    )

 
