# Indicador Docente: Sistema de Gestión Académica y Comunicación Automatizada

## Descripción
El presente proyecto es una solución integral diseñada para la gestión académica y el seguimiento automatizado de alumnos en entornos universitarios. El sistema permite el procesamiento de indicadores de rendimiento académico (BI) y la comunicación personalizada a través de canales digitales (WhatsApp y Correo Electrónico).

## Arquitectura del Sistema
El sistema se caracteriza por su arquitectura híbrida, optimizada para ejecutarse en entornos locales con requerimientos mínimos de infraestructura:

*   **Frontend y Orquestación:** Desarrollado en Python con el framework **Streamlit**, proporcionando una interfaz ágil para la carga de datos y visualización de indicadores.
*   **Motor de Automatización (WhatsApp):** Implementado en **Node.js** utilizando `whatsapp-web.js` y `Puppeteer`, permitiendo la automatización robusta de mensajes sin depender de APIs de terceros con costos elevados.
*   **Procesamiento de Datos:** Módulo de análisis en Python para la evaluación de trayectorias académicas y generación de reportes históricos.

## Funcionalidades Principales
*   **Monitoreo de Indicadores:** Generación de métricas de seguimiento semanal para identificar alumnos con riesgo de deserción o reprobación.
*   **Automatización de Comunicación:** Envío masivo y personalizado de notificaciones vía WhatsApp y Correo Electrónico.
*   **Gestión de Datos:** Procesamiento eficiente de archivos Excel con integración directa a una base de datos local (SQLite) para la persistencia del histórico.

## Instalación y Ejecución
El sistema ha sido diseñado para simplificar la puesta en marcha por parte del usuario final (docente) mediante una automatización de despliegue:

1.  Clonar el repositorio.
2.  Configurar las credenciales en el archivo `.env` (a partir de la plantilla proporcionada).
3.  Ejecutar el script `arrancar_indicador.bat` para realizar la instalación automática de dependencias y despliegue del entorno.

## Tecnologías Utilizadas
*   Python 3.11+
*   Node.js & npm
*   Streamlit
*   Puppeteer / Chromium
*   Pandas & Openpyxl
