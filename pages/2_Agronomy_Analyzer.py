import json
import os
import pandas as pd
import streamlit as st
import uuid
import plotly.express as px

st.set_page_config(
    page_title="SmartFarm - Conci",
    layout="wide",
    page_icon="sf1.png",
    initial_sidebar_state="collapsed"
)

# =================================================================
# 1. CONFIGURACIÓN DEL ENTORNO Y DATOS MAESTROS
# =================================================================
# Variables de entorno para simulación de Firestore
app_id = os.environ.get('__app_id', 'smartfarm_default_app_id')
DATA_FILE = "firestore_simulation.json"

# RUTAS DE COLECCIÓN (Las rutas deben ser únicas para cada tipo de dato)
SCORES_COLLECTION_PATH = f'artifacts/{app_id}/public/data/client_scores'
PROJECTS_COLLECTION_PATH = f'artifacts/{app_id}/public/data/agronomy_projects'

PROTOCOLOS_AA = [
    "Pulverizadora PLA", "Sembradora PLA", "Sembradora JD",
    "ExactApply", "AutoPath", "S700 Combine Advisor", "S7 Automation",
    "Autotrac Turn Automation", "Machine Sync", "HarvestLab", "Grain Sensing"
]

ESTADOS_PROYECTO = ["No Iniciado", "En Proceso", "Completado"]

# Colores primarios para Streamlit (Green theme)
COLOR_COMPLETADO = "#4CAF50"  # Verde éxito
COLOR_EN_PROCESO = "#FFC107"  # Amarillo advertencia
COLOR_NO_INICIADO = "#BDBDBD"  # Gris neutro


# =================================================================
# 2. FUNCIONES DE SIMULACIÓN DE FIRESTORE
# =================================================================

def load_firestore_data():
    """Carga todos los datos de la simulación de Firestore desde el archivo JSON."""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"ERROR: Archivo {DATA_FILE} corrupto o vacío. Iniciando con datos vacíos.")
        return {}
    except Exception:
        return {}


def save_firestore_data(data):
    """Guarda los datos en el archivo JSON, con manejo de errores."""
    print(f"DEBUG: Intentando guardar datos en {DATA_FILE}. Total de colecciones: {len(data)}")
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print("DEBUG: Guardado de datos exitoso.")
        return True
    except Exception as e:
        # Mensaje de error muy claro si el guardado falla
        st.error(
            f"❌ ERROR CRÍTICO DE PERSISTENCIA: Falló al guardar los cambios en el archivo de simulación. "
            f"La eliminación NO es permanente. Causa: {e}"
        )
        print(f"ERROR: Error crítico al guardar datos: {e}")
        return False


def load_client_scores_data():
    """
    Obtiene la lista de clientes directamente desde
    los proyectos cargados en el CSV.
    """

    projects = load_agronomy_projects()

    clientes = {}

    for proyecto in projects:

        nombre = str(
            proyecto.get(
                "CLIENTE",
                ""
            )
        ).strip()

        if not nombre:
            continue

        clientes[nombre] = {

            "Cliente":
                nombre,

            "Sucursal":
                proyecto.get(
                    "SUCURSAL",
                    ""
                ),

            "Categoria_Evaluacion":
                proyecto.get(
                    "CATEGORÍA DE EVALUACIÓN",
                    ""
                )

        }

    return list(
        clientes.values()
    )



@st.cache_data(ttl=60, show_spinner=False)
def load_agronomy_projects():

    repo = st.secrets["github"]["repo"]

    token = st.secrets["github"]["token"]

    path = "datos_proyectos_agronomy_analyzer.csv"

    url = (
        f"https://api.github.com/repos/"
        f"{repo}/contents/{path}"
    )

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
        return []

    respuesta.raise_for_status()

    df = pd.read_csv(
        io.StringIO(
            respuesta.text
        ),
        low_memory=False
    )

    return df.to_dict(
        orient="records"
    )



