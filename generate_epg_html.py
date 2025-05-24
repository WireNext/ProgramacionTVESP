import gzip
import requests
import re
from datetime import datetime, timedelta
import pytz
from lxml import etree

# Configuración de diseño
COLUMN_WIDTH = 150
ROW_HEIGHT = 90
PROGRAM_PADDING = 8
MIN_PROGRAM_WIDTH = 120

# Descargar y descomprimir XML
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
    root = etree.fromstring(cleaned_data.encode(), parser=etree.XMLParser(recover=True))
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
    except Exception:
        continue

# Organizar por canales
channels = {}
for program in programs:
    channels.setdefault(program['channel'], []).append(program)

for channel in channels:
    channels[channel].sort(key=lambda x: x['start'])

# Crear franjas horarias cada 30 min
current_slot = datetime(now.year, now.month, now.day, now.hour, 30 if now.minute >= 30 else 0)
current_slot = tz.localize(current_slot)
time_slots = []
while current_slot <= end_time:
    time_slots.append(current_slot)
    current_slot += timedelta(minutes=30)

# Función de posicionamiento
def calculate_program_positions(programs, time_slots):
    positioned = []
    for program in programs:
        start_pos = max(0, ((program['start'] - time_slots[0]).total_seconds() / 1800) * COLUMN_WIDTH)
        end_pos = ((program['end'] - time_slots[0]).total_seconds() / 1800) * COLUMN_WIDTH
        width = max(MIN_PROGRAM_WIDTH, end_pos - start_pos)

        vertical_pos = 0
        for other in positioned:
            if not (end_pos <= other['left'] or start_pos >= other['left'] + other['width']):
                vertical_pos = max(vertical_pos, other['top'] + ROW_HEIGHT)

        positioned.append({
            'program': program,
            'left': start_pos,
            'width': width,
            'top': vertical_pos
        })
    return positioned

# Generar bloques HTML de canales y programas
channel_blocks = ""
for channel in sorted(channels.keys()):
    channel_html = f'<div class="channel"><div class="channel-name">{channel}</div><div class="programs-container">'
    positioned = calculate_program_positions(channels[channel], time_slots)
    for item in positioned:
        program = item['program']
        channel_html += f'''
        <div class="program {'now' if program['is_current'] else ''}" 
             style="left: {item['left']}px; width: {item['width']}px; top: {item['top']}px">
            <div class="program-title">{program['title']}
                {'<span class="now-badge">AHORA</span>' if program['is_current'] else ''}
            </div>
            <div class="program-time">{program['start'].strftime('%H:%M')} - {program['end'].strftime('%H:%M')}</div>
        </div>
        '''
    channel_html += "</div></div>"
    channel_blocks += channel_html

# HTML final
html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Programación TV</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f5f7fa;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .timeline {{
            display: flex;
            margin-left: 220px;
        }}
        .time-slot {{
            min-width: {COLUMN_WIDTH}px;
            text-align: center;
            font-size: 14px;
            color: #555;
            padding: 5px;
        }}
        .channel {{
            position: relative;
            margin-bottom: 30px;
        }}
        .channel-name {{
            position: absolute;
            left: 0;
            width: 220px;
            font-weight: bold;
        }}
        .programs-container {{
            margin-left: 220px;
            position: relative;
            min-height: {ROW_HEIGHT}px;
        }}
        .program {{
            position: absolute;
            padding: {PROGRAM_PADDING}px;
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            border-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            height: {ROW_HEIGHT - 10}px;
            overflow: hidden;
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
        <div class="timeline">
            {''.join(f'<div class="time-slot">{slot.strftime("%H:%M")}</div>' for slot in time_slots)}
        </div>
        {channel_blocks}
    </div>
</body>
</html>
"""

# Guardar en archivo
with open("guia_tv.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ HTML generado correctamente en 'guia_tv.html'")
