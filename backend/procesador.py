import sqlite3
import pandas as pd
import os
import re

DB_PATH = "indicador_docente.db"

def normalizar_texto(texto):
    if pd.isna(texto) or texto is None:
        return ""
    txt_str = str(texto).strip()
    if txt_str.lower() in ["nan", "none", "null", ""]:
        return ""
    return txt_str

# NUEVA FUNCIÓN: Limpia los teléfonos de raíz antes de que toquen la BD
def normalizar_celular(texto):
    if pd.isna(texto) or texto is None:
        return ""
    
    # Lo pasamos a string limpio
    txt_str = str(texto).strip()
    
    # Si viene con el .0 de los floats de Pandas, se lo mochamos de inmediato
    if txt_str.endswith('.0'):
        txt_str = txt_str[:-2]
        
    # Quitamos cualquier pinche carácter que no sea un número (guiones, espacios, signos de más)
    txt_str = re.sub(r'\D', '', txt_str)
    
    if txt_str.lower() in ["nan", "none", "null", ""]:
        return ""
    return txt_str

def procesar_y_guardar_tablero(ruta_archivo, semana):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_tablero (
            matricula TEXT,
            nombre_estudiante TEXT,
            celular TEXT,
            correo TEXT,
            estatus_aprobacion TEXT,
            semana_bimestre INTEGER,
            estado_seguimiento TEXT DEFAULT 'Por Contactar',
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (matricula, semana_bimestre)
        )
    """)
    conn.commit()

    if str(ruta_archivo).lower().endswith('.csv'):
        df = pd.read_csv(ruta_archivo)
    else:
        df = pd.read_excel(ruta_archivo)
    
    # NOMBRES EXACTOS Y FIJOS DEL EXCEL:
    col_matricula = 'Total Estudiantes'
    col_nombre = 'Estudiante'
    col_celular = 'CELULAR'
    col_estatus = 'Aprobacion'
    col_correo = 'Correo_estudiante'
    
    for col in [col_matricula, col_nombre, col_celular, col_estatus]:
        if col not in df.columns:
            raise ValueError(f"Falta la columna exacta: '{col}' en tu archivo.")
        
    registros_procesados = 0
    
    for _, row in df.iterrows():
        mat = normalizar_texto(row[col_matricula])
        nom = normalizar_texto(row[col_nombre])
        # USA LA NUEVA FUNCIÓN AQUÍ PARA EL CELULAR:
        cel = normalizar_celular(row[col_celular])
        mail = normalizar_texto(row[col_correo])
        est = normalizar_texto(row[col_estatus])
        
        if not mat or not nom or not cel:
            continue
            
        cursor.execute("""
            INSERT INTO historico_tablero (matricula, nombre_estudiante, celular, correo, estatus_aprobacion, semana_bimestre, estado_seguimiento)
            VALUES (?, ?, ?, ?, ?, ?, 'Por Contactar')
            ON CONFLICT(matricula, semana_bimestre) DO UPDATE SET
                nombre_estudiante = excluded.nombre_estudiante,
                celular = excluded.celular,
                estatus_aprobacion = excluded.estatus_aprobacion
        """, (mat, nom, cel, mail, est, int(semana)))
        
        registros_procesados += 1
        
    conn.commit()
    conn.close()
    return registros_procesados