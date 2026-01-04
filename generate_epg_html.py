import requests
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
import os

# CONFIGURACIÓN
EPG_URL = "https://www.tdtchannels.com/epg/TV.xml.gz"
OUTPUT_FILE = "index.html"

def download_and_extract(url):
    print(f"Descargando EPG desde {url}...")
    response = requests.get(url, timeout=30)
    with open("temp_guide.xml.gz", "wb") as f:
        f.write(response.content)
    
    print("Descomprimiendo...")
    with gzip.open("temp_guide.xml.gz", "rb") as f_in:
        with open("guide.xml", "wb") as f_out:
            f_out.write(f_in.read())

def generate_html():
    print("Procesando XML y generando HTML...")
    tree = ET.parse("guide.xml")
    root = tree.getroot()
    
    now = datetime.now().strftime("%Y%m%d") # Para filtrar programas de hoy
    
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Guía TV TDT</title>
        <style>
            :root { --bg: #0f172a; --card: #1e293b; --accent: #38bdf8; --text: #f8fafc; }
            body { font-family: 'Inter', system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
            .container { max-width: 1000px; margin: auto; }
            .header { text-align: center; margin-bottom: 30px; }
            #search { width: 100%; padding: 12px; border-radius: 8px; border: none; background: var(--card); color: white; margin-bottom: 20px; box-sizing: border-box; }
            .canal-card { background: var(--card); border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
            .canal-nombre { color: var(--accent); border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between; }
            .programa { display: grid; grid-template-columns: 80px 1fr; gap: 15px; padding: 10px 0; border-bottom: 1px solid #334155; }
            .programa:last-child { border: none; }
            .hora { font-weight: bold; color: #94a3b8; }
            .titulo { font-weight: 600; margin-bottom: 4px; }
            .desc { font-size: 0.85em; color: #94a3b8; line-height: 1.4; }
            .tag-vivo { background: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7em; text-transform: uppercase; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Guía TDT Channels</h1>
                <input type="text" id="search" placeholder="Buscar canal o programa..." onkeyup="filterContent()">
                <p style="font-size: 0.8em; color: #64748b;">Actualizado: """ + datetime.now().strftime("%d/%m/%Y %H:%M") + """</p>
            </div>
            <div id="lista-canales">
    """

    # Mapeo de nombres de canales
    canales_dict = {ch.get('id'): ch.find('display-name').text for ch in root.findall('channel')}
    
    # Agrupar programas por canal (solo los de hoy para no pesar demasiado)
    programas_por_canal = {}
    for prog in root.findall('programme'):
        ch_id = prog.get('channel')
        start_time = prog.get('start')
        
        if ch_id in canales_dict and start_time.startswith(now):
            if ch_id not in programas_por_canal:
                programas_por_canal[ch_id] = []
            
            hora = f"{start_time[8:10]}:{start_time[10:12]}"
            titulo = prog.find('title').text if prog.find('title') is not None else "Sin título"
            desc = prog.find('desc').text if prog.find('desc') is not None else ""
            
            programas_por_canal[ch_id].append({'hora': hora, 'titulo': titulo, 'desc': desc})

    # Generar bloques de canales
    for ch_id, progs in programas_por_canal.items():
        html_content += f'<div class="canal-card"> <div class="canal-nombre"><h2>{canales_dict[ch_id]}</h2></div>'
        for p in progs[:6]: # Limitamos a los próximos 6 programas por canal
            html_content += f"""
            <div class="programa">
                <div class="hora">{p['hora']}</div>
                <div>
                    <div class="titulo">{p['titulo']}</div>
                    <div class="desc">{p['desc'][:150]}...</div>
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

if __name__ == "__main__":
    download_and_extract(EPG_URL)
    generate_html()
    # Limpieza
    if os.path.exists("guide.xml"): os.remove("guide.xml")
    if os.path.exists("temp_guide.xml.gz"): os.remove("temp_guide.xml.gz")