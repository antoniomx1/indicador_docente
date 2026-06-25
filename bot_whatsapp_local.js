const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

// Argumentos desde Python
const dbPath = process.argv[2] || 'indicador_docente.db';
const semana = process.argv[3] || 1;
const cuerpoMensajeStreamlit = process.argv[4] || ''; 
const matriculasFiltradasStr = process.argv[5] || ''; // <-- Recibimos la lista desde Streamlit

const RUTA_TEMPLATES_DIR = path.resolve(process.cwd(), "Mensajes/templates");

// Función rastreadora para no andar a ciegas
function logDebug(texto) {
    const timestamp = new Date().toISOString().replace(/T/, ' ').replace(/\..+/, '');
    fs.appendFileSync('debug_whatsapp.txt', `[${timestamp}] ${texto}\n`, 'utf8');
    console.log(texto);
}

logDebug(`\n==================================================`);
logDebug(`[INICIO] Bot despertado. BD=${dbPath}, Semana=${semana}`);

// Inicializamos el Chrome real de tu Debian
const client = new Client({
    authStrategy: new LocalAuth({ clientId: "utel_local", dataPath: './.wwebjs_auth' }),
    puppeteer: { 
        headless: false, 
        executablePath: '/usr/bin/google-chrome',
        args: [
            "--no-sandbox", 
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled"
        ] 
    }
});

client.on('ready', () => {
    logDebug('[WA] ¡Navegador en estado READY! Chats cargados con éxito.');
    enviarCampanaMamon();
});

// --- INGENIERÍA ANTI-BAN (CARRUSELES) ---
function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

function leerLineasOpciones(ruta) {
    if (!fs.existsSync(ruta)) {
        logDebug(`[WARN] Archivo de plantilla no encontrado: ${ruta}`);
        return [];
    }
    return fs.readFileSync(ruta, "utf8").replace(/\r\n/g, "\n").split("\n").map(s => s.trim()).filter(s => s && !s.startsWith("#"));
}

function parseNombreCorto(completo) {
    if (!completo) return "";
    return completo.split(" ")[0];
}

const soloDigitos = (s) => (s || "").toString().replace(/\D+/g, "");

// === FUNCIÓN PARA EVITAR EL "NO LID" ===
async function resolverWid(client, numero) {
  const base = soloDigitos(numero);
  const candidatos = [];
  if (/^52\d{10}$/.test(base)) {
    candidatos.push(base, base.replace(/^52/, "521"));
  } else if (/^\d{10}$/.test(base)) {
    candidatos.push("521" + base, "52" + base);
  } else if (/^\d{7,15}$/.test(base)) {
    candidatos.push(base);
  } else {
    logDebug(`[WID] Número con formato inválido: "${numero}" -> "${base}"`);
    return null;
  }
  for (const cand of candidatos) {
    try {
      logDebug(`[WID] getNumberId(${cand})`);
      const info = await client.getNumberId(cand);
      if (info && info._serialized) return info._serialized;
    } catch (e) {
      logDebug(`[WID] No resolvió ${cand} - ${e?.message || e}`);
    }
  }
  return null;
}