def get_latest_project_for_client(client_name):
    """Busca el proyecto más reciente para un cliente dado."""
    all_projects = load_agronomy_projects()
    client_projects = [p for p in all_projects if p.get('Cliente') == client_name]

    if not client_projects:
        return None, None  # No project found

    # Ordenar por fecha de registro descendente para obtener el último
    try:
        df_projects = pd.DataFrame(client_projects)
        df_projects['Fecha_Registro_dt'] = pd.to_datetime(df_projects['Fecha_Registro'], errors='coerce')
        # Filtra Nulos antes de ordenar
        df_projects = df_projects.dropna(subset=['Fecha_Registro_dt'])
        latest_project = df_projects.sort_values(by='Fecha_Registro_dt', ascending=False).iloc[0].to_dict()
    except Exception as e:
        # Fallback a la clasificación de strings si hay un error o no hay datos
        client_projects.sort(key=lambda x: x.get('Fecha_Registro', '2000-01-01'), reverse=True)
        latest_project = client_projects[0]

    return latest_project.get('id'), latest_project


def delete_project(project_ids_to_delete):
    """Elimina proyectos de la simulación de Firestore por su ID y verifica la persistencia."""
    if not project_ids_to_delete:
        return

    firestore_data = load_firestore_data()
    projects = firestore_data.get(PROJECTS_COLLECTION_PATH, {})

    deleted_count = 0
    original_project_count = len(projects)

    for doc_id in project_ids_to_delete:
        if doc_id in projects:
            del projects[doc_id]
            deleted_count += 1

    # Asignamos el diccionario modificado de vuelta a la estructura global
    firestore_data[PROJECTS_COLLECTION_PATH] = projects

    if deleted_count > 0:
        # 1. Guardar los cambios
        save_success = save_firestore_data(firestore_data)

        if save_success:
            # 2. VERIFICACIÓN CRÍTICA: Recargar los datos para confirmar la persistencia
            reloaded_projects = load_agronomy_projects()

            if len(reloaded_projects) == original_project_count - deleted_count:
                # Éxito en la persistencia
                st.toast(f"✅ {deleted_count} proyecto(s) eliminado(s) y guardados. Recargando...")

                # 3. Forzar la interfaz a reflejar los cambios
                if 'select_cliente_widget' in st.session_state:
                    # No es necesario llamar a load_project_data_callback, ya que el st.rerun hará que todo se cargue de nuevo.
                    st.rerun()
            else:
                # Fallo en la persistencia (el archivo no se actualizó correctamente)
                st.error(
                    f"❌ ERROR CRÍTICO: La eliminación de {deleted_count} proyecto(s) falló al guardarse persistentemente. "
                    "El archivo JSON de simulación no refleja los cambios. Esto es un problema de permisos."
                )
    else:
        st.warning("No se encontró ningún proyecto para eliminar.")


# =================================================================
# 3. LÓGICA DE CARGA DE ESTADO (SESSION STATE)
# =================================================================

def initialize_session_state(first_client):
    """Inicializa todas las claves de session_state con valores seguros."""
    if 'current_project_id' not in st.session_state:
        st.session_state.current_project_id = None
        st.session_state.protocol_default = PROTOCOLOS_AA[0]
        st.session_state.nombre_default = ''
        st.session_state.ubicacion_default = ''

        # Valores de Etapa por defecto
        st.session_state.plan_status_default = ESTADOS_PROYECTO[0]
        st.session_state.plan_hours_default = 0
        st.session_state.reco_status_default = ESTADOS_PROYECTO[0]
        st.session_state.reco_hours_default = 0
        st.session_state.informe_status_default = ESTADOS_PROYECTO[0]
        st.session_state.informe_hours_default = 0

        # Control de UI
        st.session_state.select_cliente_widget = first_client
        st.session_state.form_key_suffix = 0
        st.session_state.initial_load_done = False
        st.session_state.selected_rows_indices = []  # Para la tabla de eliminación


