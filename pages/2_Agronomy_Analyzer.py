import io
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
import plotly.figure_factory as ff

from datetime import datetime


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

    # ---------------------------------------------------
    # GANTT
    # ---------------------------------------------------

    st.markdown("---")

    st.subheader(
        "📅 Cronograma de Proyectos"
    )

    gantt_data = []

    hoy = datetime.now()

    for _, row in df_f.iterrows():

        q_val = str(
            row.get(
                "Q PLANTEADO",
                ""
            )
        ).strip().upper()

        fy_val = str(
            row.get(
                "FY",
                "26"
            )
        ).strip()

        try:

            fy_int = int(fy_val)

            start_year = (
                (2000 + fy_int) - 1
                if fy_int < 100
                else fy_int - 1
            )

        except ValueError:

            start_year = 2025

        q_dates = {

            "Q1": (
                datetime(
                    start_year,
                    11,
                    1
                ),
                datetime(
                    start_year + 1,
                    1,
                    31
                )
            ),

            "Q2": (
                datetime(
                    start_year + 1,
                    2,
                    1
                ),
                datetime(
                    start_year + 1,
                    4,
                    30
                )
            ),

            "Q3": (
                datetime(
                    start_year + 1,
                    5,
                    1
                ),
                datetime(
                    start_year + 1,
                    7,
                    31
                )
            ),

            "Q4": (
                datetime(
                    start_year + 1,
                    8,
                    1
                ),
                datetime(
                    start_year + 1,
                    10,
                    31
                )
            )

        }

        plan_est = str(
            row.get(
                "Planificación - Estado",
                ""
            )
        ).upper()

        reco_est = str(
            row.get(
                "Recopilación de Datos - Estado",
                ""
            )
        ).upper()

        info_est = str(
            row.get(
                "Generación de informe - Estado",
                ""
            )
        ).upper()

        if q_val in q_dates:

            start, end = q_dates[q_val]

            if info_est == "COMPLETADO":

                estado = "✅ Terminado"

            elif (
                "EN PROCESO" in [
                    plan_est,
                    reco_est,
                    info_est
                ]
            ) or (
                "COMPLETADO" in [
                    plan_est,
                    reco_est
                ]
            ):

                estado = "🟡 En Proceso"

            elif start <= hoy <= end:

                estado = "🔴 Debería estar Activo"

            else:

                estado = "⚪ Pendiente"

            gantt_data.append(

                dict(

                    Task=f"{row['CLIENTE']} - {row['NOMBRE']}",

                    Start=start,

                    Finish=end,

                    Resource=estado

                )

            )

    if gantt_data:

        df_gantt = pd.DataFrame(
            gantt_data
        )

        colores = {

            "✅ Terminado":
                "#2ca02c",

            "🟡 En Proceso":
                "#f2b134",

            "🔴 Debería estar Activo":
                "#d62728",

            "⚪ Pendiente":
                "#9e9e9e"

        }

        fig_gantt = ff.create_gantt(

            df_gantt,

            colors=colores,

            index_col="Resource",

            show_colorbar=True,

            group_tasks=True,

            showgrid_x=True

        )

        fig_gantt.update_layout(

            height=max(
                450,
                len(df_gantt) * 35
            ),

            margin=dict(
                t=30,
                b=30,
                l=250
            )

        )

        fig_gantt.add_vline(

            x=hoy.timestamp() * 1000,

            line_dash="dash",

            line_color="orange",

            annotation_text="HOY"

        )

        st.plotly_chart(

            fig_gantt,

            use_container_width=True

        )

    else:

        st.info(
            "No se encontraron proyectos para los filtros seleccionados."
        )


# ===================================================
# TAB EDICIÓN
# ===================================================

with tab_edicion:

    st.info(
        "Aquí irá el módulo de edición que ya tienen desarrollado."
    )

