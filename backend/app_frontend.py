import streamlit as st
import pandas as pd
import sqlite3
import os
import subprocess
import plotly.express as px
from procesador import procesar_y_guardar_tablero

DB_PATH = "indicador_docente.db"

st.set_page_config(page_title="Tablero BI UTEL", page_icon="📊", layout="wide")

st.title("📊 Indicador Docente (Módulo BI)")
st.markdown("---")

st.sidebar.header("⚙️ Configuración")
semana_seleccionada = st.sidebar.selectbox("Selecciona la Semana del Bimestre:", options=[1, 2, 3, 4, 5, 6, 7, 8], index=0)

# --- SECCIÓN 1: CARGA DE DATOS ---
st.header("📥 Cargar Tablero Docente")
archivo_subido = st.file_uploader("Arrastra aquí el archivo Excel o CSV")

if archivo_subido is not None:
    nombre_temporal = archivo_subido.name
    with open(nombre_temporal, "wb") as f:
        f.write(archivo_subido.getbuffer())
        
    if st.button("🚀 Procesar e Inyectar Datos (UPSERT)"):
        with st.spinner("Procesando..."):
            try:
                insertados = procesar_y_guardar_tablero(nombre_temporal, semana_seleccionada)
                st.success(f"¡Cámara! Se procesaron {insertados} registros para la Semana {semana_seleccionada}.")
                st.rerun()
            except Exception as e:
                st.error(f"Error en el proceso: {e}")
            finally:
                if os.path.exists(nombre_temporal):
                    os.remove(nombre_temporal)

st.markdown("---")

# --- SECCIÓN 2: GRÁFICOS ---
st.header(f"📈 Radiografía de la Semana {semana_seleccionada}")
try:
    conn = sqlite3.connect(DB_PATH)
    df_stats = pd.read_sql_query(f"SELECT estatus_aprobacion, COUNT(*) as cantidad FROM historico_tablero WHERE semana_bimestre = {semana_seleccionada} GROUP BY estatus_aprobacion", conn)
    conn.close()
    
    if not df_stats.empty:
        df_stats = df_stats.sort_values(by='cantidad', ascending=False)
        col1, col2 = st.columns([1, 2])
        with col1: st.dataframe(df_stats, use_container_width=True)
        with col2:
            fig = px.funnel(df_stats, x='cantidad', y='estatus_aprobacion', color='estatus_aprobacion')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sube tu archivo para generar el gráfico, caón.")
except Exception:
    pass

st.markdown("---")

# --- SECCIÓN 3: CANAL DE COMUNICACIÓN ---
st.markdown("<h2 style='text-align: center; background-color: #1E3A8A; color: white; padding: 15px; border-radius: 10px;'>Selección de Canal de Seguimiento</h2>", unsafe_allow_html=True)
canal_elegido = st.radio("👇 Elige por dónde vas a contactar a los alumnos:", ["💬 WhatsApp Masivo", "📧 Correo Electrónico"], horizontal=True)

st.markdown("---")
st.header("🚀 Ejecutar Seguimiento Masivo")
cuerpo_msg = st.text_area("Cuerpo del mensaje:", value="Noto que no has ingresado al aula esta semana. ¿Todo bien por allá?")

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

if "WhatsApp" in canal_elegido:
    if st.button("🔥 ENVIAR SEGUIMIENTO POR WHATSAPP", type="primary", use_container_width=True):
        st.success("🚀 Levantando bot de WhatsApp...")
        subprocess.Popen(["node", "bot_whatsapp_local.js", DB_PATH, str(semana_seleccionada), cuerpo_msg])
    
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
        # Le ponemos el spinner para que se vea que está jalando
        with st.spinner("🚀 Enviando correos, aguanta vara caón..."):
            
            # Usamos subprocess.run para que Streamlit se espere a que termine
            resultado = subprocess.run(
                ["python3", "bot_correo_local.py", DB_PATH, str(semana_seleccionada), asunto_correo, cuerpo_msg],
                capture_output=True, # Atrapamos los prints de la terminal
                text=True
            )
            
        # Cuando sale del spinner, ya terminó el script
        st.success("🎉 ¡Ya quedó, caón! Operativo de correos terminado.")
        
        # Le ponemos un desplegable mamalón para ver el reporte exacto
        with st.expander("👀 Ver resumen del envío"):
            st.code(resultado.stdout)