import gzip
import requests
import re
from datetime import datetime, timedelta
import pytz
from lxml import etree

# Configuración de diseño
COLUMN_WIDTH = 150  # Más ancho para mejor visualización
ROW_HEIGHT = 90     # Más alto para cada canal
PROGRAM_PADDING = 8 # Espaciado interno
MIN_PROGRAM_WIDTH = 120 # Ancho mínimo para programas cortos

# Descargar y procesar el XML
EPG_URL = "https://www.tdtchannels.com/epg/TV.xml.gz"
response = requests.get(EPG_URL)
with open("TV.xml.gz", "wb") as f:
    f.write(response.content)

with gzip.open("TV.xml.gz", "rb") as f:
    xml_data = f.read()

# Limpiar XML
cleaned_data = re.sub(r'[^\x00-\x7F]+', '', xml_data.decode('utf-8', 'ignore'))
cleaned_data = cleaned_data.split("<tv>")[-1]
cleaned_data = "<tv>" + cleaned_data

try:
    root = etree.fromstring(cleaned_data, parser=etree.XMLParser(recover=True))
except etree.XMLSyntaxError as e:
    print(f"Error al parsear el XML: {e}")
    exit(1)

# Configuración de hora
tz = pytz.timezone("Europe/Madrid")
now = datetime.now(tz)
end_time = now + timedelta(hours=3)

# Procesar programas
programs = []
for programme in root.findall("programme"):
    try:
        channel = programme.attrib.get("channel", "Desconocido")
        start = datetime.strptime(programme.attrib["start"][:14], "%Y%m%d%H%M%S")
        start = tz.localize(start)
        end = datetime.strptime(programme.attrib["stop"][:14], "%Y%m%d%H%M%S")
        end = tz.localize(end)
        
        if end <= now or start >= end_time:
            continue
            
        title = programme.find("title").text if programme.find("title") is not None else "Sin título"
        programs.append({
            'channel': channel,
            'start': start,
            'end': end,
            'title': title,
            'is_current': now >= start and now <= end
        })
    except Exception as e:
        continue

# Organizar por canales
channels = {}
for program in programs:
    if program['channel'] not in channels:
        channels[program['channel']] = []
    channels[program['channel']].append(program)

# Ordenar canales y programas
sorted_channels = sorted(channels.keys())
for channel in sorted_channels:
    channels[channel].sort(key=lambda x: x['start'])

# Crear slots de tiempo cada 30 minutos
current_slot = datetime(now.year, now.month, now.day, now.hour, 30 if now.minute >= 30 else 0)
current_slot = tz.localize(current_slot)
time_slots = []
while current_slot <= end_time:
    time_slots.append(current_slot)
    current_slot += timedelta(minutes=30)

# Función para calcular posición y ancho sin solapamientos
def calculate_program_positions(programs, time_slots):
    positioned_programs = []
    for program in programs:
        start_pos = max(0, ((program['start'] - time_slots[0]).total_seconds() / 1800) * COLUMN_WIDTH)
        end_pos = ((program['end'] - time_slots[0]).total_seconds() / 1800) * COLUMN_WIDTH
        width = max(MIN_PROGRAM_WIDTH, end_pos - start_pos)
        
        # Buscar posición vertical disponible (para evitar solapamientos)
        vertical_pos = 0
        for other in positioned_programs:
            if not (end_pos <= other['left'] or start_pos >= other['left'] + other['width']):
                vertical_pos = max(vertical_pos, other['top'] + ROW_HEIGHT)
        
        positioned_programs.append({
            'program': program,
            'left': start_pos,
            'width': width,
            'top': vertical_pos
        })
    
    return positioned_programs