async function enviarCampanaMamon() {
    logDebug(`[SQLITE] Abriendo base de datos: ${dbPath}`);
    let db = new sqlite3.Database(dbPath);
    
    // 1. Armamos la consulta base por semana
    let query = `SELECT matricula, nombre_estudiante, celular, estatus_aprobacion FROM historico_tablero WHERE semana_bimestre = ?`;
    let params = [semana];

    // 2. Si recibimos una lista de matrículas específicas, inyectamos el filtro IN (...)
    if (matriculasFiltradasStr) {
        const listado = matriculasFiltradasStr.split(',').map(m => `'${m.strip ? m.strip() : m.trim()}'`).join(',');
        query += ` AND matricula IN (${listado})`;
        logDebug(`[FILTRO ACTIVO] Solo se enviará a las matrículas del segmento seleccionado.`);
    }

    logDebug(`[SQLITE] Lanzando consulta de alumnos para la semana: ${semana}`);

    db.all(query, params, async (err, rows) => {
        if (err) { 
            logDebug(`[💥 ERROR SQLITE] No se pudo leer la tabla: ${err.message}`); 
            db.close();
            return; 
        }
        
        logDebug(`[SQLITE] Filas devueltas por la consulta: ${rows ? rows.length : 0}`);
        
        if (!rows || !rows.length) { 
            logDebug("[⚠️ ALERTA] SQLite regresó CERO alumnos. Nada que enviar."); 
            db.close();
            return; 
        }

        const mapCategorias = { nunca: [], np: [], reprobado: [] };
        rows.forEach(r => {
            const est = (r.estatus_aprobacion || "").toLowerCase();
            if (est.includes("nunca")) mapCategorias.nunca.push(r);
            else if (est.includes("np") || est.includes("participa")) mapCategorias.np.push(r);
            else if (est.includes("reprob")) mapCategorias.reprobado.push(r);
        });

        logDebug(`[CATEGORIAS] Clasificados -> Nuncas: ${mapCategorias.nunca.length}, NPs: ${mapCategorias.np.length}, Reprobados: ${mapCategorias.reprobado.length}`);

        const headers = {
            nunca: shuffle(leerLineasOpciones(path.join(RUTA_TEMPLATES_DIR, "headers_nunca.txt"))),
            np: shuffle(leerLineasOpciones(path.join(RUTA_TEMPLATES_DIR, "headers_np.txt"))),
            reprobado: shuffle(leerLineasOpciones(path.join(RUTA_TEMPLATES_DIR, "headers_reprobado.txt")))
        };
        const footers = {
            nunca: shuffle(leerLineasOpciones(path.join(RUTA_TEMPLATES_DIR, "footers_nunca.txt"))),
            np: shuffle(leerLineasOpciones(path.join(RUTA_TEMPLATES_DIR, "footers_np.txt"))),
            reprobado: shuffle(leerLineasOpciones(path.join(RUTA_TEMPLATES_DIR, "footers_reprobado.txt")))
        };

        let mezcla = [];
        let maxLen = Math.max(mapCategorias.nunca.length, mapCategorias.np.length, mapCategorias.reprobado.length);
        for (let i = 0; i < maxLen; i++) {
            if (mapCategorias.nunca[i]) mezcla.push({ cat: 'nunca', reg: mapCategorias.nunca[i] });
            if (mapCategorias.np[i]) mezcla.push({ cat: 'np', reg: mapCategorias.np[i] });
            if (mapCategorias.reprobado[i]) mezcla.push({ cat: 'reprobado', reg: mapCategorias.reprobado[i] });
        }

        logDebug(`[MEZCLA] Total en cola intercalada para enviar: ${mezcla.length}`);

        let hIdx = { nunca: 0, np: 0, reprobado: 0 };
        let fIdx = { nunca: 0, np: 0, reprobado: 0 };

        let enviadosExitosos = 0;
        let rebotados = 0;
        let listaFallidos = [];

        for (const item of mezcla) {
            const { cat, reg } = item;
            
            let primerNombre = reg.nombre_estudiante ? reg.nombre_estudiante.split(" ")[0] : "";
            
            let headerRaw = headers[cat].length ? headers[cat][hIdx[cat] % headers[cat].length] : "";
            let footerRaw = footers[cat].length ? footers[cat][fIdx[cat] % footers[cat].length] : "";
            
            hIdx[cat]++;
            fIdx[cat]++;

            let header = headerRaw.replace(/\{\{\s*nombre_corto\s*\}\}/gi, primerNombre);
            let footer = footerRaw.replace(/\{\{\s*nombre_corto\s*\}\}/gi, primerNombre);
            let body = cuerpoMensajeStreamlit.replace(/{nombre}/gi, primerNombre);

            let msgFinal = [header, body, footer].filter(Boolean).join("\n\n").trim();

            const wid = await resolverWid(client, reg.celular);

            if (!wid) {
                logDebug(`[⚠️ SKIP] No se pudo resolver el WID legítimo para: ${reg.celular} (${reg.nombre_estudiante})`);
                rebotados++;
                listaFallidos.push(reg.nombre_estudiante || reg.celular);
                continue;
            }

            logDebug(`[ENVIANDO] A matricula: ${reg.matricula} | WID Resuelto: ${wid}`);

            try {
                await client.sendMessage(wid, msgFinal);
                logDebug(`[🚀 ENVIADO OK] -> ${reg.matricula}`);
                enviadosExitosos++;
                
                // Conservamos el registro guardando el estatus actual para que el conteo funcione
                db.run(`INSERT INTO logs_interacciones (matricula, semana_bimestre, canal, estatus_aprobacion) VALUES (?, ?, 'whatsapp', ?)`, [reg.matricula, semana, reg.estatus_aprobacion], (e) => {
                    if (e) logDebug(`[DB LOG ERR] No se pudo guardar interaccion: ${e.message}`);
                });
            } catch (e) {
                logDebug(`[❌ ERR ENVIO] Matricula ${reg.matricula}: ${e.message}`);
                rebotados++;
                listaFallidos.push(reg.nombre_estudiante || reg.celular);
            }

            const delay = 6000 + Math.floor(Math.random() * 6000);
            logDebug(`[PAUSA] Esperando ${delay / 1000} segundos antes del siguiente...`);
            await new Promise(r => setTimeout(r, delay));
        }

        db.close();
        logDebug("[FIN COMUNICACION] Todos los mensajes de la cola listos.");

        // >>> CORTE DE CAJA Y CIERRE <<<
        logDebug("\n" + "=".repeat(45));
        logDebug(" 📊 RESUMEN DEL OPERATIVO DE WHATSAPP:");
        logDebug("=".repeat(45));
        logDebug(`✔️ Entregas exitosas: ${enviadosExitosos}`);
        logDebug(`⚠️ Envíos fallidos:   ${rebotados}`);
        if (rebotados > 0) {
            logDebug(`👀 Favor de revisar los siguientes contactos: ${listaFallidos.join(", ")}`);
        }
        logDebug("=".repeat(45) + "\n");

        logDebug("[CIERRE] Apagando el bot y cerrando el navegador...");
        await client.destroy();
        logDebug("[CIERRE] Proceso terminado limpiecito.");
        process.exit(0);
    });
}

client.initialize().catch(err => logDebug(`[INIT CRISIS] ${err.message}`));