import gzip
import requests
import re
from datetime import datetime, timedelta
import pytz
from lxml import etree

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
end_time = now + timedelta(hours=2)

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

# Crear slots de tiempo cada 30 minutos (solo para referencia)
current_slot = datetime(now.year, now.month, now.day, now.hour, 30 if now.minute >= 30 else 0)
current_slot = tz.localize(current_slot)
time_slots = []
while current_slot <= end_time:
    time_slots.append(current_slot)
    current_slot += timedelta(minutes=30)

# Calcular el ancho mínimo de cada columna (30 minutos)
COLUMN_WIDTH = 100  # en píxeles

# Generar HTML
html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Programación TV - Próximas 2 horas</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f0f2f5;
        }}
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        header {{
            background: #e50914;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .time-display {{
            background: rgba(0,0,0,0.2);
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 14px;
        }}
        .program-container {{
            overflow-x: auto;
            padding: 15px;
        }}
        .timeline {{
            display: flex;
            margin-left: 200px;
            position: relative;
            height: 30px;
        }}
        .time-slot {{
            min-width: {COLUMN_WIDTH}px;
            text-align: center;
            font-size: 12px;
            color: #7f8c8d;
            border-bottom: 1px solid #ddd;
        }}
        .channels {{
            margin-top: 10px;
        }}
        .channel-row {{
            display: flex;
            margin-bottom: 10px;
            position: relative;
            height: 60px;
        }}
        .channel-name {{
            position: absolute;
            left: 0;
            width: 180px;
            padding: 10px;
            background: #f8f9fa;
            font-weight: 600;
            border-radius: 4px;
            height: 100%;
            box-sizing: border-box;
        }}
        .programs {{
            display: flex;
            margin-left: 190px;
            height: 100%;
            position: relative;
        }}
        .program {{
            position: absolute;
            padding: 8px;
            border-radius: 4px;
            background: #e3f2fd;
            border-left: 3px solid #2196f3;
            height: 100%;
            box-sizing: border-box;
            overflow: hidden;
        }}
        .program.now {{
            background: #fff8e1;
            border-left: 3px solid #ffc107;
        }}
        .program-title {{
            font-weight: 500;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .program-time {{
            font-size: 12px;
            color: #7f8c8d;
        }}
        .now-badge {{
            display: inline-block;
            background: #e53935;
            color: white;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 10px;
            margin-left: 8px;
        }}
        @media (max-width: 768px) {{
            .channel-name {{
                width: 120px;
                font-size: 14px;
            }}
            .programs {{
                margin-left: 125px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Programación TV</h1>
            <div class="time-display">Actualizado: {now.strftime('%H:%M')}</div>
        </header>
        
        <div class="program-container">
            <div class="timeline">
                {' '.join(
                    f'<div class="time-slot" style="min-width: {COLUMN_WIDTH}px">{slot.strftime("%H:%M")}</div>'
                    for slot in time_slots
                )}
            </div>
            
            <div class="channels">
                {''.join(
                    f'''
                    <div class="channel-row">
                        <div class="channel-name">{channel}</div>
                        <div class="programs">
                            {' '.join(
                                f'''
                                <div class="program {'now' if program['is_current'] else ''}" 
                                     style="left: {((program['start'] - time_slots[0]).total_seconds() / 1800) * COLUMN_WIDTH}px; 
                                          width: {((program['end'] - program['start']).total_seconds() / 1800) * COLUMN_WIDTH}px">
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

with open("programacion.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Parrilla de programación generada correctamente en programacion.html")