def load_project_data_callback():
    """Callback para cargar datos del último proyecto al cambiar el cliente y refrescar el estado."""
    client_name = st.session_state.get('select_cliente_widget')

    if not client_name:
        return

    # CRÍTICO: Incrementar el sufijo de la clave del formulario ANTES de cargar
    st.session_state.form_key_suffix += 1

    doc_id, project_data = get_latest_project_for_client(client_name)

    if project_data:
        st.session_state.current_project_id = doc_id

        # Info base
        st.session_state.protocol_default = project_data.get('Protocolo', PROTOCOLOS_AA[0])
        st.session_state.nombre_default = project_data.get('Nombre_Evaluacion', '')
        st.session_state.ubicacion_default = project_data.get('Ubicacion_Evaluacion', '')

        # Etapas
        st.session_state.plan_status_default = project_data.get('Planificacion_Estado', ESTADOS_PROYECTO[0])
        st.session_state.plan_hours_default = int(project_data.get('Planificacion_Horas', 0))
        st.session_state.reco_status_default = project_data.get('Recopilacion_Estado', ESTADOS_PROYECTO[0])
        st.session_state.reco_hours_default = int(project_data.get('Recopilacion_Horas', 0))
        st.session_state.informe_status_default = project_data.get('Informe_Estado', ESTADOS_PROYECTO[0])
        st.session_state.informe_hours_default = int(project_data.get('Informe_Horas', 0))

        st.toast(f"Datos del último proyecto '{project_data.get('Nombre_Evaluacion')}' cargados para edición.")
    else:
        # Set clean defaults if no project found
        st.session_state.current_project_id = None
        st.session_state.protocol_default = PROTOCOLOS_AA[0]
        st.session_state.nombre_default = ''
        st.session_state.ubicacion_default = ''
        st.session_state.plan_status_default = ESTADOS_PROYECTO[0]
        st.session_state.plan_hours_default = 0
        st.session_state.reco_status_default = ESTADOS_PROYECTO[0]
        st.session_state.reco_hours_default = 0
        st.session_state.informe_status_default = ESTADOS_PROYECTO[0]
        st.session_state.informe_hours_default = 0

        st.toast(f"No hay proyectos registrados para {client_name}. Ingresa uno nuevo.")


# =================================================================
# 4. INTERFAZ Y LÓGICA DE CARGA (INIT & UI)
# =================================================================

# --- Encabezado Moderno ---
st.markdown(
    f"<h1>🚜 Agronomy Analyzer <span style='color: #ba8c00;'>|</span> Gestión de Proyectos 📋</h1>",
    unsafe_allow_html=True
)
st.markdown("---")

client_scores_data = load_client_scores_data()

if not client_scores_data:

    st.warning(
        "Todavía no existen Agronomys cargados."
    )

    client_scores_data = []


# Convertir los datos de clientes a DataFrame
df_clients = pd.DataFrame(client_scores_data)
df_unique_clients = df_clients[['Cliente', 'Sucursal', 'Categoria_Evaluacion']].drop_duplicates(
    subset=['Cliente']).reset_index(drop=True)
client_names = df_unique_clients['Cliente'].unique().tolist()
first_client = client_names[0] if client_names else None

# Inicialización segura
initialize_session_state(first_client)

# Carga inicial de datos para el primer cliente al iniciar la página
if not st.session_state.initial_load_done and client_names:
    st.session_state.select_cliente_widget = first_client
    load_project_data_callback()
    st.session_state.initial_load_done = True
    st.rerun()  # Forzar rerun solo en la carga inicial

# --- SELECCIÓN DE CLIENTE (FUERA DEL FORMULARIO) ---
with st.container(border=True):
    st.subheader("Selección y Carga de Proyecto")

    current_client_key = st.session_state.get('select_cliente_widget', first_client)

    safe_index = client_names.index(current_client_key) if current_client_key in client_names else 0

    # Este selectbox debe usar el valor que está en session_state para mantener la selección
    selected_client_name = st.selectbox(
        "1. Selecciona el Cliente SmartFarm:",
        options=client_names,
        index=safe_index,
        key="select_cliente_widget",
        on_change=load_project_data_callback
    )

    # Obtener los datos del cliente seleccionado para incluirlos en el registro del proyecto
    client_info = {}
    if selected_client_name:
        client_info = df_unique_clients[df_unique_clients['Cliente'] == selected_client_name].iloc[0].to_dict()
        st.markdown(f"""
        <div style="
            padding: 10px; 
            border: 0px dashed; 
            border-radius: 5px; 
            margin-top: 15px; 
            ">
            Sucursal: {client_info['Sucursal']}<br>
            Categoría: {client_info['Categoria_Evaluacion']}
        </div>
        """, unsafe_allow_html=True)

