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
for programme in root.findall("programme"):  # Corregido de "programme" a "programme"
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

# Crear slots de tiempo cada 30 minutos (asegurando zona horaria)
current_slot = datetime(now.year, now.month, now.day, now.hour, 30 if now.minute >= 30 else 0)
current_slot = tz.localize(current_slot)  # Asegurar que tiene zona horaria
time_slots = []
while current_slot <= end_time:
    time_slots.append(current_slot)
    current_slot += timedelta(minutes=30)

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
        .program-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .program-table th {{
            background: #f8f9fa;
            position: sticky;
            top: 0;
            z-index: 10;
            padding: 12px 15px;
            text-align: left;
            border-bottom: 2px solid #ddd;
            font-weight: 600;
        }}
        .program-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            vertical-align: top;
        }}
        .channel-name {{
            font-weight: 600;
            color: #2c3e50;
            background: #f8f9fa;
            position: sticky;
            left: 0;
            min-width: 180px;
        }}
        .time-slot-header {{
            min-width: 100px;
            text-align: center;
            font-weight: 500;
            color: #7f8c8d;
        }}
        .program-cell {{
            min-width: 200px;
            border-left: 1px solid #eee;
        }}
        .program {{
            padding: 8px;
            border-radius: 4px;
            margin-bottom: 5px;
        }}
        .current-program {{
            background: #e3f2fd;
            border-left: 3px solid #2196f3;
        }}
        .now-program {{
            background: #fff8e1;
            border-left: 3px solid #ffc107;
        }}
        .program-title {{
            font-weight: 500;
            margin-bottom: 4px;
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
            .container {{
                padding: 0;
            }}
            .program-table td, .program-table th {{
                padding: 8px 10px;
                font-size: 14px;
            }}
            .channel-name {{
                min-width: 120px;
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
        
        <div style="overflow-x: auto;">
            <table class="program-table">
                <thead>
                    <tr>
                        <th class="channel-name">Canal</th>
                        {' '.join(
                            f'<th class="time-slot-header">{slot.strftime("%H:%M")}</th>'
                            for slot in time_slots
                        )}
                    </tr>
                </thead>
                <tbody>
                    {''.join(
                        f'''
                        <tr>
                            <td class="channel-name">{channel}</td>
                            {' '.join(
                                f'''
                                <td class="program-cell">
                                    {''.join(
                                        f'''
                                        <div class="program {'current-program' if program['is_current'] else ''} {'now-program' if program['start'] <= now <= program['end'] else ''}">
                                            <div class="program-title">
                                                {program['title']}
                                                {'' if not (program['start'] <= now <= program['end']) else '<span class="now-badge">AHORA</span>'}
                                            </div>
                                            <div class="program-time">
                                                {program['start'].strftime('%H:%M')} - {program['end'].strftime('%H:%M')}
                                            </div>
                                        </div>
                                        '''
                                        for program in channels[channel]
                                        if program['start'].strftime('%H:%M') == slot.strftime('%H:%M') or 
                                           (program['start'] <= slot and program['end'] > slot)
                                    )}
                                </td>
                                '''
                                for slot in time_slots
                            )}
                        </tr>
                        '''
                        for channel in sorted_channels
                    )}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

with open("programacion.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Parrilla de programación generada correctamente en programacion.html")
