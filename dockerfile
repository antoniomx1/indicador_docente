# Usamos una base de Python ligera
FROM python:3.11-slim

# Evitamos basura y forzamos la salida en consola
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalamos dependencias del sistema: Node.js, npm, y Chromium para WhatsApp Web
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Definimos nuestra carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero los archivos de requerimientos para aprovechar el caché
COPY requirements.txt package.json package-lock.json* ./

# Instalamos librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalamos los módulos de Node.js
RUN npm install

# Copiamos todo el resto del código al contenedor
COPY . .

# Exponemos el puerto donde vive Streamlit
EXPOSE 8501

# Arrancamos Streamlit directo
CMD ["streamlit", "run", "backend/app_frontend.py", "--server.port=8501", "--server.address=0.0.0.0"]