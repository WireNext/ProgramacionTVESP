import requests
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import json

EPG_URL = "https://www.tdtchannels.com/epg/TV.xml.gz"
XML_GZ_FILE = "temp_guide.xml.gz"
XML_FILE = "guide.xml"
OUTPUT_FILE = "index.html"
TEMPLATE_FILE = "template.html"


def download_and_extract(url):
    print(f"Descargando EPG desde {url}...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    with open(XML_GZ_FILE, "wb") as f:
        f.write(response.content)

    print("Descomprimiendo...")
    with gzip.open(XML_GZ_FILE, "rb") as f_in:
        with open(XML_FILE, "wb") as f_out:
            f_out.write(f_in.read())
    print("Descarga completada.")


def parse_epg():
    print("Procesando XML...")
    now = datetime.now().strftime("%Y%m%d")
    canales_dict = {}
    programas_por_canal = {}

    try:
        context = ET.iterparse(XML_FILE, events=("start", "end"))
        context = iter(context)
        event, root = next(context)

        for event, elem in context:
            try:
                if event == "end" and elem.tag == "channel":
                    ch_id = elem.get("id")
                    name_el = elem.find("display-name")
                    name = name_el.text if name_el is not None else ch_id
                    icon_el = elem.find("icon")
                    icon = icon_el.get("src") if icon_el is not None else ""
                    canales_dict[ch_id] = {"name": name, "icon": icon}
                    root.clear()

                if event == "end" and elem.tag == "programme":
                    ch_id = elem.get("channel")
                    start_time = elem.get("start", "")
                    stop_time = elem.get("stop", "")

                    if start_time.startswith(now):
                        if ch_id not in programas_por_canal:
                            programas_por_canal[ch_id] = []

                        hora_start = f"{start_time[8:10]}:{start_time[10:12]}"
                        hora_stop = f"{stop_time[8:10]}:{stop_time[10:12]}" if stop_time else ""
                        titulo_el = elem.find("title")
                        titulo = titulo_el.text if titulo_el is not None else "Sin título"
                        desc_el = elem.find("desc")
                        desc = desc_el.text if desc_el is not None else ""
                        cat_el = elem.find("category")
                        categoria = cat_el.text if cat_el is not None else ""

                        programas_por_canal[ch_id].append({
                            "hora": hora_start,
                            "fin": hora_stop,
                            "titulo": titulo,
                            "desc": desc,
                            "categoria": categoria,
                        })
                    root.clear()
            except Exception:
                continue

    except Exception as e:
        print(f"Aviso: Interrupción en la lectura: {e}")

    return canales_dict, programas_por_canal


def get_category_emoji(categoria):
    cat = categoria.lower() if categoria else ""
    mapping = {
        "noticias": "📰", "news": "📰", "information": "📰",
        "deporte": "⚽", "sports": "⚽", "sport": "⚽",
        "pelicul": "🎬", "movie": "🎬", "cine": "🎬",
        "serie": "📺", "show": "📺",
        "música": "🎵", "music": "🎵",
        "niños": "🧸", "children": "🧸", "kids": "🧸",
        "document": "🎥", "naturaleza": "🌿",
        "entretenimiento": "🎭", "entertainment": "🎭",
        "cocina": "🍳", "cooking": "🍳",
    }
    for key, emoji in mapping.items():
        if key in cat:
            return emoji
    return "📡"


def generate_html(canales_dict, programas_por_canal):
    print("Generando HTML...")
    updated = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Build channels data for JS
    channels_data = []
    for ch_id in sorted(programas_por_canal.keys()):
        canal_info = canales_dict.get(ch_id, {"name": ch_id, "icon": ""})
        nombre = canal_info["name"]
        icon = canal_info["icon"]
        progs = sorted(programas_por_canal[ch_id], key=lambda x: x["hora"])[:8]
        for p in progs:
            p["emoji"] = get_category_emoji(p["categoria"])
        channels_data.append({
            "id": ch_id,
            "name": nombre,
            "icon": icon,
            "programs": progs,
        })

    channels_json = json.dumps(channels_data, ensure_ascii=False)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    output = template.replace("{{UPDATED}}", updated)
    output = output.replace("{{CHANNELS_DATA}}", channels_json)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"✅ Web generada: {OUTPUT_FILE}")


def cleanup():
    for f in [XML_GZ_FILE, XML_FILE]:
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    download_and_extract(EPG_URL)
    canales_dict, programas_por_canal = parse_epg()
    generate_html(canales_dict, programas_por_canal)
    cleanup()
    print("Proceso completado.")