# =================================================================
# 5. FORMULARIO DE REGISTRO DE PROYECTO (USANDO DEFAULTS DE SESSION STATE)
# =================================================================
key_suffix = st.session_state.form_key_suffix

st.markdown("---")

# Diccionarios para guardar las claves de los widgets para lectura posterior
stage_widget_keys = {}

# Definición de claves de widgets base
base_widget_keys = {
    'protocol': f"select_protocolo_form_{key_suffix}",
    'nombre': f"nombre_evaluacion_{key_suffix}",
    'ubicacion': f"ubicacion_evaluacion_{key_suffix}"
}


# --- FUNCIÓN DE ENTRADA CON ESTILOS DE COLOR ---
def create_stage_inputs(stage_name, default_status, default_hours, suffix):
    """Crea los selectbox y number_input para una etapa, mostrando el estado actual con color."""

    status_key = f"{stage_name}_estado_{suffix}"
    hours_key = f"{stage_name}_horas_{suffix}"

    # 1. Obtenemos el valor actual (o el default si es la primera carga)
    current_status = st.session_state.get(status_key, default_status)

    # 2. Mapeo de colores
    color_map = {
        "Completado": (COLOR_COMPLETADO, "white"),
        "En Proceso": (COLOR_EN_PROCESO, "black"),
        "No Iniciado": (COLOR_NO_INICIADO, "black")
    }
    bg_color, text_color = color_map.get(current_status, (COLOR_NO_INICIADO, "black"))

    # Estilo HTML para el título/estado de la etapa
    styled_html = f"""
    <div style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 15px;
        margin-bottom: 10px;
        border-radius: 8px; 
        background-color: {bg_color}; 
        color: {text_color};
        font-size: 1.1em;
        font-weight: 700;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    ">
        <span>{stage_name}:</span> 
        <span>{current_status}</span>
    </div>
    """
    st.markdown(styled_html, unsafe_allow_html=True)

    # 3. Input Widgets
    col_status, col_hours = st.columns([3, 2])

    status_index = ESTADOS_PROYECTO.index(default_status) if default_status in ESTADOS_PROYECTO else 0

    with col_status:
        st.caption("Cambiar Estado")
        st.selectbox(
            f"Estado de {stage_name}:",
            options=ESTADOS_PROYECTO,
            index=status_index,
            key=status_key,
            label_visibility="collapsed"  # Ocultamos la etiqueta para que se vea más limpio
        )

    with col_hours:
        st.caption("Horas Dedicadas")
        st.number_input(
            f"Horas Dedicadas a {stage_name} (h):",
            min_value=0,
            step=1,
            value=default_hours,
            key=hours_key,
            label_visibility="collapsed"  # Ocultamos la etiqueta para que se vea más limpio
        )

    return status_key, hours_key


# --- FIN FUNCIÓN DE ENTRADA CON ESTILOS DE COLOR ---

