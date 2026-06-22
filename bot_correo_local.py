import sys
import sqlite3
import smtplib
import time
import os
from email.message import EmailMessage
from dotenv import load_dotenv

# Cargamos las credenciales ocultas
load_dotenv()

# Atrapamos lo que nos mande Streamlit
DB_PATH = sys.argv[1] if len(sys.argv) > 1 else 'indicador_docente.db'
SEMANA = sys.argv[2] if len(sys.argv) > 2 else 1
ASUNTO_TPL = sys.argv[3] if len(sys.argv) > 3 else 'Aviso Importante UTEL'
CUERPO_TPL = sys.argv[4] if len(sys.argv) > 4 else 'Hola {nombre}'

EMAIL_USUARIO = os.getenv("UTEL_EMAIL_USER")
EMAIL_PASSWORD = os.getenv("UTEL_EMAIL_PASS")

def enviar_email(destinatario, asunto, cuerpo, user, pwd):
    msg = EmailMessage()
    msg.set_content(cuerpo)
    msg['Subject'] = asunto
    msg['From'] = user
    msg['To'] = destinatario
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(user, pwd)
        smtp.send_message(msg)

def main():
    print("🚀 Iniciando envío automatizado de Correos...")
    
    if not EMAIL_USUARIO or not EMAIL_PASSWORD:
        print("❌ Error: No se encontraron las credenciales en el archivo .env")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Buscamos a los alumnos de la semana seleccionada
    try:
        cursor.execute("SELECT matricula, nombre_estudiante, correo FROM historico_tablero WHERE semana_bimestre = ?", (SEMANA,))
        alumnos = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"❌ Error de BD: {e}. Verifica que la columna 'correo' exista en tu tabla.")
        conn.close()
        return
        
    conn.close()

    if not alumnos:
        print("⚠️ Cero alumnos encontrados para esta semana. Nada que enviar.")
        return

    enviados_exitosos = 0
    rebotados = 0
    lista_fallidos = []

    for matricula, nombre_completo, correo_destino in alumnos:
        # Validamos que el correo tenga formato decente
        if not correo_destino or '@' not in str(correo_destino):
            rebotados += 1
            lista_fallidos.append(nombre_completo)
            continue

        # Extraemos solo el primer nombre
        primer_nombre = str(nombre_completo).strip().split(" ")[0].capitalize() if nombre_completo else "Estudiante"
        
        # Inyectamos el placeholder
        asunto_final = ASUNTO_TPL.replace('{nombre}', primer_nombre)
        cuerpo_final = CUERPO_TPL.replace('{nombre}', primer_nombre)

        try:
            enviar_email(correo_destino, asunto_final, cuerpo_final, EMAIL_USUARIO, EMAIL_PASSWORD)
            enviados_exitosos += 1
            print(f"✅ Correo enviado a: {primer_nombre} ({correo_destino})")
            time.sleep(2)  # Seguro anti-spam
        except Exception as e:
            rebotados += 1
            lista_fallidos.append(nombre_completo)
            print(f"❌ Falló el envío a {correo_destino}. Detalles: {e}")

    # Corte de caja limpio y profesional
    print("\n" + "="*45)
    print(" 📊 RESUMEN DEL OPERATIVO DE CORREOS:")
    print("="*45)
    print(f"✔️ Entregas exitosas: {enviados_exitosos}")
    print(f"⚠️ Envíos fallidos:   {rebotados}")

    if rebotados > 0:
        print(f"👀 Favor de revisar los siguientes contactos: {lista_fallidos}")
    print("="*45)

if __name__ == "__main__":
    main()