import io
import re

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# =========================================================
# CONFIGURACIÓN DE LA PÁGINA
# =========================================================

st.set_page_config(
    page_title="Gestión de Licencias",
    page_icon="🔑",
    layout="wide"
)

HISTORICO_PATH = "datos_licencias_clientes.csv"
ESTADOS_ACTIVOS = {
    "Vigente",
    "Vence en 30 días",
    "Vence en 60 días",
    "Vence en 90 días"
}

# =========================================================
# FUNCIONES AUXILIARES
# =========================================================


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def normalizar_licencia_admin(valor):
    """Quita el prefijo administrativo sin perder el producto licenciado."""
    texto = normalizar_texto(valor)
    texto = re.sub(
        r"^(NUEVO|RENOVAR|RENOVACIÓN|ACTUALIZACIÓN)\s*-\s*",
        "",
        texto,
        flags=re.IGNORECASE
    )
    return texto.strip()


def cargar_config_github():
    try:
        return (
            st.secrets["github"]["repo"],
            st.secrets["github"]["token"]
        )
    except Exception:
        return None, None


@st.cache_data(ttl=300, show_spinner=False)
def cargar_base_licencias(repo, token, path):
    if not repo or not token:
        return pd.DataFrame()

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.raw+json"
    }

    respuesta = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    if respuesta.status_code == 404:
        return pd.DataFrame()

    respuesta.raise_for_status()

    return pd.read_csv(
        io.StringIO(respuesta.text),
        low_memory=False
    )


def preparar_foto_actual(df):
    """
    Construye la foto vigente más reciente.

    Regla principal para Control administrativo:
    - Agrupa por componente + licencia normalizada.
    - Si existe un registro actualmente activo, descarta los históricos vencidos.
    - Si no existe ninguno activo, conserva el registro de vencimiento más reciente.

    Para Operations Center conserva una fila por licencia/componente en la última foto.
    """
    base = df.copy()

    columnas_fecha = [
        "Fecha de Actualización",
        "Fecha de Carga",
        "Fecha Inicio Licencia",
        "Fecha Vencimiento"
    ]

    for columna in columnas_fecha:
        if columna in base.columns:
            base[columna] = pd.to_datetime(
                base[columna],
                format="mixed",
                dayfirst=True,
                errors="coerce"
            )

    base["Días para Vencer"] = pd.to_numeric(
        base.get("Días para Vencer"),
        errors="coerce"
    )

    ultima_actualizacion = base["Fecha de Actualización"].max()
    foto = base[
        base["Fecha de Actualización"].eq(ultima_actualizacion)
    ].copy()

    foto["Licencia Normalizada"] = np.where(
        foto["Fuente"].eq("Control administrativo"),
        foto["Nombre Licencia"].apply(normalizar_licencia_admin),
        foto["Nombre Licencia"].fillna("").astype(str).str.strip()
    )

    # Evita claves vacías y mantiene trazabilidad de registros sin componente resuelto.
    foto["Clave Componente Dashboard"] = (
        foto["Clave Componente"]
        .fillna(foto["Serie Componente"])
        .fillna(foto["Serie Asignada Licencia"])
    )
    
    # Para los que siguen vacíos
    mask_sin_clave = foto["Clave Componente Dashboard"].isna()
    
    foto.loc[
        mask_sin_clave,
        "Clave Componente Dashboard"
    ] = (
        "SIN_COMPONENTE_"
        + foto.loc[mask_sin_clave]
        .index.astype(str)
    )
    
    foto["Clave Componente Dashboard"] = (
        foto["Clave Componente Dashboard"]
        .astype(str)
        .str.strip()
    )


    foto["Es activa"] = foto["Estado Licencia"].isin(ESTADOS_ACTIVOS)

    admin = foto[
        foto["Fuente"].eq("Control administrativo")
    ].copy()

    operations = foto[
        foto["Fuente"].eq("Operations Center")
    ].copy()

    if not admin.empty:
        claves_admin = [
            "Clave Componente Dashboard",
            "Licencia Normalizada"
        ]

        # Activas primero; dentro del mismo estado, vence más tarde primero.
        admin = admin.sort_values(
            [
                "Es activa",
                "Fecha Vencimiento",
                "Fecha Inicio Licencia",
                "Fecha de Carga"
            ],
            ascending=[False, False, False, False],
            na_position="last"
        )

        admin = admin.drop_duplicates(
            subset=claves_admin,
            keep="first"
        )

    if not operations.empty:
        operations["Clave OC Dashboard"] = (
            operations["Número Licencia"]
            .fillna(operations["Clave Licencia"])
            .fillna(operations["Licencia Normalizada"])
            .astype(str)
            .str.strip()
        )

        operations = operations.sort_values(
            [
                "Fecha Vencimiento",
                "Fecha Inicio Licencia",
                "Fecha de Carga"
            ],
            ascending=[False, False, False],
            na_position="last"
        )

        operations = operations.drop_duplicates(
            subset=[
                "Clave Componente Dashboard",
                "Clave OC Dashboard"
            ],
            keep="first"
        )

    actual = pd.concat(
        [operations, admin],
        ignore_index=True,
        sort=False
    )

    return actual, ultima_actualizacion


