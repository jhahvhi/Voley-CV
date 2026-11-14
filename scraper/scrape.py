#!/usr/bin/env python3
"""Descarga clasificaciones y calendarios de fvbcv.com y genera data/data.json.

Uso:  python3 scraper/scrape.py [--solo SLUG] [--salida data/data.json]

Cada competición se pide una sola vez: la vista "calendario" de la federación
devuelve, por cada fase y grupo, la clasificación y todas las jornadas.
"""
import argparse
import datetime
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

BASE = "https://fvbcv.com/competiciones/"
UA = "Mozilla/5.0 (X11; Linux x86_64) voley-resumen/1.0"
PAUSA = 1.0  # segundos entre peticiones, para no cargar el servidor

CATEGORIAS = ["Benjamín", "Alevín", "Infantil", "Cadete", "Juvenil", "Junior", "Sub19", "Senior"]


def pedir(url, datos=None, intentos=3):
    cuerpo = urllib.parse.urlencode(datos).encode() if datos else None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, data=cuerpo, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # red inestable: reintenta
            if i == intentos - 1:
                raise
            print(f"  reintento ({e})", file=sys.stderr)
            time.sleep(3 * (i + 1))


def limpio(s):
    return re.sub(r"\s+", " ", s or "").strip()


def sin_tildes(s):
    return s.translate(str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU"))


def listar_competiciones():
    """Slugs enlazados desde la página general = competiciones de la temporada actual."""
    html = pedir(BASE)
    slugs = []
    for m in re.finditer(r'href=["\']https?://fvbcv\.com/competiciones/([a-z0-9-]+)/?["\']', html):
        if m.group(1) not in slugs:
            slugs.append(m.group(1))
    return slugs


def clasificar(nombre):
    """Deduce categoría (edad) y género a partir del nombre de la competición."""
    n = sin_tildes(nombre).upper()
    cat = "Otras"
    for c in CATEGORIAS:
        if sin_tildes(c).upper() in n:
            cat = c
            break
    if cat == "Otras" and re.search(r"\bS[FM]\b", n):
        cat = "Senior"
    if cat == "Sub19":
        cat = "Juvenil"
    if re.search(r"FEMENIN|\bS(UB19)?F\b|SUB19F", n):
        gen = "Femenino"
    elif re.search(r"MASCULIN|\bSM\b", n):
        gen = "Masculino"
    else:
        gen = ""
    return cat, gen


def escudo(td):
    img = td.find("img") if td else None
    if not img or not img.get("src"):
        return ""
    return img["src"].rsplit("/", 1)[-1]


def num(s):
    s = limpio(s)
    return int(s) if re.fullmatch(r"-?\d+", s) else 0


def leer_clasificacion(tabla):
    filas = []
    for tr in tabla.find_all("tr"):
        nombre = tr.find("span", class_="equipo")
        # La federación mete "DESCANSA" como un equipo más en los grupos impares.
        if not nombre or limpio(nombre.get_text()).upper() == "DESCANSA":
            continue
        tds = tr.find_all("td")
        pos = tr.find("td", class_="POS")
        # Tras posición, flecha, escudo y nombre vienen las columnas numéricas.
        valores = [num(td.get_text()) for td in tds[4:]]
        valores += [0] * (11 - len(valores))
        pj, pg3, pg2, pp1, pp0, np_, sf, sc, pf, pc, pts = valores[:11]
        filas.append({
            "pos": num(re.sub(r"\D", "", pos.get_text())) if pos else len(filas) + 1,
            "equipo": limpio(nombre.get_text()),
            "escudo": escudo(tr.find("td", class_="club-escudo-min")),
            "pj": pj, "pg3": pg3, "pg2": pg2, "pp1": pp1, "pp0": pp0, "np": np_,
            "sf": sf, "sc": sc, "pf": pf, "pc": pc, "pts": pts,
        })
    return filas


def leer_partidos(tabla, jornada):
    partidos = []
    for tr in tabla.find_all("tr"):
        equipos = tr.find_all("span", class_="equipo")
        if len(equipos) < 2:
            continue
        fecha, hora = "", ""
        f = tr.find("span", class_="fechaa")
        if f:
            txt = f.get_text(" ")
            m = re.search(r"(\d{2})/(\d{2})/(\d{4})", txt)
            if m:
                fecha = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            m = re.search(r"(\d{1,2}:\d{2})", txt)
            if m:
                hora = m.group(1)
        marcador = limpio(tr.find("td", class_="score").get_text(" ")) if tr.find("td", class_="score") else ""
        sl = sv = None
        parciales = ""
        m = re.match(r"(\d+)\s*-\s*(\d+)", marcador)
        if m:
            sl, sv = int(m.group(1)), int(m.group(2))
            p = re.search(r"\(([^)]*)\)", marcador)
            if p:
                parciales = limpio(p.group(1)).replace("/", " · ")
        campo = ""
        c = tr.find("td", class_="campo")
        if c and c.find("div"):
            campo = limpio(re.sub(r"^\s*Campo:\s*", "", c.find("div").get("data-content", "")))
        escudos = tr.find_all("td", class_="club-escudo-min")
        partidos.append({
            "jor": jornada, "fecha": fecha, "hora": hora,
            "local": limpio(equipos[0].get_text()), "visit": limpio(equipos[1].get_text()),
            "el": escudo(escudos[0]) if escudos else "",
            "ev": escudo(escudos[1]) if len(escudos) > 1 else "",
            "sl": sl, "sv": sv, "parciales": parciales, "campo": campo,
        })
    return partidos


def leer_competicion(slug):
    html = pedir(BASE + slug + "/", {"nocarga": 1, "tipo": "calendario", "tipo2": ""})
    sopa = BeautifulSoup(html, "html.parser")

    nombre = slug
    sel = sopa.find("select", id="competi")
    if sel:
        op = sel.find("option", selected=True) or sel.find("option")
        if op:
            nombre = limpio(op.get_text())
    temporada = ""
    m = re.search(r"\s*-\s*(\d{4}-\d{4})\s*$", nombre)
    if m:
        temporada = m.group(1)
        nombre = nombre[:m.start()]

    grupos = []
    actual = None
    jornada = ""
    # Recorre el documento en orden: título de grupo -> clasificación -> jornadas.
    for el in sopa.find_all(["h5", "table"]):
        if el.name == "h5":
            txt = limpio(el.get_text())
            if re.match(r"CLASIFICACI", txt, re.I):
                continue
            m = re.match(r"JOR\.?\s*(.+)", txt, re.I)
            if m:
                jornada = m.group(1)
            elif " - " in txt and not el.find_parent("table"):
                fase, _, grupo = txt.rpartition(" - ")
                actual = {"fase": fase, "grupo": grupo, "clasificacion": [], "partidos": []}
                grupos.append(actual)
            continue
        clases = el.get("class") or []
        if "estadisticastablas" in clases:
            if actual is None:
                actual = {"fase": "", "grupo": "", "clasificacion": [], "partidos": []}
                grupos.append(actual)
            actual["clasificacion"] = leer_clasificacion(el)
        elif "partidos" in clases and "tabla" in clases:
            if actual is None:
                actual = {"fase": "", "grupo": "", "clasificacion": [], "partidos": []}
                grupos.append(actual)
            actual["partidos"].extend(leer_partidos(el, jornada))

    # Los partidos aplazados aparecen repetidos: quita duplicados exactos.
    for g in grupos:
        vistos, unicos = set(), []
        for p in g["partidos"]:
            clave = (p["jor"], p["local"], p["visit"], p["fecha"], p["hora"])
            if clave not in vistos:
                vistos.add(clave)
                unicos.append(p)
        g["partidos"] = unicos
    grupos = [g for g in grupos if g["clasificacion"] or g["partidos"]]

    cat, gen = clasificar(nombre)
    return {"slug": slug, "nombre": nombre, "temporada": temporada,
            "categoria": cat, "genero": gen, "grupos": grupos}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", help="procesa solo esta competición (para pruebas)")
    ap.add_argument("--salida", default=str(Path(__file__).resolve().parent.parent / "data" / "data.json"))
    args = ap.parse_args()

    slugs = [args.solo] if args.solo else listar_competiciones()
    if not slugs:
        sys.exit("No se ha encontrado ninguna competición: ¿ha cambiado la web?")

    competiciones, fallos = [], []
    for slug in slugs:
        print(slug, file=sys.stderr)
        try:
            c = leer_competicion(slug)
            if c["grupos"]:
                competiciones.append(c)
            else:
                print("  (sin datos)", file=sys.stderr)
        except Exception as e:
            fallos.append(slug)
            print(f"  ERROR: {e}", file=sys.stderr)
        time.sleep(PAUSA)

    # Si falla demasiado, no pises los datos buenos que ya hay publicados.
    if not competiciones or len(fallos) > len(slugs) / 2:
        sys.exit(f"Demasiados fallos ({len(fallos)}/{len(slugs)}); no se actualiza.")

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    # Sin cambios desde la última vez: no reescribas (evita commits vacíos de contenido).
    if salida.exists() and not args.solo:
        try:
            if json.loads(salida.read_text(encoding="utf-8")).get("competiciones") == competiciones:
                print("Sin cambios.", file=sys.stderr)
                return
        except ValueError:
            pass
    datos = {
        "actualizado": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
        "competiciones": competiciones,
    }
    salida.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n_eq = sum(len(g["clasificacion"]) for c in competiciones for g in c["grupos"])
    n_pa = sum(len(g["partidos"]) for c in competiciones for g in c["grupos"])
    print(f"{len(competiciones)} competiciones, {n_eq} equipos, {n_pa} partidos -> {salida}", file=sys.stderr)


if __name__ == "__main__":
    main()
