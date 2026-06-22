import webview
import subprocess
import time
import os
import sys

def arrancar_app():
    # Apuntamos a tu carpeta backend real
    script_frontend = os.path.join("backend", "app_frontend.py")
    
    # Lanzamos Streamlit en background
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", script_frontend, "--server.headless", "true", "--server.port", "8501"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Esperamos a que levante el puerto local
    time.sleep(3)
    
    # Abrimos la ventana ligera que no traga RAM
    webview.create_window("Indicador Docente UTEL", "http://localhost:8501", width=1024, height=768)
    webview.start()
    
    # Al cerrar la ventana, matamos Streamlit
    proc.terminate()

if __name__ == "__main__":
    arrancar_app()