def opciones_ordenadas(serie):
    return sorted(
        serie.dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique()
    )


# =========================================================
# CARGA DE DATOS
# =========================================================

repo, token = cargar_config_github()

df_licencias = pd.DataFrame()
error_carga = None

try:
    df_licencias = cargar_base_licencias(
        repo,
        token,
        HISTORICO_PATH
    )
except Exception as error:
    error_carga = error

if error_carga is not None:
    st.error(f"No se pudo leer la base de licencias: {error_carga}")
    st.stop()

if df_licencias.empty:
    st.warning(
        "No se encontró información de licencias. "
        "Configurá GitHub o cargá datos_licencias_clientes.csv desde el sidebar."
    )
    st.stop()

columnas_requeridas = [
    "Fecha de Actualización",
    "Sucursal",
    "Organización",
    "Tipo Máquina",
    "Modelo Máquina",
    "Nombre Licencia",
    "Estado Licencia",
    "Fuente",
    "Clave Componente",
    "Fecha Vencimiento"
]

faltantes = [
    columna
    for columna in columnas_requeridas
    if columna not in df_licencias.columns
]

if faltantes:
    st.error(
        "La base no contiene las columnas necesarias: "
        + ", ".join(faltantes)
    )
    st.stop()

foto_actual, fecha_actualizacion = preparar_foto_actual(df_licencias)

# =========================================================
# SIDEBAR DE FILTROS
# =========================================================