with st.container(border=True):
    if st.session_state.current_project_id:
        st.subheader(f"📝 Actualizar Último Proyecto")
    else:
        st.subheader("➕ Registrar Nuevo Protocolo")

    with st.form("agronomy_project_form"):

        # --- Info Base (Usando las claves definidas arriba) ---
        col_sel_protocolo, _ = st.columns([1, 1])
        with col_sel_protocolo:
            protocol_index = PROTOCOLOS_AA.index(
                st.session_state.protocol_default) if st.session_state.protocol_default in PROTOCOLOS_AA else 0
            st.selectbox(
                "2. Selecciona el Protocolo (Agronomy Analyzer):",
                options=PROTOCOLOS_AA,
                index=protocol_index,
                key=base_widget_keys['protocol']
            )

        col_nombre, col_ubicacion = st.columns(2)

        with col_nombre:
            st.text_input(
                "3. Nombre de la Evaluación/Proyecto",
                value=st.session_state.nombre_default,
                placeholder="Ej: 'SF - AutoPath' o Nombre Predeterminado del Proyecto",
                key=base_widget_keys['nombre']
            )

        with col_ubicacion:
            st.text_input(
                "4. Ubicación de la Evaluación (Lote/Campo)",
                value=st.session_state.ubicacion_default,
                placeholder="Ej: SF - Juan Ciervo - Granja Illinois - Lote Prueba",
                key=base_widget_keys['ubicacion']
            )

        st.markdown("---")

        # --- Seguimiento de Etapas (Llamando a la función mejorada) ---
        st.subheader("5. Seguimiento de Etapas y Tiempos")

        stage_widget_keys['plan_status'], stage_widget_keys['plan_hours'] = create_stage_inputs(
            "Planificación",
            st.session_state.plan_status_default,
            st.session_state.plan_hours_default,
            key_suffix
        )
        st.markdown("---")

        stage_widget_keys['reco_status'], stage_widget_keys['reco_hours'] = create_stage_inputs(
            "Recopilación de Datos",
            st.session_state.reco_status_default,
            st.session_state.reco_hours_default,
            key_suffix
        )
        st.markdown("---")

        stage_widget_keys['informe_status'], stage_widget_keys['informe_hours'] = create_stage_inputs(
            "Generación de Informe",
            st.session_state.informe_status_default,
            st.session_state.informe_hours_default,
            key_suffix
        )
        st.markdown("---")

        submit_label = "Actualizar Proyecto" if st.session_state.current_project_id else "Guardar Nuevo Proyecto"
        submitted = st.form_submit_button(submit_label, type="primary")

        if submitted:
            # LECTURA CRÍTICA DE TODOS LOS VALORES DEL FORMULARIO A TRAVÉS DE SESSION STATE
            selected_protocol = st.session_state[base_widget_keys['protocol']]
            evaluation_name = st.session_state[base_widget_keys['nombre']]
            evaluation_location = st.session_state[base_widget_keys['ubicacion']]

            plan_status = st.session_state[stage_widget_keys['plan_status']]
            plan_hours = st.session_state[stage_widget_keys['plan_hours']]
            reco_status = st.session_state[stage_widget_keys['reco_status']]
            reco_hours = st.session_state[stage_widget_keys['reco_hours']]
            informe_status = st.session_state[stage_widget_keys['informe_status']]
            informe_hours = st.session_state[stage_widget_keys['informe_hours']]

            # 1. Validación
            if not selected_client_name or not evaluation_name.strip() or not evaluation_location.strip():
                st.error("Por favor, completa los campos obligatorios (Cliente, Nombre y Ubicación).")
            else:
                # 2. Decidir si es UPDATE o CREATE
                doc_id = st.session_state.current_project_id if st.session_state.current_project_id else str(
                    uuid.uuid4())
                action_type = "Actualizado" if st.session_state.current_project_id else "Guardado"

                # Sumar las horas totales
                total_hours = plan_hours + reco_hours + informe_hours

                new_project_document = {
                    "id": doc_id,
                    "Cliente": selected_client_name,
                    "Sucursal": client_info.get('Sucursal', 'N/A'),
                    "Perfil_Tecnologico": client_info.get('Categoria_Evaluacion', 'N/A'),
                    "Protocolo": selected_protocol,
                    "Nombre_Evaluacion": evaluation_name.strip(),
                    "Ubicacion_Evaluacion": evaluation_location.strip(),

                    # Campos de Seguimiento
                    "Planificacion_Estado": plan_status,
                    "Planificacion_Horas": plan_hours,
                    "Recopilacion_Estado": reco_status,
                    "Recopilacion_Horas": reco_hours,
                    "Informe_Estado": informe_status,
                    "Informe_Horas": informe_hours,
                    "Total_Horas": total_hours,

                    "Fecha_Registro": pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S')
                }

                # 3. Cargar datos existentes y guardar/actualizar el proyecto
                firestore_data = load_firestore_data()
                if PROJECTS_COLLECTION_PATH not in firestore_data:
                    firestore_data[PROJECTS_COLLECTION_PATH] = {}

                # Sobreescribir el documento completo usando doc_id como clave.
                firestore_data[PROJECTS_COLLECTION_PATH][doc_id] = new_project_document

                # 4. Guardar en la simulación de Firestore
                save_success = save_firestore_data(firestore_data)

                if save_success:
                    st.success(
                        f"¡Proyecto '{evaluation_name.strip()}' para {selected_client_name} {action_type} con éxito! ID: {doc_id[:8]}...")

                    # Si fue un GUARDADO (nuevo), actualizamos el ID de sesión
                    if action_type == "Guardado":
                        st.session_state.current_project_id = doc_id

                    # RECARGA: Forzar la recarga de datos al session_state y rotar la clave del formulario
                    load_project_data_callback()
                    st.rerun()

