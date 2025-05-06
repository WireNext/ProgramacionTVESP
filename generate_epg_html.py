import gzip
import requests
import re
from datetime import datetime, timedelta
import pytz
from lxml import etree

# URL del archivo EPG
EPG_URL = "https://www.tdtchannels.com/epg/TV.xml.gz"

# Descargar y descomprimir el archivo
response = requests.get(EPG_URL)
with open("TV.xml.gz", "wb") as f:
    f.write(response.content)

with gzip.open("TV.xml.gz", "rb") as f:
    xml_data = f.read()

# Limpiar y parsear el XML
cleaned_data = re.sub(r'[^\x00-\x7F]+', '', xml_data.decode('utf-8', 'ignore'))
cleaned_data = cleaned_data.split("<tv>")[-1]
cleaned_data = "<tv>" + cleaned_data

try:
    root = etree.fromstring(cleaned_data, parser=etree.XMLParser(recover=True))
except etree.XMLSyntaxError as e:
    print(f"Error al parsear el XML: {e}")
    exit(1)

# Obtener la hora actual en zona horaria de Madrid
tz = pytz.timezone("Europe/Madrid")
now = datetime.now(tz)

# Procesar programas
all_programs = []
for programme in root.findall("programme"):
    canal = programme.attrib.get("channel", "Desconocido")
    inicio = datetime.strptime(programme.attrib["start"][:14], "%Y%m%d%H%M%S")
    inicio = tz.localize(inicio)
    fin = datetime.strptime(programme.attrib["stop"][:14], "%Y%m%d%H%M%S")
    fin = tz.localize(fin)
    
    titulo = programme.find("title").text if programme.find("title") is not None else "Sin título"
    
    all_programs.append({
        'canal': canal,
        'inicio': inicio,
        'fin': fin,
        'titulo': titulo
    })

# Filtrar programas relevantes (ahora y próximas 2 horas)
end_time = now + timedelta(hours=2)
relevant_programs = [p for p in all_programs if p['fin'] > now and p['inicio'] < end_time]

# Agrupar por canal
channels = {}
for program in relevant_programs:
    if program['canal'] not in channels:
        channels[program['canal']] = []
    channels[program['canal']].append(program)

# Ordenar canales y programas
sorted_channels = sorted(channels.keys())
for channel in sorted_channels:
    channels[channel].sort(key=lambda x: x['inicio'])

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
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        header {{
            background: #e50914;
            color: white;
            padding: 15px;
            text-align: center;
        }}
        .time-marker {{
            background: #333;
            color: white;
            padding: 5px 10px;
            margin: 10px;
            display: inline-block;
            border-radius: 4px;
        }}
        .program-grid {{
            display: grid;
            grid-template-columns: 200px repeat(4, 1fr);
            overflow-x: auto;
        }}
        .channel-header {{
            position: sticky;
            left: 0;
            background: #f8f8f8;
            padding: 10px;
            border-bottom: 1px solid #ddd;
            font-weight: bold;
            z-index: 2;
        }}
        .time-slot {{
            padding: 10px;
            text-align: center;
            background: #f8f8f8;
            border-bottom: 1px solid #ddd;
            border-right: 1px solid #ddd;
            font-size: 14px;
        }}
        .program {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
            border-right: 1px solid #ddd;
            min-height: 60px;
        }}
        .current {{
            background-color: #fff8e1;
        }}
        .now {{
            background-color: #e8f4fc;
            position: relative;
        }}
        .now::after {{
            content: "AHORA";
            position: absolute;
            top: 5px;
            right: 5px;
            background: #e50914;
            color: white;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 10px;
        }}
        .program-title {{
            font-weight: 500;
            margin-bottom: 5px;
        }}
        .program-time {{
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Programación TV</h1>
            <div class="time-marker">Hora actual: {now.strftime('%H:%M')}</div>
        </header>
        
        <div class="program-grid">
            <!-- Cabecera de canales y tiempos -->
            <div class="channel-header">Canal</div>
            <!-- Las franjas horarias se generarán dinámicamente -->
            
            <!-- Programación por canal -->
            {''.join(
                f'''
                <div class="channel-header">{channel}</div>
                {' '.join(
                    f'''
                    <div class="program {'current' if program['inicio'] <= now <= program['fin'] else ''} 
                                       {'now' if program['inicio'] <= now <= program['fin'] else ''}">
                        <div class="program-title">{program['titulo']}</div>
                        <div class="program-time">
                            {program['inicio'].strftime('%H:%M')} - {program['fin'].strftime('%H:%M')}
                        </div>
                    </div>
                    '''
                    for program in channels[channel]
                )}
                '''
                for channel in sorted_channels
            )}
        </div>
    </div>
</body>
</html>
"""

# Guardar el archivo HTML
with open("programacion.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("HTML generado correctamente en programacion.html")
