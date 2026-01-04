import requests
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import re

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
    print("Procesando XML con modo de recuperación de errores...")
    now = datetime.now().strftime("%Y%m%d")
    canales_dict = {}
    programas_por_canal = {}

    # Leemos el archivo de forma secuencial para evitar errores de memoria y tokens
    try:
        context = ET.iterparse("guide.xml", events=("start", "end"))
        context = iter(context)
        event, root = next(context)
        
        for event, elem in context:
            try:
                if event == "end" and elem.tag == "channel":
                    ch_id = elem.get('id')
                    name = elem.find('display-name').text if elem.find('display-name') is not None else ch_id
                    canales_dict[ch_id] = name
                    root.clear() # Liberar memoria
                
                if event == "end" and elem.tag == "programme":
                    ch_id = elem.get('channel')
                    start_time = elem.get('start')
                    
                    if start_time and start_time.startswith(now):
                        if ch_id not in programas_por_canal:
                            programas_por_canal[ch_id] = []
                        
                        hora = f"{start_time[8:10]}:{start_time[10:12]}"
                        titulo = elem.find('title').text if elem.find('title') is not None else "Sin título"
                        desc = elem.find('desc').text if elem.find('desc') is not None else ""
                        
                        programas_por_canal[ch_id].append({'hora': hora, 'titulo': titulo, 'desc': desc})
                    root.clear() # Liberar memoria
            except Exception:
                continue # Si un elemento concreto falla, saltamos al siguiente
    except Exception as e:
        print(f"Aviso: Interrupción en la lectura (algunos canales pueden faltar): {e}")

    # --- DISEÑO HTML ---
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Guía TV TDT</title>
        <style>
            :root { --bg: #0f172a; --card: #1e293b; --accent: #38bdf8; --text: #f8fafc; }
            body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
            .container { max-width: 900px; margin: auto; }
            .header { text-align: center; margin-bottom: 30px; position: sticky; top: 0; background: var(--bg); padding: 15px; border-bottom: 1px solid #334155; }
            #search { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #334155; background: var(--card); color: white; }
            .canal-card { background: var(--card); border-radius: 12px; padding: 15px; margin-bottom: 20px; border: 1px solid #334155; }
            .canal-nombre { color: var(--accent); border-bottom: 1px solid #334155; padding-bottom: 8px; margin-bottom: 10px; }
            .programa { display: flex; gap: 15px; padding: 8px 0; border-bottom: 1px solid #1e293b; }
            .hora { color: var(--accent); font-weight: bold; min-width: 55px; }
            .desc { font-size: 0.85em; color: #94a3b8; margin-top: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📺 Guía TDT</h1>
                <input type="text" id="search" placeholder="Buscar canal..." onkeyup="filter()">
                <p style="font-size: 0.7em; color: #64748b;">Actualizado: """ + datetime.now().strftime("%H:%M") + """</p>
            </div>
            <div id="lista">
    """

    for ch_id in sorted(programas_por_canal.keys()):
        nombre = canales_dict.get(ch_id, ch_id)
        progs = sorted(programas_por_canal[ch_id], key=lambda x: x['hora'])
        
        html_content += f'<div class="canal-card"><h2 class="canal-nombre">{nombre}</h2>'
        for p in progs[:6]:
            html_content += f"""
            <div class="programa">
                <span class="hora">{p['hora']}</span>
                <div>
                    <b class="titulo">{p['titulo']}</b>
                    <div class="desc">{p['desc']}</div>
                </div>
            </div>"""
        html_content += "</div>"

    html_content += """
            </div>
        </div>
        <script>
            function filter() {
                let q = document.getElementById('search').value.toLowerCase();
                let cards = document.getElementsByClassName('canal-card');
                for (let c of cards) {
                    c.style.display = c.innerText.toLowerCase().includes(q) ? "block" : "none";
                }
            }
        </script>
    </body></html>"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Web generada con éxito.")

if __name__ == "__main__":
    download_and_extract(EPG_URL)
    generate_html()