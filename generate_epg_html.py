import gzip
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz

# URL del archivo EPG
EPG_URL = "https://www.tdtchannels.com/epg/TV.xml.gz"

# Descargar y descomprimir el archivo
response = requests.get(EPG_URL)
with open("TV.xml.gz", "wb") as f:
    f.write(response.content)

with gzip.open("TV.xml.gz", "rb") as f:
    xml_data = f.read()

# Parsear el XML
root = ET.fromstring(xml_data)

# Obtener la hora actual en zona horaria de Madrid
tz = pytz.timezone("Europe/Madrid")
now = datetime.now(tz)

# Crear un diccionario para almacenar la programación por canal
programacion = {}

for programme in root.findall("programme"):
    canal = programme.attrib["channel"]
    inicio = datetime.strptime(programme.attrib["start"][:14], "%Y%m%d%H%M%S")
    inicio = tz.localize(inicio)
    fin = datetime.strptime(programme.attrib["stop"][:14], "%Y%m%d%H%M%S")
    fin = tz.localize(fin)

    if inicio <= now <= fin:
        titulo = programme.find("title").text if programme.find("title") is not None else "Sin título"
        if canal not in programacion:
            programacion[canal] = []
        programacion[canal].append({
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
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f9f9f9; }
        h1 { text-align: center; margin-bottom: 40px; }
        .canal { margin-bottom: 40px; }
        table { width: 100%; border-collapse: collapse; background: #fff; }
        th, td { padding: 10px; border: 1px solid #ccc; text-align: left; }
        th { background-color: #333; color: #fff; }
        @media (max-width: 600px) {
            table, thead, tbody, th, td, tr { display: block; }
            th { position: sticky; top: 0; }
            td { border: none; padding: 8px 10px; }
        }
    </style>
</head>
<body>
    <h1>Programación de la Televisión Española</h1>
"""

for canal, programas in programacion.items():
    html_content += f"<div class='canal'>\n<h2>{canal}</h2>\n<table>\n<tr><th>Inicio</th><th>Fin</th><th>Programa</th></tr>\n"
    for prog in programas:
        html_content += f"<tr><td>{prog['inicio']}</td><td>{prog['fin']}</td><td>{prog['titulo']}</td></tr>\n"
    html_content += "</table>\n</div>\n"

html_content += """
</body>
</html>
"""

# Guardar en index.html
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
