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
            --channel-tab-active: white;
            --channel-tab-inactive: #f5f5f5;
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
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            background-color: var(--time-marker);
            color: white;
            padding: 3px 10px;
            border-radius: 0 0 4px 4px;
            font-size: 12px;
            font-weight: bold;
            z-index: 10;
        }
        
        .channels-container {
            display: flex;
            position: relative;
            margin-top: 40px;
        }
        
        .channel-tabs {
            width: 150px;
            flex-shrink: 0;
            border-right: 1px solid var(--border-color);
            background: var(--channel-tab-inactive);
        }
        
        .channel-tab {
            padding: 15px 10px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            transition: all 0.2s;
            font-size: 14px;
            font-weight: 500;
        }
        
        .channel-tab:hover {
            background-color: var(--hover-color);
        }
        
        .channel-tab.active {
            background-color: var(--channel-tab-active);
            font-weight: 700;
            border-right: 3px solid var(--primary-color);
        }
        
        .programs-container {
            flex-grow: 1;
            overflow-x: auto;
            position: relative;
        }
        
        .timeline {
            display: flex;
            min-width: max-content;
            position: relative;
            padding-top: 40px;
        }
        
        .time-slot {
            width: 80px;
            flex-shrink: 0;
            text-align: center;
            font-size: 12px;
            color: #666;
            padding: 5px;
            border-right: 1px dashed var(--border-color);
        }
        
        .programs-grid {
            display: flex;
            flex-direction: column;
        }
        
        .channel-programs {
            display: flex;
            height: 60px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .program {
            padding: 8px 5px;
            border-right: 1px solid var(--border-color);
            overflow: hidden;
            font-size: 13px;
            position: relative;
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
            top: -20px;
            left: 0;
            font-size: 11px;
            color: var(--time-marker);
            font-weight: bold;
        }
        
        @media (max-width: 768px) {
            .channel-tabs {
                width: 120px;
            }
            
            .time-slot {
                width: 60px;
            }
            
            .channel-tab {
                padding: 12px 8px;
                font-size: 13px;
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
        
        <div class="channels-container">
            <div class="channel-tabs" id="channelTabs">
                <!-- Pestañas de canales se generarán con JavaScript -->
            </div>
            
            <div class="programs-container">
                <div class="timeline" id="timeline">
                    <!-- Franjas horarias se generarán con JavaScript -->
                </div>
                
                <div class="programs-grid" id="programsGrid">
                    <!-- Programación se generará con JavaScript -->
                </div>
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
        
        // Generar franjas horarias
        function generateTimeSlots() {
            const timeline = document.getElementById('timeline');
            timeline.innerHTML = '';
            
            // Crear franjas cada 30 minutos desde las 6:00 hasta las 00:00
            for (let hour = 6; hour <= 24; hour++) {
                const hourStr = hour === 24 ? '00' : String(hour).padStart(2, '0');
                timeline.innerHTML += `
                    <div class="time-slot">${hourStr}:00</div>
                    <div class="time-slot">${hourStr}:30</div>
                `;
            }
        }
        
        // Generar pestañas de canales
        function generateChannelTabs() {
            const channelTabs = document.getElementById('channelTabs');
            channelTabs.innerHTML = '';
            
            channels.forEach((channel, index) => {
                channelTabs.innerHTML += `
                    <div class="channel-tab ${index === 0 ? 'active' : ''}" 
                         data-channel="${channel}" 
                         onclick="showChannel('${channel}')">
                        ${channel}
                    </div>
                `;
            });
        }
        
        // Generar la programación
        function generateProgramsGrid() {
            const programsGrid = document.getElementById('programsGrid');
            programsGrid.innerHTML = '';
            
            channels.forEach(channel => {
                const channelPrograms = allPrograms.filter(p => p['canal'] === channel);
                const channelRow = document.createElement('div');
                channelRow.className = 'channel-programs';
                channelRow.id = `channel-${channel.replace(/\s+/g, '-')}`;
                channelRow.style.display = 'none';
                
                // Ordenar programas por hora de inicio
                channelPrograms.sort((a, b) => {
                    return a['inicio'].localeCompare(b['inicio']);
                });
                
                // Crear celdas de programa
                channelPrograms.forEach(program => {
                    const startTime = new Date(`2000-01-01T${program['inicio']}:00`);
                    const endTime = new Date(`2000-01-01T${program['fin']}:00`);
                    
                    // Calcular duración en minutos
                    const duration = (endTime - startTime) / (1000 * 60);
                    const width = (duration / 30) * 80; // 80px = 30 minutos
                    
                    const isCurrent = currentPrograms.some(p => 
                        p['canal'] === program['canal'] && 
                        p['titulo'] === program['titulo']
                    );
                    
                    channelRow.innerHTML += `
                        <div class="program ${isCurrent ? 'current' : ''}" style="width: ${width}px">
                            ${isCurrent ? '<div class="now-label">AHORA</div>' : ''}
                            <div class="program-title">${program['titulo']}</div>
                            <div class="program-time">${program['inicio']} - ${program['fin']}</div>
                        </div>
                    `;
                });
                
                programsGrid.appendChild(channelRow);
            });
            
            // Mostrar el primer canal por defecto
            if (channels.length > 0) {
                showChannel(channels[0]);
            }
        }
        
        // Mostrar programación de un canal específico
        function showChannel(channelName) {
            // Actualizar pestañas activas
            document.querySelectorAll('.channel-tab').forEach(tab => {
                tab.classList.remove('active');
                if (tab.dataset.channel === channelName) {
                    tab.classList.add('active');
                }
            });
            
            // Ocultar todas las filas de programación
            document.querySelectorAll('.channel-programs').forEach(row => {
                row.style.display = 'none';
            });
            
            // Mostrar la fila del canal seleccionado
            const channelId = `channel-${channelName.replace(/\s+/g, '-')}`;
            document.getElementById(channelId).style.display = 'flex';
        }
        
        // Inicializar la guía
        document.addEventListener('DOMContentLoaded', () => {
            generateTimeSlots();
            generateChannelTabs();
            generateProgramsGrid();
        });
    </script>
</body>
</html>
"""
# Guardar el archivo HTML generado
with open("programacion.html", "w", encoding="utf-8") as f:
    f.write(html_content)
