import sqlite3

DB_NAME = "indicador_docente.db"

def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Tabla de Configuración (Credenciales)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS config_docente (
        correo_usuario TEXT PRIMARY KEY,
        contrasena_aplicacion TEXT NOT NULL
    )
    """)
    
    # 2. Tabla de Histórico del Tablero Docente
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_tablero (
        id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
        semana_bimestre INTEGER NOT NULL,
        matricula TEXT NOT NULL,
        nombre_estudiante TEXT,
        correo_estudiante TEXT,
        celular TEXT,
        estatus_aprobacion TEXT,
        nacionalidad TEXT,
        fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 3. Tabla de Logs de Envío e Interacción
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs_interacciones (
        id_interaccion INTEGER PRIMARY KEY AUTOINCREMENT,
        matricula TEXT NOT NULL,
        semana_bimestre INTEGER NOT NULL,
        canal TEXT NOT NULL,
        fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        respondio INTEGER DEFAULT 0
    )
    """)
    
    conn.commit()
    conn.close()
    print("¡Cámara! Base de datos y tablas listas de forma local.")

if __name__ == "__main__":
    inicializar_db()