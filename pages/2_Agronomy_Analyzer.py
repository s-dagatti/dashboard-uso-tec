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

# ---------------------------------------------------
# GANTT DE PROYECTOS
# ---------------------------------------------------
df_gantt = df_f.copy()

df_gantt["Agronomy Proyecto"] = (

    df_gantt["CLIENTE"]
    .fillna("Sin Cliente")
    .astype(str)

    + " - "

    + df_gantt["NOMBRE"]
    .fillna("Sin Nombre")
    .astype(str)

)

st.markdown("---")

st.subheader(
    "📅 Planificación de Proyectos Agronomy"
)

# ---------------------------------------------------
# FECHAS DE CADA Q
# ---------------------------------------------------

q_fechas = {

    "Q1": (
        pd.Timestamp("2025-11-01"),
        pd.Timestamp("2026-01-31")
    ),

    "Q2": (
        pd.Timestamp("2026-02-01"),
        pd.Timestamp("2026-04-30")
    ),

    "Q3": (
        pd.Timestamp("2026-05-01"),
        pd.Timestamp("2026-07-31")
    ),

    "Q4": (
        pd.Timestamp("2026-08-01"),
        pd.Timestamp("2026-10-31")
    )

}

hoy = pd.Timestamp.today().normalize()

df_gantt = df_f.copy()

# ---------------------------------------------------
# INICIO Y FIN SEGÚN EL Q
# ---------------------------------------------------

df_gantt["Inicio"] = (

    df_gantt["Q PLANTEADO"]

    .map(
        lambda q:
        q_fechas[q][0]
        if q in q_fechas
        else pd.NaT
    )

)

df_gantt["Fin"] = (

    df_gantt["Q PLANTEADO"]

    .map(
        lambda q:
        q_fechas[q][1]
        if q in q_fechas
        else pd.NaT
    )

)

# ---------------------------------------------------
# ESTADO DEL PROYECTO
# ---------------------------------------------------

def clasificar_proyecto(row):

    plan = str(
        row["Planificación - Estado"]
    ).strip()

    datos = str(
        row["Recopilación de Datos - Estado"]
    ).strip()

    informe = str(
        row["Generación de informe - Estado"]
    ).strip()

    # COMPLETADO

    if informe == "Completado":

        return "🟢 Terminado"

    # NUNCA INICIADO

    sin_avance = (

        plan == "No Iniciado"

        and

        datos == "No Iniciado"

        and

        informe == "No Iniciado"

    )

    if sin_avance:

        if hoy < row["Inicio"]:

            return "⚪ Pendiente"

        else:

            return "🔴 Debería estar activo"

    # EN PROCESO

    return "🟡 En proceso"

# ---------------------------------------------------
# CATEGORÍA
# ---------------------------------------------------

df_gantt["Estado Proyecto"] = (

    df_gantt

    .apply(
        clasificar_proyecto,
        axis=1
    )

)

# ---------------------------------------------------
# ORDEN
# ---------------------------------------------------

df_gantt = (

    df_gantt

    .sort_values(
        [
            "FY",
            "Q PLANTEADO",
            "Agronomy Proyecto"
        ]
    )
)

# ---------------------------------------------------
# GANTT
# ---------------------------------------------------

fig_gantt = px.timeline(

    df_gantt,

    x_start="Inicio",

    x_end="Fin",

    y="Agronomy Proyecto",

    color="Estado Proyecto",

    hover_data=[

        "Tipo de Proyecto",

        "FY",

        "Q PLANTEADO"

    ],

    color_discrete_map={

        "⚪ Pendiente":
            "#9e9e9e",

        "🔴 Debería estar activo":
            "#d62728",

        "🟡 En proceso":
            "#f2b134",

        "🟢 Terminado":
            "#2ca02c"

    }

)

fig_gantt.update_yaxes(
    autorange="reversed"
)

fig_gantt.update_layout(

    height=800,

    xaxis_title="Año Fiscal",

    yaxis_title="Agronomy",

    hovermode="closest",

    legend_title_text="Estado"

)

st.plotly_chart(
    fig_gantt,
    use_container_width=True
)

