import requests
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import re

# CONFIGURACIÓN
EPG_URL = "https://www.tdtchannels.com/epg/TV.xml.gz"
OUTPUT_FILE = "index.html"

def download_and_extract(url):
    print(f"Descargando EPG desde {url}...")
    response = requests.get(url, timeout=30)
    with open("temp_guide.xml.gz", "wb") as f:
        f.write(response.content)
    
    print("Descomprimiendo y limpiando caracteres ilegales...")
    with gzip.open("temp_guide.xml.gz", "rb") as f_in:
        content = f_in.read().decode('utf-8', errors='ignore') # Ignora caracteres que rompen el XML
        # Eliminar caracteres de control que suelen causar el "invalid token"
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
        with open("guide.xml", "w", encoding="utf-8") as f_out:
            f_out.write(content)

def generate_html():
    print("Procesando XML y generando HTML...")
    try:
        tree = ET.parse("guide.xml")
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error crítico al leer el XML: {e}")
        return

    now = datetime.now().strftime("%Y%m%d")
    
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Guía TV TDT</title>
        <style>
            :root { --bg: #0f172a; --card: #1e293b; --accent: #38bdf8; --text: #f8fafc; }
            body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
            .container { max-width: 900px; margin: auto; }
            .header { text-align: center; margin-bottom: 30px; position: sticky; top: 0; background: var(--bg); padding: 10px; z-index: 100; }
            #search { width: 100%; padding: 15px; border-radius: 12px; border: 2px solid #334155; background: var(--card); color: white; font-size: 16px; outline: none; }
            #search:focus { border-color: var(--accent); }
            .canal-card { background: var(--card); border-radius: 12px; padding: 15px; margin-bottom: 25px; border: 1px solid #334155; }
            .canal-nombre { color: var(--accent); margin-top: 0; font-size: 1.4rem; border-bottom: 2px solid #334155; padding-bottom: 10px; }
            .programa { display: flex; gap: 15px; padding: 12px 0; border-bottom: 1px solid #334155; }
            .programa:last-child { border: none; }
            .hora { font-weight: bold; color: var(--accent); min-width: 60px; }
            .titulo { font-weight: 600; margin-bottom: 4px; display: block; }
            .desc { font-size: 0.85em; color: #94a3b8; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📺 Guía TDT España</h1>
                <input type="text" id="search" placeholder="Buscar canal o película..." onkeyup="filterContent()">
                <p style="font-size: 0.8em; color: #64748b;">Actualizado: """ + datetime.now().strftime("%d/%m/%Y %H:%M") + """</p>
            </div>
            <div id="lista-canales">
    """

    canales_dict = {ch.get('id'): ch.find('display-name').text for ch in root.findall('channel')}
    programas_por_canal = {}

    for prog in root.findall('programme'):
        ch_id = prog.get('channel')
        start_time = prog.get('start')
        
        if ch_id in canales_dict and start_time.startswith(now):
            if ch_id not in programas_por_canal:
                programas_por_canal[ch_id] = []
            
            hora = f"{start_time[8:10]}:{start_time[10:12]}"
            titulo = prog.find('title').text if prog.find('title') is not None else "Sin título"
            desc = prog.find('desc').text if prog.find('desc') is not None else "Sin descripción."
            
            programas_por_canal[ch_id].append({'hora': hora, 'titulo': titulo, 'desc': desc})

    for ch_id, progs in programas_por_canal.items():
        html_content += f'<div class="canal-card"><h2 class="canal-nombre">{canales_dict[ch_id]}</h2>'
        # Ordenar por hora y mostrar los más recientes
        for p in sorted(progs, key=lambda x: x['hora'])[:8]:
            html_content += f"""
            <div class="programa">
                <div class="hora">{p['hora']}</div>
                <div>
                    <span class="titulo">{p['titulo']}</span>
                    <div class="desc">{p['desc']}</div>
                </div>
            </div>"""
        html_content += "</div>"

    html_content += """
            </div>
        </div>
        <script>
            function filterContent() {
                let input = document.getElementById('search').value.toLowerCase();
                let cards = document.getElementsByClassName('canal-card');
                for (let i = 0; i < cards.length; i++) {
                    let text = cards[i].innerText.toLowerCase();
                    cards[i].style.display = text.includes(input) ? "block" : "none";
                }
            }
        </script>
    </body>
    </html>
    """
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("¡Proceso finalizado correctamente!")

if __name__ == "__main__":
    download_and_extract(EPG_URL)
    generate_html()