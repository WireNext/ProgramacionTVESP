import gzip
import requests
import re
from datetime import datetime
import pytz
from lxml import etree  # Usamos lxml en lugar de xml.etree.ElementTree

# URL del archivo EPG
EPG_URL = "https://www.tdtchannels.com/epg/TV.xml.gz"

# Descargar y descomprimir el archivo
response = requests.get(EPG_URL)
with open("TV.xml.gz", "wb") as f:
    f.write(response.content)

with gzip.open("TV.xml.gz", "rb") as f:
    xml_data = f.read()

# Limpiar caracteres problemáticos antes de parsear
cleaned_data = re.sub(r'[^\x00-\x7F]+', '', xml_data.decode('utf-8', 'ignore'))

# Eliminar todo lo que esté antes del primer <tv> (o <root> si es el caso)
cleaned_data = cleaned_data.split("<tv>")[-1]  # Tomamos solo lo que está después de <tv>
cleaned_data = "<tv>" + cleaned_data  # Añadimos de nuevo el <tv> de apertura

# Intentamos parsear el XML con lxml con la opción recover=True
try:
    root = etree.fromstring(cleaned_data, parser=etree.XMLParser(recover=True))
except etree.XMLSyntaxError as e:
    print(f"Error al parsear el XML: {e}")
    print("Fragmento del XML problemático (alrededor de la línea de error):")
    print(cleaned_data[32200:32240])  # Muestra el fragmento alrededor del error
    exit(1)

# Obtener la hora actual en zona horaria de Madrid
tz = pytz.timezone("Europe/Madrid")
now = datetime.now(tz)

# Crear un diccionario para almacenar la programación por canal
programacion = {}
current_programs = []
next_programs = []

for programme in root.findall("programme"):
    canal = programme.attrib.get("channel", "Desconocido")
    inicio = datetime.strptime(programme.attrib["start"][:14], "%Y%m%d%H%M%S")
    inicio = tz.localize(inicio)
    fin = datetime.strptime(programme.attrib["stop"][:14], "%Y%m%d%H%M%S")
    fin = tz.localize(fin)

    # Filtramos por los programas actuales y los próximos
    if inicio <= now <= fin:
        titulo = programme.find("title").text if programme.find("title") is not None else "Sin título"
        current_programs.append({
            "canal": canal,
            "inicio": inicio.strftime("%H:%M"),
            "fin": fin.strftime("%H:%M"),
            "titulo": titulo
        })
    elif now < inicio:
        titulo = programme.find("title").text if programme.find("title") is not None else "Sin título"
        next_programs.append({
            "canal": canal,
            "inicio": inicio.strftime("%H:%M"),
            "fin": fin.strftime("%H:%M"),
            "titulo": titulo
        })

