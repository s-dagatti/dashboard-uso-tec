import io
import re
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st

# Configuración inicial de la página
st.set_page_config(
    page_title="Dashboard Uso de Tecnología - Conci", 
    page_icon="mtg.png",
    layout="wide"
)

# --- 1. LECTURA DESDE GITHUB (s-dagatti/uso-tec-v2) ---
@st.cache_data(ttl=60, show_spinner=False)
def cargar_base_datos():
    repo = st.secrets.get("github", {}).get("repo", "s-dagatti/uso-tec-v2")
    path = st.secrets.get("github", {}).get("path", "datos_consolidados_conci.csv")
    token = st.secrets.get("github", {}).get("token", None)
    
    # Lectura vía GitHub API con Token
    if token:
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3.raw"
        }
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return pd.read_csv(io.StringIO(res.text))
            
    # Fallback a URL Raw del repositorio
    raw_url = f"https://raw.githubusercontent.com/{repo}/main/{path}"
    return pd.read_csv(raw_url)

@st.cache_data(ttl=60, show_spinner=False)
def cargar_base_cosecha():

    repo = st.secrets["github"]["repo"]

    token = st.secrets["github"]["token"]

    path = "datos_automatizacion_cosecha.csv"

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.raw"
    }

    res = requests.get(
        url,
        headers=headers
    )

    if res.status_code == 200:

        return pd.read_csv(
            io.StringIO(res.text)
        )

    return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def cargar_base_picadoras():

    repo = st.secrets["github"]["repo"]

    token = st.secrets["github"]["token"]

    path = "datos_picadoras_harvestlab.csv"

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.raw"
    }

    res = requests.get(
        url,
        headers=headers
    )

    if res.status_code == 200:

        return pd.read_csv(
            io.StringIO(res.text)
        )

    return pd.DataFrame()


# --- 2. FILTRO DE VERSIÓN DE SOFTWARE (≥ 23.3) ---
def es_version_valida(version_str):
    if pd.isna(version_str):
        return False
    # Normaliza separadores '23-3' -> '23.3'
    limpio = str(version_str).strip().split()[0].replace('-', '.')
    match = re.match(r'^(\d+)\.(\d+)', limpio)
    if match:
        major, minor = int(match.group(1)), int(match.group(2))
        return (major, minor) >= (23, 3)
    return False

# --- 3. CARGA Y PREPROCESAMIENTO ---
try:
    df_raw = cargar_base_datos()
except Exception as e:
    st.error(f"❌ Error al conectar con la base de datos en GitHub (`s-dagatti/uso-tec-v2`): {e}")
    st.stop()

# Conversión de fechas y tipos numéricos
df_raw['Fecha_inicio_dt'] = pd.to_datetime(df_raw['Fecha de inicio'], dayfirst=True, errors='coerce')
df_raw['Fecha_fin_dt'] = pd.to_datetime(df_raw['Fecha de terminación'], dayfirst=True, errors='coerce')

if 'AutoTrac™ Activo' in df_raw.columns:
    df_raw['AutoTrac™ Activo'] = pd.to_numeric(df_raw['AutoTrac™ Activo'], errors='coerce')

# Identificación dinámica de columnas de Licencia, Vencimiento y Estado Licencia
col_licencia = 'Licencia' if 'Licencia' in df_raw.columns else ('licencia' if 'licencia' in df_raw.columns else None)
col_fin_licencia = 'Fin Licenicia' if 'Fin Licenicia' in df_raw.columns else ('Fin Licencia' if 'Fin Licencia' in df_raw.columns else None)

col_estado_licencia = None
for c in ['Estado Licencia', 'estado licencia', 'Estado de Licencia', 'Estado de la licencia', 'Estado_Licencia']:
    if c in df_raw.columns:
        col_estado_licencia = c
        break

# Identificación de pantallas aptas (versión >= 23.3)
df_raw['es_valida'] = df_raw['Versión Software Monitor'].apply(es_version_valida)

# --- 4. SIDEBAR (FILTROS) ---
st.sidebar.image(
    "isg.png",
    use_container_width=True
)

st.sidebar.header("Filtros de Análisis")

df_sidebar = df_raw.copy()

# Checkbox: Excluir CONCI SA
excluir_conci = st.sidebar.checkbox("Excluir valores de CONCI SA", value=False)
if excluir_conci:
    df_sidebar = df_sidebar[~df_sidebar['Organización'].fillna('').str.upper().str.contains('CONCI SA')].copy()

# Filtro: Sucursal
sucursales = ["Todas"] + sorted([s for s in df_sidebar['Sucursal'].dropna().unique() if str(s).strip() != ''])
sel_sucursal = st.sidebar.selectbox("Sucursal", sucursales)

# Filtro: Razón Social (Organización)
razones = ["Todas"] + sorted([r for r in df_sidebar['Organización'].dropna().unique() if str(r).strip() != ''])
sel_razon = st.sidebar.selectbox("Razón Social", razones)

# Filtro: Tipo de Máquina
tipos = ["Todos"] + sorted([
    t
    for t in df_sidebar['Tipo']
    .dropna()
    .unique()
    if str(t).strip() != ''
])

sel_tipo = st.sidebar.selectbox(
    "Tipo de Máquina",
    tipos
)

# Filtro: Modelo de Máquina
modelos = sorted([
    m
    for m in df_sidebar["Modelo"]
    .dropna()
    .unique()
    if str(m).strip() != ""
])

sel_modelos = st.sidebar.multiselect(
    "Modelo",
    modelos
)

# Filtro: Licencia
if col_licencia:
    licencias = ["Todas"] + sorted([l for l in df_sidebar[col_licencia].dropna().unique() if str(l).strip() != ''])
    sel_licencia = st.sidebar.selectbox("Licencia", licencias)
else:
    sel_licencia = "Todas"

# Filtro: Estado Licencia (directo de la columna de la base de datos)
if col_estado_licencia and col_estado_licencia in df_sidebar.columns:
    estados_licencia = ["Todos"] + sorted([str(e).strip() for e in df_sidebar[col_estado_licencia].dropna().unique() if str(e).strip() != ''])
    sel_estado_licencia = st.sidebar.selectbox("Estado Licencia", estados_licencia)
else:
    sel_estado_licencia = "Todos"

# Filtro: Slider Período de Análisis
fecha_min = df_sidebar['Fecha_inicio_dt'].min()
fecha_max = df_sidebar['Fecha_fin_dt'].max()

if pd.notna(fecha_min) and pd.notna(fecha_max):
    rango_fechas = st.sidebar.slider(
        "Período de Análisis",
        min_value=fecha_min.date(),
        max_value=fecha_max.date(),
        value=(fecha_min.date(), fecha_max.date()),
        format="DD/MM/YYYY"
    )
else:
    rango_fechas = None

# --- 5. APLICACIÓN DE FILTROS A LA BASE GENERAL ---
df_filtrado_raw = df_sidebar.copy()

if sel_sucursal != "Todas":
    df_filtrado_raw = df_filtrado_raw[df_filtrado_raw['Sucursal'] == sel_sucursal]

if sel_razon != "Todas":
    df_filtrado_raw = df_filtrado_raw[df_filtrado_raw['Organización'] == sel_razon]

if sel_tipo != "Todos":
    df_filtrado_raw = df_filtrado_raw[df_filtrado_raw['Tipo'] == sel_tipo]

if sel_modelos:

    df_filtrado_raw = df_filtrado_raw[
        df_filtrado_raw["Modelo"]
        .isin(sel_modelos)
    ]

if col_licencia and sel_licencia != "Todas":
    df_filtrado_raw = df_filtrado_raw[df_filtrado_raw[col_licencia] == sel_licencia]

if col_estado_licencia and sel_estado_licencia != "Todos":
    df_filtrado_raw = df_filtrado_raw[df_filtrado_raw[col_estado_licencia].astype(str).str.strip() == sel_estado_licencia]

if rango_fechas:
    df_filtrado_raw = df_filtrado_raw[
        (df_filtrado_raw['Fecha_inicio_dt'].dt.date >= rango_fechas[0]) & 
        (df_filtrado_raw['Fecha_fin_dt'].dt.date <= rango_fechas[1])
    ]

# Base de registros correspondientes a monitores aptos (≥ 23.3)
df_filtrado_aptas = df_filtrado_raw[df_filtrado_raw['es_valida']].copy()

# Registros aptos filtrando únicamente aquellos con uso de AutoTrac >= 1%
df_filtrado_autotrac = df_filtrado_aptas[
    pd.notna(df_filtrado_aptas['AutoTrac™ Activo']) & (df_filtrado_aptas['AutoTrac™ Activo'] >= 1)
]

# --- 6. PESTAÑA: USO DE AUTOTRAC ---
tab_autotrac, tab_guiado, tab_cosechadoras, tab_pulverizadoras, tab_picadoras = st.tabs([
    "AutoTrac",
    "Guiado Avanzado",
    "Cosechadoras",
    "Pulverizadoras",
    "Picadoras"
])

