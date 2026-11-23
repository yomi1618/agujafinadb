"""Ejecuta todas las peticiones de test_curls.txt sin necesitar bash (sirve en el cmd de Windows).

Lee cada línea que empieza con "req", reemplaza $BASE y $H como lo haría bash,
envía la petición y muestra el código HTTP junto al comentario de la línea.

Uso, desde la carpeta API y con la API encendida:
    python correr_test_curls.py                 resumen: una línea por petición
    python correr_test_curls.py --cuerpo        además muestra el JSON de cada respuesta
    python correr_test_curls.py > resultados.txt   guarda la salida en un archivo
"""
import re
import shlex
import sys
from pathlib import Path

import requests

ARCHIVO = Path(__file__).with_name("test_curls.txt")
MOSTRAR_CUERPO = "--cuerpo" in sys.argv


def leer_variables(texto):
    """Toma BASE y H de las primeras líneas del archivo, igual que bash."""
    base = re.search(r"^BASE=(\S+)", texto, re.M)
    cabecera = re.search(r"^H='([^']+)'", texto, re.M)
    return (base.group(1) if base else "http://localhost:5000",
            cabecera.group(1) if cabecera else "Content-Type: application/json")


def separar_comentario(linea):
    """Devuelve (comando, comentario): el comentario empieza en un # fuera de comillas."""
    comillas = None
    for i, c in enumerate(linea):
        if c in "'\"" and comillas in (None, c):
            comillas = None if comillas else c
        elif c == "#" and comillas is None:
            return linea[:i].strip(), linea[i + 1:].strip()
    return linea.strip(), ""


def ejecutar(tokens):
    """Interpreta las opciones de curl que usa el archivo: -X, -H, -d y la URL."""
    metodo, cabeceras, datos, url = None, {}, None, None
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "-X":
            metodo = tokens[i + 1]; i += 2
        elif t == "-H":
            k, v = tokens[i + 1].split(":", 1); cabeceras[k.strip()] = v.strip(); i += 2
        elif t == "-d":
            datos = tokens[i + 1]; i += 2
        else:
            url = t; i += 1
    metodo = metodo or ("POST" if datos is not None else "GET")
    r = requests.request(metodo, url, headers=cabeceras,
                         data=datos.encode("utf-8") if datos is not None else None, timeout=10)
    return metodo, url, r


def main():
    texto = ARCHIVO.read_text(encoding="utf-8")
    base, cabecera = leer_variables(texto)
    print(f"Ejecutando {ARCHIVO.name} contra {base}\n")
    codigos = {}
    for numero, linea in enumerate(texto.splitlines(), start=1):
        linea = linea.strip()
        if not linea.startswith("req "):
            continue
        comando, comentario = separar_comentario(linea)
        comando = comando.replace('"$H"', f'"{cabecera}"').replace("$BASE", base)
        try:
            metodo, url, r = ejecutar(shlex.split(comando)[1:])
        except requests.ConnectionError:
            print(f"No hay conexión con {base}. ¿Está encendida la API (python app.py)?")
            sys.exit(1)
        except Exception as e:
            print(f"línea {numero:>3}  NO SE PUDO EJECUTAR: {e}")
            continue
        codigos[r.status_code] = codigos.get(r.status_code, 0) + 1
        ruta = url.replace(base, "")
        nota = f"   # {comentario}" if comentario else ""
        print(f"línea {numero:>3}  {r.status_code}  {metodo:<6} {ruta}{nota}")
        if MOSTRAR_CUERPO:
            print("            " + r.text.strip().replace("\n", "\n            ") + "\n")
    resumen = ", ".join(f"{n} con {c}" for c, n in sorted(codigos.items()))
    print(f"\n{sum(codigos.values())} peticiones: {resumen}")


if __name__ == "__main__":
    main()