# Generar HTML
html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Programación TV - Próximas horas</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f7fa;
            color: #333;
        }}
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(135deg, #e50914, #b00710);
            color: white;
            padding: 20px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        h1 {{
            margin: 0;
            font-weight: 600;
            font-size: 24px;
        }}
        .time-display {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 5px 15px;
            border-radius: 20px;
            margin-top: 10px;
            font-size: 14px;
        }}
        .program-view {{
            padding: 20px;
            position: relative;
        }}
        .timeline-container {{
            position: sticky;
            top: 80px;
            background: white;
            z-index: 50;
            padding-top: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .timeline {{
            display: flex;
            margin-left: 200px;
            height: 40px;
            background: #f8f9fa;
            border-radius: 5px 5px 0 0;
            align-items: center;
        }}
        .time-slot {{
            min-width: {COLUMN_WIDTH}px;
            text-align: center;
            font-size: 13px;
            color: #555;
            font-weight: 500;
            padding: 5px;
            flex-shrink: 0;
        }}
        .channels-container {{
            margin-top: 10px;
            position: relative;
        }}
        .channel {{
            margin-bottom: 15px;
            position: relative;
            min-height: {ROW_HEIGHT}px;
        }}
        .channel-name {{
            position: absolute;
            left: 0;
            width: 180px;
            padding: 10px 15px;
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
            height: {ROW_HEIGHT}px;
            box-sizing: border-box;
            display: flex;
            align-items: center;
            border-radius: 5px;
            z-index: 20;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .programs-container {{
            margin-left: 190px;
            position: relative;
            height: {ROW_HEIGHT}px;
            overflow: visible;
        }}
        .program {{
            position: absolute;
            padding: {PROGRAM_PADDING}px;
            border-radius: 6px;
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            height: {ROW_HEIGHT - 10}px;
            box-sizing: border-box;
            overflow: hidden;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            z-index: 10;
        }}
        .program.now {{
            background: #fff8e1;
            border-left: 4px solid #ffc107;
            z-index: 15;
        }}
        .program-title {{
            font-weight: 500;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: 14px;
        }}
        .program-time {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .now-badge {{
            display: inline-block;
            background: #e53935;
            color: white;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 8px;
        }}
        @media (max-width: 768px) {{
            .channel-name {{
                width: 120px;
                font-size: 14px;
                padding: 10px;
            }}
            .programs-container {{
                margin-left: 125px;
            }}
            .timeline {{
                margin-left: 125px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Programación TV</h1>
            <div class="time-display">Actualizado: --:--</div>
        </header>
        
        <div class="program-view">
            <div class="timeline-container">
                <div class="timeline">
                    {' '.join(
                        f'<div class="time-slot" style="min-width: {COLUMN_WIDTH}px">{slot.strftime("%H:%M")}</div>'
                        for slot in time_slots
                    )}
                </div>
            </div>
            
            <div class="channels-container">
                {''.join(
                    f'''
                    <div class="channel">
                        <div class="channel-name">{channel}</div>
                        <div class="programs-container">
                            {' '.join(
                                f'''
                                <div class="program {'now' if program['is_current'] else ''}" 
                                     style="left: {((program['start'] - time_slots[0]).total_seconds() / 1800) * COLUMN_WIDTH}px; 
                                          width: {max(MIN_PROGRAM_WIDTH, ((program['end'] - program['start']).total_seconds() / 1800) * COLUMN_WIDTH)}px">
                                    <div class="program-title">
                                        {program['title']}
                                        {'<span class="now-badge">AHORA</span>' if program['is_current'] else ''}
                                    </div>
                                    <div class="program-time">
                                        {program['start'].strftime('%H:%M')} - {program['end'].strftime('%H:%M')}
                                    </div>
                                </div>
                                '''
                                for program in channels[channel]
                                if program['end'] > time_slots[0] and program['start'] < time_slots[-1] + timedelta(minutes=30)
                            )}
                        </div>
                    </div>
                    '''
                    for channel in sorted_channels
                )}
            </div>
        </div>
    </div>
</body>
</html>
"""

html_content += '''
    <script>
        function updateTimeDisplay() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const display = document.querySelector('.time-display');
            if (display) {
                display.textContent = 'Actualizado: ' + hours + ':' + minutes;
            }
        }

        updateTimeDisplay(); // Ejecutar al cargar
        setInterval(updateTimeDisplay, 60000); // Actualizar cada minuto
    </script>
</body>
</html>
'''

with open("programacion.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Parrilla de programación generada correctamente en programacion.html")
