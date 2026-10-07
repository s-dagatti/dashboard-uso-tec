import io
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------

st.set_page_config(
    page_title="Agronomy Analyzer",
    page_icon="🌱",
    layout="wide"
)

# ---------------------------------------------------
# CARGA DESDE GITHUB
# ---------------------------------------------------

@st.cache_data(ttl=60)

def cargar_base():

    repo = "s-dagatti/uso-tec-v2"

    path = "datos_proyectos_agronomy_analyzer.csv"

    token = st.secrets["github"]["token"]

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    headers = {

        "Authorization": f"token {token}",

        "Accept": "application/vnd.github.v3.raw"

    }

    res = requests.get(
        url,
        headers=headers
    )

    res.raise_for_status()

    return pd.read_csv(
        io.StringIO(res.text)
    )

# ---------------------------------------------------
# BASE
# ---------------------------------------------------

df = cargar_base()

# ---------------------------------------------------
# FECHAS
# ---------------------------------------------------

if "FECHA Y HORA" in df.columns:

    df["FECHA Y HORA"] = pd.to_datetime(
        df["FECHA Y HORA"],
        dayfirst=True,
        errors="coerce"
    )

# ---------------------------------------------------
# HORAS
# ---------------------------------------------------

columnas_horas = [

    "Planificación - Horas",

    "Recopilación de Datos - Horas",

    "Generación de informe - Horas"

]

for col in columnas_horas:

    if col in df.columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

df["Horas Totales"] = (
    df[columnas_horas]
    .sum(axis=1)
)

# ---------------------------------------------------
# TABS
# ---------------------------------------------------

tab_dashboard, tab_edicion = st.tabs(
    [
        "📊 Visualización",
        "✏️ Edición"
    ]
)

# ===================================================
# TAB DASHBOARD
# ===================================================

with tab_dashboard:

    st.title(
        "Agronomy Analyzer"
    )

    st.caption(
        "Seguimiento de proyectos agronómicos"
    )

    # ---------------------------------------------------
    # FILTROS
    # ---------------------------------------------------

    f1, f2, f3, f4 = st.columns(4)

    with f1:

        lista_fy = sorted(
            df["FY"]
            .dropna()
            .unique()
        )

        sel_fy = st.selectbox(
            "FY",
            ["Todos"] + lista_fy
        )
        

    with f2:

        lista_sucursal = sorted(
            df["SUCURSAL"]
            .dropna()
            .unique()
        )

        sel_sucursal = st.selectbox(
            "Sucursal",
            ["Todas"] + lista_sucursal
        )


    with f3:

        lista_q = sorted(
            df["Q PLANTEADO"]
            .dropna()
            .unique()
        )

        sel_q = st.selectbox(
            "Q",
            ["Todos"] + lista_q
        )


    with f4:

        lista_tipo = sorted(
            df["Tipo de Proyecto"]
            .dropna()
            .unique()
        )

        sel_tipo = st.selectbox(
            "Tipo de Proyecto",
            ["Todos"] + lista_tipo
        )

    # ---------------------------------------------------
    # FILTROS APLICADOS
    # ---------------------------------------------------

    df_f = df.copy()

    if sel_fy != "Todos":
    
        df_f = df_f[
            df_f["FY"] == sel_fy
        ]
    
    if sel_sucursal != "Todas":
    
        df_f = df_f[
            df_f["SUCURSAL"] == sel_sucursal
        ]
    
    if sel_q != "Todos":
    
        df_f = df_f[
            df_f["Q PLANTEADO"] == sel_q
        ]
    
    if sel_tipo != "Todos":
    
        df_f = df_f[
            df_f["Tipo de Proyecto"] == sel_tipo
        ]

    # ---------------------------------------------------
    # KPIs
    # ---------------------------------------------------

    proyectos_activos = len(df_f)

    horas_totales = (
        df_f["Horas Totales"]
        .sum()
    )

    informes_terminados = (

        df_f[
            "Generación de informe - Estado"
        ]

        .fillna("")

        .astype(str)

        .str.strip()

        .eq("Completado")

        .sum()

    )

    tasa_cierre = (

        informes_terminados

        /

        proyectos_activos

        * 100

        if proyectos_activos > 0

        else 0

    )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "📁 Proyectos Activos",
        f"{proyectos_activos:,}"
    )

    k2.metric(
        "⏱ Horas Totales",
        f"{horas_totales:,.1f}"
    )

    k3.metric(
        "📄 Informes Terminados",
        f"{informes_terminados:,}"
    )

    k4.metric(
        "✅ Tasa de Cierre",
        f"{tasa_cierre:.1f}%"
    )

# ===================================================
# TAB EDICIÓN
# ===================================================

with tab_edicion:

    st.info(
        "Aquí irá el módulo de edición que ya tienen desarrollado."
    )
