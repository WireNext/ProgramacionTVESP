import gzip
import requests
import re
from datetime import datetime, timedelta
import pytz
from lxml import etree

# Configuración de diseño
CHANNEL_COLUMN_WIDTH = 220
# Granularidad de la cuadrícula en minutos. Usamos 5 minutos para mayor precisión.
GRID_SLOT_MINUTES = 5

# Descargar y descomprimir XML
EPG_URL = "https://www.tdtchannels.com/epg/TV.xml.gz"
print("📥 Descargando EPG desde TV.xml.gz...")
try:
    response = requests.get(EPG_URL, timeout=10)
    response.raise_for_status()
    xml_data = gzip.decompress(response.content)
except requests.exceptions.RequestException as e:
    print(f"❌ Error al descargar el EPG: {e}")
    exit(1)

# Limpiar XML y parsear
cleaned_data = re.sub(r'[^\x00-\x7F]+', '', xml_data.decode('utf-8', 'ignore'))
# A veces, el XML viene con un preámbulo, así que lo limpiamos para que sea válido
cleaned_data = cleaned_data.split("<tv>")[-1]
cleaned_data = "<tv>" + cleaned_data

try:
    root = etree.fromstring(cleaned_data.encode(), parser=etree.XMLParser(recover=True))
except etree.XMLSyntaxError as e:
    print(f"❌ Error al parsear el XML: {e}")
    exit(1)

# Configuración de hora
tz = pytz.timezone("Europe/Madrid")
now = datetime.now(tz)
# Ventana de tiempo: 30 minutos antes de ahora y 3 horas después
start_time_window = now - timedelta(minutes=30)
end_time_window = now + timedelta(hours=3)

# Procesar programas y filtrar por ventana de tiempo
programs = []
for programme in root.findall("programme"):
    try:
        channel_id = programme.attrib.get("channel")
        start_str = programme.attrib["start"][:14]
        end_str = programme.attrib["stop"][:14]
        
        start = tz.localize(datetime.strptime(start_str, "%Y%m%d%H%M%S"))
        end = tz.localize(datetime.strptime(end_str, "%Y%m%d%H%M%S"))

        if end < start_time_window or start > end_time_window:
            continue
        
        # Ignorar programas sin título
        title_element = programme.find("title")
        title = title_element.text if title_element is not None else "Sin título"
        
        programs.append({
            'channel_id': channel_id,
            'start': start,
            'end': end,
            'title': title,
            'is_current': now >= start and now <= end
        })
    except (KeyError, ValueError, TypeError):
        # Ignorar programas con datos inválidos
        continue

print(f"✅ Programas procesados. Encontrados {len(programs)} programas en el rango de tiempo.")

# Organizar por canales
channels_data = {}
for program in programs:
    channels_data.setdefault(program['channel_id'], []).append(program)

# Obtener nombres de los canales del XML
channel_names = {channel.attrib.get("id"): channel.find("display-name").text for channel in root.findall("channel")}

# Crear franjas horarias
# El inicio de la línea de tiempo se ajusta a la media hora más cercana o a la hora
timeline_start = datetime(now.year, now.month, now.day, now.hour, 30 if now.minute > 30 else 0)
timeline_start = tz.localize(timeline_start)
timeline_end = timeline_start + timedelta(hours=3, minutes=30)

# Generar los slots de la línea de tiempo para el header (cada 30 min)
header_time_slots = []
current_slot = timeline_start
while current_slot < timeline_end:
    header_time_slots.append(current_slot)
    current_slot += timedelta(minutes=30)

# Calcular el número total de columnas para la cuadrícula (granularidad de 5 minutos)
total_grid_columns = int((timeline_end - timeline_start).total_seconds() / 60 / GRID_SLOT_MINUTES)

