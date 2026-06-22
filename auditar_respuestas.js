const { Client, LocalAuth } = require('whatsapp-web.js');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

const dbPath = process.argv[2] || 'indicador_docente.db';
const semana = process.argv[3] || 1;

function logAuditor(texto) {
    const timestamp = new Date().toISOString().replace(/T/, ' ').replace(/\..+/, '');
    fs.appendFileSync('debug_auditor.txt', `[${timestamp}] ${texto}\n`, 'utf8');
    console.log(texto);
}

logAuditor(`\n==================================================`);
logAuditor(`[AUDITOR] Iniciando auditoría de chats para la Semana ${semana}`);

const client = new Client({
    authStrategy: new LocalAuth({ clientId: "utel_local", dataPath: './.wwebjs_auth' }),
    puppeteer: { 
        headless: false, // Lo dejamos visible para que use tu sesión del Chrome real
        executablePath: '/usr/bin/google-chrome',
        args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"] 
    }
});

client.on('ready', async () => {
    logAuditor('[AUDITOR] Conectado a WhatsApp Web con éxito. Escaneando base de datos...');
    
    let db = new sqlite3.Database(dbPath);
    
    // Traemos solo a los alumnos que ya contactamos o que siguen en espera en esta semana
    const query = `SELECT matricula, nombre_estudiante, celular FROM historico_tablero WHERE semana_bimestre = ? AND estado_seguimiento IN ('Contactado', 'Esperando Respuesta')`;
    
    db.all(query, [semana], async (err, rows) => {
        if (err) {
            logAuditor(`[💥 ERR] No se pudo leer SQLite: ${err.message}`);
            db.close();
            process.exit(1);
        }
        
        logAuditor(`[AUDITOR] Alumnos pendientes de auditar esta semana: ${rows.length}`);
        
        if (rows.length === 0) {
            logAuditor(`[AUDITOR] No hay alumnos en estado 'Contactado' o 'Esperando Respuesta'. Nada que auditar.`);
            db.close();
            process.exit(0);
        }

        for (const alumno of rows) {
            let baseNum = alumno.celular.replace(/\D+/g, "");
            let numeroAValidar = baseNum.startsWith("52") ? baseNum : "521" + baseNum;
            if (baseNum.length === 10) numeroAValidar = "521" + baseNum;
            
            let wid = numeroAValidar + "@c.us";
            logAuditor(`\n[REVISANDO] ${alumno.nombre_estudiante} (Mat: ${alumno.matricula}) | WID: ${wid}`);

            try {
                const chat = await client.getChatById(wid);
                // Jalamos los últimos 15 mensajes del chat para tener buen margen de revisión
                const mensajes = await chat.fetchMessages({ limit: 15 });
                
                if (!mensajes || mensajes.length === 0) {
                    logAuditor(`[INFO] Chat vacío o inalcanzable. Se queda en espera.`);
                    continue;
                }

                // 1. Encontrar el timestamp de nuestro último mensaje enviado por la ráfaga
                let miUltimoEnvioTs = 0;
                for (let i = mensajes.length - 1; i >= 0; i--) {
                    if (mensajes[i].fromMe) {
                        miUltimoEnvioTs = mensajes[i].timestamp;
                        break;
                    }
                }

                if (miUltimoEnvioTs === 0) {
                    logAuditor(`[WARN] No encontré ningún mensaje tuyo en este chat. Saltando.`);
                    continue;
                }

                // 2. Contar cuántas respuestas envió el alumno DESPUÉS de nuestro envío masivo
                let respuestasAlumno = 0;
                mensajes.forEach(msg => {
                    if (!msg.fromMe && msg.timestamp > miUltimoEnvioTs) {
                        respuestasAlumno++;
                    }
                });

                logDebugAuditor(alumno.matricula, respuestasAlumno, miUltimoEnvioTs, db, semana);

            } catch (e) {
                logAuditor(`[❌ CHAT ERR] No se pudo abrir el chat de ${alumno.matricula}: ${e.message}`);
            }
            
            // Pausa breve entre chats para no saturar Puppeteer
            await new Promise(r => setTimeout(r, 1500));
        }

        logAuditor(`\n[AUDITOR FIN] Auditoría de la semana completada con éxito.`);
        db.close();
        process.exit(0);
    });
});

function logDebugAuditor(matricula, respuestasAlumno, miUltimoEnvioTs, db, semana) {
    logAuditor(`[CONTEO] Respuestas del alumno después de tu ráfaga: ${respuestasAlumno}`);

    if (respuestasAlumno >= 2) {
        // !!! LOGICA DE ORO TRASPASADA !!! Se marca como RESPONDIDO
        logAuditor(`[🎉 RESPONDIDO] ¡Macheo Humano! El alumno contestó ${respuestasAlumno} veces. Actualizando BD...`);
        db.run(`UPDATE historico_tablero SET estado_seguimiento = 'Respondido' WHERE matricula = ? AND semana_bimestre = ?`, [matricula, semana]);
    } else {
        // Si no ha contestado 2 veces, revisamos si ya pasaron 24 horas desde tu envío para mandarlo a la lista de castigo
        const ahoraTs = Math.floor(Date.now() / 1000);
        const horasPasadas = (ahoraTs - miUltimoEnvioTs) / 3600;
        
        if (horasPasadas >= 24) {
            logAuditor(`[⏰ ALERTA] Ya pasaron ${horasPasadas.toFixed(1)} horas sin 2 respuestas reales. Estado: Esperando Respuesta.`);
            db.run(`UPDATE historico_tablero SET estado_seguimiento = 'Esperando Respuesta' WHERE matricula = ? AND semana_bimestre = ?`, [matricula, ...[semana]]);
        } else {
            logAuditor(`[INFO] Lleva ${horasPasadas.toFixed(1)} horas desde el envío. Aún en tiempo de gracia.`);
        }
    }
}

client.initialize().catch(err => logAuditor(`[CRISIS INIT] ${err.message}`));