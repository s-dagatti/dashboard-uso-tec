import io
import pandas as pd
import requests
import streamlit as st
import plotly.express as px

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
import base64

def guardar_base_github(df):

    repo = "s-dagatti/uso-tec-v2"

    path = "datos_proyectos_agronomy_analyzer.csv"

    token = st.secrets["github"]["token"]

    url = (
        f"https://api.github.com/repos/"
        f"{repo}/contents/{path}"
    )

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Obtener SHA actual
    res_get = requests.get(
        url,
        headers=headers
    )

    sha = res_get.json()["sha"]

    csv_bytes = (
        df.to_csv(index=False)
        .encode("utf-8")
    )

    contenido = (
        base64.b64encode(csv_bytes)
        .decode("utf-8")
    )

    payload = {

        "message":
            "Actualización proyecto Agronomy",

        "content":
            contenido,

        "sha":
            sha

    }

    res_put = requests.put(

        url,

        headers=headers,

        json=payload

    )

    return res_put.status_code in [200, 201]

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

        fig_gantt = px.timeline(

            df_gantt,
        
            x_start="Start",
        
            x_end="Finish",
        
            y="Task",
        
            color="Resource",
        
            color_discrete_map={
        
                "✅ Terminado":
                    "#2ca02c",
        
                "🟡 En Proceso":
                    "#f2b134",
        
                "🔴 Debería estar Activo":
                    "#d62728",
        
                "⚪ Pendiente":
                    "#9e9e9e"
        
            }
        
        )
        
        fig_gantt.update_yaxes(
            autorange="reversed"
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
            ),
        
            legend_title_text="Estado"
        
        )
        
        fig_gantt.add_vline(
        
            x=hoy,
        
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

    # ---------------------------------------------------
    # TABLA MAESTRA DE PROYECTOS
    # ---------------------------------------------------
    
    st.markdown("---")
    
    st.subheader(
        "📌 Listado Maestro de Proyectos"
    )
    
    # -----------------------------------------
    # ESTILO DE ESTADOS
    # -----------------------------------------
    
    def color_estado(valor):
    
        v = str(valor).strip().upper()
    
        if v == "COMPLETADO":
    
            return (
                "background-color: #2ca02c;"
                "color: white;"
                "font-weight: bold;"
            )
    
        elif v == "EN PROCESO":
    
            return (
                "background-color: #f2b134;"
                "color: black;"
                "font-weight: bold;"
            )
    
        elif v == "NO INICIADO":
    
            return (
                "background-color: #d62728;"
                "color: white;"
                "font-weight: bold;"
            )
    
        return ""
    
    # -----------------------------------------
    # COLUMNAS A MOSTRAR
    # -----------------------------------------
    
    df_tabla = df_f.copy()
    
    columnas_tabla = [
    
        "FY",
    
        "CLIENTE",
    
        "NOMBRE",
    
        "Tipo de Proyecto",
    
        "SUCURSAL",
    
        "Q PLANTEADO",
    
        "ID PRUEBA",
    
        "LINK ACCESO",
    
        "Planificación - Estado",
    
        "Recopilación de Datos - Estado",
    
        "Generación de informe - Estado",
    
        "Horas Totales"
    
    ]
    
    columnas_tabla = [
    
        c
    
        for c in columnas_tabla
    
        if c in df_tabla.columns
    
    ]
    
    df_tabla = df_tabla[
        columnas_tabla
    ].copy()
    
    # -----------------------------------------
    # RENOMBRAR
    # -----------------------------------------
    
    df_tabla = df_tabla.rename(
    
        columns={
    
            "FY":
                "FY",
    
            "CLIENTE":
                "Cliente",
    
            "NOMBRE":
                "Nombre",
    
            "Tipo de Proyecto":
                "Tipo",
    
            "SUCURSAL":
                "Sucursal",
    
            "Q PLANTEADO":
                "Trimestre",
    
            "ID PRUEBA":
                "ID Prueba",
    
            "LINK ACCESO":
                "Enlace",
    
            "Planificación - Estado":
                "Planificación",
    
            "Recopilación de Datos - Estado":
                "Datos",
    
            "Generación de informe - Estado":
                "Informe",
    
            "Horas Totales":
                "Hs Totales"
    
        }
    
    )
    
    # -----------------------------------------
    # FORMATO TABLA
    # -----------------------------------------
    
    tabla_style = (
    
        df_tabla
    
        .style
    
        .map(
            color_estado,
            subset=["Planificación"]
        )
    
        .map(
            color_estado,
            subset=["Datos"]
        )
    
        .map(
            color_estado,
            subset=["Informe"]
        )
    
        .format(
            {
                "Hs Totales": "{:.1f}"
            }
        )
    
    )
    
    # -----------------------------------------
    # VISUALIZACIÓN
    # -----------------------------------------
    
    st.dataframe(
    
        tabla_style,
    
        use_container_width=True,
    
        hide_index=True,
    
        column_config={
    
            "Enlace": st.column_config.LinkColumn(
    
                "Enlace",
    
                display_text="🔗 Abrir"
    
            )
    
        }
    
    )

    # ---------------------------------------------------
    # ANÁLISIS DE ESFUERZO
    # ---------------------------------------------------
    
    st.markdown("---")
    
    st.subheader(
        "📊 Análisis de Esfuerzo"
    )
    
    g1, g2 = st.columns(2)
    
    # ---------------------------------------------------
    # HORAS POR SUCURSAL
    # ---------------------------------------------------
    
    with g1:
    
        hs_sucursal = (
    
            df_f
    
            .groupby(
                "SUCURSAL",
                dropna=False
            )["Horas Totales"]
    
            .sum()
    
            .reset_index()
    
            .sort_values(
                "Horas Totales",
                ascending=False
            )
    
        )
    
        fig_sucursal = px.bar(
    
            hs_sucursal,
    
            x="SUCURSAL",
    
            y="Horas Totales",
    
            text_auto=".1f",
    
            title="⏱ Horas Totales por Sucursal",
    
            color_discrete_sequence=[
                "#367c2b"
            ]
    
        )
    
        fig_sucursal.update_layout(
    
            xaxis_title="Sucursal",
    
            yaxis_title="Horas Totales",
    
            showlegend=False
    
        )
    
        st.plotly_chart(
            fig_sucursal,
            use_container_width=True
        )
    
    # ---------------------------------------------------
    # HORAS POR ETAPA
    # ---------------------------------------------------
    
    with g2:
    
        horas_etapa = pd.DataFrame(
    
            {
    
                "Etapa": [
    
                    "Planificación",
    
                    "Recopilación de Datos",
    
                    "Generación de Informe"
    
                ],
    
                "Horas": [
    
                    df_f[
                        "Planificación - Horas"
                    ].sum(),
    
                    df_f[
                        "Recopilación de Datos - Horas"
                    ].sum(),
    
                    df_f[
                        "Generación de informe - Horas"
                    ].sum()
    
                ]
    
            }
    
        )
    
        fig_etapas = px.pie(
    
            horas_etapa,
    
            values="Horas",
    
            names="Etapa",
    
            hole=0.45,
    
            title="🕒 Distribución de Horas por Etapa",
    
            color_discrete_sequence=px.colors.qualitative.Pastel
    
        )
    
        fig_etapas.update_traces(
    
            textinfo="percent+label"
    
        )
    
        st.plotly_chart(
    
            fig_etapas,
    
            use_container_width=True
    
        )



# ===================================================
# TAB EDICIÓN
# ===================================================

with tab_edicion:

    st.subheader(
        "✏️ Actualización de Proyectos"
    )

    if df.empty:

        st.warning(
            "No existen proyectos disponibles."
        )

    else:

        df_edit = df.copy()

        # -----------------------------------------
        # SELECTOR
        # -----------------------------------------

        df_edit["SELECTOR"] = (

            df_edit["CLIENTE"]
            .astype(str)

            + " | "

            + df_edit["NOMBRE"]
            .astype(str)

        )

        seleccion = st.selectbox(

            "Seleccione el proyecto:",

            [""] + df_edit["SELECTOR"].tolist()

        )

        if seleccion:

            idx = df_edit[
                df_edit["SELECTOR"] == seleccion
            ].index[0]

            row = df_edit.loc[idx]

            st.info(
                f"📍 Cliente: {row['CLIENTE']} | "
                f"Proyecto: {row['NOMBRE']}"
            )

            with st.form("editar_proyecto"):

                # ---------------------------------------------------
                # PLANIFICACIÓN GENERAL
                # ---------------------------------------------------

                c1, c2, c3, c4 = st.columns(4)

                fy_options = [
                    "25",
                    "26",
                    "27",
                    "28"
                ]

                fy_actual = str(
                    row.get("FY", "26")
                )

                fy_nuevo = c1.selectbox(

                    "FY",

                    fy_options,

                    index=(
                        fy_options.index(fy_actual)
                        if fy_actual in fy_options
                        else 1
                    )

                )

                q_options = [
                    "Q1",
                    "Q2",
                    "Q3",
                    "Q4"
                ]

                q_actual = str(
                    row.get(
                        "Q PLANTEADO",
                        "Q1"
                    )
                ).upper()

                q_nuevo = c2.selectbox(

                    "Trimestre",

                    q_options,

                    index=(
                        q_options.index(q_actual)
                        if q_actual in q_options
                        else 0
                    )

                )

                id_nuevo = c3.text_input(

                    "ID Prueba",

                    value=str(
                        row.get(
                            "ID PRUEBA",
                            ""
                        )
                    )

                )

                link_nuevo = c4.text_input(

                    "Link",

                    value=str(
                        row.get(
                            "LINK ACCESO",
                            ""
                        )
                    )

                )

                st.divider()

                st.subheader(
                    "Estados y Horas"
                )

                estado_options = [

                    "No Iniciado",

                    "En Proceso",

                    "Completado"

                ]

                cambios = {}

                etapas = [

                    (
                        "Planificación - Estado",
                        "Planificación - Horas"
                    ),

                    (
                        "Recopilación de Datos - Estado",
                        "Recopilación de Datos - Horas"
                    ),

                    (
                        "Generación de informe - Estado",
                        "Generación de informe - Horas"
                    )

                ]

                for estado_col, hora_col in etapas:

                    a, b = st.columns([2, 1])

                    estado_actual = str(
                        row.get(
                            estado_col,
                            "No Iniciado"
                        )
                    )

                    horas_actual = float(
                        row.get(
                            hora_col,
                            0
                        )
                    )

                    cambios[estado_col] = a.selectbox(

                        estado_col.replace(
                            " - Estado",
                            ""
                        ),

                        estado_options,

                        index=(
                            estado_options.index(
                                estado_actual
                            )
                            if estado_actual in estado_options
                            else 0
                        )

                    )

                    cambios[hora_col] = b.number_input(

                        hora_col.replace(
                            " - Horas",
                            ""
                        ),

                        min_value=0.0,

                        value=horas_actual,

                        step=0.5

                    )

                # ---------------------------------------------------
                # BOTÓN
                # ---------------------------------------------------

                guardar = st.form_submit_button(
                    "💾 Guardar Cambios"
                )

            # Fuerza estas columnas a texto
            
            for col in [
            
                "ID PRUEBA",
            
                "LINK ACCESO"
            
            ]:
            
                if col in df.columns:
            
                    df[col] = (
                        df[col]
                        .fillna("")
                        .astype(str)
                    )
            
                        
            if guardar:
            
                try:
            
                    # FY
                    df.loc[idx, "FY"] = int(fy_nuevo)
            
                    # Q
                    df.loc[idx, "Q PLANTEADO"] = q_nuevo
            
                    # ID

                    df.loc[idx, "ID PRUEBA"] = (
                    
                        str(id_nuevo)
                    
                        if id_nuevo is not None
                    
                        else ""
                    
                    )
                    
                    # LINK
                    
                    df.loc[idx, "LINK ACCESO"] = (
                    
                        str(link_nuevo)
                    
                        if link_nuevo is not None
                    
                        else ""
                    
                    )

            
                    # Estados y Horas
            
                    for campo, valor in cambios.items():

                        if "Horas" in campo:
                    
                            try:
                    
                                df.loc[idx, campo] = float(valor)
                    
                            except Exception:
                    
                                df.loc[idx, campo] = 0.0
                    
                        else:
                    
                            df.loc[idx, campo] = str(valor)

            
                    exito = guardar_base_github(df)
            
                    if exito:
            
                        st.success(
                            "✅ Proyecto actualizado correctamente."
                        )
            
                        st.cache_data.clear()
            
                        st.rerun()
            
                    else:
            
                        st.error(
                            "❌ No se pudo guardar en GitHub."
                        )
            
                except Exception as e:
            
                    st.error(
                        f"Error guardando: {e}"
                    )


