import gzip
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz
import re

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

# Leer el XML línea por línea y eliminar las líneas con caracteres no válidos
cleaned_lines = []
for line in cleaned_data.splitlines():
    try:
        # Intentar parsear cada línea
        ET.fromstring(f"<root>{line}</root>")
        cleaned_lines.append(line)
    except ET.ParseError:
        # Si la línea no es válida, la ignoramos
        print(f"Se omitió una línea inválida: {line[:50]}...")

# Volver a unir las líneas limpiadas
cleaned_data = "\n".join(cleaned_lines)

# Intentar parsear el XML completo
try:
    root = ET.fromstring(cleaned_data)
except ET.ParseError as e:
    print(f"Error al parsear el XML: {e}")
    exit(1)

# Obtener la hora actual en zona horaria de Madrid
tz = pytz.timezone("Europe/Madrid")
now = datetime.now(tz)

# Crear un diccionario para almacenar la programación por canal
programacion = {}
current_programs = []
next_programs = []

for programme in root.findall("programme"):
    canal = programme.attrib["channel"]
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
    <link rel="stylesheet" href="https://cdn.datatables.net/1.12.1/css/jquery.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.12.1/js/jquery.dataTables.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f9f9f9; }
        h1 { text-align: center; margin-bottom: 40px; }
        table { width: 100%; border-collapse: collapse; background: #fff; margin-bottom: 20px; }
        th, td { padding: 10px; border: 1px solid #ccc; text-align: left; }
        th { background-color: #333; color: #fff; }
    </style>
</head>
<body>
    <h1>Programación de la Televisión Española</h1>

    <h2>Programa Actual</h2>
    <table id="current-programs" class="display">
        <thead>
            <tr>
                <th>Canal</th>
                <th>Inicio</th>
                <th>Fin</th>
                <th>Título</th>
            </tr>
        </thead>
        <tbody>
"""

# Mostrar programas actuales en emisión
for program in current_programs:
    html_content += f"""
    <tr>
        <td>{program['canal']}</td>
        <td>{program['inicio']}</td>
        <td>{program['fin']}</td>
        <td>{program['titulo']}</td>
    </tr>
    """

html_content += """
        </tbody>
    </table>

    <h2>Próximos Programas</h2>
    <table id="next-programs" class="display">
        <thead>
            <tr>
                <th>Canal</th>
                <th>Inicio</th>
                <th>Fin</th>
                <th>Título</th>
            </tr>
        </thead>
        <tbody>
"""

# Mostrar los próximos programas
for program in next_programs:
    html_content += f"""
    <tr>
        <td>{program['canal']}</td>
        <td>{program['inicio']}</td>
        <td>{program['fin']}</td>
        <td>{program['titulo']}</td>
    </tr>
    """

html_content += """
        </tbody>
    </table>

    <script>
        $(document).ready(function() {
            $('#current-programs').DataTable();
            $('#next-programs').DataTable();
        });
    </script>
</body>
</html>
"""

# Guardar el archivo HTML
with open("programacion_tv.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("El archivo HTML se ha generado con éxito.")