# Función para calcular las posiciones en la cuadrícula
def calculate_grid_positions(programs, timeline_start):
    positioned_programs = []
    
    # La columna 1 es para el nombre del canal. Los programas empiezan en la columna 2.
    timeline_offset = 2
    
    for program in programs:
        duration_minutes = (program['end'] - program['start']).total_seconds() / 60
        start_offset_minutes = (program['start'] - timeline_start).total_seconds() / 60
        
        # Calcular la columna de inicio
        start_column = int(start_offset_minutes / GRID_SLOT_MINUTES) + timeline_offset
        
        # Calcular el número de columnas que ocupa
        num_columns = int(duration_minutes / GRID_SLOT_MINUTES)
        
        if num_columns == 0:
            # Los programas muy cortos aún necesitan ocupar al menos una columna
            num_columns = 1
        
        positioned_programs.append({
            'program': program,
            'grid_column_start': start_column,
            'grid_column_span': num_columns
        })
        
    return positioned_programs

# Generar bloques HTML de canales y programas
channel_blocks = ""
for channel_id in sorted(channels_data.keys()):
    channel_name = channel_names.get(channel_id, "Canal Desconocido")
    
    # Generar el bloque del nombre del canal
    channel_blocks += f'<div class="channel-name">{channel_name}</div>'
    
    # Generar los programas de ese canal
    positioned = calculate_grid_positions(channels_data[channel_id], timeline_start)
    for item in positioned:
        program = item['program']
        
        # Construir el style para CSS Grid
        style = f"grid-column: {item['grid_column_start']} / span {item['grid_column_span']};"
        
        is_current_class = "now" if program['is_current'] else ""
        now_badge = '<span class="now-badge">AHORA</span>' if program['is_current'] else ''
        
        channel_blocks += f'''
        <div class="program {is_current_class}" style="{style}">
            <div class="program-title">{program['title']}{now_badge}</div>
            <div class="program-time">{program['start'].strftime('%H:%M')} - {program['end'].strftime('%H:%M')}</div>
        </div>
        '''

# HTML final
html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Programación TV</title>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background: #f5f7fa;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
            width: 95%;
            margin: auto;
        }}
        /* Estilos de cuadrícula para una maquetación perfecta */
        .grid-container {{
            display: grid;
            grid-template-columns: {CHANNEL_COLUMN_WIDTH}px repeat({total_grid_columns}, 1fr);
            gap: 5px; /* Reducimos el espacio entre elementos para aprovechar mejor el espacio */
            position: relative;
        }}
        .timeline {{
            grid-column: 2 / -1; /* Ocupa todas las columnas de la línea de tiempo */
            display: grid;
            grid-template-columns: repeat({len(header_time_slots)}, 1fr);
            gap: 5px;
            justify-items: center;
            align-items: center;
            padding-bottom: 10px;
            border-bottom: 1px solid #ddd;
            margin-bottom: 10px;
        }}
        .time-slot {{
            text-align: center;
            font-size: 14px;
            color: #555;
            grid-column: span 6; /* Cada slot de 30 min ocupa 6 columnas de 5 min */
        }}
        .channel-name {{
            font-weight: bold;
            padding: 10px;
            display: flex;
            align-items: center;
            grid-column: 1 / 2; /* Ocupa la primera columna */
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
        }}
        .program {{
            padding: 8px;
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            border-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            height: 80px;
            overflow: hidden;
            grid-row: span 1;
            align-self: center;
        }}
        .program.now {{
            background: #fff8e1;
            border-left: 4px solid #ffc107;
        }}
        .program-title {{
            font-weight: bold;
            font-size: 14px;
        }}
        .program-time {{
            font-size: 12px;
            color: #666;
        }}
        .now-badge {{
            background: #e53935;
            color: white;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 8px;
            margin-left: 6px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Programación TV</h1>
        <p>Actualizado: {now.strftime('%d/%m/%Y %H:%M')}</p>
        <div class="grid-container">
            <div class="timeline">
                {''.join(f'<div class="time-slot">{slot.strftime("%H:%M")}</div>' for slot in header_time_slots)}
            </div>
            {channel_blocks}
        </div>
    </div>
</body>
</html>
"""

# Guardar en archivo
with open("programacion.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ HTML generado correctamente en 'programacion.html'")