# Generar el HTML
html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Programación TV España - Próximas 2 horas</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #e50914;
            --secondary-color: #b00710;
            --background-color: #f5f5f5;
            --text-color: #333;
            --border-color: #e1e1e1;
            --hover-color: #f1f1f1;
            --time-marker: #e50914;
            --current-program: #fff8e1;
            --now-playing: #e8f4fc;
            --channel-bg: #f9f9f9;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Roboto', sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background-color);
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        header {
            background-color: var(--primary-color);
            color: white;
            padding: 15px 20px;
        }
        
        h1 {
            font-weight: 500;
            font-size: 24px;
        }
        
        .current-time {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 3px 10px;
            border-radius: 4px;
            margin-left: 10px;
            font-size: 14px;
        }
        
        .time-range {
            text-align: center;
            padding: 10px;
            background: var(--secondary-color);
            color: white;
            font-weight: 500;
        }
        
        .program-grid {
            display: grid;
            grid-template-columns: 150px repeat(4, 1fr);
            overflow-x: auto;
        }
        
        .channel-row {
            display: contents;
        }
        
        .channel-name {
            position: sticky;
            left: 0;
            background: var(--channel-bg);
            padding: 12px 15px;
            border-bottom: 1px solid var(--border-color);
            font-weight: 500;
            z-index: 2;
        }
        
        .time-slot {
            text-align: center;
            padding: 8px 5px;
            border-bottom: 1px solid var(--border-color);
            background: var(--channel-bg);
            font-size: 13px;
            font-weight: 500;
        }
        
        .program {
            padding: 12px 8px;
            border-bottom: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            font-size: 13px;
            position: relative;
        }
        
        .program.current {
            background-color: var(--current-program);
            border-left: 3px solid var(--primary-color);
        }
        
        .program.now {
            background-color: var(--now-playing);
            font-weight: 500;
        }
        
        .program-title {
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .program-time {
            font-size: 11px;
            color: #666;
        }
        
        .now-label {
            position: absolute;
            top: 4px;
            right: 8px;
            background: var(--primary-color);
            color: white;
            font-size: 10px;
            padding: 2px 5px;
            border-radius: 3px;
        }
        
        @media (max-width: 768px) {
            .program-grid {
                grid-template-columns: 120px repeat(4, 1fr);
            }
            
            .channel-name {
                padding: 10px 12px;
                font-size: 14px;
            }
            
            .program {
                padding: 10px 6px;
                font-size: 12px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Programación TV <span class="current-time">Ahora: """ + now.strftime("%H:%M") + """</span></h1>
        </header>
        
        <div class="time-range">
            Próximas 2 horas: """ + now.strftime("%H:%M") + """ - """ + (now + timedelta(hours=2)).strftime("%H:%M") + """
        </div>
        
        <div class="program-grid" id="programGrid">
            <!-- Cabecera con franjas horarias -->
            <div class="channel-row">
                <div class="channel-name">Canal</div>
                <!-- Las franjas horarias se generarán con JavaScript -->
            </div>
            
            <!-- Las filas de programación se generarán con JavaScript -->
        </div>
    </div>

    <script>
        // Datos de programación
        const currentPrograms = """ + str(current_programs) + """;
        const nextPrograms = """ + str(next_programs) + """;
        
        // Procesar datos para la visualización
        const allPrograms = [...currentPrograms, ...nextPrograms];
        const channels = [...new Set(allPrograms.map(p => p['canal']))];
        
        // Función para formatear hora como HH:MM
        function formatTime(date) {
            return date.toTimeString().substr(0, 5);
        }
        
        // Obtener el rango de las próximas 2 horas
        const now = new Date();
        const endTime = new Date(now.getTime() + 2 * 60 * 60 * 1000);
        
        // Generar franjas horarias cada 30 minutos
        function generateTimeSlots() {
            const timeSlots = [];
            let currentSlot = new Date(now);
            
            // Redondear a la media hora más cercana
            const minutes = currentSlot.getMinutes();
            if (minutes < 30) {
                currentSlot.setMinutes(0);
            } else {
                currentSlot.setMinutes(30);
            }
            
            // Generar slots hasta cubrir 2 horas
            while (currentSlot <= endTime) {
                timeSlots.push(new Date(currentSlot));
                currentSlot = new Date(currentSlot.getTime() + 30 * 60 * 1000);
            }
            
            return timeSlots;
        }
        
        // Generar la cuadrícula de programación
        function generateProgramGrid() {
            const timeSlots = generateTimeSlots();
            const programGrid = document.getElementById('programGrid');
            
            // Generar cabecera con franjas horarias
            const headerRow = document.querySelector('.channel-row');
            timeSlots.forEach(slot => {
                headerRow.innerHTML += `
                    <div class="time-slot">${formatTime(slot)}</div>
                `;
            });
            
            // Generar filas para cada canal
            channels.forEach(channel => {
                const channelPrograms = allPrograms
                    .filter(p => p['canal'] === channel)
                    .sort((a, b) => a['inicio'].localeCompare(b['inicio']));
                
                if (channelPrograms.length === 0) return;
                
                const row = document.createElement('div');
                row.className = 'channel-row';
                row.innerHTML = `<div class="channel-name">${channel}</div>`;
                
                // Para cada franja horaria, encontrar el programa correspondiente
                timeSlots.forEach((slot, index) => {
                    const slotEnd = new Date(slot.getTime() + 30 * 60 * 1000);
                    
                    // Buscar programa que se solape con esta franja
                    const program = channelPrograms.find(p => {
                        const pStart = new Date(`2000-01-01T${p['inicio']}:00`);
                        const pEnd = new Date(`2000-01-01T${p['fin']}:00`);
                        return pStart < slotEnd && pEnd > slot;
                    });
                    
                    if (program) {
                        const isCurrent = currentPrograms.some(p => 
                            p['canal'] === program['canal'] && 
                            p['titulo'] === program['titulo']
                        );
                        
                        const isNow = isCurrent && 
                            new Date(`2000-01-01T${program['inicio']}:00`) <= now && 
                            new Date(`2000-01-01T${program['fin']}:00`) >= now;
                        
                        row.innerHTML += `
                            <div class="program ${isCurrent ? 'current' : ''} ${isNow ? 'now' : ''}">
                                ${isNow ? '<span class="now-label">AHORA</span>' : ''}
                                <div class="program-title">${program['titulo']}</div>
                                <div class="program-time">${program['inicio']} - ${program['fin']}</div>
                            </div>
                        `;
                    } else {
                        row.innerHTML += '<div class="program"></div>';
                    }
                });
                
                programGrid.appendChild(row);
            });
        }
        
        // Inicializar la cuadrícula al cargar la página
        document.addEventListener('DOMContentLoaded', generateProgramGrid);
    </script>
</body>
</html>
"""
# Guardar el archivo HTML generado
with open("programacion.html", "w", encoding="utf-8") as f:
    f.write(html_content)
