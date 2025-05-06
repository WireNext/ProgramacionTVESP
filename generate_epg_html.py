import gzip
import requests
import re
from datetime import datetime, timedelta
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
    <title>Programación TV España</title>
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
            --channel-header: #f8f8f8;
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
            padding: 0;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 15px;
        }
        
        header {
            background-color: var(--primary-color);
            color: white;
            padding: 15px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        h1 {
            text-align: center;
            font-weight: 500;
            font-size: 28px;
        }
        
        .time-marker {
            position: sticky;
            left: 0;
            background-color: var(--time-marker);
            color: white;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            z-index: 10;
            margin: 10px 0;
            display: inline-block;
        }
        
        .programs-container {
            overflow-x: auto;
            position: relative;
            margin-top: 20px;
        }
        
        .timeline {
            display: flex;
            min-width: max-content;
            position: sticky;
            top: 0;
            background: white;
            z-index: 5;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .time-slot {
            width: 80px;
            flex-shrink: 0;
            text-align: center;
            font-size: 12px;
            color: #666;
            padding: 8px 5px;
            border-bottom: 1px solid var(--border-color);
            background: var(--channel-header);
        }
        
        .programs-grid {
            display: flex;
            flex-direction: column;
        }
        
        .channel-row {
            display: flex;
            min-height: 60px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .channel-header {
            position: sticky;
            left: 0;
            width: 150px;
            padding: 10px;
            background: var(--channel-header);
            font-weight: 500;
            z-index: 3;
            border-right: 1px solid var(--border-color);
            display: flex;
            align-items: center;
        }
        
        .programs-row {
            display: flex;
            flex-grow: 1;
            min-width: max-content;
        }
        
        .program {
            padding: 8px 5px;
            border-right: 1px solid var(--border-color);
            overflow: hidden;
            font-size: 13px;
            position: relative;
            min-height: 60px;
        }
        
        .program.current {
            background-color: var(--current-program);
            font-weight: 500;
        }
        
        .program-title {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .program-time {
            font-size: 11px;
            color: #666;
            margin-top: 3px;
        }
        
        .now-label {
            position: absolute;
            top: 4px;
            right: 4px;
            background: var(--primary-color);
            color: white;
            font-size: 10px;
            padding: 2px 4px;
            border-radius: 3px;
        }
        
        @media (max-width: 768px) {
            .channel-header {
                width: 120px;
                font-size: 14px;
            }
            
            .time-slot {
                width: 60px;
            }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>Guía de Programación TV</h1>
        </div>
    </header>
    
    <div class="container">
        <div class="time-marker">Ahora: """ + now.strftime("%H:%M") + """</div>
        
        <div class="programs-container">
            <div class="timeline" id="timeline">
                <!-- Franjas horarias se generarán con JavaScript -->
            </div>
            
            <div class="programs-grid" id="programsGrid">
                <!-- Programación se generará con JavaScript -->
            </div>
        </div>
    </div>

    <script>
        // Datos de programación
        const currentPrograms = """ + str(current_programs) + """;
        const nextPrograms = """ + str(next_programs) + """;
        
        // Procesar datos para la visualización
        const allPrograms = [...currentPrograms, ...nextPrograms];
        const channels = [...new Set(allPrograms.map(p => p['canal']))];
        
        // Generar franjas horarias (solo próximas 2 horas)
        function generateTimeSlots() {
            const timeline = document.getElementById('timeline');
            timeline.innerHTML = '';
            
            const now = new Date();
            const endTime = new Date(now.getTime() + 2 * 60 * 60 * 1000);
            
            // Redondear a la media hora más cercana
            let currentSlot = new Date(now);
            const minutes = currentSlot.getMinutes();
            if (minutes < 30) {
                currentSlot.setMinutes(0);
            } else {
                currentSlot.setMinutes(30);
            }
            
            // Crear franjas cada 30 minutos para las próximas 2 horas
            while (currentSlot <= endTime) {
                const hours = currentSlot.getHours().toString().padStart(2, '0');
                const mins = currentSlot.getMinutes().toString().padStart(2, '0');
                timeline.innerHTML += `<div class="time-slot">${hours}:${mins}</div>`;
                currentSlot = new Date(currentSlot.getTime() + 30 * 60 * 1000);
            }
        }
        
        // Generar la programación para todos los canales
        function generateProgramsGrid() {
            const programsGrid = document.getElementById('programsGrid');
            programsGrid.innerHTML = '';
            
            // Primero generamos todas las franjas horarias para calcular posiciones
            const timeSlots = [];
            const now = new Date();
            const endTime = new Date(now.getTime() + 2 * 60 * 60 * 1000);
            
            // Redondear a la media hora más cercana
            let currentSlot = new Date(now);
            const minutes = currentSlot.getMinutes();
            if (minutes < 30) {
                currentSlot.setMinutes(0);
            } else {
                currentSlot.setMinutes(30);
            }
            
            while (currentSlot <= endTime) {
                timeSlots.push(new Date(currentSlot));
                currentSlot = new Date(currentSlot.getTime() + 30 * 60 * 1000);
            }
            
            // Para cada canal, crear una fila
            channels.forEach(channel => {
                const channelPrograms = allPrograms.filter(p => p['canal'] === channel);
                
                if (channelPrograms.length === 0) return;
                
                const row = document.createElement('div');
                row.className = 'channel-row';
                
                // Cabecera del canal
                row.innerHTML = `<div class="channel-header">${channel}</div>`;
                
                const programsRow = document.createElement('div');
                programsRow.className = 'programs-row';
                
                // Para cada franja horaria, buscar programas
                timeSlots.forEach(slot => {
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
                        
                        programsRow.innerHTML += `
                            <div class="program ${isCurrent ? 'current' : ''}">
                                ${isNow ? '<span class="now-label">AHORA</span>' : ''}
                                <div class="program-title">${program['titulo']}</div>
                                <div class="program-time">${program['inicio']} - ${program['fin']}</div>
                            </div>
                        `;
                    } else {
                        programsRow.innerHTML += '<div class="program"></div>';
                    }
                });
                
                row.appendChild(programsRow);
                programsGrid.appendChild(row);
            });
        }
        
        // Inicializar la guía
        document.addEventListener('DOMContentLoaded', () => {
            generateTimeSlots();
            generateProgramsGrid();
        });
    </script>
</body>
</html>
"""
# Guardar el archivo HTML generado
with open("programacion.html", "w", encoding="utf-8") as f:
    f.write(html_content)