with tab_autotrac:
    col_logo, col_titulo = st.columns([1,12])
    with col_logo:
        st.image(
            "autotrac.png",
            width=80
        )
    with col_titulo:
        st.title(
            "Uso de Autotrac"
        )
    
    st.caption("Promedio de adopción para monitores aptos (**software ≥ 23.3**) considerando registros con **uso ≥ 1%**.")

    # --- PERÍODO EVALUADO ---
    if not df_filtrado_raw.empty:
        primera_fecha = df_filtrado_raw['Fecha_inicio_dt'].min().strftime('%d/%m/%Y')
        ultima_fecha = df_filtrado_raw['Fecha_fin_dt'].max().strftime('%d/%m/%Y')
        st.info(f" **Período Evaluado:** Desde **{primera_fecha}** hasta **{ultima_fecha}**")
    else:
        st.warning("⚠️ No existen datos para los filtros seleccionados en el período indicado.")

    # --- CÁLCULO DE KPIS ---
    promedio_autotrac = (
        df_filtrado_autotrac["AutoTrac™ Activo"].mean()
            if not df_filtrado_autotrac.empty
            else None
    )

    max_fecha_kpi = (
        df_filtrado_autotrac["Fecha_fin_dt"].max()
        if not df_filtrado_autotrac.empty
        else None
    )
    
    if pd.notna(max_fecha_kpi):
        df_kpi_ult_semana = df_filtrado_autotrac[
            df_filtrado_autotrac["Fecha_fin_dt"] == max_fecha_kpi
        ]
    
        promedio_ult_semana_kpi = (
            df_kpi_ult_semana["AutoTrac™ Activo"].mean()
            if not df_kpi_ult_semana.empty
            else None
        )
    else:
        promedio_ult_semana_kpi = None

    if promedio_autotrac is not None and promedio_ult_semana_kpi is not None:
        delta_autotrac = promedio_ult_semana_kpi - promedio_autotrac
        delta_str = f"{delta_autotrac:+.2f}% respecto al promedio del período"
    else:
        delta_str = None

    maquinas_totales = df_filtrado_raw["Número de serie de la máquina"].nunique()
    maquinas_aptas = df_filtrado_aptas["Número de serie de la máquina"].nunique()

    kpi1, kpi2, kpi3 = st.columns(3)

    with kpi1:
        st.metric(
            label="Promedio AutoTrac™ Activo",
            value=(
                f"{promedio_autotrac:.2f}%"
                if promedio_autotrac is not None
                else "Sin Datos"
            ),
            delta=delta_str,
        )

    with kpi2:
        st.metric(
            label="Máquinas Totales",
            value=f"{maquinas_totales:,}".replace(",", "."),
        )

    with kpi3:
        st.metric(
            label="Máquinas Aptas (≥ 23.3)",
            value=f"{maquinas_aptas:,}".replace(",", "."),
        )

    # --- TABLA RESUMEN POR MÁQUINA ---
    st.subheader("Promedio de Uso de AutoTrac™ por Máquina")

    if not df_filtrado_aptas.empty:
        df_filtrado_aptas.loc[:, "AutoTrac_Filtrado"] = df_filtrado_aptas[
            "AutoTrac™ Activo"
        ].apply(lambda x: x if (pd.notna(x) and x >= 1) else None)

        max_fecha_analisis = df_filtrado_aptas["Fecha_fin_dt"].max()
        
        if pd.notna(max_fecha_analisis):
        
            df_filtrado_aptas.loc[:, "es_ult_semana"] = (
                df_filtrado_aptas["Fecha_fin_dt"] == max_fecha_analisis
            )
        
            df_ult_semana = (
                df_filtrado_aptas[df_filtrado_aptas["es_ult_semana"]]
                .groupby("Máquina")["AutoTrac_Filtrado"]
                .mean()
                .reset_index()
            )
        
            df_ult_semana.rename(
                columns={"AutoTrac_Filtrado": "Promedio_Ultima_Semana"},
                inplace=True
            )
        
        else:
        
            df_ult_semana = pd.DataFrame(
                columns=["Máquina", "Promedio_Ultima_Semana"]
            )

        # Extraer los últimos datos del período para Sucursal, Licencia, Vencimiento y Estado Licencia
        cols_ultimos = ["Sucursal"]
        if col_licencia and col_licencia in df_filtrado_aptas.columns:
            cols_ultimos.append(col_licencia)
        if col_fin_licencia and col_fin_licencia in df_filtrado_aptas.columns:
            cols_ultimos.append(col_fin_licencia)
        if col_estado_licencia and col_estado_licencia in df_filtrado_aptas.columns:
            cols_ultimos.append(col_estado_licencia)

        df_ultimos_datos = (
            df_filtrado_aptas.sort_values("Fecha_fin_dt")
            .groupby("Número de serie de la máquina")[cols_ultimos]
            .last()
            .reset_index()
        )

        group_cols = [
            "Número de serie de la máquina",
            "Máquina",
            "Tipo",
            "Organización"
        ]

        df_promedios = df_filtrado_aptas.groupby(
            group_cols, dropna=False, as_index=False
        ).agg(
            Promedio_AutoTrac=("AutoTrac_Filtrado", "mean"),
            Períodos_Con_Uso=("AutoTrac_Filtrado", "count"),
            Total_Períodos=("Fecha_inicio_dt", "count"),
        )

        df_promedios = pd.merge(
            df_promedios,
            df_ultimos_datos,
            on="Número de serie de la máquina",
            how="left"
        )

        df_promedios = pd.merge(
            df_promedios, df_ult_semana, on="Máquina", how="left"
        )

        # --- SLIDER DE FILTRADO POR % DE USO PROMEDIO ---
        col_slider, _ = st.columns([2, 1])
        with col_slider:
            rango_uso = st.slider(
                "🎚️ Filtrar por % de uso promedio de AutoTrac™",
                min_value=0.0,
                max_value=100.0,
                value=(0.0, 100.0),
                step=1.0,
                format="%.0f%%"
            )

        min_uso, max_uso = rango_uso

        # Condición de filtro: dentro del rango, o sin registros si el mínimo es 0%
        condicion_rango = (df_promedios["Promedio_AutoTrac"] >= min_uso) & (df_promedios["Promedio_AutoTrac"] <= max_uso)
        if min_uso == 0.0:
            condicion_rango = condicion_rango | df_promedios["Promedio_AutoTrac"].isna()

        df_promedios = df_promedios[condicion_rango].copy()

        def evaluar_evolucion(row):
            prom_gen = row["Promedio_AutoTrac"]
            prom_ult = row["Promedio_Ultima_Semana"]

            if pd.isna(prom_gen) or pd.isna(prom_ult):
                return "⚪ Sin datos últ. semana"

            diff = prom_ult - prom_gen
            # Cambio directo en puntos porcentuales reales
            if diff > 0.5:
                return f"🟢(+{diff:.2f}%)"
            elif diff < -0.5:
                return f"🔴({diff:.2f}%)"
            else:
                return "➡️(0.00%)"

        df_promedios["Evolución AutoTrac"] = df_promedios.apply(
            evaluar_evolucion, axis=1
        )

        df_promedios["AutoTrac™ Promedio (%)"] = df_promedios[
            "Promedio_AutoTrac"
        ].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "Sin Registros ( < 1% )")

        if col_licencia and col_licencia in df_promedios.columns:
            df_promedios["Licencia"] = df_promedios[col_licencia].fillna("-")
        else:
            df_promedios["Licencia"] = "-"

        if col_fin_licencia and col_fin_licencia in df_promedios.columns:
            df_promedios["Vencimiento Licencia"] = pd.to_datetime(
                df_promedios[col_fin_licencia], dayfirst=True, errors="coerce"
            ).dt.strftime("%d/%m/%Y").fillna("-")
        else:
            df_promedios["Vencimiento Licencia"] = "-"

        if col_estado_licencia and col_estado_licencia in df_promedios.columns:
            df_promedios["Estado Licencia"] = df_promedios[col_estado_licencia].fillna("-")
        else:
            df_promedios["Estado Licencia"] = "-"

        cols_display = [
            "Máquina",
            "Tipo",
            "Organización",
            "Sucursal",
            "AutoTrac™ Promedio (%)",
            "Evolución AutoTrac",
            "Licencia",
            "Vencimiento Licencia",
            "Estado Licencia",
        ]

        df_promedios_display = df_promedios.sort_values(
            by="Promedio_AutoTrac", ascending=False, na_position="last"
        )[cols_display]

        # --- FORMATO CONDICIONAL DE COLOR DE TEXTO ---
        def colorear_evolucion(val):
            if isinstance(val, str):
                if "🟢" in val:
                    return "color: #2e7d32; font-weight: bold;"
                elif "🔴" in val:
                    return "color: #d32f2f; font-weight: bold;"
            return ""

        def colorear_estado_licencia(val):
            if isinstance(val, str):
                val_lower = val.lower().strip()
                if "vigente" in val_lower:
                    return "color: #2e7d32; font-weight: bold;"
                elif "vencid" in val_lower:
                    return "color: #d32f2f; font-weight: bold;"
                elif "sin licencia" in val_lower or val == "-":
                    return "color: #757575;"
            return ""

        styled_df = df_promedios_display.style

        if hasattr(styled_df, "map"):
            styled_df = (
                styled_df.map(colorear_evolucion, subset=["Evolución AutoTrac"])
                .map(colorear_estado_licencia, subset=["Estado Licencia"])
            )
        else:
            styled_df = (
                styled_df.applymap(colorear_evolucion, subset=["Evolución AutoTrac"])
                .applymap(colorear_estado_licencia, subset=["Estado Licencia"])
            )

        st.dataframe(styled_df, use_container_width=True)

        # --- 7. ANÁLISIS DEL ESTADO DE KITS PUK (LICENCIAS RENOVABLES) ---
        st.markdown("---")
        st.subheader("Análisis del Estado de Kits PUK (Licencias Renovables)")
        st.caption(
            "Los PUKs incluyen licencias **Renovable Esencial** y **Renovable"
            " Avanzada**, las cuales requieren estar activas para operar AutoTrac™."
        )

        def es_licencia_puk(lic_val):
            if pd.isna(lic_val):
                return False
            val_str = str(lic_val).lower().strip()
            return (
                ("renovable" in val_str)
                or ("esencial" in val_str)
                or ("escencial" in val_str)
                or ("avanzada" in val_str)
            )

        def normalizar_tipo_puk(lic_val):
            val_str = str(lic_val).lower()
            if "avanzada" in val_str:
                return "Renovable Avanzada"
            return "Renovable Esencial"

        df_puk = df_promedios[
            df_promedios["Licencia"].apply(es_licencia_puk)
        ].copy()

        if not df_puk.empty:
            col_fecha_origen = (
                col_fin_licencia
                if col_fin_licencia in df_puk.columns
                else "Vencimiento Licencia"
            )

            df_puk["Fecha_venc_dt"] = pd.to_datetime(
                df_puk[col_fecha_origen], dayfirst=True, errors="coerce"
            )

            df_puk["Tipo_PUK"] = df_puk["Licencia"].apply(normalizar_tipo_puk)

            hoy = pd.Timestamp.today().normalize()
            proximo_mes = hoy + pd.Timedelta(days=30)

            if "Estado Licencia" in df_puk.columns:
                estado_clean = (
                    df_puk["Estado Licencia"].astype(str).str.lower().str.strip()
                )
                puk_activas = df_puk[estado_clean == "vigente"]
                puk_vencidas = df_puk[
                    (estado_clean.str.contains("vencid", na=False))
                    | (estado_clean.str.contains("no tiene", na=False))
                ]
            else:
                puk_activas = df_puk[df_puk["Fecha_venc_dt"] >= hoy]
                puk_vencidas = df_puk[
                    (df_puk["Fecha_venc_dt"] < hoy)
                    | (df_puk["Vencimiento Licencia"] == "-")
                ]

            puk_por_vencer = df_puk[
                (df_puk["Fecha_venc_dt"] >= hoy)
                & (df_puk["Fecha_venc_dt"] <= proximo_mes)
            ]

            col_puk1, col_puk2, col_puk3 = st.columns(3)

            with col_puk1:
                st.metric(
                    label="🟢 Licencias Activas (PUK)", value=len(puk_activas)
                )

            with col_puk2:
                st.metric(
                    label="🔴 Licencias Vencidas / Sin Lic. (PUK)",
                    value=len(puk_vencidas),
                )

            with col_puk3:
                st.metric(
                    label="⚠️ Por Vencer Próximo Mes", value=len(puk_por_vencer)
                )

            # --- GRÁFICO DE VENCIMIENTOS EN EL TIEMPO ---
            df_puk_chart = df_puk.dropna(subset=["Fecha_venc_dt"]).copy()

            if not df_puk_chart.empty:
                df_puk_chart["Año_Mes"] = (
                    df_puk_chart["Fecha_venc_dt"].dt.to_period("M").astype(str)
                )

                df_grouped = (
                    df_puk_chart.groupby(["Año_Mes", "Tipo_PUK"])
                    .size()
                    .reset_index(name="Cantidad")
                    .sort_values("Año_Mes")
                )

                fig_puk = px.bar(
                    df_grouped,
                    x="Año_Mes",
                    y="Cantidad",
                    color="Tipo_PUK",
                    barmode="group",
                    title="Cronograma Histórico y Futuro de Vencimientos PUK",
                    labels={
                        "Año_Mes": "Mes de Vencimiento",
                        "Cantidad": "Cantidad de Licencias",
                        "Tipo_PUK": "Tipo de Licencia",
                    },
                    color_discrete_map={
                        "Renovable Esencial": "#2b5c8f",
                        "Renovable Avanzada": "#367c2b",
                    },
                    text="Cantidad",
                )

                fig_puk.update_layout(
                    xaxis_type="category",
                    xaxis_title="Mes de Vencimiento",
                    yaxis_title="Cantidad de Licencias",
                    legend_title_text="Tipo de PUK",
                    hovermode="x unified",
                )

                st.plotly_chart(fig_puk, use_container_width=True)
            else:
                st.info("No hay fechas de vencimiento válidas registradas para graficar.")

            # --- TABLA DETALLE DE PUKS ---
            st.markdown("##### Detalle de Equipos con Licencia PUK")

            df_puk["Vencimiento Licencia"] = df_puk["Fecha_venc_dt"].apply(
                lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "-"
            )

            df_puk_display = df_puk.sort_values(
                by="Fecha_venc_dt", ascending=True, na_position="last"
            )[cols_display]

            styled_puk = df_puk_display.style

            if hasattr(styled_puk, "map"):
                styled_puk = styled_puk.map(
                    colorear_evolucion, subset=["Evolución AutoTrac"]
                ).map(colorear_estado_licencia, subset=["Estado Licencia"])
            else:
                styled_puk = styled_puk.applymap(
                    colorear_evolucion, subset=["Evolución AutoTrac"]
                ).applymap(colorear_estado_licencia, subset=["Estado Licencia"])

            st.dataframe(styled_puk, use_container_width=True)

        else:
            st.info(
                "ℹ️ No se encontraron máquinas con licencias PUK (Renovable"
                " Esencial / Avanzada) para los filtros seleccionados."
            )

        # --- 8. GRÁFICO HISTÓRICO SEMANAL DE ADOPCIÓN DE AUTOTRAC ---
        st.markdown("---")
        st.subheader("Evolución Semanal del Uso de AutoTrac™")
        st.caption(
            "Evolución semanal de la cantidad de máquinas aptas que utilizaron"
            " AutoTrac™ (≥ 1%) y el porcentaje promedio de uso registrado."
        )

        df_hist_semanal = df_filtrado_aptas.dropna(subset=["Fecha_fin_dt"]).copy()

        if not df_hist_semanal.empty:
            df_hist_semanal["Semana_Inicio"] = df_hist_semanal[
                "Fecha_fin_dt"
            ].dt.to_period("W").dt.start_time

            df_autotrac_semanal = df_hist_semanal[
                pd.notna(df_hist_semanal["AutoTrac™ Activo"])
                & (df_hist_semanal["AutoTrac™ Activo"] >= 1)
            ]

            df_semanal = (
                df_autotrac_semanal.groupby("Semana_Inicio")
                .agg(
                    Cant_Maquinas=("Máquina", "nunique"),
                    Promedio_AutoTrac=("AutoTrac™ Activo", "mean"),
                )
                .reset_index()
                .sort_values("Semana_Inicio")
            )

            df_semanal["Semana_Str"] = df_semanal["Semana_Inicio"].dt.strftime(
                "%d/%m/%Y"
            )

            if not df_semanal.empty:
                fig_semanal = make_subplots(specs=[[{"secondary_y": True}]])

                fig_semanal.add_trace(
                    go.Bar(
                        x=df_semanal["Semana_Str"],
                        y=df_semanal["Cant_Maquinas"],
                        name="Máquinas con AutoTrac™",
                        marker_color="#2b5c8f",
                        text=df_semanal["Cant_Maquinas"],
                        textposition="auto",
                    ),
                    secondary_y=False,
                )

                fig_semanal.add_trace(
                    go.Scatter(
                        x=df_semanal["Semana_Str"],
                        y=df_semanal["Promedio_AutoTrac"],
                        name="% Promedio AutoTrac™",
                        mode="lines+markers+text",
                        line=dict(color="#367c2b", width=3),
                        marker=dict(size=8),
                        text=df_semanal["Promedio_AutoTrac"].apply(
                            lambda x: f"{x:.1f}%"
                        ),
                        textposition="top center",
                    ),
                    secondary_y=True,
                )

                fig_semanal.update_layout(
                    title="Tendencia Semanal: Equipos Activos vs. % de Adopción",
                    xaxis_title="Semana",
                    hovermode="x unified",
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                    ),
                    margin=dict(t=50, b=40, l=10, r=10),
                )

                fig_semanal.update_yaxes(
                    title_text="Cantidad de Máquinas", secondary_y=False
                )
                fig_semanal.update_yaxes(
                    title_text="% Promedio AutoTrac™",
                    secondary_y=True,
                    range=[0, 110],
                )

                st.plotly_chart(fig_semanal, use_container_width=True)
            else:
                st.info(
                    "No se registraron equipos con uso de AutoTrac™ ≥ 1% en el"
                    " período seleccionado."
                )
        else:
            st.info("No existen fechas válidas registradas para agrupar por semana.")

        # ==============================================================================
        # PESTAÑA: GUIADO AVANZADO
        # ==============================================================================
        with tab_guiado:

            # Columnas exactas de Guiado Avanzado
            cols_guiado_avanzado = [
                "AutoPath™ Activo",
                "Automatización de maniobras AutoTrac™ Activo",
                "Guiado pasivo de implemento AutoTrac™ Activo",
                "John Deere Machine Sync Vehículo guía activo",
            ]
            
            nombres_cortos = {
                "AutoPath™ Activo": "AutoPath™",
                "Automatización de maniobras AutoTrac™ Activo": "Turn Automation",
                "Guiado pasivo de implemento AutoTrac™ Activo": "Implement Guidance",
                "John Deere Machine Sync Vehículo guía activo": "Machine Sync",
            }
            
            # Filtrar únicamente las columnas que existen en la base
            cols_presentes = [c for c in cols_guiado_avanzado if c in df_filtrado_raw.columns]
            
            if cols_presentes:
                # 1. Monitores aptos (software >= 23.3) dentro del período seleccionado
                df_ga = df_filtrado_raw[df_filtrado_raw["es_valida"]].copy()
            
                if not df_ga.empty:
                    col_sn = "Número de serie de la máquina" if "Número de serie de la máquina" in df_ga.columns else "Máquina"
                    
                    # 2. Limpieza inicial
                    cols_clean = []
                    for col in cols_presentes:
                        clean_col = f"{col}_clean"
                        cols_clean.append(clean_col)
                        df_ga[col] = pd.to_numeric(df_ga[col], errors="coerce")
            
                    if col_sn in df_ga.columns:
                        # 3. FILTRO DE ACTIVIDAD REAL Y ADOPCIÓN
                        df_adoptadas_mask = pd.DataFrame(index=df_ga.index)
                        
                        for col, clean_col in zip(cols_presentes, cols_clean):
                            val_original = df_ga[col]
                            ha_usado_antes = df_ga.groupby(col_sn)[col].transform(lambda x: (x > 0.0).any())
                            
                            df_adoptadas_mask[clean_col] = val_original.where(ha_usado_antes, np.nan)
                            df_adoptadas_mask[clean_col] = df_adoptadas_mask[clean_col].apply(lambda x: 0.0 if pd.notna(x) and x == 0.0 else x)
                        
                        for clean_col in cols_clean:
                            df_ga[clean_col] = df_adoptadas_mask[clean_col]

                    # Identificar la última semana dentro del período seleccionado
                    max_fecha_ga = df_ga["Fecha_fin_dt"].max()
                    inicio_ult_semana = max_fecha_ga - pd.Timedelta(days=7) if pd.notna(max_fecha_ga) else None
            
                    df_ga_ult_semana = (
                        df_ga[df_ga["Fecha_fin_dt"] >= inicio_ult_semana]
                        if inicio_ult_semana is not None
                        else pd.DataFrame()
                    )
            
                    # ------------------------------------------------------------------
                    # BLOQUE 1: KPIS GENERALES (PROMEDIO ENTRE LAS 4 TECNOLOGÍAS)
                    # ------------------------------------------------------------------
                    col_logo, col_titulo = st.columns([1,12])
                    with col_logo:
                        st.image(
                            "Tractor.png",
                            width=80
                        )
                    with col_titulo:
                        st.title(
                            "Guiado Avanzado"
                        )

            
                    medias_periodo_cols = [df_ga[c].mean() for c in cols_clean]
                    medias_periodo_cols_num = [m if pd.notna(m) else 0.0 for m in medias_periodo_cols]
                    
                    prom_gen_periodo = sum(medias_periodo_cols_num) / len(cols_presentes) if len(cols_guiado_avanzado) > 0 else None
            
                    if not df_ga_ult_semana.empty:
                        medias_semana_cols = [df_ga_ult_semana[c].mean() for c in cols_clean]
                        medias_semana_cols_num = [m if pd.notna(m) else 0.0 for m in medias_semana_cols]
                        prom_gen_semana = sum(medias_semana_cols_num) / len(cols_presentes) if len(cols_guiado_avanzado) > 0 else None
                    else:
                        prom_gen_semana = None
            
                    tiene_datos_global = any(pd.notna(m) for m in medias_periodo_cols)
            
                    val_gen_str = f"{prom_gen_periodo:.2f}%" if (prom_gen_periodo is not None and tiene_datos_global) else "Sin Datos"
                    
                    if prom_gen_periodo is not None and prom_gen_semana is not None and tiene_datos_global:
                        delta_gen = prom_gen_semana - prom_gen_periodo
                        delta_gen_str = f"{delta_gen:+.2f}% vs. últ. semana"
                    else:
                        delta_gen_str = None
            
                    mask_periodo = df_ga[cols_clean].notna().any(axis=1)
                    cant_maq_periodo = df_ga.loc[mask_periodo, col_sn].nunique() if col_sn in df_ga.columns else 0
            
                    if not df_ga_ult_semana.empty and col_sn in df_ga_ult_semana.columns:
                        mask_semana = df_ga_ult_semana[cols_clean].notna().any(axis=1)
                        cant_maq_semana = df_ga_ult_semana.loc[mask_semana, col_sn].nunique()
                        diff_maq = cant_maq_semana - cant_maq_periodo
                        delta_maq_str = (
                            f"{cant_maq_semana:,}".replace(",", ".")
                            + " en la última fotografía"
                        )
                    else:
                        delta_maq_str = None
            
                    kpi_gen1, kpi_gen2 = st.columns(2)
            
                    with kpi_gen1:
                        st.metric(
                            label="Promedio General Guiado Avanzado (Período)",
                            value=val_gen_str,
                            delta=delta_gen_str,
                        )
            
                    with kpi_gen2:
                        st.metric(
                            label="Máquinas Activas (Con adopción > 0% en período)",
                            value=f"{cant_maq_periodo:,}".replace(",", "."),
                            delta=delta_maq_str,
                        )
            
            
                    # ------------------------------------------------------------------
                    # BLOQUE 2: KPIS INDIVIDUALES POR TECNOLOGÍA
                    # ------------------------------------------------------------------
                    st.markdown("---")
                    cols_widgets = st.columns(len(cols_presentes))
            
                    for idx, col in enumerate(cols_presentes):
                        clean_col = f"{col}_clean"
                        with cols_widgets[idx]:
                            nombre_kpi = nombres_cortos.get(col, col)
            
                            prom_periodo = df_ga[clean_col].mean()
                            prom_semana = (
                                df_ga_ult_semana[clean_col].mean()
                                if not df_ga_ult_semana.empty
                                else None
                            )
            
                            val_act_str = f"{prom_periodo:.2f}%" if pd.notna(prom_periodo) else "Sin Datos"
            
                            if pd.notna(prom_periodo) and pd.notna(prom_semana):
                                diff = prom_semana - prom_periodo
                                delta_str = f"{diff:+.2f}% vs. últ. semana"
                            else:
                                delta_str = None
            
                            st.metric(
                                label=nombre_kpi,
                                value=val_act_str,
                                delta=delta_str,
                            )
            
                    # ------------------------------------------------------------------
                    # SELECTOR DE TECNOLOGÍA PARA DETALLE Y SERIE HISTÓRICA
                    # ------------------------------------------------------------------
                    st.markdown("---")
                    st.subheader("Análisis Detallado por Tecnología")
            
                    # Mapeo inverso para el selectbox
                    opciones_tech_dict = {nombres_cortos.get(c, c): c for c in cols_presentes}
                    
                    tech_seleccionada_label = st.selectbox(
                        "Seleccione la tecnología a inspeccionar en detalle y gráfico histórico:",
                        options=list(opciones_tech_dict.keys()),
                        key="select_tech_guiado_avanzado"
                    )
                    
                    col_sel = opciones_tech_dict[tech_seleccionada_label]
                    clean_col_sel = f"{col_sel}_clean"

                    # ------------------------------------------------------------------
                    # BLOQUE 3: TABLA DETALLE POR MÁQUINA (DINÁMICA SEGÚN SELECCIÓN)
                    # ------------------------------------------------------------------
                    st.markdown("####")
                    st.markdown(f" **Detalle de {tech_seleccionada_label} y Licencias por Máquina**")
            
                    col_maq = "Máquina" if "Máquina" in df_ga.columns else ("Número de serie de la máquina" if "Número de serie de la máquina" in df_ga.columns else None)
                    col_tipo = "Tipo" if "Tipo" in df_ga.columns else ("Tipo de máquina" if "Tipo de máquina" in df_ga.columns else None)
                    col_org = "Organización" if "Organización" in df_ga.columns else ("Organizacion" if "Organizacion" in df_ga.columns else None)
                    col_suc = "Sucursal" if "Sucursal" in df_ga.columns else None
            
                    group_keys = [c for c in [col_maq, col_tipo, col_org, col_suc] if c and c in df_ga.columns]
            
                    if group_keys and clean_col_sel in df_ga.columns:
                        tabla_periodo = df_ga.groupby(group_keys)[clean_col_sel].mean().reset_index()
                        tabla_periodo.rename(columns={clean_col_sel: col_sel}, inplace=True)
            
                        tabla_periodo = tabla_periodo[tabla_periodo[col_sel].notna()].copy()
            
                        if not tabla_periodo.empty:
                            if not df_ga_ult_semana.empty:
                                tabla_semana = df_ga_ult_semana.groupby(group_keys)[clean_col_sel].mean().reset_index()
                                tabla_semana.rename(columns={clean_col_sel: "col_semana_val"}, inplace=True)
                                df_tabla_final = pd.merge(tabla_periodo, tabla_semana, on=group_keys, how="left")
                            else:
                                df_tabla_final = tabla_periodo
                                df_tabla_final["col_semana_val"] = np.nan
            
                            def calc_dif_num(row):
                                v_per = row[col_sel]
                                v_sem = row["col_semana_val"]
                                if pd.notna(v_per) and pd.notna(v_sem):
                                    return v_sem - v_per
                                else:
                                    return 0.0
                            
                            df_tabla_final["_diff_num"] = df_tabla_final.apply(calc_dif_num, axis=1)

                            def calc_evolucion_str(row):
                                v_per = row[col_sel]
                                v_sem = row["col_semana_val"]
                                if pd.notna(v_per) and pd.notna(v_sem):
                                    diff = v_sem - v_per
                                    return f"{diff:+.2f}%"
                                else:
                                    return "-"
            
                            df_tabla_final["Evolución"] = df_tabla_final.apply(calc_evolucion_str, axis=1)
            
                            cols_lic_meta = [c for c in [col_licencia, col_fin_licencia, col_estado_licencia] if c and c in df_ga.columns]
                            if cols_lic_meta and col_maq:
                                df_lic_last = df_ga.sort_values("Fecha_fin_dt").groupby(col_maq)[cols_lic_meta].last().reset_index()
                                df_tabla_final = pd.merge(df_tabla_final, df_lic_last, on=col_maq, how="left")
            
                            df_tabla_final[f"{col_sel}_fmt"] = df_tabla_final[col_sel].apply(
                                lambda x: f"{x:.2f}%" if pd.notna(x) else "-"
                            )
            
                            col_order_target = [
                                (col_maq, "Máquina"),
                                (col_tipo, "Tipo"),
                                (col_org, "Organización"),
                                (col_suc, "Sucursal"),
                                (f"{col_sel}_fmt", tech_seleccionada_label),
                                ("Evolución", f"Evolución {tech_seleccionada_label}"),
                                (col_licencia, "Licencia"),
                                (col_fin_licencia, "Vencimiento Licencia"),
                                (col_estado_licencia, "Estado Licencia"),
                            ]
            
                            cols_existentes_renombrar = {}
                            cols_para_mostrar = []
            
                            for orig, dest in col_order_target:
                                if orig and orig in df_tabla_final.columns:
                                    cols_para_mostrar.append(orig)
                                    cols_existentes_renombrar[orig] = dest
            
                            df_final_view = df_tabla_final[cols_para_mostrar].rename(columns=cols_existentes_renombrar)
            
                            def estilizar_tabla(row):
                                styles = [''] * len(row)
                                col_evo_name = f"Evolución {tech_seleccionada_label}"
                                
                                if col_evo_name in df_final_view.columns:
                                    idx_evo = list(df_final_view.columns).index(col_evo_name)
                                    val_diff = df_tabla_final.iloc[row.name]["_diff_num"]
                                    if pd.notna(val_diff):
                                        if val_diff > 0:
                                            styles[idx_evo] = 'color: #2e7d32; font-weight: bold;'
                                        elif val_diff < 0:
                                            styles[idx_evo] = 'color: #c62828; font-weight: bold;'

                                if "Estado Licencia" in df_final_view.columns:
                                    idx_lic = list(df_final_view.columns).index("Estado Licencia")
                                    val_estado = str(row["Estado Licencia"]).strip().lower()
                                    if "vigente" in val_estado or "activa" in val_estado:
                                        styles[idx_lic] = 'color: #2e7d32; font-weight: bold;'
                                    elif "vencida" in val_estado or "expirada" in val_estado:
                                        styles[idx_lic] = 'color: #c62828; font-weight: bold;'

                                return styles

                            df_styled = df_final_view.style.apply(estilizar_tabla, axis=1)
                            st.dataframe(df_styled, use_container_width=True)
                        else:
                            st.info(f"ℹ️ No se encontraron máquinas con adopción registrada (> 0%) de {tech_seleccionada_label} en el período seleccionado.")
                    else:
                        st.info("ℹ️ No se encontraron suficientes datos o columnas para armar la tabla detallada.")

                    # ------------------------------------------------------------------
                    # BLOQUE 4: SERIE HISTÓRICA (DINÁMICA SEGÚN SELECCIÓN)
                    # ------------------------------------------------------------------
                    st.markdown("---")
                    st.subheader(f" Serie Histórica - {tech_seleccionada_label}")

                    col_fecha_agrup = "Fecha_fin_dt" if "Fecha_fin_dt" in df_ga.columns else ("Fecha" if "Fecha" in df_ga.columns else None)
                    
                    if col_fecha_agrup and clean_col_sel in df_ga.columns:
                        df_activos_hist = df_ga[
                            pd.notna(df_ga[clean_col_sel]) &
                            (df_ga[clean_col_sel] > 0)
                        ].copy()
                        
                        df_hist = (
                            df_activos_hist
                            .groupby(col_fecha_agrup)
                            .agg(
                                Uso_Promedio=(clean_col_sel, "mean"),
                                Maquinas_Activas=(col_sn, "nunique")
                            )
                            .reset_index()
                        )

                        df_hist = df_hist.sort_values(col_fecha_agrup)
                        df_hist["Fecha_str"] = df_hist[col_fecha_agrup].dt.strftime("%Y-%m-%d")

                        if not df_hist.empty:
                            import plotly.graph_objects as go
                            from plotly.subplots import make_subplots

                            fig_hist = make_subplots(specs=[[{"secondary_y": True}]])

                            fig_hist.add_trace(
                                go.Bar(
                                    x=df_hist["Fecha_str"],
                                    y=df_hist["Maquinas_Activas"],
                                    name="Máquinas Activas",
                                    marker_color="rgba(70, 130, 180, 0.6)",
                                ),
                                secondary_y=False,
                            )

                            fig_hist.add_trace(
                                go.Scatter(
                                    x=df_hist["Fecha_str"],
                                    y=df_hist["Uso_Promedio"],
                                    name="% Uso Promedio",
                                    mode="lines+markers",
                                    line=dict(color="#2e7d32", width=3),
                                ),
                                secondary_y=True,
                            )

                            fig_hist.update_layout(
                                title=f"Evolución Semanal de Uso y Máquinas Activas ({tech_seleccionada_label})",
                                xaxis_title="Período / Fecha",
                                hovermode="x unified",
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            )

                            fig_hist.update_yaxes(title_text="Cantidad de Máquinas", secondary_y=False)
                            fig_hist.update_yaxes(title_text="% Uso Promedio", secondary_y=True, tickformat=".1f")

                            st.plotly_chart(fig_hist, use_container_width=True)

                        # ==============================================================================
                        # OPORTUNIDADES DE ADOPCIÓN - MACHINE SYNC
                        # ==============================================================================
                        
                        if tech_seleccionada_label == "Machine Sync":
                        
                            st.markdown("---")
                            st.subheader("Oportunidades de Adopción - Machine Sync")
                        
                            st.caption(
                                "Organizaciones que poseen una combinación compatible de "
                                "cosechadora + tractor y presentan menos de 1% de uso promedio "
                                "de Machine Sync durante el período analizado."
                            )
                        
                            # ----------------------------------------------------------
                            # MODELOS COMPATIBLES
                            # ----------------------------------------------------------
                        
                            trac_ms_list = [
                                "7M 200",
                                "7M 215",
                                "7M 230",
                                "7230R"
                            ]
                        
                            cos_models = [
                                "S760",
                                "S770",
                                "S780",
                                "S790",
                                "S7 600",
                                "S7 700",
                                "S7 800",
                                "S7 900"
                            ]
                        
                            col_sync = "John Deere Machine Sync Vehículo guía activo"
                        
                            # ----------------------------------------------------------
                            # BASE COMPLETA DEL PERÍODO SELECCIONADO
                            # ----------------------------------------------------------
                        
                            df_ms_base = df_ga.copy()
                        
                            df_ms_cos = df_ms_base[
                                (df_ms_base["Tipo"] == "Cosechadora")
                                &
                                (df_ms_base["Modelo"].isin(cos_models))
                            ].copy()
                        
                            df_ms_trac = df_ms_base[
                                (df_ms_base["Tipo"] == "Tractor")
                                &
                                (df_ms_base["Modelo"].isin(trac_ms_list))
                            ].copy()
                        
                            if (
                                not df_ms_cos.empty
                                and
                                not df_ms_trac.empty
                                and
                                col_sync in df_ms_cos.columns
                            ):
                        
                                # ------------------------------------------------------
                                # PROMEDIO DE USO POR ORGANIZACIÓN
                                # ------------------------------------------------------
                        
                                df_sync_org = (
                                    df_ms_cos
                                    .groupby("Organización")
                                    .agg(
                                        {
                                            col_sync: "mean",
                                            "Sucursal": "last",
                                            "Modelo": "first"
                                        }
                                    )
                                    .reset_index()
                                    .rename(
                                        columns={
                                            col_sync: "Machine Sync (%)",
                                            "Modelo": "Cosechadora"
                                        }
                                    )
                                )
                        
                                df_trac_org = (
                                    df_ms_trac
                                    .groupby("Organización")
                                    .agg(
                                        {
                                            "Modelo": "first"
                                        }
                                    )
                                    .reset_index()
                                    .rename(
                                        columns={
                                            "Modelo": "Tractor"
                                        }
                                    )
                                )
                        
                                # ------------------------------------------------------
                                # MERGE
                                # ------------------------------------------------------
                        
                                df_m_ms = pd.merge(
                                    df_sync_org,
                                    df_trac_org,
                                    on="Organización",
                                    how="inner"
                                )
                        
                                # ------------------------------------------------------
                                # KPIs
                                # ------------------------------------------------------
                        
                                total_orgs = (
                                    df_m_ms["Organización"]
                                    .nunique()
                                )
                        
                                orgs_con_uso = (
                                    df_m_ms[
                                        df_m_ms["Machine Sync (%)"].fillna(0) >= 1
                                    ]["Organización"]
                                    .nunique()
                                )
                        
                                orgs_potenciales = (
                                    df_m_ms[
                                        df_m_ms["Machine Sync (%)"].fillna(0) < 1
                                    ]["Organización"]
                                    .nunique()
                                )
                        
                                adopcion = (
                                    (orgs_con_uso / total_orgs * 100)
                                    if total_orgs > 0
                                    else 0
                                )
                        
                                kpi1, kpi2, kpi3 = st.columns(3)
                        
                                with kpi1:
                                    st.metric(
                                        "Organizaciones Compatibles",
                                        total_orgs
                                    )
                        
                                with kpi2:
                                    st.metric(
                                        "Potenciales",
                                        orgs_potenciales
                                    )
                        
                                with kpi3:
                                    st.metric(
                                        "Adopción Actual",
                                        f"{adopcion:.1f}%"
                                    )
                        
                                # ------------------------------------------------------
                                # TABLA
                                # ------------------------------------------------------
                        
                                st.markdown("#### Detalle de Organizaciones")
                        
                                def color_sync(row):
                        
                                    uso = row["Machine Sync (%)"]
                        
                                    if pd.isna(uso) or uso < 1:
                                        return [
                                            "background-color: #7f1d1d; color: white;"
                                        ] * len(row)
                        
                                    return [
                                        "background-color: #14532d; color: white;"
                                    ] * len(row)
                        
                                st.dataframe(
                        
                                    df_m_ms
                                    .sort_values(
                                        "Machine Sync (%)",
                                        ascending=True,
                                        na_position="first"
                                    )
                                    .style
                                    .apply(
                                        color_sync,
                                        axis=1
                                    )
                                    .format(
                                        {
                                            "Machine Sync (%)": "{:.1f}%"
                                        },
                                        na_rep="0.0%"
                                    ),
                        
                                    use_container_width=True
                        
                                )
                        
                                # ------------------------------------------------------
                                # GRÁFICOS
                                # ------------------------------------------------------
                        
                                col_b, col_p = st.columns(2)
                        
                                with col_b:
                        
                                    df_pot_ms = df_m_ms[
                                        df_m_ms["Machine Sync (%)"]
                                        .fillna(0) < 1
                                    ]
                        
                                    if not df_pot_ms.empty:
                        
                                        df_chart_ms = (
                                            df_pot_ms
                                            .groupby("Sucursal")
                                            ["Organización"]
                                            .nunique()
                                            .reset_index(
                                                name="Cant. Organizaciones"
                                            )
                                        )
                        
                                        fig_bar_ms = px.bar(
                        
                                            df_chart_ms.sort_values(
                                                "Cant. Organizaciones",
                                                ascending=False
                                            ),
                        
                                            x="Sucursal",
                                            y="Cant. Organizaciones",
                        
                                            title="Potenciales por Sucursal",
                        
                                            color="Sucursal",
                        
                                            text_auto=True
                        
                                        )
                        
                                        st.plotly_chart(
                                            fig_bar_ms,
                                            use_container_width=True
                                        )
                        
                                with col_p:
                        
                                    df_pie = (
                                        df_m_ms
                                        .drop_duplicates("Organización")
                                        .copy()
                                    )
                        
                                    df_pie["Estado"] = np.where(
                        
                                        df_pie["Machine Sync (%)"]
                                        .fillna(0) >= 1,
                        
                                        "Con Uso",
                        
                                        "Potencial"
                        
                                    )
                        
                                    fig_pie_ms = px.pie(
                        
                                        df_pie,
                        
                                        names="Estado",
                        
                                        hole=0.55,
                        
                                        title="Estado de Adopción",
                        
                                        color="Estado",
                        
                                        color_discrete_map={
                                            "Con Uso": "#2ca02c",
                                            "Potencial": "#d62728"
                                        }
                        
                                    )
                        
                                    st.plotly_chart(
                                        fig_pie_ms,
                                        use_container_width=True
                                    )
                        
                            else:
                        
                                st.info(
                                    "ℹ️ No se encontraron organizaciones con combinaciones "
                                    "compatibles Tractor + Cosechadora para Machine Sync."
                                )

                        # ==============================================================================
                        # OPORTUNIDADES DE ADOPCIÓN - AUTOPATH
                        # ==============================================================================
                        
                        if (
                            tech_seleccionada_label == "AutoPath™"
                            or
                            tech_seleccionada_label == "Implement Guidance"
                        ):
                        
                            st.markdown("---")
                        
                            if tech_seleccionada_label == "Implement Guidance":
                        
                                st.subheader("Oportunidades de Adopción - Implement Guidance")
                        
                                st.info(
                                    "Implement Guidance se encuentra asociado al uso de "
                                    "AutoPath™. Por lo tanto las oportunidades mostradas "
                                    "corresponden a potenciales usuarios de AutoPath™."
                                )
                        
                            else:
                        
                                st.subheader("Oportunidades de Adopción - AutoPath™")
                        
                            st.caption(
                                "Organizaciones que poseen una combinación compatible de "
                                "tractor + pulverizadora y presentan menos de 1% de uso "
                                "promedio de AutoPath™ durante el período analizado."
                            )
                        
                            # ----------------------------------------------------------
                            # MODELOS COMPATIBLES
                            # ----------------------------------------------------------
                        
                            trac_ap_list = [
                                "7M 200",
                                "7M 215",
                                "7M 230",
                                "7200J",
                                "7210J",
                                "7215J",
                                "7230J",
                                "7230R",
                                "8245R",
                                "8250R",
                                "8270R",
                                "8295R",
                                "8320R",
                                "8335R",
                                "8345R",
                                "8370R",
                                "8370RT",
                                "8400R",
                                "9420R",
                                "9470R",
                                "9520R",
                                "9570R",
                                "9R 390"
                            ]
                        
                            pulv_models = [
                                "M4025",
                                "M4030",
                                "M4040",
                                "4730"
                            ]
                        
                            col_ap = "AutoPath™ Activo"
                        
                            df_ap_base = df_ga.copy()
                        
                            df_ap_trac = df_ap_base[
                                (df_ap_base["Tipo"] == "Tractor")
                                &
                                (df_ap_base["Modelo"].isin(trac_ap_list))
                            ].copy()
                        
                            df_ap_pulv = df_ap_base[
                                (df_ap_base["Tipo"] == "Pulverizadora")
                                &
                                (df_ap_base["Modelo"].isin(pulv_models))
                            ].copy()
                        
                            if (
                                not df_ap_trac.empty
                                and
                                not df_ap_pulv.empty
                                and
                                col_ap in df_ap_pulv.columns
                            ):
                        
                                # ------------------------------------------------------
                                # PROMEDIO DE USO POR ORGANIZACIÓN
                                # ------------------------------------------------------
                        
                                df_ap_org = (
                        
                                    df_ap_pulv
                        
                                    .groupby("Organización")
                        
                                    .agg(
                                        {
                                            col_ap: "mean",
                                            "Sucursal": "last",
                                            "Modelo": "first"
                                        }
                                    )
                        
                                    .reset_index()
                        
                                    .rename(
                                        columns={
                                            col_ap: "AutoPath (%)",
                                            "Modelo": "Pulverizadora"
                                        }
                                    )
                        
                                )
                        
                                df_trac_org = (
                        
                                    df_ap_trac
                        
                                    .groupby("Organización")
                        
                                    .agg(
                                        {
                                            "Modelo": "first"
                                        }
                                    )
                        
                                    .reset_index()
                        
                                    .rename(
                                        columns={
                                            "Modelo": "Tractor"
                                        }
                                    )
                        
                                )
                        
                                df_m_ap = pd.merge(
                        
                                    df_ap_org,
                                    df_trac_org,
                        
                                    on="Organización",
                        
                                    how="inner"
                        
                                )
                        
                                # ------------------------------------------------------
                                # KPI
                                # ------------------------------------------------------
                        
                                total_orgs = (
                                    df_m_ap["Organización"]
                                    .nunique()
                                )
                        
                                orgs_con_uso = (
                                    df_m_ap[
                                        df_m_ap["AutoPath (%)"].fillna(0) >= 1
                                    ]["Organización"]
                                    .nunique()
                                )
                        
                                orgs_potenciales = (
                                    df_m_ap[
                                        df_m_ap["AutoPath (%)"].fillna(0) < 1
                                    ]["Organización"]
                                    .nunique()
                                )
                        
                                adopcion = (
                                    (orgs_con_uso / total_orgs * 100)
                                    if total_orgs > 0
                                    else 0
                                )
                        
                                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                        
                                with kpi1:
                                    st.metric(
                                        "Organizaciones Compatibles",
                                        total_orgs
                                    )
                        
                                with kpi2:
                                    st.metric(
                                        "Potenciales AutoPath",
                                        orgs_potenciales
                                    )
                        
                                with kpi3:
                                    st.metric(
                                        "Adopción Actual",
                                        f"{adopcion:.1f}%"
                                    )
                        
                                with kpi4:
                                    st.metric(
                                        "Potencial Implement Guidance",
                                        orgs_potenciales
                                    )
                        
                                # ------------------------------------------------------
                                # TABLA
                                # ------------------------------------------------------
                        
                                st.markdown("#### Detalle de Organizaciones")
                        
                                def color_ap(row):
                        
                                    uso = row["AutoPath (%)"]
                        
                                    if pd.isna(uso) or uso < 1:
                                        return [
                                            "background-color: #7f1d1d; color: white;"
                                        ] * len(row)
                        
                                    return [
                                        "background-color: #14532d; color: white;"
                                    ] * len(row)
                        
                                st.dataframe(
                        
                                    df_m_ap
                        
                                    .sort_values(
                                        "AutoPath (%)",
                                        ascending=True,
                                        na_position="first"
                                    )
                        
                                    .style
                        
                                    .apply(
                                        color_ap,
                                        axis=1
                                    )
                        
                                    .format(
                                        {
                                            "AutoPath (%)": "{:.1f}%"
                                        },
                                        na_rep="0.0%"
                                    ),
                        
                                    use_container_width=True
                        
                                )
                        
                                # ------------------------------------------------------
                                # GRÁFICOS
                                # ------------------------------------------------------
                        
                                col_b, col_p = st.columns(2)
                        
                                with col_b:
                        
                                    df_pot_ap = df_m_ap[
                                        df_m_ap["AutoPath (%)"]
                                        .fillna(0) < 1
                                    ]
                        
                                    if not df_pot_ap.empty:
                        
                                        df_chart_ap = (
                        
                                            df_pot_ap
                        
                                            .groupby("Sucursal")
                                            ["Organización"]
                        
                                            .nunique()
                        
                                            .reset_index(
                                                name="Cant. Organizaciones"
                                            )
                        
                                        )
                        
                                        fig_bar_ap = px.bar(
                        
                                            df_chart_ap.sort_values(
                                                "Cant. Organizaciones",
                                                ascending=False
                                            ),
                        
                                            x="Sucursal",
                                            y="Cant. Organizaciones",
                        
                                            title="Potenciales por Sucursal",
                        
                                            color="Sucursal",
                        
                                            text_auto=True
                        
                                        )
                        
                                        st.plotly_chart(
                                            fig_bar_ap,
                                            use_container_width=True
                                        )
                        
                                with col_p:
                        
                                    df_pie_ap = (
                                        df_m_ap
                                        .drop_duplicates("Organización")
                                        .copy()
                                    )
                        
                                    df_pie_ap["Estado"] = np.where(
                        
                                        df_pie_ap["AutoPath (%)"]
                                        .fillna(0) >= 1,
                        
                                        "Con Uso",
                        
                                        "Potencial"
                        
                                    )
                        
                                    fig_pie_ap = px.pie(
                        
                                        df_pie_ap,
                        
                                        names="Estado",
                        
                                        hole=0.55,
                        
                                        title="Estado de Adopción",
                        
                                        color="Estado",
                        
                                        color_discrete_map={
                                            "Con Uso": "#2ca02c",
                                            "Potencial": "#d62728"
                                        }
                        
                                    )
                        
                                    st.plotly_chart(
                                        fig_pie_ap,
                                        use_container_width=True
                                    )
                        
                            else:
                        
                                st.info(
                                    "ℹ️ No se encontraron organizaciones con combinaciones "
                                    "compatibles Tractor + Pulverizadora para AutoPath™."
                                )

                        # ==============================================================================
                        # OPORTUNIDADES DE ADOPCIÓN - TURN AUTOMATION (ATTA)
                        # ==============================================================================
                        
                        if tech_seleccionada_label == "Turn Automation":
                        
                            st.markdown("---")
                            st.subheader("Oportunidades de Adopción - Turn Automation")
                        
                            st.caption(
                                "Máquinas compatibles con Automatización de Maniobras "
                                "(ATTA) que presentan menos de 1% de uso promedio "
                                "durante el período analizado."
                            )
                        
                            # ----------------------------------------------------------
                            # MODELOS COMPATIBLES
                            # ----------------------------------------------------------
                        
                            atta_models = [
                                "S790",
                                "S780",
                                "S770",
                                "S760",
                                "S7 900",
                                "S7 800",
                                "S7 700",
                                "S7 600",
                                "7M 200",
                                "7M 215",
                                "7M 230",
                                "8245R",
                                "8250R",
                                "8270R",
                                "8295R",
                                "8320R",
                                "8335R",
                                "8345R",
                                "8370R",
                                "8370RT",
                                "8400R",
                                "9R390",
                                "9R 390"
                            ]
                        
                            col_atta = "Automatización de maniobras AutoTrac™ Activo"
                        
                            df_atta_base = df_ga.copy()
                        
                            df_atta = df_atta_base[
                                df_atta_base["Modelo"].isin(atta_models)
                            ].copy()
                        
                            if (
                                not df_atta.empty
                                and
                                col_atta in df_atta.columns
                            ):
                        
                                # ------------------------------------------------------
                                # PROMEDIO DE USO POR ORGANIZACIÓN + MODELO
                                # ------------------------------------------------------
                        
                                df_atta_org = (
                                    df_atta
                                    .groupby(
                                        [
                                            "Organización",
                                            "Modelo",
                                            "Sucursal"
                                        ]
                                    )
                                    .agg(
                                        {
                                            col_atta: "mean"
                                        }
                                    )
                                    .reset_index()
                                    .rename(
                                        columns={
                                            col_atta: "ATTA (%)"
                                        }
                                    )
                                )
                        
                                # ------------------------------------------------------
                                # KPIs
                                # ------------------------------------------------------
                        
                                total_orgs = (
                                    df_atta_org["Organización"]
                                    .nunique()
                                )
                        
                                total_maquinas = len(df_atta_org)
                        
                                orgs_con_uso = (
                                    df_atta_org[
                                        df_atta_org["ATTA (%)"].fillna(0) >= 1
                                    ]["Organización"]
                                    .nunique()
                                )
                        
                                orgs_potenciales = (
                                    df_atta_org[
                                        df_atta_org["ATTA (%)"].fillna(0) < 1
                                    ]["Organización"]
                                    .nunique()
                                )
                        
                                adopcion = (
                                    (orgs_con_uso / total_orgs * 100)
                                    if total_orgs > 0
                                    else 0
                                )
                        
                                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                        
                                with kpi1:
                                    st.metric(
                                        "Organizaciones Compatibles",
                                        total_orgs
                                    )
                        
                                with kpi2:
                                    st.metric(
                                        "Potenciales ATTA",
                                        orgs_potenciales
                                    )
                        
                                with kpi3:
                                    st.metric(
                                        "Adopción Actual",
                                        f"{adopcion:.1f}%"
                                    )
                        
                                with kpi4:
                                    st.metric(
                                        "Máquinas Compatibles",
                                        total_maquinas
                                    )
                        
                                # ------------------------------------------------------
                                # TABLA
                                # ------------------------------------------------------
                        
                                st.markdown("#### Detalle de Organizaciones")
                        
                                def color_atta(row):
                        
                                    uso = row["ATTA (%)"]
                        
                                    if pd.isna(uso) or uso < 1:
                                        return [
                                            "background-color: #7f1d1d; color: white;"
                                        ] * len(row)
                        
                                    return [
                                        "background-color: #14532d; color: white;"
                                    ] * len(row)
                        
                                st.dataframe(
                        
                                    df_atta_org
                                    .sort_values(
                                        "ATTA (%)",
                                        ascending=True,
                                        na_position="first"
                                    )
                                    .style
                                    .apply(
                                        color_atta,
                                        axis=1
                                    )
                                    .format(
                                        {
                                            "ATTA (%)": "{:.1f}%"
                                        },
                                        na_rep="0.0%"
                                    ),
                        
                                    use_container_width=True
                        
                                )
                        
                                # ------------------------------------------------------
                                # GRÁFICOS
                                # ------------------------------------------------------
                        
                                col_b, col_p = st.columns(2)
                        
                                with col_b:
                        
                                    df_pot_atta = df_atta_org[
                                        df_atta_org["ATTA (%)"]
                                        .fillna(0) < 1
                                    ]
                        
                                    if not df_pot_atta.empty:
                        
                                        df_chart_atta = (
                                            df_pot_atta
                                            .groupby("Sucursal")
                                            ["Organización"]
                                            .nunique()
                                            .reset_index(
                                                name="Cant. Organizaciones"
                                            )
                                        )
                        
                                        fig_bar_atta = px.bar(
                        
                                            df_chart_atta.sort_values(
                                                "Cant. Organizaciones",
                                                ascending=False
                                            ),
                        
                                            x="Sucursal",
                                            y="Cant. Organizaciones",
                        
                                            title="Potenciales por Sucursal",
                        
                                            color="Sucursal",
                        
                                            text_auto=True
                        
                                        )
                        
                                        st.plotly_chart(
                                            fig_bar_atta,
                                            use_container_width=True
                                        )
                        
                                with col_p:
                        
                                    df_pie_atta = (
                                        df_atta_org
                                        .drop_duplicates("Organización")
                                        .copy()
                                    )
                        
                                    df_pie_atta["Estado"] = np.where(
                        
                                        df_pie_atta["ATTA (%)"]
                                        .fillna(0) >= 1,
                        
                                        "Con Uso",
                        
                                        "Potencial"
                        
                                    )
                        
                                    fig_pie_atta = px.pie(
                        
                                        df_pie_atta,
                        
                                        names="Estado",
                        
                                        hole=0.55,
                        
                                        title="Estado de Adopción",
                        
                                        color="Estado",
                        
                                        color_discrete_map={
                                            "Con Uso": "#2ca02c",
                                            "Potencial": "#d62728"
                                        }
                        
                                    )
                        
                                    st.plotly_chart(
                                        fig_pie_atta,
                                        use_container_width=True
                                    )
                        
                            else:
                        
                                st.info(
                                    "ℹ️ No se encontraron máquinas compatibles "
                                    "para Turn Automation en el período seleccionado."
                                )
                        else:
                             st.info(f"ℹ️ No hay suficientes datos temporales para graficar la serie histórica de {tech_seleccionada_label}.")
                    else:
                        st.info("ℹ️ No se encontraron las columnas de fecha necesarias para generar el gráfico histórico.")
                      
    else:
        st.write(
            "No hay máquinas aptas con datos disponibles para mostrar en la tabla."
        )
