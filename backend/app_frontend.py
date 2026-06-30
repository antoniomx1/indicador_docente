import streamlit as st
import pandas as pd
import sqlite3
import os
import subprocess
import plotly.express as px
from procesador import procesar_y_guardar_tablero
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "indicador_docente.db")


st.set_page_config(page_title="Tablero BI UTEL", page_icon="📊", layout="wide")

st.title("📊 Indicador Docente (Módulo BI)")
st.markdown("---")

st.sidebar.header("⚙️ Configuración")
semana_seleccionada = st.sidebar.selectbox("Selecciona la Semana del Bimestre:", options=[1, 2, 3, 4, 5, 6, 7, 8], index=0)

# ========================================================
#             BUSCADOR EXPRESS EN LA BARRA LATERAL
# ========================================================
with st.sidebar:
    st.markdown("---")
    st.subheader("🔍 Buscador Express de Alumnos")
    
    # Input de texto que acepta matrícula, nombre, cel o correo
    termino_busqueda = st.text_input("Ingresa Nombre, Matrícula, Teléfono o Correo:")
    
    if termino_busqueda:
        # CONEXIÓN EXPRESS EXCLUSIVA PARA EL BUSCADOR
        conn_busqueda = sqlite3.connect(DB_PATH)
        
        # Query que busca en el histórico y jala el canal del último log registrado
        query_busqueda = f"""
            SELECT 
                h.matricula,
                h.nombre_estudiante,
                h.celular,
                h.correo,
                h.estatus_aprobacion,
                h.semana_bimestre,
                (
                    SELECT li.canal 
                    FROM logs_interacciones li 
                    WHERE li.matricula = h.matricula 
                    ORDER BY li.semana_bimestre DESC 
                    LIMIT 1
                ) as ultimo_canal
            FROM historico_tablero h
            WHERE (
                LOWER(h.nombre_estudiante) LIKE LOWER('%{termino_busqueda}%')
                OR h.matricula LIKE '%{termino_busqueda}%'
                OR h.celular LIKE '%{termino_busqueda}%'
                OR LOWER(h.correo) LIKE LOWER('%{termino_busqueda}%')
            )
            ORDER BY h.semana_bimestre DESC
            LIMIT 3;
        """
        
        df_busqueda = pd.read_sql_query(query_busqueda, conn_busqueda)
        conn_busqueda.close() # La cerramos de inmediato para no dejarla colgada
        
        if not df_busqueda.empty:
            st.success(f"Se encontraron {len(df_busqueda)} de coincidencias:")
            for idx, alumno in df_busqueda.iterrows():
                canal_contacto = alumno['ultimo_canal'] if alumno['ultimo_canal'] else "Sin contacto aún"
                
                # Pintamos una tarjeta limpia por cada alumno encontrado
                st.markdown(
                    f"""
                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid #2e7d32;">
                        <span style="font-size: 12px; color: #555;"><b>Semana {alumno['semana_bimestre']}</b></span><br>
                        <b>🧑‍🎓 {alumno['nombre_estudiante']}</b><br>
                        🆔 <b>Matrícula:</b> {alumno['matricula']}<br>
                        📞 <b>Tel:</b> {alumno['celular']}<br>
                        📧 <b>Correo:</b> {alumno['correo']}<br>
                        🚨 <b>NR:</b> {alumno['estatus_aprobacion']}<br>
                        📢 <b>Contactado por:</b> {canal_contacto}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.error("No se encontró ningún alumno con ese dato.")



# --- SECCIÓN 1: CARGA DE DATOS ---
st.header("📥 Cargar Tablero Docente")

# 1. Creamos un contador en el session_state para reiniciar el uploader cuando queramos
if "contador_uploader" not in st.session_state:
    st.session_state.contador_uploader = 0

col_bloque, col_upload = st.columns([1, 2])

with col_bloque:
    st.markdown("**1. Asigna el Bloque:**")
    bloque_seleccionado = st.selectbox(
        "¿A qué bloque pertenece este Excel?", 
        options=["--- Selecciona Bloque ---", "Bloque A", "Bloque D"], 
        index=0,
        key="selector_bloque_carga"
    )

with col_upload:
    st.markdown("**2. Sube tu archivo:**")
    # Amárramos la key al contador dinámico para poder resetearlo alv
    archivo_subido = st.file_uploader(
        "Arrastra aquí el archivo Excel o CSV", 
        label_visibility="collapsed",
        key=f"uploader_excel_{st.session_state.contador_uploader}"
    )

if archivo_subido is not None:
    nombre_temporal = archivo_subido.name
    with open(nombre_temporal, "wb") as f:
        f.write(archivo_subido.getbuffer())
        
    if st.button("🚀 Procesar e Inyectar Datos (UPSERT)", type="primary"):
        if bloque_seleccionado == "--- Selecciona Bloque ---":
            st.error("⚠️ ¡AGUAS, CAÓN! Te falta seleccionar el bloque. Recuerda que es un puto peligro inyectar datos sin asignarle el bloque correcto. Elige Bloque A o Bloque D antes de continuar.")
            if os.path.exists(nombre_temporal):
                os.remove(nombre_temporal)
        else:
            with st.spinner("Procesando e inyectando datos por bloque..."):
                try:
                    letra_bloque = bloque_seleccionado.split(" ")[1]
                    insertados = procesar_y_guardar_tablero(nombre_temporal, semana_seleccionada, letra_bloque)
                    
                    # EL TRUCO MAESTRO: Le sumamos 1 al contador para cambiarle la KEY al uploader. 
                    # Esto hace que Streamlit piense que es un componente nuevo y borre el archivo viejo al tiro.
                    st.session_state.contador_uploader += 1
                    
                    st.success(f"¡Cámara! Se procesaron {insertados} registros del {bloque_seleccionado} para la Semana {semana_seleccionada}.")
                    
                    # Le metemos un mini delay de 1.5 segundos para que alcances a ver el letrero verde antes del rerun
                    import time
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error en el proceso: {e}")
                finally:
                    if os.path.exists(nombre_temporal):
                        os.remove(nombre_temporal)

st.markdown("---")

# --- SECCIÓN 2: INDICADOR DE ESTRATEGIAS MASIVAS ---
st.header(f"🎯 Segmentación Estratégica - Semana {semana_seleccionada}")
try:
    conn = sqlite3.connect(DB_PATH)
    
    # Primero verificamos si la tabla ya existe para que no truene el script entero
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs_interacciones (
        id_interaccion INTEGER PRIMARY KEY AUTOINCREMENT,
        matricula TEXT NOT NULL,
        semana_bimestre INTEGER NOT NULL,
        canal TEXT NOT NULL,
        estatus_aprobacion TEXT,
        fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        respondio INTEGER DEFAULT 0
    )
    """)
    conn.commit()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historico_tablero'")
    tabla_existe = cursor.fetchone()
    
    if tabla_existe:
        # Si la tabla existe, ejecutamos tu consulta agrupada perrona