# =================================================================
# 6. TABLA PERMANENTE DE PROYECTOS REGISTRADOS
# =================================================================

st.markdown("---")
st.header("Historial de Proyectos Registrados")

projects_data = load_agronomy_projects()

if not projects_data:
    st.info("Aún no hay proyectos de Agronomy Analyzer registrados.")
else:
    df_projects = pd.DataFrame(projects_data)

    # Asegurar la existencia de las columnas y recalcular Total_Horas
    required_cols = ['id', 'Planificacion_Estado', 'Planificacion_Horas', 'Recopilacion_Estado', 'Recopilacion_Horas',
                     'Informe_Estado', 'Informe_Horas', 'Total_Horas']
    for col in required_cols:
        if col not in df_projects.columns:
            df_projects[col] = 0 if 'Horas' in col else 'No Iniciado'

    df_projects['Total_Horas'] = df_projects['Planificacion_Horas'] + df_projects['Recopilacion_Horas'] + df_projects[
        'Informe_Horas']

    # Conversión a datetime para ordenar correctamente
    df_projects['Fecha_Registro_dt'] = pd.to_datetime(df_projects['Fecha_Registro'], errors='coerce')
    df_projects.sort_values(by='Fecha_Registro_dt', ascending=False, inplace=True)
    df_projects.drop(columns=['Fecha_Registro_dt'], inplace=True, errors='ignore')

    # Añadir columna de selección (FALSE por defecto)
    df_projects['Seleccionar'] = False

    # Definición de las columnas que queremos mostrar y sus nuevos nombres
    column_mapping = {
        'Seleccionar': 'Seleccionar',  # Columna clave para la eliminación
        'id': 'ID de Documento',
        'Fecha_Registro': 'Fecha de Registro',
        'Cliente': 'Cliente',
        'Sucursal': 'Sucursal',
        'Perfil_Tecnologico': 'Perfil Tecnológico',
        'Protocolo': 'Protocolo AA',
        'Nombre_Evaluacion': 'Nombre del Proyecto',
        'Ubicacion_Evaluacion': 'Ubicación',
        'Planificacion_Estado': 'Planificación (Estado)',
        'Planificacion_Horas': 'Planificación (h)',
        'Recopilacion_Estado': 'Recopilación (Estado)',
        'Recopilacion_Horas': 'Recopilación (h)',
        'Informe_Estado': 'Informe (Estado)',
        'Informe_Horas': 'Informe (h)',
        'Total_Horas': 'Total Horas'
    }

    # Seleccionar y renombrar las columnas
    df_projects_display = df_projects.rename(columns=column_mapping)
    df_projects_display = df_projects_display[
        [col for col in column_mapping.values() if col in df_projects_display.columns]]

    # Columnas visibles en la tabla (incluyendo la nueva columna Seleccionar)
    display_cols_full = [
        'Seleccionar',
        'Fecha de Registro',
        'Cliente',
        'Protocolo AA',
        'Nombre del Proyecto',
        'Planificación (Estado)',
        'Planificación (h)',
        'Recopilación (Estado)',
        'Recopilación (h)',
        'Informe (Estado)',
        'Informe (h)',
        'Total Horas'
    ]

    DATAFRAME_KEY = "data_editor_delete_v4"

    st.markdown("### 🗑️ Eliminar Proyectos")
    st.info(
        "💡 **Instrucción:** Marca la casilla de la columna **'Seleccionar'** (a la izquierda) para marcar los proyectos que deseas eliminar.")

    # Preparamos las configuraciones de columnas para deshabilitar la edición de datos
    column_config = {
        col: st.column_config.Column(
            disabled=True,
            width='small' if 'h)' in col else 'medium'
        )
        for col in df_projects_display.columns
    }

    # Habilitamos la edición SOLO para la columna 'Seleccionar' (el checkbox)
    column_config['Seleccionar'] = st.column_config.CheckboxColumn(
        "Seleccionar",
        default=False,
        help="Marca para seleccionar el proyecto para su eliminación.",
        width="small",
        disabled=False  # Habilitamos la edición de este campo (el checkbox)
    )

    # --- st.data_editor con Checkbox definido por el usuario ---
    edited_df = st.data_editor(
        df_projects_display.drop(columns=['ID de Documento', 'Sucursal', 'Perfil Tecnológico', 'Ubicación'],
                                 errors='ignore'),
        column_order=display_cols_full,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        key=DATAFRAME_KEY,
        num_rows="fixed",  # Evita que el usuario agregue filas
    )

    # ACCESO CRÍTICO: La selección se obtiene directamente del DataFrame editado
    # Filtramos las filas donde la columna 'Seleccionar' es True
    selected_projects_df = edited_df[edited_df['Seleccionar'] == True]

    # Obtenemos los índices posicionales de las filas seleccionadas en el DataFrame actual
    selected_indices_in_editor = selected_projects_df.index.tolist()

    # -----------------------------------------------------
    # LÓGICA DE ELIMINACIÓN CON BOTÓN DE CONFIRMACIÓN
    # -----------------------------------------------------
    if selected_indices_in_editor:
        # Mapeamos los índices posicionales del DataFrame filtrado (df_projects)
        # a los IDs de los documentos originales
        original_indices = df_projects.iloc[selected_indices_in_editor].index.tolist()
        ids_to_delete = df_projects.loc[original_indices, 'id'].tolist()

        # Botón de Confirmación de Eliminación (Solo visible si hay selección)
        if st.button(f"🗑️ Confirmar Eliminación de {len(ids_to_delete)} Proyecto(s)", type="secondary"):
            delete_project(ids_to_delete)
    else:
        st.caption("Selecciona una o más casillas para habilitar la eliminación.")

    st.markdown("---")