with tab_cosechadoras:

    col_logo, col_titulo = st.columns([1,21])
    with col_logo:
        st.image(
            "Cosechadora.png",
            width=80
        )
    with col_titulo:
        st.title(
            "Uso de Tecnología en Cosechadoras"
        )


    subtab_s7x9, subtab_s700 = st.tabs([
        "S7 / X9",
        "S700"
    ])

    with subtab_s7x9:

        st.subheader(
            "Automatización de Cosecha — S7 / X9"
        )
    
        # ---------------------------------------------------
        # CARGA DE DATOS
        # ---------------------------------------------------
        
        df_cosecha = cargar_base_cosecha()
        
        df_cosecha["Fecha_inicio_dt"] = pd.to_datetime(
            df_cosecha["Fecha de inicio"],
            format="mixed",
            errors="coerce"
        )
        
        df_cosecha["Fecha_fin_dt"] = pd.to_datetime(
            df_cosecha["Fecha de terminación"],
            format="mixed",
            errors="coerce"
        )

        
        # ---------------------------------------------------
        # FILTRO DE CULTIVO
        # ---------------------------------------------------
        
        st.markdown("---")
        
        cultivos = sorted([
            c
            for c in df_cosecha["Cultivo"]
            .dropna()
            .unique()
        ])
        
        sel_cultivos = st.multiselect(
            "Cultivo",
            cultivos
        )
        
        # ---------------------------------------------------
        # APLICACIÓN FILTRO
        # ---------------------------------------------------
        
        df_cosecha_filtrado = df_cosecha.copy()

        # ------------------------------------------
        # FILTROS GLOBALES DEL DASHBOARD
        # ------------------------------------------
        
        if sel_sucursal != "Todas":
        
            df_cosecha_filtrado = (
                df_cosecha_filtrado[
                    df_cosecha_filtrado["Sucursal"]
                    == sel_sucursal
                ]
            )
        
        if sel_razon != "Todas":
        
            df_cosecha_filtrado = (
                df_cosecha_filtrado[
                    df_cosecha_filtrado[
                        "Nombre de organización"
                    ] == sel_razon
                ]
            )
            
        if rango_fechas:
            df_cosecha_filtrado = (
                df_cosecha_filtrado[
                    (
                        df_cosecha_filtrado[
                            "Fecha_inicio_dt"
                        ].dt.date
                        >= rango_fechas[0]
                    )
                    &
                    (
                        df_cosecha_filtrado[
                            "Fecha_fin_dt"
                        ].dt.date
                        <= rango_fechas[1]
                    )
                ]
            )
        

        
        if sel_cultivos:
        
            df_cosecha_filtrado = (
                df_cosecha_filtrado[
                    df_cosecha_filtrado["Cultivo"]
                    .isin(sel_cultivos)
                ]
            )

        # ---------------------------------------------------
        # NORMALIZACIÓN DE COLUMNAS
        # ---------------------------------------------------
    
        col_ajustes = (
            "Automatización de ajustes de cosecha - Utilización (%)"
        )
    
        col_velocidad = (
            "Automatización de la velocidad de avance - Utilización (%)"
        )
    
        col_productividad = (
            "Automatización de la velocidad de avance - Mayor productividad (%)"
        )
    
        # ---------------------------------------------------
        # KPI GENERALES
        # ---------------------------------------------------
    
        st.subheader("Resumen General")
    
        cosechadoras = (
            df_cosecha_filtrado["Número de serie"]
            .nunique()
        )
    
        organizaciones = (
            df_cosecha_filtrado["Nombre de organización"]
            .nunique()
        )
    
        hectareas = (
            df_cosecha_filtrado[
                "Superficie cosechada (ha)"
            ]
            .fillna(0)
            .sum()
        )
    
        productividad_media = (
            df_cosecha_filtrado[col_productividad]
            .mean()
        )
    
        kpi1, kpi2, kpi3 = st.columns(3)
    
        kpi1.metric(
            "Cosechadoras",
            cosechadoras
        )
    
        kpi2.metric(
            "Organizaciones",
            organizaciones
        )
    
        kpi3.metric(
            "Hectáreas Cosechadas",
            f"{hectareas:,.0f}"
        )
    
    
        # ---------------------------------------------------
        # KPI TECNOLÓGICOS
        # ---------------------------------------------------
    
        st.subheader("Indicadores Tecnológicos")
    
        prom_ajustes = (
            df_cosecha_filtrado[col_ajustes]
            .mean()
        )
    
        prom_velocidad = (
            df_cosecha_filtrado[col_velocidad]
            .mean()
        )
    
        hectareas_automatizadas = (
            df_cosecha_filtrado[
                "Automatización de ajustes de cosecha - Activado (ha)"
            ]
            .fillna(0)
            .sum()
        )
    
        superficie_total = (
            df_cosecha_filtrado[
                "Superficie cosechada (ha)"
            ]
            .fillna(0)
            .sum()
        )
    
        cobertura = (
            hectareas_automatizadas /
            superficie_total * 100
            if superficie_total > 0
            else 0
        )
    
        kpi5, kpi6, kpi7 = st.columns(3)
    
        kpi5.metric(
            "Automatización Ajustes",
            f"{prom_ajustes:.1f}%"
        )
    
        kpi6.metric(
            "Automatización Velocidad",
            f"{prom_velocidad:.1f}%"
        )
    
        kpi7.metric(
            "Cobertura Automatizada",
            f"{cobertura:.1f}%"
        )
    
        # ---------------------------------------------------
        # GRÁFICO 1 - HISTÓRICO SEMANAL DE SUPERFICIE
        # APILADA POR CULTIVO
        # ---------------------------------------------------
        
        st.markdown("---")
        st.subheader(
            "Evolución Semanal de la Superficie Cosechada por Cultivo"
        )
        
        df_superficie_semana = (
            df_cosecha_filtrado
            .dropna(
                subset=[
                    "Fecha_fin_dt",
                    "Cultivo",
                    "Superficie cosechada (ha)"
                ]
            )
            .groupby(
                [
                    "Fecha_fin_dt",
                    "Cultivo"
                ],
                as_index=False
            )
            .agg(
                Superficie_Cosechada=(
                    "Superficie cosechada (ha)",
                    "sum"
                )
            )
            .sort_values("Fecha_fin_dt")
        )
        
        if not df_superficie_semana.empty:
        
            fig_superficie_semana = px.bar(
                df_superficie_semana,
                x="Fecha_fin_dt",
                y="Superficie_Cosechada",
                color="Cultivo",
                barmode="stack",
                labels={
                    "Fecha_fin_dt": "Semana",
                    "Superficie_Cosechada": "Superficie cosechada (ha)"
                },
                title="Superficie Cosechada por Semana y Cultivo"
            )
        
            fig_superficie_semana.update_layout(
                xaxis_title="Fecha de terminación de la semana",
                yaxis_title="Superficie cosechada (ha)",
                hovermode="x unified",
                legend_title_text="Cultivo"
            )
        
            fig_superficie_semana.update_xaxes(
                tickformat="%d/%m/%Y"
            )
        
            st.plotly_chart(
                fig_superficie_semana,
                use_container_width=True
            )

        
        # ---------------------------------------------------
        # GRÁFICO 2 - MÁQUINAS Y USO DE TECNOLOGÍA
        # POR SEMANA
        # ---------------------------------------------------
        
        st.markdown("---")
        st.subheader(
            "Evolución Semanal de la Adopción Tecnológica"
        )
        
        df_sem = (
            df_cosecha_filtrado
            .dropna(
                subset=["Fecha_fin_dt"]
            )
            .groupby(
                "Fecha_fin_dt",
                as_index=False
            )
            .agg(
                Ajustes=(
                    col_ajustes,
                    "mean"
                ),
                Velocidad=(
                    col_velocidad,
                    "mean"
                ),
                Maquinas=(
                    "Número de serie",
                    "nunique"
                )
            )
            .sort_values("Fecha_fin_dt")
        )
        
        if not df_sem.empty:
        
            from plotly.subplots import make_subplots
            import plotly.graph_objects as go
        
            fig_adopcion = make_subplots(
                specs=[
                    [
                        {
                            "secondary_y": True
                        }
                    ]
                ]
            )
        
            # Barras
            fig_adopcion.add_trace(
                go.Bar(
                    x=df_sem["Fecha_fin_dt"],
                    y=df_sem["Maquinas"],
                    name="Máquinas trabajando",
                    marker_color="#2b5c8f",
                    text=df_sem["Maquinas"],
                    textposition="auto"
                ),
                secondary_y=False
            )
        
            # Línea ajustes
            fig_adopcion.add_trace(
                go.Scatter(
                    x=df_sem["Fecha_fin_dt"],
                    y=df_sem["Ajustes"],
                    mode="lines+markers",
                    name="Automatización de ajustes",
                    line=dict(color="#f2b134", width=3)
                ),
                secondary_y=True
            )
        
            # Línea velocidad
            fig_adopcion.add_trace(
                go.Scatter(
                    x=df_sem["Fecha_fin_dt"],
                    y=df_sem["Velocidad"],
                    mode="lines+markers",
                    name="Automatización de velocidad",
                    line=dict(color="#2ca02c", width=3)
                ),
                secondary_y=True
            )
        
            fig_adopcion.update_yaxes(
                title_text="Cantidad de máquinas",
                secondary_y=False
            )
        
            fig_adopcion.update_yaxes(
                title_text="Utilización promedio (%)",
                range=[0, 110],
                secondary_y=True
            )
        
            fig_adopcion.update_xaxes(
                tickformat="%d/%m/%Y"
            )
        
            fig_adopcion.update_layout(
                title="Máquinas Trabajando y Uso Promedio de Tecnología por Semana",
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
        
            st.plotly_chart(
                fig_adopcion,
                use_container_width=True
            )

        #---------------------------------------
        #      TABLA POR MAQUINA
        #---------------------------------------
        
        st.markdown("---")
        st.subheader("Uso de Tecnología por Máquina")
        
        # ---------------------------------------------------
        # PROMEDIOS HISTÓRICOS
        # ---------------------------------------------------
        
        df_maquinas = (
            df_cosecha_filtrado
            .groupby(
                [
                    "Nombre de organización",
                    "Nombre de máquina",
                    "Número de serie"
                ],
                as_index=False
            )
            .agg(
                Hectareas=(
                    "Superficie cosechada (ha)",
                    "sum"
                ),
                Ajustes=(
                    col_ajustes,
                    "mean"
                ),
                Velocidad=(
                    col_velocidad,
                    "mean"
                ),
                Productividad=(
                    col_productividad,
                    "mean"
                )
            )
        )
        
        # ---------------------------------------------------
        # ÚLTIMA SEMANA
        # ---------------------------------------------------
        
        ultima_fecha = (
            df_cosecha_filtrado["Fecha_fin_dt"]
            .max()
        )
        
        df_ultima_semana = (
            df_cosecha_filtrado[
                df_cosecha_filtrado["Fecha_fin_dt"]
                == ultima_fecha
            ]
            .groupby(
                [
                    "Nombre de organización",
                    "Nombre de máquina",
                    "Número de serie"
                ],
                as_index=False
            )
            .agg(
                Ajustes_Ult=(
                    col_ajustes,
                    "mean"
                ),
                Velocidad_Ult=(
                    col_velocidad,
                    "mean"
                )
            )
        )
        
        # ---------------------------------------------------
        # MERGE
        # ---------------------------------------------------
        
        df_maquinas = pd.merge(
        
            df_maquinas,
        
            df_ultima_semana,
        
            on=[
                "Nombre de organización",
                "Nombre de máquina",
                "Número de serie"
            ],
        
            how="left"
        
        )
        
        # ---------------------------------------------------
        # EVOLUCIÓN
        # ---------------------------------------------------
        
        df_maquinas["Diff_Ajustes"] = (
            df_maquinas["Ajustes_Ult"]
            -
            df_maquinas["Ajustes"]
        )
        
        df_maquinas["Diff_Velocidad"] = (
            df_maquinas["Velocidad_Ult"]
            -
            df_maquinas["Velocidad"]
        )
        
        def formato_evolucion(x):
        
            if pd.isna(x):
                return "⚪ Sin datos"
        
            if x > 0.5:
                return f"🟢 +{x:.1f}%"
        
            if x < -0.5:
                return f"🔴 {x:.1f}%"
        
            return "➡️ 0.0%"
        
        df_maquinas["Evolución Ajustes"] = (
            df_maquinas["Diff_Ajustes"]
            .apply(formato_evolucion)
        )
        
        df_maquinas["Evolución Velocidad"] = (
            df_maquinas["Diff_Velocidad"]
            .apply(formato_evolucion)
        )
        
        # ---------------------------------------------------
        # RENOMBRAR COLUMNAS
        # ---------------------------------------------------
        
        df_maquinas = df_maquinas.rename(
        
            columns={
        
                "Nombre de organización":
                    "Organización",
        
                "Nombre de máquina":
                    "Máquina",
        
                "Número de serie":
                    "Serie",
        
                "Hectareas":
                    "Superficie (ha)",
        
                "Ajustes":
                    "Ajustes (%)",
        
                "Velocidad":
                    "Velocidad (%)",
        
                "Productividad":
                    "Productividad (%)"
        
            }
        
        )
        
        # ---------------------------------------------------
        # ORDENAR
        # ---------------------------------------------------
        
        df_maquinas = (
            df_maquinas
            .sort_values(
                "Superficie (ha)",
                ascending=False
            )
        )
        
        # ---------------------------------------------------
        # MOSTRAR TABLA
        # ---------------------------------------------------
        df_maquinas_view = df_maquinas[
            [
                "Organización",
                "Máquina",
                "Serie",
                "Superficie (ha)",
                "Ajustes (%)",
                "Evolución Ajustes",
                "Velocidad (%)",
                "Evolución Velocidad"
            ]
        ].copy()
        
                
        st.dataframe(
            df_maquinas_view.style.format(
                {
                    "Superficie (ha)": "{:,.0f}",
                    "Ajustes (%)": "{:.1f}%",
                    "Velocidad (%)": "{:.1f}%",
                    "Productividad (%)": "{:.1f}%"
                }
            ),
            use_container_width=True
        )
        
        #---------------------------------------
        #       TABLA POR CULTIVO
        #---------------------------------------
    
        st.subheader("Uso de Tecnología por Cultivo")
    
        df_cultivo = (
            df_cosecha_filtrado
            .groupby(
                "Cultivo",
                as_index=False
            )
            .agg(
                Hectareas=(
                    "Superficie cosechada (ha)",
                    "sum"
                ),
                Ajustes=(
                    col_ajustes,
                    "mean"
                ),
                Velocidad=(
                    col_velocidad,
                    "mean"
                ),
                Productividad=(
                    col_productividad,
                    "mean"
                )
            )
        )
        
        df_cultivo = (
            df_cultivo
            .sort_values(
                "Hectareas",
                ascending=False
            )
        )
    
        st.dataframe(
            df_cultivo.style.format(
                {
                    "Hectareas": "{:,.0f}",
                    "Ajustes": "{:.1f}%",
                    "Velocidad": "{:.1f}%",
                    "Productividad": "{:.1f}%"
                }
            ),
            use_container_width=True
        )
        

    


    #----------------------------------------------#
    #------- SUB TAB S700 -------------------------#
    #----------------------------------------------#
    
    with subtab_s700:
    
        st.subheader(
            "Tecnología en Cosechadoras S700"
        )
    
        # ---------------------------------------------------
        # BASE FILTRADA DEL DASHBOARD
        # ---------------------------------------------------
    
        df_s700 = df_filtrado_raw.copy()
    
        # Filtrar únicamente cosechadoras S700
    
        df_s700 = df_filtrado_raw[
            (
                df_filtrado_raw["Modelo"]
                .astype(str)
                .str.upper()
                .str.startswith("S7")
            )
            &
            (
                ~df_filtrado_raw["Modelo"]
                .astype(str)
                .str.upper()
                .str.startswith("S7 ")
            )
        ].copy()

    
        # ---------------------------------------------------
        # KPIs
        # ---------------------------------------------------
    
        st.subheader("Indicadores Tecnológicos")
    
        prom_auto = (
            df_s700["Auto Maintain Activado"]
            .mean()
        )
    
        prom_hs = (
            df_s700["Harvest Smart Activado"]
            .mean()
        )
    
        if pd.isna(prom_auto):
            prom_auto = 0
    
        if pd.isna(prom_hs):
            prom_hs = 0
    
        kpi1, kpi2 = st.columns(2)
    
        kpi1.metric(
            "Auto Maintain",
            f"{prom_auto:.1f}%"
        )
    
        kpi2.metric(
            "Harvest Smart",
            f"{prom_hs:.1f}%"
        )
    
        # ---------------------------------------------------
        # TABLA
        # ---------------------------------------------------
    
        st.markdown("---")
        st.subheader("Uso de Tecnología por Máquina")
    
        df_tabla_s700 = (
            df_s700
            .groupby(
                [
                    "Organización",
                    "Modelo",
                    "Número de serie de la máquina"
                ],
                as_index=False
            )
            .agg(
                Auto_Maintain=(
                    "Auto Maintain Activado",
                    "mean"
                ),
                Harvest_Smart=(
                    "Harvest Smart Activado",
                    "mean"
                ),
                Sucursal=(
                    "Sucursal",
                    "last"
                ),
                Licencia=(
                    col_licencia,
                    "last"
                ),
                Fin_Licencia=(
                    "Fin Licencia",
                    "last"
                ),
                Estado_Licencia=(
                    col_estado_licencia,
                    "last"
                )
            )
        )
    
        df_tabla_s700 = df_tabla_s700.rename(
            columns={
                "Número de serie de la máquina":
                    "Serie",
                "Auto_Maintain":
                    "Auto Maintain (%)",
                "Harvest_Smart":
                    "Harvest Smart (%)",
                "Fin_Licencia":
                    "Fin Licencia",
                "Estado_Licencia":
                    "Estado Licencia"
            }
        )
    
        st.dataframe(
    
            df_tabla_s700.style.format(
                {
                    "Auto Maintain (%)": "{:.1f}%",
                    "Harvest Smart (%)": "{:.1f}%"
                }
            ),
    
            use_container_width=True
    
        )
    
        # ---------------------------------------------------
        # EVOLUCIÓN HISTÓRICA
        # ---------------------------------------------------
    
        st.markdown("---")
        st.subheader(
            "Evolución de Uso de Tecnología"
        )
    
        df_s700_activas = df_s700[
            (
                df_s700["Auto Maintain Activado"].notna()
            )
            |
            (
                df_s700["Harvest Smart Activado"].notna()
            )
        ].copy()
        
        df_s700_activas["Fecha_fin_dt"] = pd.to_datetime(
            df_s700_activas["Fecha_fin_dt"],
            errors="coerce"
        )
        
        df_hist_s700 = (
            df_s700_activas
            .groupby("Fecha_fin_dt")
            .agg(
                AutoMaintain=(
                    "Auto Maintain Activado",
                    "mean"
                ),
                HarvestSmart=(
                    "Harvest Smart Activado",
                    "mean"
                ),
                Maquinas=(
                    "Número de serie de la máquina",
                    "nunique"
                )
            )
            .reset_index()
            .sort_values("Fecha_fin_dt")
        )

        from plotly.subplots import make_subplots
        import plotly.graph_objects as go
    
        fig_s700 = make_subplots(
            specs=[[{"secondary_y": True}]]
        )
    
        # Barras
    
        fig_s700.add_trace(
            go.Bar(
                x=df_hist_s700["Fecha_fin_dt"],
                y=df_hist_s700["Maquinas"],
                name="Máquinas Trabajando",
                marker_color="#2b5c8f",
                text=df_hist_s700["Maquinas"],
                textposition="auto"
            ),
            secondary_y=False
        )
    
        # Auto Maintain
    
        fig_s700.add_trace(
            go.Scatter(
                x=df_hist_s700["Fecha_fin_dt"],
                y=df_hist_s700["AutoMaintain"],
                mode="lines+markers",
                name="Auto Maintain",
                line=dict(
                    width=3,
                    color="#367c2b"
                )
            ),
            secondary_y=True
        )
    
        # Harvest Smart
    
        fig_s700.add_trace(
            go.Scatter(
                x=df_hist_s700["Fecha_fin_dt"],
                y=df_hist_s700["HarvestSmart"],
                mode="lines+markers",
                name="Harvest Smart",
                line=dict(
                    width=3,
                    color="#f2b134"
                )
            ),
            secondary_y=True
        )
    
        fig_s700.update_yaxes(
            title_text="Cantidad de Máquinas",
            secondary_y=False
        )
    
        fig_s700.update_yaxes(
            title_text="% Utilización",
            range=[0, 110],
            secondary_y=True
        )
    
        fig_s700.update_layout(
            title="Uso de Tecnología por Semana",
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
    
        st.plotly_chart(
            fig_s700,
            use_container_width=True
        )



# ----------------------------------------------#
#------- TAB PULVERIZADORAS --------------------#
#----------------------------------------------#

with tab_pulverizadoras:

    col_logo, col_titulo = st.columns([1,12])
    with col_logo:
        st.image(
            "pulve.png",
            width=80
        )
    
    with col_titulo:
        st.title(
            "Análisis CropCare"
        )


    # ---------------------------------------------------
    # BASE FILTRADA DEL DASHBOARD
    # ---------------------------------------------------

    df_pulv = df_filtrado_raw[
        df_filtrado_raw["Tipo"]
        .astype(str)
        .str.upper()
        .str.contains("PULVERIZADORA", na=False)
    ].copy()

    if df_pulv.empty:

        st.warning(
            "No se encontraron registros de pulverizadoras "
            "para los filtros seleccionados."
        )

    else:

        col_autotrac = "AutoTrac™ Activo"
        col_pulsacion = "Pulsación Activo"
        col_secciones = "Tiempo de control de secciones Activo"
        
        # ---------------------------------------------------
        # FILTRO DE USO REAL (>= 1%)
        # ---------------------------------------------------
        
        autotrac_filtrado = (
            df_pulv[col_autotrac]
            .where(df_pulv[col_autotrac] >= 1)
        )
        
        pulsacion_filtrado = (
            df_pulv[col_pulsacion]
            .where(df_pulv[col_pulsacion] >= 1)
        )
        
        secciones_filtrado = (
            df_pulv[col_secciones]
            .where(df_pulv[col_secciones] >= 1)
        )


        # ---------------------------------------------------
        # ÚLTIMA FOTO
        # ---------------------------------------------------

        ultima_fecha_pulv = (
            df_pulv["Fecha_fin_dt"]
            .max()
        )

        df_pulv_actual = (
            df_pulv[
                df_pulv["Fecha_fin_dt"]
                == ultima_fecha_pulv
            ]
        )

        fecha_formateada = (
            ultima_fecha_pulv.strftime("%d/%m/%Y")
            if pd.notna(ultima_fecha_pulv)
            else "-"
        )

        st.subheader(
            f"Resumen Actual (Última Semana: {fecha_formateada})"
        )

        # ---------------------------------------------------
        # KPIs
        # ---------------------------------------------------

        promedio_autotrac = (
            autotrac_filtrado
            .mean()
        )
        
        promedio_secciones = (
            secciones_filtrado
            .mean()
        )
        
        promedio_pulsacion = (
            pulsacion_filtrado
            .mean()
        )

        total_pulverizadoras = (
            df_pulv[
                "Número de serie de la máquina"
            ]
            .nunique()
        )



        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Pulverizadoras",
                total_pulverizadoras
            )

        with col2:
            st.metric(
                "AutoTrac™",
                f"{promedio_autotrac:.1f}%"
                if pd.notna(promedio_autotrac)
                else "Sin datos"
            )

        with col3:
            st.metric(
                "Control de Secciones",
                f"{promedio_secciones:.1f}%"
                if pd.notna(promedio_secciones)
                else "Sin datos"
            )

        with col4:
            st.metric(
                "Pulsación",
                f"{promedio_pulsacion:.1f}%"
                if pd.notna(promedio_pulsacion)
                else "Sin datos"
            )

        # ---------------------------------------------------
        # TABLA INDIVIDUAL
        # ---------------------------------------------------

        st.markdown("---")
        st.subheader(
            "Uso de Tecnología por Pulverizadora"
        )

        df_tabla = (
            df_pulv_actual
            .groupby(
                [
                    "Organización",
                    "Modelo",
                    "Número de serie de la máquina"
                ],
                as_index=False
            )
            .agg(
                AutoTrac=(
                    col_autotrac,
                    "mean"
                ),
                Pulsacion=(
                    col_pulsacion,
                    "mean"
                ),
                Secciones=(
                    col_secciones,
                    "mean"
                ),
                Sucursal=(
                    "Sucursal",
                    "last"
                ),
                Licencia=(
                    col_licencia,
                    "last"
                ),
                Fin_Licencia=(
                    "Fin Licencia",
                    "last"
                ),
                Estado_Licencia=(
                    col_estado_licencia,
                    "last"
                )
            )
        )

        df_tabla = df_tabla.rename(
            columns={
                "Número de serie de la máquina":
                    "Serie",
                "AutoTrac":
                    "AutoTrac (%)",
                "Pulsacion":
                    "Pulsación (%)",
                "Secciones":
                    "Control Secciones (%)",
                "Fin_Licencia":
                    "Fin Licencia",
                "Estado_Licencia":
                    "Estado Licencia"
            }
        )

        st.dataframe(

            df_tabla.style.format(
                {
                    "AutoTrac (%)": "{:.1f}%",
                    "Pulsación (%)": "{:.1f}%",
                    "Control Secciones (%)": "{:.1f}%"
                }
            ),

            use_container_width=True

        )

        # ---------------------------------------------------
        # HISTÓRICO DE ADOPCIÓN
        # ---------------------------------------------------

        st.markdown("---")
        st.subheader(
            "Evolución Histórica del Uso de Tecnología"
        )

        df_pulv_activas = df_pulv[
            (
                df_pulv[col_autotrac].notna()
            )
            |
            (
                df_pulv[col_pulsacion].notna()
            )
            |
            (
                df_pulv[col_secciones].notna()
            )
        ].copy()

        df_hist = (
            df_pulv_activas
            .groupby("Fecha_fin_dt")
            .agg(
        
                Prom_AutoTrac=(
                    col_autotrac,
                    lambda x: x[x >= 1].mean()
                ),
        
                Prom_Pulsacion=(
                    col_pulsacion,
                    lambda x: x[x >= 1].mean()
                ),
        
                Prom_Secciones=(
                    col_secciones,
                    lambda x: x[x >= 1].mean()
                ),
        
                Maquinas=(
                    "Número de serie de la máquina",
                    "nunique"
                )
        
            )
            .reset_index()
            .sort_values("Fecha_fin_dt")
        )


        from plotly.subplots import make_subplots
        import plotly.graph_objects as go

        fig_pulv = make_subplots(
            specs=[[{"secondary_y": True}]]
        )

        # Barras
        fig_pulv.add_trace(
            go.Bar(
                x=df_hist["Fecha_fin_dt"],
                y=df_hist["Maquinas"],
                name="Máquinas trabajando",
                marker_color="rgba(120,120,120,0.4)",
                text=df_hist["Maquinas"],
                textposition="auto"
            ),
            secondary_y=False
        )

        # AutoTrac
        fig_pulv.add_trace(
            go.Scatter(
                x=df_hist["Fecha_fin_dt"],
                y=df_hist["Prom_AutoTrac"],
                mode="lines+markers",
                name="AutoTrac™",
                line=dict(
                    color="orange",
                    width=3
                )
            ),
            secondary_y=True
        )

        # Secciones
        fig_pulv.add_trace(
            go.Scatter(
                x=df_hist["Fecha_fin_dt"],
                y=df_hist["Prom_Secciones"],
                mode="lines+markers",
                name="Control de Secciones",
                line=dict(
                    color="#9467bd",
                    width=3
                )
            ),
            secondary_y=True
        )

        # Pulsación
        fig_pulv.add_trace(
            go.Scatter(
                x=df_hist["Fecha_fin_dt"],
                y=df_hist["Prom_Pulsacion"],
                mode="lines+markers",
                name="Pulsación",
                line=dict(
                    color="#2ca02c",
                    width=3
                )
            ),
            secondary_y=True
        )

        fig_pulv.update_yaxes(
            title_text="Cantidad de Equipos",
            secondary_y=False
        )

        fig_pulv.update_yaxes(
            title_text="% Utilización",
            range=[0, 110],
            secondary_y=True
        )

        fig_pulv.update_layout(
            title="Máquinas Trabajando y Uso de Tecnología",
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        st.plotly_chart(
            fig_pulv,
            use_container_width=True
        )

        #----------------
        # PIE CHARTS
        #----------------

        df_pie_at = df_pulv_actual.copy()

        df_pie_at["Estado"] = np.where(
            df_pie_at[col_autotrac].fillna(0) >= 1,
            "Con Uso",
            "Sin Datos / Bajo Uso"
        )
        
        fig_at = px.pie(
            df_pie_at.groupby("Estado")
            .size()
            .reset_index(name="Cantidad"),
            names="Estado",
            values="Cantidad",
            title="AutoTrac™",
            hole=0.4,
            color="Estado",
            color_discrete_map={
                "Con Uso": "#2ca02c",
                "Sin Datos / Bajo Uso": "#d62728"
            }
        )

        df_pie_sec = df_pulv_actual.copy()
        
        df_pie_sec["Estado"] = np.where(
            df_pie_sec[col_secciones].fillna(0) >= 1,
            "Con Uso",
            "Sin Datos / Bajo Uso"
        )
        
        fig_sec = px.pie(
            df_pie_sec.groupby("Estado")
            .size()
            .reset_index(name="Cantidad"),
            names="Estado",
            values="Cantidad",
            title="Control de Secciones",
            hole=0.4,
            color="Estado",
            color_discrete_map={
                "Con Uso": "#2ca02c",
                "Sin Datos / Bajo Uso": "#d62728"
            }
        )
        fig_sec.update_traces(
            textinfo="percent+label"
        )

        df_pie_puls = df_pulv_actual.copy()
        
        df_pie_puls["Estado"] = np.where(
            df_pie_puls[col_pulsacion].fillna(0) >= 1,
            "Con Uso",
            "Sin Datos / Bajo Uso"
        )
        
        fig_puls = px.pie(
            df_pie_puls.groupby("Estado")
            .size()
            .reset_index(name="Cantidad"),
            names="Estado",
            values="Cantidad",
            title="Pulsación",
            hole=0.4,
            color="Estado",
            color_discrete_map={
                "Con Uso": "#2ca02c",
                "Sin Datos / Bajo Uso": "#d62728"
            }
        )
        fig_puls.update_traces(
            textinfo="percent+label"
        )

        col_p1, col_p2, col_p3 = st.columns(3)
        
        with col_p1:
            st.plotly_chart(
                fig_at,
                use_container_width=True
            )
        
        with col_p2:
            st.plotly_chart(
                fig_sec,
                use_container_width=True
            )
        
        with col_p3:
            st.plotly_chart(
                fig_puls,
                use_container_width=True
            )
        
                        



with tab_picadoras:
    

    col_logo, col_titulo = st.columns([1, 12])

    with col_logo:

        st.image(
            "Picadora.png",
            width=80
        )

    with col_titulo:

        st.title(
            "Análisis de Calidad de Picado"
        )

    # ---------------------------------------------------
    # CARGA BASE
    # ---------------------------------------------------

    df_pic = cargar_base_picadoras()

    df_pic["Fecha_inicio_dt"] = pd.to_datetime(
        df_pic["Fecha de inicio"],
        format="mixed",
        errors="coerce"
    )
    
    df_pic["Fecha_fin_dt"] = pd.to_datetime(
        df_pic["Fecha de terminación"],
        format="mixed",
        errors="coerce"
    )

    # ---------------------------------------------------
    # APLICAR FILTROS DEL SIDEBAR
    # ---------------------------------------------------
    
    # Excluir CONCI SA
    
    if excluir_conci:
    
        if "Organizaciones" in df_pic.columns:
    
            df_pic = df_pic[
                ~df_pic["Organizaciones"]
                .fillna("")
                .astype(str)
                .str.upper()
                .str.contains("CONCI SA")
            ]
    
    # -----------------------------------------
    # SUCURSAL
    # -----------------------------------------
    
    if sel_sucursal != "Todas":
    
        if "Sucursal" in df_pic.columns:
    
            df_pic = df_pic[
                df_pic["Sucursal"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                ==
                str(sel_sucursal)
                .strip()
                .upper()
            ]
    
    # -----------------------------------------
    # RAZÓN SOCIAL
    # -----------------------------------------
    
    if sel_razon != "Todas":
    
        if "Organizaciones" in df_pic.columns:
    
            df_pic = df_pic[
                df_pic["Organizaciones"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                ==
                str(sel_razon)
                .strip()
                .upper()
            ]
    
    # -----------------------------------------
    # TIPO DE MÁQUINA
    # -----------------------------------------
    
    if sel_tipo != "Todos":
    
        if "Tipo" in df_pic.columns:
    
            df_pic = df_pic[
                df_pic["Tipo"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                ==
                str(sel_tipo)
                .strip()
                .upper()
            ]
    
    # -----------------------------------------
    # MODELOS
    # -----------------------------------------
    
    if sel_modelos:
    
        if "Modelo" in df_pic.columns:
    
            df_pic = df_pic[
                df_pic["Modelo"]
                .isin(sel_modelos)
            ]
    
    # -----------------------------------------
    # FECHAS
    # -----------------------------------------
    
    if rango_fechas:
    
        fecha_ini = pd.Timestamp(
            rango_fechas[0]
        )
    
        fecha_fin = pd.Timestamp(
            rango_fechas[1]
        )
    
        df_pic = df_pic[
            (
                df_pic["Fecha_fin_dt"]
                >= fecha_ini
            )
            &
            (
                df_pic["Fecha_fin_dt"]
                <= fecha_fin
            )
        ]
    
    # ---------------------------------------------------
    # CONTROL DE DATOS VACÍOS
    # ---------------------------------------------------
    
    if df_pic.empty:
    
        st.warning(
            "No hay registros de picadoras para los filtros seleccionados."
        )
    
        st.stop()



    # ---------------------------------------------------
    # FILTROS NUEVOS
    # ---------------------------------------------------

    st.markdown("---")

    f1, f2 = st.columns(2)

    with f1:

        min_hectareas = st.number_input(
            "Superficie mínima a considerar (ha)",
            min_value=0.0,
            value=1.0,
            step=0.5
        )

    with f2:

        cultivos_disponibles = sorted(
            df_pic["Tipo de cultivo"]
            .dropna()
            .unique()
        )

        cultivo_seleccionado = st.multiselect(
            "Cultivo",
            cultivos_disponibles,
            default=cultivos_disponibles
        )

    # ---------------------------------------------------
    # FILTRO HECTAREAS
    # ---------------------------------------------------

    df_pic = df_pic[
        df_pic["Superficie cosechada"]
        >= min_hectareas
    ]

    # ---------------------------------------------------
    # FILTRO CULTIVO
    # ---------------------------------------------------

    if cultivo_seleccionado:

        df_pic = df_pic[
            df_pic["Tipo de cultivo"]
            .isin(cultivo_seleccionado)
        ]

    # ---------------------------------------------------
    # DATASETS ESPECIFICOS
    # ---------------------------------------------------

    df_maiz = df_pic[
        df_pic["Tipo de cultivo"]
        == "Maíz para ensilado"
    ].copy()

    df_alfalfa = df_pic[
        df_pic["Tipo de cultivo"]
        == "Alfalfa"
    ].copy()

    # ---------------------------------------------------
    # TABS
    # ---------------------------------------------------

    subtab_productividad, subtab_hl_maiz, subtab_hl_alfalfa = st.tabs(
        [
            "Productividad",
            "HarvestLab Maíz",
            "HarvestLab Alfalfa"
        ]
    )

    
    with subtab_productividad:
        

    
        # ---------------------------------------------------
        # KPI 1 - AUTOTRAC
        # ---------------------------------------------------
    
        autotrac_promedio = (
    
            df_pic["AutoTrac™"]
            .fillna(0)
    
            /
    
            df_pic["Superficie cosechada"]
            .replace(0, np.nan)
    
            * 100
    
        ).mean()
    
        # ---------------------------------------------------
        # KPI 2 - SUPERFICIE
        # ---------------------------------------------------
    
        superficie_total = (
            df_pic[
                "Superficie cosechada"
            ]
            .fillna(0)
            .sum()
        )
    
        # ---------------------------------------------------
        # KPI 3 - COMBUSTIBLE
        # ---------------------------------------------------
    
        combustible_ha = (
            df_pic[
                "Índice de combustible (área)"
            ]
            .mean()
        )
    
        # ---------------------------------------------------
        # KPI 4 - TONELADAS HÚMEDAS
        # ---------------------------------------------------
    
        toneladas_humedas = (
            df_pic[
                "Peso húmedo total"
            ]
            .fillna(0)
            .sum()
        )
    
        # ---------------------------------------------------
        # KPI 5 - HECTÁREAS CON CONSTITUYENTES
        # ---------------------------------------------------
        
        mask_curva = (
        
            df_pic["Almidón"].notna()
        
            |
        
            df_pic["Proteína bruta"].notna()
        
            |
        
            df_pic["Fibra detergente neutro"].notna()
        
            |
        
            df_pic["Fibra detergente ácido"].notna()
        
            |
        
            df_pic["Azúcar"].notna()
        
            |
        
            df_pic["Ceniza bruta"].notna()
        
        )
        
        ha_constituyentes = (
        
            df_pic.loc[
                mask_curva,
                "Superficie cosechada"
            ]
        
            .fillna(0)
        
            .sum()
        
        )
        
        porc_constituyentes = (
        
            ha_constituyentes
        
            /
        
            superficie_total
        
            * 100
        
            if superficie_total > 0
        
            else 0
        
        )
        
        # ---------------------------------------------------
        # KPIs
        # ---------------------------------------------------
        
        
        
        st.subheader(
                "Análisis de Calidad de Picado"
            )
        
        k1, k2, k3, k4, k5 = st.columns(5)
        
        k1.metric(
            "AutoTrac Promedio",
            f"{autotrac_promedio:.1f}%"
        )
        
        k2.metric(
            "Superficie Total",
            f"{superficie_total:,.0f} ha"
        )
        
        k3.metric(
            "Combustible",
            f"{combustible_ha:.1f} L/ha"
        )
        
        k4.metric(
            "Producción Húmeda",
            f"{toneladas_humedas:,.0f} t"
        )
        
        k5.metric(
            "Ha con Constituyentes",
            f"{porc_constituyentes:.1f}%"
        )
    
        # ---------------------------------------------------
        # HISTÓRICO
        # ---------------------------------------------------
        
        st.markdown("---")
        st.subheader(
            "Evolución Semanal de Trabajo"
        )
        
        df_hist = (
        
            df_pic
        
            .groupby(
                [
                    "Fecha_fin_dt",
                    "Tipo de cultivo"
                ]
            )
        
            .agg(
                Superficie=(
                    "Superficie cosechada",
                    "sum"
                )
            )
        
            .reset_index()
        
            .sort_values(
                "Fecha_fin_dt"
            )
        
        )
        
        # ---------------------------------------------------
        # MAQUINAS POR SEMANA
        # ---------------------------------------------------
        
        df_maq_hist = (
        
            df_pic
        
            .groupby("Fecha_fin_dt")
        
            ["Equipo"]
        
            .nunique()
        
            .reset_index()
        
        )
        
        # ---------------------------------------------------
        # GRAFICO
        # ---------------------------------------------------
        
        from plotly.subplots import make_subplots
        import plotly.graph_objects as go
        
        fig_pic = make_subplots(
            specs=[[{"secondary_y": True}]]
        )
        
        # ---------------------------------------------------
        # BARRAS POR CULTIVO
        # ---------------------------------------------------
        
        colores_cultivo = {
        
            "Maíz para ensilado":
                "#f2c230",
        
            "Alfalfa":
                "#2ca02c"
        
        }
        
        for cultivo in (
        
            df_hist["Tipo de cultivo"]
        
            .dropna()
        
            .unique()
        
        ):
        
            df_temp = (
        
                df_hist[
                    df_hist["Tipo de cultivo"]
                    == cultivo
                ]
        
            )
        
            fig_pic.add_trace(
        
                go.Bar(
        
                    x=df_temp["Fecha_fin_dt"],
        
                    y=df_temp["Superficie"],
        
                    name=cultivo,
        
                    marker_color=
                        colores_cultivo.get(
                            cultivo,
                            "#999999"
                        )
        
                ),
        
                secondary_y=False
        
            )
        
        # ---------------------------------------------------
        # LINEA DE MAQUINAS
        # ---------------------------------------------------
        
        fig_pic.add_trace(
        
            go.Scatter(
        
                x=df_maq_hist["Fecha_fin_dt"],
        
                y=df_maq_hist["Equipo"],
        
                mode="lines+markers",
        
                name="Máquinas",
        
                line=dict(
                    color="#2b5c8f",
                    width=3
                )
        
            ),
        
            secondary_y=True
        
        )
        
        # ---------------------------------------------------
        # EJES
        # ---------------------------------------------------
        
        fig_pic.update_yaxes(
            title_text="Superficie (ha)",
            secondary_y=False
        )
        
        fig_pic.update_yaxes(
            title_text="Cantidad de Máquinas",
            secondary_y=True
        )
        
        # ---------------------------------------------------
        # LAYOUT
        # ---------------------------------------------------
        
        fig_pic.update_layout(
        
            title=
                "Superficie por Cultivo y Máquinas Trabajando",
        
            barmode="stack",
        
            hovermode="x unified",
        
            legend=dict(
        
                orientation="h",
        
                yanchor="bottom",
        
                y=1.02,
        
                xanchor="right",
        
                x=1
        
            )
        
        )
        
        st.plotly_chart(
            fig_pic,
            use_container_width=True
        )



        
        # ---------------------------------------------------
        # TABLA POR MÁQUINA
        # ---------------------------------------------------
        
        st.markdown("---")
        st.subheader("Uso de Tecnología por Picadora")
        
        df_maquinas = (
            df_pic
            .groupby(
                [
                    "Organizaciones",
                    "Equipo",
                    "Nombre de máquina"
                ],
                as_index=False
            )
            .agg(
                Hectareas=(
                    "Superficie cosechada",
                    "sum"
                ),
                AutoTrac=(
                    "AutoTrac™",
                    "sum"
                )
            )
        )
        
        # -----------------------------------------
        # % AUTOTRAC
        # -----------------------------------------
        
        df_maquinas["AutoTrac (%)"] = np.where(
        
            df_maquinas["Hectareas"] > 0,
        
            df_maquinas["AutoTrac"]
            /
            df_maquinas["Hectareas"]
            *
            100,
        
            np.nan
        
        )
        
        # -----------------------------------------
        # % HECTÁREAS CON CONSTITUYENTES
        # -----------------------------------------
        
        df_constit = (
            df_pic.assign(
                Tiene_Constituyentes=mask_curva
            )
            .groupby(
                [
                    "Organizaciones",
                    "Equipo",
                    "Nombre de máquina"
                ],
                as_index=False
            )
            .agg(
                Hectareas_Total=(
                    "Superficie cosechada",
                    "sum"
                ),
                Hectareas_Const=(
                    "Superficie cosechada",
                    lambda x: x[
                        mask_curva.loc[x.index]
                    ].sum()
                )
            )
        )
        
        df_constit["Constituyentes (%)"] = np.where(
        
            df_constit["Hectareas_Total"] > 0,
        
            df_constit["Hectareas_Const"]
            /
            df_constit["Hectareas_Total"]
            *
            100,
        
            np.nan
        
        )
        
        # -----------------------------------------
        # ESTADO HARVESTLAB
        # -----------------------------------------
        
        def clasificar_maquina(grupo):
        
            tiene_const = (
        
                grupo["Almidón"].notna()
        
                |
        
                grupo["Proteína bruta"].notna()
        
                |
        
                grupo["Fibra detergente neutro"].notna()
        
                |
        
                grupo["Fibra detergente ácido"].notna()
        
                |
        
                grupo["Azúcar"].notna()
        
                |
        
                grupo["Ceniza bruta"].notna()
        
            ).any()
        
            if tiene_const:
        
                return "🟢 Curva Constituyentes Activada"
        
            ms = grupo["Materia seca"].dropna()
        
            if len(ms) > 0:
        
                tiene_decimal = (
        
                    (ms % 1 != 0)
                    .any()
                )
        
                if tiene_decimal:
        
                    return "🟡 Curva Constituyentes Desactivada"
        
            return "⚪ Sin HarvestLab"
        
        df_estado = (
        
            df_pic
        
            .groupby(
                [
                    "Organizaciones",
                    "Equipo",
                    "Nombre de máquina"
                ]
            )
        
            .apply(
                clasificar_maquina
            )
        
            .reset_index(
                name="Estado HarvestLab"
            )
        
        )
        
        # -----------------------------------------
        # MERGE
        # -----------------------------------------
        
        df_maquinas = pd.merge(
            df_maquinas,
            df_constit[
                [
                    "Organizaciones",
                    "Equipo",
                    "Nombre de máquina",
                    "Constituyentes (%)"
                ]
            ],
            on=[
                "Organizaciones",
                "Equipo",
                "Nombre de máquina"
            ],
            how="left"
        )
        
        df_maquinas = pd.merge(
            df_maquinas,
            df_estado,
            on=[
                "Organizaciones",
                "Equipo",
                "Nombre de máquina"
            ],
            how="left"
        )
        
        # -----------------------------------------
        # RENOMBRAR
        # -----------------------------------------
        
        df_maquinas = df_maquinas.rename(
            columns={
                "Organizaciones": "Organización",
                "Nombre de máquina": "Máquina",
                "Equipo": "Serie",
                "Hectareas": "Hectáreas Picadas"
            }
        )
        
        # -----------------------------------------
        # COLUMNAS FINALES
        # -----------------------------------------
        
        df_maquinas_view = df_maquinas[
            [
                "Organización",
                "Máquina",
                "Serie",
                "Hectáreas Picadas",
                "AutoTrac (%)",
                "Constituyentes (%)",
                "Estado HarvestLab"
            ]
        ].copy()
        
        # -----------------------------------------
        # TABLA
        # -----------------------------------------
        
        st.dataframe(
        
            df_maquinas_view.style.format(
                {
                    "Hectáreas Picadas": "{:,.0f}",
                    "AutoTrac (%)": "{:.1f}%",
                    "Constituyentes (%)": "{:.1f}%"
                }
            ),
        
            use_container_width=True
        
        )

        
        # ---------------------------------------------------
        # PIE CHARTS
        # ---------------------------------------------------
        
        st.markdown("---")
        st.subheader("Estado HarvestLab")
        
        col_p1, col_p2 = st.columns(2)
        
        # -----------------------------------------
        # PIE MAQUINAS
        # -----------------------------------------
        
        with col_p1:
        
            df_pie_maq = (
                df_maquinas
                .groupby("Estado HarvestLab")
                .size()
                .reset_index(name="Cantidad")
            )
        
            fig_maq = px.pie(
        
                df_pie_maq,
        
                names="Estado HarvestLab",
        
                values="Cantidad",
        
                title="Cantidad de Máquinas",
        
                hole=0.45
        
            )
        
            st.plotly_chart(
                fig_maq,
                use_container_width=True
            )
        
        # -----------------------------------------
        # PIE HECTAREAS
        # -----------------------------------------
        
        with col_p2:
        
            df_pie_ha = (
                df_maquinas
                .groupby("Estado HarvestLab")
                ["Hectáreas Picadas"]
                .sum()
                .reset_index()
            )
        
            fig_ha = px.pie(
        
                df_pie_ha,
        
                names="Estado HarvestLab",
        
                values="Hectáreas Picadas",
        
                title="Hectáreas Picadas",
        
                hole=0.45
        
            )
        
            st.plotly_chart(
                fig_ha,
                use_container_width=True
            )

        with subtab_hl_maiz:

            col_logo, col_titulo = st.columns([1, 14])

            with col_logo:
                st.image(
                    "HL_3000.png",
                    width=70
                )
        
            with col_titulo:
                st.subheader(
                    "Calidad de Forraje y Constituyentes"
                )
        
            # ---------------------------------------------------
            # BASE HARVESTLAB MAIZ
            # ---------------------------------------------------
            
            df_hl = df_maiz.copy()
            
            columnas_constituyentes_maiz = [
            
                "Almidón",
            
                "Proteína bruta",
            
                "Fibra detergente neutro",
            
                "Fibra detergente ácido",
            
                "Ceniza bruta"
            
            ]
            
            mask_harvestlab_maiz = (
            
                df_hl[columnas_constituyentes_maiz]
            
                .notna()
            
                .any(axis=1)
            
            )
            
            # Mantener solamente registros con HarvestLab
            
            df_hl = (
            
                df_hl[
                    mask_harvestlab_maiz
                ]
            
                .copy()
            
            )
            
            if df_hl.empty:
            
                st.warning(
                    "No existen registros de Maíz con constituyentes de HarvestLab para los filtros seleccionados."
                )
            
                st.stop()
            
                    
            # ---------------------------------------------------
            # CURVA DE CONSTITUYENTES
            # ---------------------------------------------------
        
            mask_curva = (
        
                df_hl["Almidón"].notna()
        
                |
        
                df_hl["Proteína bruta"].notna()
        
                |
        
                df_hl["Fibra detergente neutro"].notna()
        
                |
        
                df_hl["Fibra detergente ácido"].notna()
        
                |
        
                df_hl["Azúcar"].notna()
        
                |
        
                df_hl["Ceniza bruta"].notna()
        
            )
        
            # ---------------------------------------------------
            # KPIs
            # ---------------------------------------------------
        
            materia_seca = (
                df_hl["Materia seca"]
                .mean()
            )
        
            almidon = (
                df_hl["Almidón"]
                .mean()
            )
        
            proteina = (
                df_hl["Proteína bruta"]
                .mean()
            )
        
            porc_curva = (
                mask_curva.sum()
                /
                len(df_hl)
                * 100
                if len(df_hl) > 0
                else 0
            )
        
            k1, k2, k3, k4 = st.columns(4)
        
            k1.metric(
                "Materia Seca",
                f"{materia_seca:.1f}%"
            )
        
            k2.metric(
                "Almidón",
                f"{almidon:.1f}%"
            )
        
            k3.metric(
                "Proteína Bruta",
                f"{proteina:.1f}%"
            )
        
            k4.metric(
                "Curva Activa",
                f"{porc_curva:.1f}%"
            )
        
            # ---------------------------------------------------
            # EVOLUCIÓN HISTÓRICA
            # ---------------------------------------------------
        
            st.markdown("---")
            st.subheader(
                "Evolución Semanal de Calidad"
            )
        
            df_hist = (
        
                df_hl
        
                .groupby("Fecha_fin_dt")
        
                .agg(
        
                    MateriaSeca=(
                        "Materia seca",
                        "mean"
                    ),
        
                    Almidon=(
                        "Almidón",
                        "mean"
                    ),
        
                    Proteina=(
                        "Proteína bruta",
                        "mean"
                    )
        
                )
        
                .reset_index()
        
                .sort_values(
                    "Fecha_fin_dt"
                )
        
            )
        
            fig_hist = px.line(
        
                df_hist,
        
                x="Fecha_fin_dt",
        
                y=[
                    "MateriaSeca",
                    "Almidon",
                    "Proteina"
                ],
        
                markers=True,
        
                title="Evolución de Constituyentes"
        
            )
        
            fig_hist.update_layout(
                hovermode="x unified"
            )
        
            st.plotly_chart(
                fig_hist,
                use_container_width=True
            )
        
        
            # ---------------------------------------------------
            # SCORE DE CALIDAD
            # ---------------------------------------------------
            
            def estado_materia_seca(valor):

                if pd.isna(valor):
                    return "Sin datos"
            
                if 35 <= valor <= 40:
                    return "Excelente"
            
                if 32 <= valor < 35 or 40 < valor <= 43:
                    return "Atención"
            
                return "Crítico"
            
            
            def estado_almidon(valor):
            
                if pd.isna(valor):
                    return "Sin datos"
            
                if valor > 34:
                    return "Excelente"
            
                if 30 <= valor <= 34:
                    return "Atención"
            
                return "Crítico"
            
            
            def estado_proteina(valor):
            
                if pd.isna(valor):
                    return "Sin datos"
            
                if valor > 8:
                    return "Excelente"
            
                if 7 <= valor <= 8:
                    return "Atención"
            
                return "Crítico"
            
            
            def estado_fdn(valor):
            
                if pd.isna(valor):
                    return "Sin datos"
            
                if valor < 36:
                    return "Excelente"
            
                if 36 <= valor <= 40:
                    return "Atención"
            
                return "Crítico"
            
            
            def estado_fda(valor):
            
                if pd.isna(valor):
                    return "Sin datos"
            
                if valor < 21:
                    return "Excelente"
            
                if 21 <= valor <= 24:
                    return "Atención"
            
                return "Crítico"
            
            
            def estado_cenizas(valor):
            
                if pd.isna(valor):
                    return "Sin datos"
            
                if valor < 4.5:
                    return "Excelente"
            
                if 4.5 <= valor <= 6:
                    return "Atención"
            
                return "Crítico"
            
                        
            
            def calcular_score(fila):

                pesos = {
            
                    "Estado MS": 25,
            
                    "Estado Almidón": 25,
            
                    "Estado FDN": 15,
            
                    "Estado FDA": 15,
            
                    "Estado PB": 10,
            
                    "Estado Cenizas": 10
            
                }
            
                factores = {
            
                    "Excelente": 1.00,
            
                    "Atención": 0.70,
            
                    "Crítico": 0.30
            
                }
            
                puntos_obtenidos = 0
            
                peso_disponible = 0
            
                for variable, peso in pesos.items():
            
                    estado = fila.get(
                        variable,
                        "Sin datos"
                    )
            
                    if estado == "Sin datos":
                        continue
            
                    peso_disponible += peso
            
                    puntos_obtenidos += (
            
                        peso
            
                        *
            
                        factores.get(
                            estado,
                            0
                        )
            
                    )
            
                if peso_disponible == 0:
            
                    return np.nan
            
                score = (
            
                    puntos_obtenidos
            
                    /
            
                    peso_disponible
            
                    *
            
                    100
            
                )
            
                return round(
                    score,
                    1
                )


            
            
            def clasificar_score(score):

                if pd.isna(score):
            
                    return "⚪ Sin datos"
            
                if score >= 75:
            
                    return "🟢 Calidad Alta"
            
                if score >= 55:
            
                    return "🟡 Calidad Moderada"
            
                return "🔴 Calidad Crítica"
            
            # ---------------------------------------------------
            # TABLA BASE
            # ---------------------------------------------------
            
            df_tabla_hl = (
            
                df_hl
            
                .groupby(
                    [
                        "Organizaciones",
                        "Clientes",
                        "Granjas",
                        "Campos",
                        "Variedades",
                        "Equipo"
                    ],

                    as_index=False,
                    dropna=False
                )
            
                .agg(
                    Superficie=(
                        "Superficie cosechada",
                        "sum"
                    ),
            
                    MateriaSeca=(
                        "Materia seca",
                        "mean"
                    ),
            
                    Almidon=(
                        "Almidón",
                        "mean"
                    ),
            
                    Proteina=(
                        "Proteína bruta",
                        "mean"
                    ),
            
                    FDN=(
                        "Fibra detergente neutro",
                        "mean"
                    ),
            
                    FDA=(
                        "Fibra detergente ácido",
                        "mean"
                    ),
            
                    Azucar=(
                        "Azúcar",
                        "mean"
                    ),
            
                    Ceniza=(
                        "Ceniza bruta",
                        "mean"
                    ),
            
                    LargoCorte=(
                        "Largo de corte",
                        "mean"
                    )
                )
            
            )
            
            # ---------------------------------------------------
            # ESTADOS
            # ---------------------------------------------------
            
            df_tabla_hl["Estado MS"] = (
                df_tabla_hl["MateriaSeca"]
                .apply(estado_materia_seca)
            )
            
            df_tabla_hl["Estado Almidón"] = (
                df_tabla_hl["Almidon"]
                .apply(estado_almidon)
            )
            
            df_tabla_hl["Estado PB"] = (
                df_tabla_hl["Proteina"]
                .apply(estado_proteina)
            )
            
            df_tabla_hl["Estado FDN"] = (
                df_tabla_hl["FDN"]
                .apply(estado_fdn)
            )
            
            df_tabla_hl["Estado FDA"] = (
                df_tabla_hl["FDA"]
                .apply(estado_fda)
            )
            
            df_tabla_hl["Estado Cenizas"] = (
                df_tabla_hl["Ceniza"]
                .apply(estado_cenizas)
            )
            
            # ---------------------------------------------------
            # SCORE
            # ---------------------------------------------------
            
            df_tabla_hl["Score Calidad"] = (
                df_tabla_hl.apply(
                    calcular_score,
                    axis=1
                )
            )
            
            df_tabla_hl["Clasificación"] = (
                df_tabla_hl["Score Calidad"]
                .apply(clasificar_score)
            )

            score_promedio = df_tabla_hl["Score Calidad"].mean()

            # ---------------------------------------------------
            # RESUMEN DE CALIDAD
            # ---------------------------------------------------
            
            st.markdown("---")
            st.subheader("Resumen de Calidad del Forraje")
            
            col_res1, col_res2, col_res3 = st.columns(3)
            
            cant_alta = (
                df_tabla_hl["Clasificación"]
                .str.contains("Alta", na=False)
                .sum()
            )
            
            cant_media = (
                df_tabla_hl["Clasificación"]
                .str.contains("Moderada", na=False)
                .sum()
            )
            
            cant_baja = (
                df_tabla_hl["Clasificación"]
                .str.contains("Crítica", na=False)
                .sum()
            )
            
            col_res1.metric(
                "🟢 Calidad Alta",
                cant_alta
            )
            
            col_res2.metric(
                "🟡 Calidad Moderada",
                cant_media
            )
            
            col_res3.metric(
                "🔴 Calidad Crítica",
                cant_baja
            )
            
            # ---------------------------------------------------
            # PERFIL DE CALIDAD MAÍZ
            # ---------------------------------------------------
            
            perfil = pd.DataFrame({

                "Indicador": [
            
                    "Materia seca",
            
                    "Almidón",
            
                    "Proteína",
            
                    "FDN",
            
                    "FDA",
            
                    "Cenizas"
            
                ],
            
                "Actual": [
            
                    df_tabla_hl["MateriaSeca"].mean(),
            
                    df_tabla_hl["Almidon"].mean(),
            
                    df_tabla_hl["Proteina"].mean(),
            
                    df_tabla_hl["FDN"].mean(),
            
                    df_tabla_hl["FDA"].mean(),
            
                    df_tabla_hl["Ceniza"].mean()
            
                ],
            
                "Mínimo": [
            
                    35,
            
                    34,
            
                    8,
            
                    0,
            
                    0,
            
                    0
            
                ],
            
                "Máximo": [
            
                    40,
            
                    50,
            
                    12,
            
                    36,
            
                    21,
            
                    4.5
            
                ],
            
                "Objetivo": [
            
                    "35 - 40",
            
                    "> 34",
            
                    "> 8",
            
                    "< 36",
            
                    "< 21",
            
                    "< 4.5"
            
                ]
            
            })
            
                        
            # ---------------------------------------------------
            # RADAR
            # ---------------------------------------------------
            
            st.markdown("---")
            st.subheader("Radar de Calidad de Maíz")
            
            col_radar, col_tabla = st.columns([2,1])
            
            with col_tabla:
            
                st.markdown("##### 📋 Rango Objetivo")
            
                st.dataframe(
            
                    perfil[
                        [
                            "Indicador",
                            "Actual",
                            "Objetivo"
                        ]
                    ],
            
                    use_container_width=True,
                    hide_index=True
            
                )
            
            with col_radar:
            
                fig_radar = go.Figure()
            
                # -----------------------------------------
                # LIMITE SUPERIOR
                # -----------------------------------------
            
                fig_radar.add_trace(
            
                    go.Scatterpolar(
            
                        r=perfil["Máximo"],
            
                        theta=perfil["Indicador"],
            
                        fill="toself",
            
                        fillcolor="rgba(44,160,44,0.12)",
            
                        line=dict(
                            color="rgba(44,160,44,0.25)",
                            width=1
                        ),
            
                        name="Límite Superior"
            
                    )
            
                )
            
                # -----------------------------------------
                # LIMITE INFERIOR
                # -----------------------------------------
            
                fig_radar.add_trace(
            
                    go.Scatterpolar(
            
                        r=perfil["Mínimo"],
            
                        theta=perfil["Indicador"],
            
                        fill="toself",
            
                        fillcolor="rgba(44,160,44,0.30)",
            
                        line=dict(
                            color="rgba(44,160,44,0.50)",
                            width=1
                        ),
            
                        name="Límite Inferior"
            
                    )
            
                )
            
                # -----------------------------------------
                # VALOR ACTUAL
                # -----------------------------------------
            
                fig_radar.add_trace(
            
                    go.Scatterpolar(
            
                        r=perfil["Actual"],
            
                        theta=perfil["Indicador"],
            
                        mode="lines+markers",
            
                        line=dict(
                            color="#1f77b4",
                            width=4
                        ),
            
                        marker=dict(
                            size=8,
                            color="#1f77b4"
                        ),
            
                        name="Actual"
            
                    )
            
                )
            
                fig_radar.update_layout(
            
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)"
                    ),
            
                    paper_bgcolor="rgba(0,0,0,0)",
            
                    plot_bgcolor="rgba(0,0,0,0)",
            
                    showlegend=True,
            
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
            
                )
            
                st.plotly_chart(
                    fig_radar,
                    use_container_width=True
                )


            # ---------------------------------------------------
            # SCATTER MATERIA SECA x ALMIDÓN
            # ---------------------------------------------------
            
            st.markdown("---")
            st.subheader(
                "Relación Materia Seca × Almidón"
            )
            
            df_scatter = (
                df_tabla_hl.copy()
            )
            
            df_scatter = df_scatter.dropna(
                subset=[
                    "MateriaSeca",
                    "Almidon"
                ]
            )
            
            if not df_scatter.empty:
            
                fig_scatter = px.scatter(
            
                    df_scatter,
            
                    x="MateriaSeca",
            
                    y="Almidon",
            
                    color="Score Calidad",
            
                    size="Superficie",
            
                    hover_data=[
                        "Clientes",
                        "Granjas",
                        "Campos",
                        "Variedades"
                    ],
            
                    color_continuous_scale=[
                        "#d62728",
                        "#f2b134",
                        "#2ca02c"
                    ],
            
                    labels={
            
                        "MateriaSeca":
                            "Materia Seca (%)",
            
                        "Almidon":
                            "Almidón (%)",
            
                        "Score Calidad":
                            "Score"
            
                    },
            
                    title=(
                        "Materia Seca vs Almidón "
                        "coloreado por Score"
                    )
            
                )
            
                fig_scatter.add_vrect(
                    x0=32,
                    x1=36,
                    fillcolor="green",
                    opacity=0.08,
                    line_width=0
                )
            
                fig_scatter.add_hrect(
                    y0=32,
                    y1=38,
                    fillcolor="green",
                    opacity=0.08,
                    line_width=0
                )
            
                st.plotly_chart(
                    fig_scatter,
                    use_container_width=True
                )
            
            else:
            
                st.info(
                    "No existen registros con curva activa."
                )

            # ---------------------------------------------------
            # FILTROS TABLA
            # ---------------------------------------------------
            st.markdown("---")
            st.subheader(
                "Calidad de Forraje por Cliente, Granja y Campo"
            )
            
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            
            with col_f1:
            
                sel_clientes = st.multiselect(
                    "Cliente",
                    sorted(
                        df_tabla_hl["Clientes"]
                        .dropna()
                        .unique()
                    )
                )
            
            df_temp = df_tabla_hl.copy()
            
            if sel_clientes:
            
                df_temp = (
                    df_temp[
                        df_temp["Clientes"]
                        .isin(sel_clientes)
                    ]
                )
            
            with col_f2:
            
                sel_granjas = st.multiselect(
                    "Granja",
                    sorted(
                        df_temp["Granjas"]
                        .dropna()
                        .unique()
                    )
                )
            
            if sel_granjas:
            
                df_temp = (
                    df_temp[
                        df_temp["Granjas"]
                        .isin(sel_granjas)
                    ]
                )
            
            with col_f3:
            
                sel_campos = st.multiselect(
                    "Campo",
                    sorted(
                        df_temp["Campos"]
                        .dropna()
                        .unique()
                    )
                )

            with col_f4:
            
                opciones_calidad = sorted(
                    df_tabla_hl["Clasificación"]
                    .dropna()
                    .unique()
                )
            
                sel_calidad = st.multiselect(
                    "Calidad",
                    opciones_calidad
                )

            
            df_tabla_hl_filtrada = df_tabla_hl.copy()
            
            if sel_clientes:
            
                df_tabla_hl_filtrada = (
                    df_tabla_hl_filtrada[
                        df_tabla_hl_filtrada["Clientes"]
                        .isin(sel_clientes)
                    ]
                )
            
            if sel_granjas:
            
                df_tabla_hl_filtrada = (
                    df_tabla_hl_filtrada[
                        df_tabla_hl_filtrada["Granjas"]
                        .isin(sel_granjas)
                    ]
                )
            
            if sel_campos:
            
                df_tabla_hl_filtrada = (
                    df_tabla_hl_filtrada[
                        df_tabla_hl_filtrada["Campos"]
                        .isin(sel_campos)
                    ]
                )

            if sel_calidad:
            
                df_tabla_hl_filtrada = (
                    df_tabla_hl_filtrada[
                        df_tabla_hl_filtrada["Clasificación"]
                        .isin(sel_calidad)
                    ]
                )


            
            # ---------------------------------------------------
            # TABLA FINAL
            # ---------------------------------------------------
            
            df_tabla_hl_filtrada = (
            
                df_tabla_hl_filtrada
            
                .rename(
                    columns={
                        "Clientes": "Cliente",
                        "Granjas": "Granja",
                        "Campos": "Campo",
                        "Variedades": "Variedad",
                        "Superficie": "Superficie (ha)",
                        "MateriaSeca": "Materia Seca (%)",
                        "Almidon": "Almidón (%)",
                        "Proteina": "Proteína Bruta (%)",
                        "Ceniza": "Ceniza Bruta (%)"
                    }
                )
            
            )
            
            st.dataframe(
            
                df_tabla_hl_filtrada
                .sort_values(
                    "Score Calidad",
                    ascending=False
                )
                .style.format(
                    {
                        "Superficie (ha)": "{:,.1f}",
                        "Materia Seca (%)": "{:.1f}%",
                        "Almidón (%)": "{:.1f}%",
                        "Proteína Bruta (%)": "{:.1f}%",
                        "FDN": "{:.1f}%",
                        "FDA": "{:.1f}%",
                        "Ceniza Bruta (%)": "{:.1f}%",
                        "Score Calidad": "{:.0f}"
                    },
                    na_rep="N/D"
                ),
            
                use_container_width=True
            
            )

            # ---------------------------------------------------
            # RANKINGS DE CALIDAD
            # ---------------------------------------------------
            
            st.markdown("---")
            st.subheader("Rankings de Calidad de Forraje")
            
            df_rank_base = (
                df_tabla_hl
                .dropna(
                    subset=[
                        "Score Calidad",
                        "Superficie"
                    ]
                )
                .copy()
            )
            
            df_rank_base["Puntos ponderados"] = (
                df_rank_base["Score Calidad"]
                *
                df_rank_base["Superficie"]
            )
            
            col_rank_org, col_rank_cli = st.columns(2)
            
            # ---------------------------------------------------
            # ORGANIZACIONES
            # ---------------------------------------------------
            
            with col_rank_org:
            
                st.markdown(
                    "#### Organizaciones"
                )
            
                df_rank_org = (
            
                    df_rank_base
            
                    .dropna(
                        subset=["Organizaciones"]
                    )
            
                    .groupby(
                        "Organizaciones",
                        as_index=False
                    )
            
                    .agg(
            
                        PuntosPonderados=(
                            "Puntos ponderados",
                            "sum"
                        ),
            
                        Superficie=(
                            "Superficie",
                            "sum"
                        )
            
                    )
            
                )
            
                df_rank_org["Score"] = np.where(
            
                    df_rank_org["Superficie"] > 0,
            
                    df_rank_org["PuntosPonderados"]
                    /
                    df_rank_org["Superficie"],
            
                    np.nan
            
                )
            
                df_rank_org = (
            
                    df_rank_org
            
                    .sort_values(
                        "Score",
                        ascending=False
                    )
            
                    .head(15)
            
                )
            
                fig_rank_org = px.bar(

                    df_rank_org,
                
                    x="Score",
                
                    y="Organizaciones",
                
                    orientation="h",
                
                    color="Score",
                
                    text="Score",
                
                    color_continuous_scale=[
                        "#d62728",
                        "#f2b134",
                        "#2ca02c"
                    ],
                
                    title="Organizaciones con Mejor Calidad"
                
                )
                
                fig_rank_org.update_traces(
                
                    texttemplate="%{text:.1f}",
                
                    textposition="outside"
                
                )

            
                fig_rank_org.update_layout(
            
                    yaxis=dict(
                        categoryorder="total ascending"
                    )
            
                )
            
                st.plotly_chart(
                    fig_rank_org,
                    use_container_width=True
                )
            
            # ---------------------------------------------------
            # CLIENTES
            # ---------------------------------------------------
            
            with col_rank_cli:
            
                st.markdown(
                    "#### Clientes"
                )
            
                df_rank_cli = (
            
                    df_rank_base
            
                    .dropna(
                        subset=["Clientes"]
                    )
            
                    .groupby(
                        "Clientes",
                        as_index=False
                    )
            
                    .agg(
            
                        PuntosPonderados=(
                            "Puntos ponderados",
                            "sum"
                        ),
            
                        Superficie=(
                            "Superficie",
                            "sum"
                        )
            
                    )
            
                )
            
                df_rank_cli["Score"] = np.where(
            
                    df_rank_cli["Superficie"] > 0,
            
                    df_rank_cli["PuntosPonderados"]
                    /
                    df_rank_cli["Superficie"],
            
                    np.nan
            
                )
            
                df_rank_cli = (
            
                    df_rank_cli
            
                    .sort_values(
                        "Score",
                        ascending=False
                    )
            
                    .head(15)
            
                )
            
                fig_rank_cli = px.bar(

                    df_rank_cli,
                
                    x="Score",
                
                    y="Clientes",
                
                    orientation="h",
                
                    color="Score",
                
                    text="Score",
                
                    color_continuous_scale=[
                        "#d62728",
                        "#f2b134",
                        "#2ca02c"
                    ],
                
                    title="Clientes con Mejor Calidad"
                
                )
                
                fig_rank_cli.update_traces(
                
                    texttemplate="%{text:.1f}",
                
                    textposition="outside"
                
                )

            
                fig_rank_cli.update_layout(
            
                    yaxis=dict(
                        categoryorder="total ascending"
                    )
            
                )
            
                st.plotly_chart(
                    fig_rank_cli,
                    use_container_width=True
                )

            # ---------------------------------------------------
            # EQUIPOS (NÚMERO DE SERIE)
            # ---------------------------------------------------
            
            st.markdown("---")
            
            st.subheader(
                "Ranking de Equipos (Serie)"
            )
            
            df_rank_equipo = (
            
                df_rank_base
            
                .dropna(
                    subset=["Equipo"]
                )
            
                .groupby(
                    "Equipo",
                    as_index=False
                )
            
                .agg(
            
                    PuntosPonderados=(
                        "Puntos ponderados",
                        "sum"
                    ),
            
                    Superficie=(
                        "Superficie",
                        "sum"
                    )
            
                )
            
            )
            
            df_rank_equipo["Score"] = np.where(
            
                df_rank_equipo["Superficie"] > 0,
            
                df_rank_equipo["PuntosPonderados"]
            
                /
            
                df_rank_equipo["Superficie"],
            
                np.nan
            
            )
            
            df_rank_equipo = (
            
                df_rank_equipo
            
                .sort_values(
                    "Score",
                    ascending=False
                )
            
                .head(20)
            
            )
            
            fig_rank_equipo = px.bar(
            
                df_rank_equipo,
            
                x="Score",
            
                y="Equipo",
            
                orientation="h",
            
                color="Score",
            
                text="Score",
            
                color_continuous_scale=[
                    "#d62728",
                    "#f2b134",
                    "#2ca02c"
                ],
            
                title="Equipos con Mejor Calidad de Forraje"
            
            )
            
            fig_rank_equipo.update_traces(
            
                texttemplate="%{text:.1f}",
            
                textposition="outside"
            
            )
            
            fig_rank_equipo.update_layout(
            
                yaxis=dict(
                    categoryorder="total ascending"
                )
            
            )
            
            st.plotly_chart(
                fig_rank_equipo,
                use_container_width=True
            )



            # ---------------------------------------------------
            # REFERENCIA SCORE
            # ---------------------------------------------------
            
            with st.expander(
                "Cómo se calcula el Score de Calidad"
            ):
            
                st.markdown(
                    """
                    **Score ponderado de calidad de silaje de maíz**
            
                    Pesos:
            
                    - Materia seca: 25%
                    - Almidón: 25%
                    - FDN: 15%
                    - FDA: 15%
                    - Proteína bruta: 10%
                    - Cenizas: 10%
            
                    Aporte según estado:
            
                    - Excelente: 100% del peso
                    - Atención: 70% del peso
                    - Crítico: 30% del peso
                    - Sin datos: el parámetro se excluye
            
                    Clasificación final:
            
                    - 🟢 75 a 100 → Calidad Alta
                    - 🟡 55 a 74,9 → Calidad Moderada
                    - 🔴 Menos de 55 → Calidad Crítica
                    """
                )


    with subtab_hl_alfalfa:

        col_logo, col_titulo = st.columns([1, 14])
    
        with col_logo:
    
            st.image(
                "HL_3000.png",
                width=70
            )
    
        with col_titulo:
    
            st.subheader(
                "Calidad de Forraje - Alfalfa"
            )
    
        # ---------------------------------------------------
        # BASE HARVESTLAB ALFALFA
        # ---------------------------------------------------
        
        df_hl = df_alfalfa.copy()
        
        columnas_constituyentes_alfalfa = [
        
            "Proteína bruta",
        
            "Fibra detergente neutro",
        
            "Fibra detergente ácido",
        
            "Ceniza bruta"
        
        ]
        
        mask_harvestlab_alfalfa = (
        
            df_hl[columnas_constituyentes_alfalfa]
        
            .notna()
        
            .any(axis=1)
        
        )
        
        # Cobertura
        
        registros_totales_alfalfa = len(df_hl)
        
        registros_harvestlab_alfalfa = int(
            mask_harvestlab_alfalfa.sum()
        )
        
        registros_sin_harvestlab_alfalfa = int(
            (~mask_harvestlab_alfalfa).sum()
        )
        
        porc_harvestlab_alfalfa = (
        
            registros_harvestlab_alfalfa
        
            /
        
            registros_totales_alfalfa
        
            *
        
            100
        
            if registros_totales_alfalfa > 0
        
            else 0
        
        )
        
        # Mantener únicamente registros
        # con datos reales de HarvestLab
        
        df_hl = (
        
            df_hl[
                mask_harvestlab_alfalfa
            ]
        
            .copy()
        
        )
        
        if df_hl.empty:
        
            st.warning(
                "No existen registros de Alfalfa con constituyentes de HarvestLab para los filtros seleccionados."
            )
        
            st.stop()

    
        # ---------------------------------------------------
        # KPIs
        # ---------------------------------------------------
    
        materia_seca = (
            df_hl["Materia seca"]
            .mean()
        )
    
        proteina = (
            df_hl["Proteína bruta"]
            .mean()
        )
    
        fdn = (
            df_hl["Fibra detergente neutro"]
            .mean()
        )
    
        fda = (
            df_hl["Fibra detergente ácido"]
            .mean()
        )
    
        cenizas = (
            df_hl["Ceniza bruta"]
            .mean()
        )
    
        k1, k2, k3, k4, k5 = st.columns(5)
    
        k1.metric(
            "Materia Seca",
            f"{materia_seca:.1f}%"
        )
    
        k2.metric(
            "Proteína Bruta",
            f"{proteina:.1f}%"
        )
    
        k3.metric(
            "FDN",
            f"{fdn:.1f}%"
        )
    
        k4.metric(
            "FDA",
            f"{fda:.1f}%"
        )
    
        k5.metric(
            "Cenizas",
            f"{cenizas:.1f}%"
        )

        # ---------------------------------------------------
        # EVOLUCIÓN HISTÓRICA
        # ---------------------------------------------------
        
        st.markdown("---")
        st.subheader(
            "Evolución Semanal de Calidad"
        )
        
        df_hist = (
        
            df_hl
        
            .groupby("Fecha_fin_dt")
        
            .agg(
        
                MateriaSeca=(
                    "Materia seca",
                    "mean"
                ),
        
                Proteina=(
                    "Proteína bruta",
                    "mean"
                ),
        
                FDN=(
                    "Fibra detergente neutro",
                    "mean"
                ),
        
                FDA=(
                    "Fibra detergente ácido",
                    "mean"
                )
        
            )
        
            .reset_index()
        
            .sort_values(
                "Fecha_fin_dt"
            )
        
        )
        
        fig_hist = px.line(
        
            df_hist,
        
            x="Fecha_fin_dt",
        
            y=[
                "MateriaSeca",
                "Proteina",
                "FDN",
                "FDA"
            ],
        
            markers=True,
        
            title="Evolución de Calidad de Alfalfa"
        
        )
        
        fig_hist.update_layout(
            hovermode="x unified"
        )
        
        st.plotly_chart(
            fig_hist,
            use_container_width=True
        )


        # ---------------------------------------------------
        # ESTADOS DE CALIDAD ALFALFA
        # ---------------------------------------------------
        
        def estado_materia_seca_alfalfa(valor):
        
            if pd.isna(valor):
                return "Sin datos"
        
            if 35 <= valor <= 45:
                return "Excelente"
        
            if 30 <= valor < 35 or 45 < valor <= 50:
                return "Atención"
        
            return "Crítico"
        
        
        def estado_proteina_alfalfa(valor):
        
            if pd.isna(valor):
                return "Sin datos"
        
            if valor > 23:
                return "Excelente"
        
            if 20 <= valor <= 23:
                return "Atención"
        
            return "Crítico"
        
        
        def estado_fdn_alfalfa(valor):
        
            if pd.isna(valor):
                return "Sin datos"
        
            if valor < 40:
                return "Excelente"
        
            if 40 <= valor <= 45:
                return "Atención"
        
            return "Crítico"
        
        
        def estado_fda_alfalfa(valor):
        
            if pd.isna(valor):
                return "Sin datos"
        
            if valor < 30:
                return "Excelente"
        
            if 30 <= valor <= 35:
                return "Atención"
        
            return "Crítico"
        
        
        def estado_cenizas_alfalfa(valor):
        
            if pd.isna(valor):
                return "Sin datos"
        
            if valor < 10:
                return "Excelente"
        
            if 10 <= valor <= 12:
                return "Atención"
        
            return "Crítico"
        
        
        # ---------------------------------------------------
        # TABLA BASE
        # ---------------------------------------------------
        
        df_tabla_hl = (
        
            df_hl
        
            .groupby(
                [
                    "Organizaciones",
                    "Clientes",
                    "Granjas",
                    "Campos",
                    "Variedades",
                    "Equipo"
                ],
                as_index=False,
                dropna=False
            )
        
            .agg(
        
                Superficie=(
                    "Superficie cosechada",
                    "sum"
                ),
        
                MateriaSeca=(
                    "Materia seca",
                    "mean"
                ),
        
                Proteina=(
                    "Proteína bruta",
                    "mean"
                ),
        
                FDN=(
                    "Fibra detergente neutro",
                    "mean"
                ),
        
                FDA=(
                    "Fibra detergente ácido",
                    "mean"
                ),
        
                Ceniza=(
                    "Ceniza bruta",
                    "mean"
                )
        
            )
        
        )
        
        # ---------------------------------------------------
        # ESTADOS
        # ---------------------------------------------------
        
        df_tabla_hl["Estado MS"] = (
            df_tabla_hl["MateriaSeca"]
            .apply(estado_materia_seca_alfalfa)
        )
        
        df_tabla_hl["Estado PB"] = (
            df_tabla_hl["Proteina"]
            .apply(estado_proteina_alfalfa)
        )
        
        df_tabla_hl["Estado FDN"] = (
            df_tabla_hl["FDN"]
            .apply(estado_fdn_alfalfa)
        )
        
        df_tabla_hl["Estado FDA"] = (
            df_tabla_hl["FDA"]
            .apply(estado_fda_alfalfa)
        )
        
        df_tabla_hl["Estado Cenizas"] = (
            df_tabla_hl["Ceniza"]
            .apply(estado_cenizas_alfalfa)
        )
        
        # ---------------------------------------------------
        # SCORE ALFALFA
        # ---------------------------------------------------
        
        def calcular_score_alfalfa(fila):
        
            pesos = {
        
                "Estado MS": 25,
        
                "Estado PB": 30,
        
                "Estado FDN": 10,
        
                "Estado FDA": 15,
        
                "Estado Cenizas": 20
        
            }
        
            factores = {
        
                "Excelente": 1.00,
        
                "Atención": 0.70,
        
                "Crítico": 0.30
        
            }
        
            puntos = 0
            pesos_usados = 0
        
            for variable, peso in pesos.items():
        
                estado = fila.get(variable)
        
                if estado == "Sin datos":
                    continue
        
                pesos_usados += peso
        
                puntos += (
                    peso
                    *
                    factores.get(estado, 0)
                )
        
            if pesos_usados == 0:
                return np.nan
        
            return round(
                puntos
                /
                pesos_usados
                * 100,
                1
            )
        
        
        def clasificar_score_alfalfa(score):
        
            if pd.isna(score):
                return "⚪ Sin datos"
        
            if score >= 75:
                return "🟢 Calidad Alta"
        
            if score >= 55:
                return "🟡 Calidad Moderada"
        
            return "🔴 Calidad Crítica"
        
        
        df_tabla_hl["Score Calidad"] = (
            df_tabla_hl.apply(
                calcular_score_alfalfa,
                axis=1
            )
        )
        
        df_tabla_hl["Clasificación"] = (
            df_tabla_hl["Score Calidad"]
            .apply(clasificar_score_alfalfa)
        )

        # ---------------------------------------------------
        # RESUMEN DE CALIDAD
        # ---------------------------------------------------
        
        st.markdown("---")
        st.subheader("Resumen de Calidad de Alfalfa")
        
        score_promedio = (
            df_tabla_hl["Score Calidad"]
            .mean()
        )
        
        cant_alta = (
            df_tabla_hl["Clasificación"]
            .str.contains("Alta", na=False)
            .sum()
        )
        
        cant_media = (
            df_tabla_hl["Clasificación"]
            .str.contains("Moderada", na=False)
            .sum()
        )
        
        cant_baja = (
            df_tabla_hl["Clasificación"]
            .str.contains("Crítica", na=False)
            .sum()
        )
        
        c1, c2, c3, c4 = st.columns(4)
        
        c1.metric("🟢 Calidad Alta", cant_alta)
        c2.metric("🟡 Calidad Moderada", cant_media)
        c3.metric("🔴 Calidad Crítica", cant_baja)
        c4.metric("🎯 Score Promedio", f"{score_promedio:.1f}")
        
        # ---------------------------------------------------
        # PERFIL ALFALFA
        # ---------------------------------------------------
        
        perfil = pd.DataFrame({
        
            "Indicador": [
        
                "Materia seca",
        
                "Proteína",
        
                "FDN",
        
                "FDA",
        
                "Cenizas"
        
            ],
        
            "Actual": [
        
                df_tabla_hl["MateriaSeca"].mean(),
        
                df_tabla_hl["Proteina"].mean(),
        
                df_tabla_hl["FDN"].mean(),
        
                df_tabla_hl["FDA"].mean(),
        
                df_tabla_hl["Ceniza"].mean()
        
            ],
        
            "Mínimo": [
        
                35,
                23,
                0,
                0,
                0
        
            ],
        
            "Máximo": [
        
                45,
                40,
                40,
                30,
                10
        
            ],
        
            "Objetivo": [
        
                "35 - 45",
        
                "> 23",
        
                "< 40",
        
                "< 30",
        
                "< 10"
        
            ]
        
        })
        
        # ---------------------------------------------------
        # RADAR
        # ---------------------------------------------------
        
        st.markdown("---")
        st.subheader("Radar de Calidad de Alfalfa")
        
        col_radar, col_tabla = st.columns([2,1])
        
        with col_tabla:
        
            st.markdown("##### Rango Objetivo")
        
            st.dataframe(
        
                perfil[
                    [
                        "Indicador",
                        "Actual",
                        "Objetivo"
                    ]
                ],
        
                use_container_width=True,
                hide_index=True
        
            )
        
        with col_radar:
        
            fig_radar = go.Figure()
        
            fig_radar.add_trace(
        
                go.Scatterpolar(
        
                    r=perfil["Máximo"],
        
                    theta=perfil["Indicador"],
        
                    fill="toself",
        
                    fillcolor="rgba(44,160,44,0.12)",
        
                    line=dict(
                        color="rgba(44,160,44,0.25)",
                        width=1
                    ),
        
                    name="Límite Superior"
        
                )
        
            )
        
            fig_radar.add_trace(
        
                go.Scatterpolar(
        
                    r=perfil["Mínimo"],
        
                    theta=perfil["Indicador"],
        
                    fill="toself",
        
                    fillcolor="rgba(44,160,44,0.30)",
        
                    line=dict(
                        color="rgba(44,160,44,0.5)",
                        width=1
                    ),
        
                    name="Límite Inferior"
        
                )
        
            )
        
            fig_radar.add_trace(
        
                go.Scatterpolar(
        
                    r=perfil["Actual"],
        
                    theta=perfil["Indicador"],
        
                    mode="lines+markers",
        
                    line=dict(
                        color="#1f77b4",
                        width=4
                    ),
        
                    marker=dict(
                        size=8,
                        color="#1f77b4"
                    ),
        
                    name="Actual"
        
                )
        
            )
        
            fig_radar.update_layout(
        
                polar=dict(
                    bgcolor="rgba(0,0,0,0)"
                ),
        
                paper_bgcolor="rgba(0,0,0,0)",
        
                plot_bgcolor="rgba(0,0,0,0)",
        
                showlegend=True
        
            )
        
            st.plotly_chart(
                fig_radar,
                use_container_width=True
            )
        
        # ---------------------------------------------------
        # FILTROS TABLA
        # ---------------------------------------------------
        
        st.markdown("---")
        st.subheader(
            "Calidad de Alfalfa por Cliente, Granja y Campo"
        )
        
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
        
            sel_clientes_alf = st.multiselect(
                "Cliente",
                sorted(
                    df_tabla_hl["Clientes"]
                    .dropna()
                    .unique()
                ),
                key="alfalfa_cliente"
            )
        
        df_temp = df_tabla_hl.copy()
        
        if sel_clientes_alf:
        
            df_temp = (
                df_temp[
                    df_temp["Clientes"]
                    .isin(sel_clientes_alf)
                ]
            )
        
        with col_f2:
        
            sel_granjas_alf = st.multiselect(
                "Granja",
                sorted(
                    df_temp["Granjas"]
                    .dropna()
                    .unique()
                ),
                key="alfalfa_granja"
            )
        
        if sel_granjas_alf:
        
            df_temp = (
                df_temp[
                    df_temp["Granjas"]
                    .isin(sel_granjas_alf)
                ]
            )
        
        with col_f3:
        
            sel_campos_alf = st.multiselect(
                "Campo",
                sorted(
                    df_temp["Campos"]
                    .dropna()
                    .unique()
                ),
                key="alfalfa_campo"
            )
        
        with col_f4:
        
            opciones_calidad_alf = sorted(
                df_tabla_hl["Clasificación"]
                .dropna()
                .unique()
            )
        
            sel_calidad_alf = st.multiselect(
                "Calidad",
                opciones_calidad_alf,
                key="alfalfa_calidad"
            )
        
        # ---------------------------------------------------
        # APLICAR FILTROS
        # ---------------------------------------------------
        
        df_tabla_hl_filtrada = df_tabla_hl.copy()
        
        if sel_clientes_alf:
        
            df_tabla_hl_filtrada = (
                df_tabla_hl_filtrada[
                    df_tabla_hl_filtrada["Clientes"]
                    .isin(sel_clientes_alf)
                ]
            )
        
        if sel_granjas_alf:
        
            df_tabla_hl_filtrada = (
                df_tabla_hl_filtrada[
                    df_tabla_hl_filtrada["Granjas"]
                    .isin(sel_granjas_alf)
                ]
            )
        
        if sel_campos_alf:
        
            df_tabla_hl_filtrada = (
                df_tabla_hl_filtrada[
                    df_tabla_hl_filtrada["Campos"]
                    .isin(sel_campos_alf)
                ]
            )
        
        if sel_calidad_alf:
        
            df_tabla_hl_filtrada = (
                df_tabla_hl_filtrada[
                    df_tabla_hl_filtrada["Clasificación"]
                    .isin(sel_calidad_alf)
                ]
            )
        
        # ---------------------------------------------------
        # TABLA FINAL
        # ---------------------------------------------------
        
        df_tabla_hl_filtrada = (
        
            df_tabla_hl_filtrada
        
            .rename(
                columns={
                    "Organizaciones": "Organización",
                    "Clientes": "Cliente",
                    "Granjas": "Granja",
                    "Campos": "Campo",
                    "Variedades": "Variedad",
                    "Superficie": "Superficie (ha)",
                    "MateriaSeca": "Materia Seca (%)",
                    "Proteina": "Proteína Bruta (%)",
                    "FDN": "FDN (%)",
                    "FDA": "FDA (%)",
                    "Ceniza": "Ceniza Bruta (%)"
                }
            )
        
        )
        
        st.dataframe(
        
            df_tabla_hl_filtrada
        
            .sort_values(
                "Score Calidad",
                ascending=False
            )
        
            .style.format(
                {
        
                    "Superficie (ha)": "{:,.1f}",
        
                    "Materia Seca (%)": "{:.1f}%",
        
                    "Proteína Bruta (%)": "{:.1f}%",
        
                    "FDN (%)": "{:.1f}%",
        
                    "FDA (%)": "{:.1f}%",
        
                    "Ceniza Bruta (%)": "{:.1f}%",
        
                    "Score Calidad": "{:.1f}"
        
                },
                na_rep="N/D"
            ),
        
            use_container_width=True
        
        )

        # ---------------------------------------------------
        # RANKINGS DE CALIDAD
        # ---------------------------------------------------
        
        st.markdown("---")
        st.subheader("Rankings de Calidad de Alfalfa")
        
        df_rank_base = (
        
            df_tabla_hl
        
            .dropna(
                subset=[
                    "Score Calidad",
                    "Superficie"
                ]
            )
        
            .copy()
        
        )
        
        df_rank_base["Puntos ponderados"] = (
        
            df_rank_base["Score Calidad"]
        
            *
        
            df_rank_base["Superficie"]
        
        )
        
        col_rank_org, col_rank_cli = st.columns(2)
        
        # ---------------------------------------------------
        # ORGANIZACIONES
        # ---------------------------------------------------
        
        with col_rank_org:
        
            st.markdown(
                "#### Organizaciones"
            )
        
            df_rank_org = (
        
                df_rank_base
        
                .dropna(
                    subset=["Organizaciones"]
                )
        
                .groupby(
                    "Organizaciones",
                    as_index=False
                )
        
                .agg(
        
                    PuntosPonderados=(
                        "Puntos ponderados",
                        "sum"
                    ),
        
                    Superficie=(
                        "Superficie",
                        "sum"
                    ),
        
                    Registros=(
                        "Score Calidad",
                        "count"
                    )
        
                )
        
            )
        
            df_rank_org["Score"] = np.where(
        
                df_rank_org["Superficie"] > 0,
        
                df_rank_org["PuntosPonderados"]
        
                /
        
                df_rank_org["Superficie"],
        
                np.nan
        
            )
        
            df_rank_org = (
        
                df_rank_org
        
                .sort_values(
                    "Score",
                    ascending=False
                )
        
                .head(15)
        
            )
        
            fig_rank_org = px.bar(
        
                df_rank_org,
        
                x="Score",
        
                y="Organizaciones",
        
                orientation="h",
        
                color="Score",
        
                text="Score",
        
                color_continuous_scale=[
                    "#d62728",
                    "#f2b134",
                    "#2ca02c"
                ],
        
                title="Organizaciones con Mejor Calidad"
        
            )
        
            fig_rank_org.update_traces(
        
                texttemplate="%{text:.1f}",
        
                textposition="outside"
        
            )
        
            fig_rank_org.update_layout(
        
                yaxis=dict(
                    categoryorder="total ascending"
                )
        
            )
        
            st.plotly_chart(
                fig_rank_org,
                use_container_width=True
            )
        
        # ---------------------------------------------------
        # CLIENTES
        # ---------------------------------------------------
        
        with col_rank_cli:
        
            st.markdown(
                "#### Clientes"
            )
        
            df_rank_cli = (
        
                df_rank_base
        
                .dropna(
                    subset=["Clientes"]
                )
        
                .groupby(
                    "Clientes",
                    as_index=False
                )
        
                .agg(
        
                    PuntosPonderados=(
                        "Puntos ponderados",
                        "sum"
                    ),
        
                    Superficie=(
                        "Superficie",
                        "sum"
                    ),
        
                    Registros=(
                        "Score Calidad",
                        "count"
                    )
        
                )
        
            )
        
            df_rank_cli["Score"] = np.where(
        
                df_rank_cli["Superficie"] > 0,
        
                df_rank_cli["PuntosPonderados"]
        
                /
        
                df_rank_cli["Superficie"],
        
                np.nan
        
            )
        
            df_rank_cli = (
        
                df_rank_cli
        
                .sort_values(
                    "Score",
                    ascending=False
                )
        
                .head(15)
        
            )
        
            fig_rank_cli = px.bar(
        
                df_rank_cli,
        
                x="Score",
        
                y="Clientes",
        
                orientation="h",
        
                color="Score",
        
                text="Score",
        
                color_continuous_scale=[
                    "#d62728",
                    "#f2b134",
                    "#2ca02c"
                ],
        
                title="Clientes con Mejor Calidad"
        
            )
        
            fig_rank_cli.update_traces(
        
                texttemplate="%{text:.1f}",
        
                textposition="outside"
        
            )
        
            fig_rank_cli.update_layout(
        
                yaxis=dict(
                    categoryorder="total ascending"
                )
        
            )
        
            st.plotly_chart(
                fig_rank_cli,
                use_container_width=True
            )

        # ---------------------------------------------------
        # EQUIPOS (NÚMERO DE SERIE)
        # ---------------------------------------------------
        
        st.markdown("---")
        
        st.subheader(
            "Ranking de Equipos (Serie)"
        )
        
        df_rank_equipo = (
        
            df_rank_base
        
            .dropna(
                subset=["Equipo"]
            )
        
            .groupby(
                "Equipo",
                as_index=False
            )
        
            .agg(
        
                PuntosPonderados=(
                    "Puntos ponderados",
                    "sum"
                ),
        
                Superficie=(
                    "Superficie",
                    "sum"
                )
        
            )
        
        )
        
        df_rank_equipo["Score"] = np.where(
        
            df_rank_equipo["Superficie"] > 0,
        
            df_rank_equipo["PuntosPonderados"]
        
            /
        
            df_rank_equipo["Superficie"],
        
            np.nan
        
        )
        
        df_rank_equipo = (
        
            df_rank_equipo
        
            .sort_values(
                "Score",
                ascending=False
            )
        
            .head(20)
        
        )
        
        fig_rank_equipo = px.bar(
        
            df_rank_equipo,
        
            x="Score",
        
            y="Equipo",
        
            orientation="h",
        
            color="Score",
        
            text="Score",
        
            color_continuous_scale=[
                "#d62728",
                "#f2b134",
                "#2ca02c"
            ],
        
            title="Equipos con Mejor Calidad de Forraje"
        
        )
        
        fig_rank_equipo.update_traces(
        
            texttemplate="%{text:.1f}",
        
            textposition="outside"
        
        )
        
        fig_rank_equipo.update_layout(
        
            yaxis=dict(
                categoryorder="total ascending"
            )
        
        )
        
        st.plotly_chart(
            fig_rank_equipo,
            use_container_width=True
        )
        
        
            