# Consulta corregida para contar todos los canales
# --- AHORA SÍ, EL QUERY CORRECTO QUE RESPETA LA EVOLUCIÓN ACADÉMICA ---
        query_agrupada = f"""
            WITH mensajes_anteriores AS (
                -- 1. Contamos los mensajes del pasado SÓLO si se enviaron estando en el mismo estatus
                SELECT l.matricula, l.estatus_aprobacion, COUNT(*) as total_acumulado
                FROM logs_interacciones l
                WHERE l.semana_bimestre < {semana_seleccionada}
                GROUP BY l.matricula, l.estatus_aprobacion
            ),
            resumen_semanal AS (
                SELECT 
                    h.matricula,
                    h.estatus_aprobacion,
                    IFNULL(l_actual.total_envios, 0) as envios_esta_semana,
                    -- Evaluamos el acumulado pero haciendo match estricto con el estatus actual
                    IFNULL(ma.total_acumulado, 0) as envios_semanas_anteriores
                FROM historico_tablero h
                LEFT JOIN (
                    SELECT matricula, estatus_aprobacion, COUNT(*) as total_envios
                    FROM logs_interacciones
                    WHERE semana_bimestre = {semana_seleccionada}
                    GROUP BY matricula, estatus_aprobacion
                ) l_actual ON h.matricula = l_actual.matricula 
                          AND h.estatus_aprobacion = l_actual.estatus_aprobacion
                -- Aquí está la magia: el LEFT JOIN amarra matrícula Y ADEMÁS el estatus
                LEFT JOIN mensajes_anteriores ma ON h.matricula = ma.matricula 
                                               AND h.estatus_aprobacion = ma.estatus_aprobacion
                WHERE h.semana_bimestre = {semana_seleccionada}
            )
            SELECT 
                estatus_aprobacion,
                COUNT(matricula) as total_alumnos,
                envios_esta_semana as envios_estatus,
                envios_semanas_anteriores
            FROM resumen_semanal
            GROUP BY estatus_aprobacion, envios_esta_semana, envios_semanas_anteriores
            ORDER BY 
                CASE 
                    WHEN LOWER(estatus_aprobacion) LIKE '%nunca%' THEN 1
                    WHEN LOWER(estatus_aprobacion) LIKE '%np%' OR LOWER(estatus_aprobacion) LIKE '%participa%' THEN 2
                    WHEN LOWER(estatus_aprobacion) LIKE '%reprob%' THEN 3
                    WHEN LOWER(estatus_aprobacion) LIKE '%por aprobar%' THEN 4
                    WHEN LOWER(estatus_aprobacion) LIKE '%aprobado%' THEN 5
                    ELSE 6
                END ASC,
                envios_estatus ASC,
                envios_semanas_anteriores DESC
        """
        
        df_grupos = pd.read_sql_query(query_agrupada, conn)
        
        if not df_grupos.empty:
            st.subheader("📊 Resumen del Estado de tus Alumnos")
            
            # --- SECCIÓN DE SELECCIÓN DE CAMPAÑA (Tu lógica se queda intacta) ---
            opciones_campana = []
            for _, fila in df_grupos.iterrows():
                estatus = fila['estatus_aprobacion']
                envios = int(fila['envios_estatus'])
                total = fila['total_alumnos']
                
                estatus_lower = estatus.lower()
                if "nunca" in estatus_lower:
                    emoji = "🔴"
                elif "np" in estatus_lower or "participa" in estatus_lower:
                    emoji = "🟠"
                elif "reprob" in estatus_lower:
                    emoji = "🟤"
                elif "por aprobar" in estatus_lower or "aprobado" in estatus_lower:
                    emoji = "🟢"
                else:
                    emoji = "🔵"
                
                label = f"{emoji} {estatus} con {envios} envíos ({total} alumnos)"
                opciones_campana.append((label, estatus, envios))
            
            label_opciones = [opc[0] for opc in opciones_campana]
            seleccion_usuario = st.selectbox("👇 Elige el segmento objetivo para enviar mensaje:", options=label_opciones)
            
            idx_sel = label_opciones.index(seleccion_usuario)
            st.session_state['segmento_estatus'] = opciones_campana[idx_sel][1]
            st.session_state['segmento_envios'] = opciones_campana[idx_sel][2]
            
            # ========================================================
            #             EL TUNEO EJECUTIVO DE LA TABLA
            # ========================================================

            # 1. Renombramos las columnas para que se vea pro
            df_mostrar = df_grupos.rename(columns={
                'estatus_aprobacion': 'Nivel de Riesgo',
                'envios_estatus': 'Mensajes (Semana Actual)',
                'total_alumnos': 'Cantidad de Alumnos',
                'envios_semanas_anteriores': 'Mensajes Acumulados (Semanas Anteriores)'
            })

            # 2. Función para colorear el fondo según el nivel de riesgo (Mantenemos tus colores)
            def colorear_riesgo(columna):
                estilos = []
                for valor in columna:
                    val_lower = str(valor).lower()
                    if 'nunca' in val_lower:
                        estilos.append('background-color: #ffcccc; color: #cc0000; font-weight: bold;')
                    elif 'np' in val_lower or 'participa' in val_lower:
                        estilos.append('background-color: #ffe5cc; color: #cc6600; font-weight: bold;')
                    elif 'reprob' in val_lower:
                        estilos.append('background-color: #f2e6d9; color: #663300;')
                    elif 'por aprobar' in val_lower or 'aprobado' in val_lower:
                        estilos.append('background-color: #e5ffcc; color: #006600;')
                    else:
                        estilos.append('')
                return estilos

            # 3. Inyección de CSS para forzar el CENTRADO de las celdas y cabeceras de Streamlit
            st.markdown(
                """
                <style>
                div[data-testid="stDataFrame"] table td {
                    text-align: center !important;
                }
                div[data-testid="stDataFrame"] table th {
                    text-align: center !important;
                }
                </style>
                """, 
                unsafe_allow_html=True
            )

            # 4. Estilizamos las columnas numéricas: Forzamos NEGRITAS, precisión entera y CENTRADO
            df_estilizado = df_mostrar.style.apply(colorear_riesgo, subset=['Nivel de Riesgo'])\
                .format(precision=0)\
                .set_properties(**{
                    'font-weight': 'bold', 
                    'text-align': 'center'
                }, subset=['Mensajes (Semana Actual)', 'Cantidad de Alumnos', 'Mensajes Acumulados (Semanas Anteriores)'])

            # 5. Pintamos la tabla ocultando por fin el índice numérico feo
            st.dataframe(df_estilizado, use_container_width=True, hide_index=True)
            
        else:
            st.info("No hay alumnos registrados para esta semana en la base de datos.")
    else:
        # Mensaje limpio si la BD está recién borrada y vacía
        st.info("👋 ¡Pizarrón limpio! Por favor, ve a la Sección 1 de arriba, arrastra tu archivo Excel/CSV y dale procesar para inicializar los indicadores.")
        
    conn.close()