# =================================================================
# 7. DASHBOARDS Y ANÁLISIS DE DATOS (MEJORA ESTÉTICA: TARJETAS Y EXPANDER)
# =================================================================

st.header("📊 Resumen de Proyectos y Análisis")

if projects_data:  # Solo mostrar el dashboard si hay datos

    # --- 7.1 FILTROS (dentro de un Expander) ---
    with st.expander("Filtros del Dashboard"):
        col_filter1, col_filter2 = st.columns(2)

        all_clients = df_projects['Cliente'].unique().tolist()
        all_protocols = df_projects['Protocolo'].unique().tolist()

        with col_filter1:
            filter_client = st.multiselect(
                "Filtrar por Cliente",
                options=all_clients,
                default=all_clients,
                key="filter_client_dashboard"
            )

        with col_filter2:
            filter_protocol = st.multiselect(
                "Filtrar por Protocolo AA",
                options=all_protocols,
                default=all_protocols,
                key="filter_protocol_dashboard"
            )

    # Aplicar filtros
    df_filtered = df_projects.copy()

    if filter_client:
        df_filtered = df_filtered[df_filtered['Cliente'].isin(filter_client)]

    if filter_protocol:
        df_filtered = df_filtered[df_filtered['Protocolo'].isin(filter_protocol)]

    # --- VALIDACIÓN DE DATOS FILTRADOS ---
    if df_filtered.empty:
        st.warning("No hay datos disponibles para los filtros seleccionados.")
    else:
        # --- 7.2 KPIs Y GRÁFICOS ---

        col_kpi_total, col_kpi_count, col_kpi_progress, col_spacer = st.columns([2.5, 2.5, 3, 1])

        # 1. KPI de Horas Totales
        total_hours = df_filtered['Total_Horas'].sum()

        with col_kpi_total:
            st.metric(
                label="Total de Horas Dedicadas",
                value=f"{total_hours:,.0f} h",
                delta="Suma total de horas en la vista actual",
                delta_color="off"
            )

        # 2. KPI de Conteo de Proyectos
        total_projects = len(df_filtered)
        with col_kpi_count:
            st.metric(
                label="Proyectos Totales",
                value=f"{total_projects:,}",
                delta="Proyectos incluidos en los filtros actuales",
                delta_color="off"
            )

        # 3. Indicador de Proyectos Terminados (Progreso/Tarjeta Personalizada)
        completed_projects = df_filtered[df_filtered['Informe_Estado'] == 'Completado'].shape[0]
        completion_percentage = (completed_projects / total_projects *100) if total_projects > 0 else 0

        # Uso de HTML para una "tarjeta" de progreso más visual
        with col_kpi_progress:
            st.markdown(
                f"""
                <div style="
                    padding: 15px; 
                    border-radius: 10px; 
                    background-color: {COLOR_COMPLETADO}20; 
                    border: 1px solid {COLOR_COMPLETADO};
                    height: 100%;
                ">
                    <h5 style="margin: 0; color: {COLOR_COMPLETADO};">Proyectos Completados</h5>
                    <p style="font-size: 2.2em; font-weight: 700; margin: 0; color: {COLOR_COMPLETADO};">
                        {completion_percentage:.1f}%
                    </p>
                    <p style="margin: 0; font-size: 0.9em; color: #333;">
                        Informe Finalizado: {completed_projects} de {total_projects}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)  # Espacio

        # 4. Gráfico de Torta de Desglose de Horas por Etapa (Columna completa)
        col_chart, col_extra = st.columns([2, 1])

        stage_hours = {
            'Planificación': df_filtered['Planificacion_Horas'].sum(),
            'Recopilación de Datos': df_filtered['Recopilacion_Horas'].sum(),
            'Generación de Informe': df_filtered['Informe_Horas'].sum()
        }

        df_stage_hours = pd.DataFrame(
            list(stage_hours.items()),
            columns=['Etapa', 'Horas']
        )

        # Colores que coinciden con los estados (verde para informe, amarillo para recopilación, gris para planificación)
        color_map_pie = {
            'Generación de Informe': COLOR_COMPLETADO,
            'Recopilación de Datos': COLOR_EN_PROCESO,
            'Planificación': COLOR_NO_INICIADO
        }

        fig = px.pie(
            df_stage_hours,
            values='Horas',
            names='Etapa',
            title='Desglose de Horas por Etapa del Proyecto',
            hole=.4,  # Efecto dona más marcado
            color='Etapa',
            color_discrete_map=color_map_pie
        )

        fig.update_traces(textposition='outside', textinfo='percent+label')
        fig.update_layout(
            showlegend=True,
            margin=dict(l=20, r=20, t=50, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400
        )

        with col_chart:
            st.subheader("Desglose de Esfuerzo")
            st.plotly_chart(fig, use_container_width=True)

        with col_extra:
            st.subheader("Estado de Protocolos")
            # Gráfico de barras simple del estado de los protocolos
            protocol_status = df_filtered.groupby('Protocolo')['Informe_Estado'].value_counts().unstack(fill_value=0)

            if not protocol_status.empty:
                # Creamos una tabla simple, sin la columna 'Total' para mantener la limpieza
                df_status_display = protocol_status.drop(columns=['Total'], errors='ignore').reset_index()

                # Mapeamos los estados a sus colores para visualización simple (opcional)
                # En este caso, solo mostramos el conteo

                st.dataframe(
                    df_status_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Protocolo": st.column_config.Column("Protocolo AA"),
                        "Completado": st.column_config.NumberColumn("Completados", format="%d"),
                        "En Proceso": st.column_config.NumberColumn("En Proceso", format="%d"),
                        "No Iniciado": st.column_config.NumberColumn("No Iniciados", format="%d"),
                    }
                )

