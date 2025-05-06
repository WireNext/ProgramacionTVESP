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
    <style>
        :root {
            --primary-color: #3498db;
            --secondary-color: #2980b9;
            --background-color: #f8f9fa;
            --text-color: #333;
            --border-color: #ddd;
            --hover-color: #f1f1f1;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background-color);
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 15px;
        }
        
        h1 {
            text-align: center;
            margin: 30px 0;
            color: var(--primary-color);
            font-weight: 300;
        }
        
        .accordion {
            width: 100%;
            margin-bottom: 20px;
            border-radius: 5px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .accordion-item {
            margin-bottom: 5px;
            background: white;
        }
        
        .accordion-header {
            padding: 15px 20px;
            background-color: var(--primary-color);
            color: white;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.3s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .accordion-header:hover {
            background-color: var(--secondary-color);
        }
        
        .accordion-header::after {
            content: '+';
            font-size: 20px;
            transition: transform 0.3s ease;
        }
        
        .accordion-item.active .accordion-header::after {
            content: '-';
        }
        
        .accordion-content {
            padding: 0;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
        }
        
        .accordion-item.active .accordion-content {
            max-height: 1000px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        th {
            background-color: var(--hover-color);
            font-weight: 500;
        }
        
        tr:hover {
            background-color: var(--hover-color);
        }
        
        .channel-name {
            font-weight: bold;
            color: var(--secondary-color);
        }
        
        .now-playing {
            background-color: #e8f4fc;
        }
        
        .time {
            font-family: monospace;
            color: #666;
        }
        
        @media (max-width: 768px) {
            th, td {
                padding: 8px 10px;
                font-size: 13px;
            }
            
            .accordion-header {
                padding: 12px 15px;
                font-size: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Programación de la Televisión Española</h1>
        
        <div class="accordion">
            <div class="accordion-item">
                <div class="accordion-header">Programación Actual</div>
                <div class="accordion-content">
                    <table>
                        <thead>
                            <tr>
                                <th>Canal</th>
                                <th>Horario</th>
                                <th>Programa</th>
                            </tr>
                        </thead>
                        <tbody>
"""

# Mostrar programas actuales en emisión
for program in current_programs:
    html_content += f"""
                            <tr class="now-playing">
                                <td class="channel-name">{program['canal']}</td>
                                <td class="time">{program['inicio']} - {program['fin']}</td>
                                <td><strong>{program['titulo']}</strong></td>
                            </tr>
    """

html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="accordion-item">
                <div class="accordion-header">Próximos Programas</div>
                <div class="accordion-content">
                    <table>
                        <thead>
                            <tr>
                                <th>Canal</th>
                                <th>Horario</th>
                                <th>Programa</th>
                            </tr>
                        </thead>
                        <tbody>
"""

# Mostrar los próximos programas
for program in next_programs:
    html_content += f"""
                            <tr>
                                <td class="channel-name">{program['canal']}</td>
                                <td class="time">{program['inicio']} - {program['fin']}</td>
                                <td>{program['titulo']}</td>
                            </tr>
    """

html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const accordionItems = document.querySelectorAll('.accordion-item');
            
            accordionItems.forEach(item => {
                const header = item.querySelector('.accordion-header');
                
                header.addEventListener('click', () => {
                    const currentlyActive = document.querySelector('.accordion-item.active');
                    
                    // Si el item clickeado ya está activo, lo cerramos
                    if (currentlyActive && currentlyActive === item) {
                        currentlyActive.classList.remove('active');
                        return;
                    }
                    
                    // Cerramos el item activo (si hay alguno)
                    if (currentlyActive) {
                        currentlyActive.classList.remove('active');
                    }
                    
                    // Abrimos el item clickeado
                    item.classList.add('active');
                });
            });
            
            // Abrir el primer item por defecto
            if (accordionItems.length > 0) {
                accordionItems[0].classList.add('active');
            }
        });
    </script>
</body>
</html>
"""
# Guardar el archivo HTML generado
with open("programacion.html", "w", encoding="utf-8") as f:
    f.write(html_content)