except Exception as e:
    st.error(f"Error al calcular indicadores: {e}")

st.markdown("---")

st.markdown("---")

# --- SECCIÓN 3: CANAL DE COMUNICACIÓN (REDISEÑADO LIMPIO) ---
st.markdown("<h3 style='font-size: 20px; font-weight: bold;'>🛠️ Configuración del Envío</h3>", unsafe_allow_html=True)

# Usamos columnas compactas para que el selector no se vea gigante y cagado
col_canal, col_espacio = st.columns([1, 2])
with col_canal:
    canal_elegido = st.selectbox("👉 Canal de seguimiento:", ["💬 WhatsApp Masivo", "📧 Correo Electrónico"])

st.header("🚀 Redactar Mensaje de la Campaña")
cuerpo_msg = st.text_area("Cuerpo del mensaje:", value="Noto que no has ingresado al aula esta semana. ¿Todo bien por allá?", height=400)

# --- LÓGICA DE CANALES ---
RUTA_TPL = os.path.join("Mensajes", "templates")
os.makedirs(RUTA_TPL, exist_ok=True)

def gestionar_txt(nombre_archivo, label_texto):
    ruta_completa = os.path.join(RUTA_TPL, nombre_archivo)
    contenido_actual = ""
    if os.path.exists(ruta_completa):
        with open(ruta_completa, "r", encoding="utf-8") as f: contenido_actual = f.read()
    nuevo_contenido = st.text_area(label_texto, value=contenido_actual, height=120, key=nombre_archivo)
    if nuevo_contenido != contenido_actual:
        with open(ruta_completa, "w", encoding="utf-8") as f: f.write(nuevo_contenido)
        st.toast(f"💾 Guardado: {nombre_archivo}")