with st.sidebar:
    st.markdown("---")
    st.markdown("### Filtros")

    excluir_conci = st.checkbox(
        "Excluir datos de CONCI",
        value=True
    )

    base_filtros = foto_actual.copy()

    if excluir_conci:
        base_filtros = base_filtros[
            ~base_filtros["Organización"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.contains("CONCI", na=False)
        ].copy()

    filtro_sucursal = st.multiselect(
        "Sucursal",
        opciones_ordenadas(base_filtros["Sucursal"])
    )

    if filtro_sucursal:
        base_filtros = base_filtros[
            base_filtros["Sucursal"].isin(filtro_sucursal)
        ].copy()

    filtro_tipo_maquina = st.multiselect(
        "Tipo de máquina",
        opciones_ordenadas(base_filtros["Tipo Máquina"])
    )

    if filtro_tipo_maquina:
        base_filtros = base_filtros[
            base_filtros["Tipo Máquina"].isin(filtro_tipo_maquina)
        ].copy()

    filtro_modelo = st.multiselect(
        "Modelo",
        opciones_ordenadas(base_filtros["Modelo Máquina"])
    )

    if filtro_modelo:
        base_filtros = base_filtros[
            base_filtros["Modelo Máquina"].isin(filtro_modelo)
        ].copy()

    filtro_licencia = st.multiselect(
        "Licencia",
        opciones_ordenadas(base_filtros["Licencia Normalizada"])
    )

    if filtro_licencia:
        base_filtros = base_filtros[
            base_filtros["Licencia Normalizada"].isin(filtro_licencia)
        ].copy()

    filtro_estado = st.multiselect(
        "Estado de licencia",
        opciones_ordenadas(base_filtros["Estado Licencia"])
    )

    if filtro_estado:
        base_filtros = base_filtros[
            base_filtros["Estado Licencia"].isin(filtro_estado)
        ].copy()

    if st.button("Limpiar filtros", use_container_width=True):
        st.rerun()

# El dataframe ya quedó filtrado en cascada dentro del sidebar.
df_filtrado = base_filtros.copy()

# =========================================================
# ENCABEZADO
# =========================================================

col_icono, col_titulo = st.columns([1, 12])

with col_icono:
    st.markdown("# 🔑")

with col_titulo:
    st.title("Gestión de Licencias")
    fecha_texto = (
        fecha_actualizacion.strftime("%d/%m/%Y")
        if pd.notna(fecha_actualizacion)
        else "Sin fecha"
    )
    st.caption(f"Foto actual de licencias · Última actualización: {fecha_texto}")

# =========================================================
# KPIs
# =========================================================

activas = df_filtrado["Estado Licencia"].eq("Vigente").sum()
vence_30 = df_filtrado["Estado Licencia"].eq("Vence en 30 días").sum()
vence_60 = df_filtrado["Estado Licencia"].eq("Vence en 60 días").sum()
vence_90 = df_filtrado["Estado Licencia"].eq("Vence en 90 días").sum()
vencidas = df_filtrado["Estado Licencia"].eq("Vencida").sum()
no_activadas = df_filtrado["Estado Licencia"].eq("No activada").sum()

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("🔑 Vigentes", f"{activas:,}")
k2.metric("⚠️ Vencen ≤ 30 días", f"{vence_30:,}")
k3.metric("🟠 Vencen 31–60 días", f"{vence_60:,}")
k4.metric("🟡 Vencen 61–90 días", f"{vence_90:,}")
k5.metric("🔴 Vencidas", f"{vencidas:,}")
k6.metric("⚪ No activadas", f"{no_activadas:,}")

st.caption(
    f"Registros mostrados: {len(df_filtrado):,} · "
    f"Componentes: {df_filtrado['Clave Componente Dashboard'].nunique():,}"
)

# =========================================================
# GRÁFICOS
# =========================================================

st.markdown("---")
col_grafico_1, col_grafico_2 = st.columns([2, 1])

with col_grafico_1:
    st.subheader("📅 Vencimientos por mes")

    df_vencimientos = df_filtrado[
        df_filtrado["Fecha Vencimiento"].notna()
    ].copy()

    df_vencimientos["Mes Vencimiento"] = (
        df_vencimientos["Fecha Vencimiento"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    df_vencimientos = (
        df_vencimientos
        .groupby(
            ["Mes Vencimiento", "Estado Licencia"],
            as_index=False
        )
        .size()
        .rename(columns={"size": "Licencias"})
        .sort_values("Mes Vencimiento")
    )

    if not df_vencimientos.empty:
        fig_vencimientos = px.bar(
            df_vencimientos,
            x="Mes Vencimiento",
            y="Licencias",
            color="Estado Licencia",
            barmode="stack",
            labels={
                "Mes Vencimiento": "Mes de vencimiento",
                "Licencias": "Cantidad de licencias"
            },
            color_discrete_map={
                "Vigente": "#2ca02c",
                "Vence en 30 días": "#ff7f0e",
                "Vence en 60 días": "#f2b134",
                "Vence en 90 días": "#e6c84f",
                "Vencida": "#d62728",
                "No activada": "#7f7f7f",
                "Cancelada": "#9467bd",
                "Sin fecha": "#bdbdbd"
            }
        )

        fig_vencimientos.update_layout(
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
            fig_vencimientos,
            use_container_width=True
        )
    else:
        st.info("No hay fechas de vencimiento para los filtros seleccionados.")

with col_grafico_2:
    st.subheader("📊 Estado actual")

    df_estado = (
        df_filtrado
        .groupby("Estado Licencia", as_index=False)
        .size()
        .rename(columns={"size": "Licencias"})
    )

    if not df_estado.empty:
        fig_estado = px.pie(
            df_estado,
            names="Estado Licencia",
            values="Licencias",
            hole=0.55,
            color="Estado Licencia",
            color_discrete_map={
                "Vigente": "#2ca02c",
                "Vence en 30 días": "#ff7f0e",
                "Vence en 60 días": "#f2b134",
                "Vence en 90 días": "#e6c84f",
                "Vencida": "#d62728",
                "No activada": "#7f7f7f",
                "Cancelada": "#9467bd",
                "Sin fecha": "#bdbdbd"
            }
        )

        fig_estado.update_traces(
            textinfo="percent+label"
        )

        fig_estado.update_layout(
            showlegend=False
        )

        st.plotly_chart(
            fig_estado,
            use_container_width=True
        )
    else:
        st.info("No hay licencias para los filtros seleccionados.")

# =========================================================
# OPORTUNIDADES COMERCIALES
# =========================================================

st.markdown("---")
st.subheader("💰 Oportunidades de renovación")

estados_oportunidad = [
    "Vencida",
    "Vence en 30 días",
    "Vence en 60 días",
    "Vence en 90 días",
    "No activada"
]

df_oportunidades = df_filtrado[
    df_filtrado["Estado Licencia"].isin(estados_oportunidad)
].copy()

resumen_oportunidades = (
    df_oportunidades
    .groupby(
        ["Sucursal", "Estado Licencia"],
        dropna=False,
        as_index=False
    )
    .size()
    .rename(columns={"size": "Licencias"})
)

if not resumen_oportunidades.empty:
    fig_oportunidades = px.bar(
        resumen_oportunidades,
        x="Sucursal",
        y="Licencias",
        color="Estado Licencia",
        barmode="stack",
        labels={"Licencias": "Cantidad de licencias"},
        color_discrete_map={
            "Vence en 30 días": "#ff7f0e",
            "Vence en 60 días": "#f2b134",
            "Vence en 90 días": "#e6c84f",
            "Vencida": "#d62728",
            "No activada": "#7f7f7f"
        }
    )

    fig_oportunidades.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(
        fig_oportunidades,
        use_container_width=True
    )
else:
    st.success("No hay oportunidades pendientes para los filtros seleccionados.")

# =========================================================
# TABLA DETALLADA
# =========================================================

st.markdown("---")
st.subheader("📋 Detalle de licencias")

columnas_tabla = [
    "Sucursal",
    "Organización",
    "Alias Máquina",
    "Tipo Máquina",
    "Modelo Máquina",
    "Tipo Componente",
    "Modelo Componente",
    "Serie Componente",
    "Licencia Normalizada",
    "Fecha Vencimiento",
    "Días para Vencer",
    "Estado Licencia",
    "Fuente",
    "Método Vinculación"
]

columnas_tabla = [
    columna
    for columna in columnas_tabla
    if columna in df_filtrado.columns
]

df_tabla = (
    df_filtrado[columnas_tabla]
    .copy()
    .rename(
        columns={
            "Alias Máquina": "Máquina",
            "Tipo Máquina": "Tipo de Máquina",
            "Modelo Máquina": "Modelo",
            "Tipo Componente": "Tipo de Componente",
            "Modelo Componente": "Componente",
            "Serie Componente": "Serie de Componente",
            "Licencia Normalizada": "Licencia",
            "Fecha Vencimiento": "Fecha de Vencimiento",
            "Días para Vencer": "Días para Vencer",
            "Estado Licencia": "Estado",
            "Método Vinculación": "Método de Vinculación"
        }
    )
    .sort_values(
        ["Días para Vencer", "Organización"],
        ascending=[True, True],
        na_position="last"
    )
)

st.dataframe(
    df_tabla.style.format(
        {
            "Fecha de Vencimiento": lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "N/D",
            "Días para Vencer": "{:.0f}"
        },
        na_rep="N/D"
    ),
    use_container_width=True,
    hide_index=True
)

csv_filtrado = df_tabla.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "📥 Descargar detalle filtrado",
    data=csv_filtrado,
    file_name="detalle_licencias_filtrado.csv",
    mime="text/csv"
)

# =========================================================
# NOTA METODOLÓGICA
# =========================================================

with st.expander("ℹ️ Criterio de la foto actual"):
    st.markdown(
        """
        - El tablero utiliza únicamente la **última Fecha de Actualización** disponible.
        - Para **Gen4 y SF6000**, se normaliza el nombre del producto quitando los
          prefijos `Nuevo`, `Renovar` y `Actualización`.
        - Si un mismo componente y licencia tiene un registro vigente y registros
          históricos vencidos, se conserva el vigente y se desestiman los vencidos.
        - Si no existe un registro activo, se conserva el vencimiento más reciente.
        - Los registros no vinculados a una máquina se mantienen porque siguen siendo
          válidos para el seguimiento administrativo y comercial.
        """
    )