def obtener_matriculas_segmento(canal_comunicacion):
    estatus_sel = st.session_state.get('segmento_estatus')
    envios_sel = st.session_state.get('segmento_envios', 0)
    
    if not estatus_sel:
        return []
        
    conn = sqlite3.connect(DB_PATH)
    # CORRECCIÓN: Usamos la variable canal_comunicacion en el WHERE
    query_filtro = f"""
        SELECT h.matricula
        FROM historico_tablero h
        WHERE h.semana_bimestre = {semana_seleccionada}
          AND h.estatus_aprobacion = '{estatus_sel}'
          AND (
              SELECT COUNT(*) 
              FROM logs_interacciones l 
              WHERE l.matricula = h.matricula 
                AND l.semana_bimestre = h.semana_bimestre
                AND l.estatus_aprobacion = h.estatus_aprobacion 
          ) = {envios_sel}
    """
    df_mats = pd.read_sql_query(query_filtro, conn)
    conn.close()
    return df_mats['matricula'].tolist()

if "WhatsApp" in canal_elegido:
    if st.button("🔥 ENVIAR SEGUIMIENTO POR WHATSAPP", type="primary", use_container_width=True):
        matriculas_filtradas = obtener_matriculas_segmento('whatsapp')
        
        if not matriculas_filtradas:
            st.warning("⚠️ No hay alumnos en este segmento para enviar.")
        else:
            # Borramos el debug viejo para no leer reportes pasados
            if os.path.exists('debug_whatsapp.txt'):
                try: os.remove('debug_whatsapp.txt')
                except Exception: pass

            st.success(f"🚀 Ejecutando operativo de WhatsApp para {len(matriculas_filtradas)} alumnos...")
            lista_mats_str = ",".join(matriculas_filtradas)
            
            # Lanzamos el bot
            subprocess.Popen(["node", "bot_whatsapp_local.js", DB_PATH, str(semana_seleccionada), cuerpo_msg, lista_mats_str])
            
            # --- MONITOR DE PROGRESO ACTIVO ---
            with st.spinner("Espera unos minutos mientras se envian los mensajes..."):
                progreso_placeholder = st.empty()
                resumen_encontrado = False
                intentos = 0
                
                # Monitoreamos el archivo de log hasta por 10 minutos (600 iteraciones de 1s)
                while intentos < 600 and not resumen_encontrado:
                    import time
                    time.sleep(1)
                    intentos += 1
                    
                    if os.path.exists('debug_whatsapp.txt'):
                        with open('debug_whatsapp.txt', 'r', encoding='utf-8') as f:
                            log_completo = f.read()
                        
                        # Buscamos si el bot ya escribió las líneas de envío exitoso
                        lineas_envio = [linea for linea in log_completo.split('\n') if 'ENVIADO OK' in linea or 'SKIP' in linea]
                        if lineas_envio:
                            progreso_placeholder.caption(f"Última acción: {lineas_envio[-1]}")
                        
                        # Validamos si ya puso el corte de caja final
                        if "RESUMEN DEL OPERATIVO DE WHATSAPP" in log_completo:
                            resumen_encontrado = True
                            # Extraemos el fragmento del reporte final
                            reporte_final = log_completo.split("📊 RESUMEN DEL OPERATIVO DE WHATSAPP:")[1]
                            st.balloons()
                            st.success("🎉 ¡Operativo de WhatsApp completado con éxito, caón!")
                            with st.expander("👀 Ver reporte final del Bot", expanded=True):
                                st.code(f"📊 RESUMEN DEL OPERATIVO DE WHATSAPP:{reporte_final}")
                            st.rerun()
                
                if not resumen_encontrado:
                    st.info("El bot sigue procesando en segundo plano. Puedes revisar 'debug_whatsapp.txt' para ver el avance.")
                    
    st.subheader("🗂️ Edición de Textos por Estatus")
    tab_nunca, tab_np, tab_reprobado = st.tabs(["🔴 Nuncas", "🟡 NPs", "🔵 Reprobados"])
    
    with tab_nunca:
        c1, c2 = st.columns(2)
        with c1: gestionar_txt("headers_nunca.txt", "Headers:")
        with c2: gestionar_txt("footers_nunca.txt", "Footers:")
    with tab_np:
        c1, c2 = st.columns(2)
        with c1: gestionar_txt("headers_np.txt", "Headers:")
        with c2: gestionar_txt("footers_np.txt", "Footers:")
    with tab_reprobado:
        c1, c2 = st.columns(2)
        with c1: gestionar_txt("headers_reprobado.txt", "Headers:")
        with c2: gestionar_txt("footers_reprobado.txt", "Footers:")

else:
    st.info("✉️ Canal de Correo seleccionado.")
    asunto_correo = st.text_input("Asunto del correo:", value="Seguimiento de tu estatus en UTEL")
    
    if st.button("📧 ENVIAR SEGUIMIENTO POR CORREO", type="primary", use_container_width=True):
        matriculas_filtradas = obtener_matriculas_segmento('correo')
        
        if not matriculas_filtradas:
            st.warning("⚠️ No hay alumnos en este segmento para enviar.")
        else:
            with st.spinner("🚀 Enviando correos, espera unos minutos..."):
                lista_mats_str = ",".join(matriculas_filtradas)
                resultado = subprocess.run(
                    ["python3", "bot_correo_local.py", DB_PATH, str(semana_seleccionada), asunto_correo, cuerpo_msg, lista_mats_str],
                    capture_output=True,
                    text=True
                )
                
            st.balloons()
            st.success("🎉 ¡Se enviarón los correoos, puedes ver el detalle mas abajo.👇")
            with st.expander("Ver resumen del envío", expanded=True):
                st.code(resultado.stdout)