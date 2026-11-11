"""
Etapa 2: crea en Azure DevOps la jerarquía Epic > Feature > HU > Task
a partir de backlog.json (el que generaste y revisaste en la Etapa 1).

Por defecto NO crea nada: solo muestra qué crearía (modo de prueba).
Para crear de verdad, agrega --crear.

Uso:
    python crear_en_azure.py              # solo muestra el árbol
    python crear_en_azure.py --crear      # crea los work items

Requisitos:
    pip install requests
    Variables de entorno:
      AZDO_ORG       nombre de tu organización (dev.azure.com/ESTE_NOMBRE)
      AZDO_PROJECT   nombre del proyecto
      AZDO_PAT       Personal Access Token con permiso Work Items: Read & write
      AZDO_PROCESS   "scrum" o "agile" (por defecto "scrum")
"""
import argparse
import html
import json
import os
import sys
from urllib.parse import quote

import requests

ETIQUETA = "borrador-IA"
VERSION_API = "7.1"

TIPO_HU = {"scrum": "Product Backlog Item", "agile": "User Story"}


def config():
    faltan = [v for v in ("AZDO_ORG", "AZDO_PROJECT", "AZDO_PAT") if v not in os.environ]
    if faltan:
        sys.exit("Faltan variables de entorno: " + ", ".join(faltan))
    proceso = os.environ.get("AZDO_PROCESS", "scrum").lower()
    if proceso not in TIPO_HU:
        sys.exit('AZDO_PROCESS debe ser "scrum" o "agile".')
    return (
        os.environ["AZDO_ORG"],
        os.environ["AZDO_PROJECT"],
        os.environ["AZDO_PAT"],
        proceso,
    )


def a_html_lista(items):
    lis = "".join(f"<li>{html.escape(i)}</li>" for i in items)
    return f"<ul>{lis}</ul>"


class Azure:
    def __init__(self, org, proyecto, pat):
        self.base = f"https://dev.azure.com/{org}/{quote(proyecto)}"
        self.auth = ("", pat)

    def crear(self, tipo, campos, url_padre=None):
        ops = [{"op": "add", "path": f"/fields/{k}", "value": v} for k, v in campos.items()]
        if url_padre:
            ops.append({
                "op": "add",
                "path": "/relations/-",
                "value": {"rel": "System.LinkTypes.Hierarchy-Reverse", "url": url_padre},
            })
        url = f"{self.base}/_apis/wit/workitems/${quote(tipo)}?api-version={VERSION_API}"
        r = requests.post(
            url,
            json=ops,
            auth=self.auth,
            headers={"Content-Type": "application/json-patch+json"},
            timeout=60,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Azure respondió {r.status_code} al crear {tipo}: {r.text[:500]}")
        d = r.json()
        return d["id"], d["url"]


def mostrar_arbol(epica, tipo_hu):
    print(f"[Epic] {epica['titulo']}")
    for f in epica["features"]:
        print(f"  [Feature] {f['titulo']}")
        for h in f["historias"]:
            print(f"    [{tipo_hu}] {h['titulo']}  ({len(h['criterios'])} criterios)")
            for t in h["tareas"]:
                print(f"      [Task] {t}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crear", action="store_true", help="crear de verdad en Azure DevOps")
    ap.add_argument("--archivo", default="backlog.json")
    args = ap.parse_args()

    org, proyecto, pat, proceso = config()
    tipo_hu = TIPO_HU[proceso]

    epica = json.load(open(args.archivo, encoding="utf-8"))["epica"]
    mostrar_arbol(epica, tipo_hu)

    if not args.crear:
        print("\nModo de prueba: no se creó nada. Si todo está bien, ejecuta con --crear")
        return

    az = Azure(org, proyecto, pat)
    creados = []  # registro para poder revisar o borrar después

    def registrar(tipo, titulo, wid):
        creados.append({"tipo": tipo, "id": wid, "titulo": titulo})
        with open("creados.json", "w", encoding="utf-8") as f:
            json.dump(creados, f, ensure_ascii=False, indent=2)
        print(f"  creado {tipo} #{wid}: {titulo}")

    try:
        wid, url_epica = az.crear("Epic", {
            "System.Title": epica["titulo"],
            "System.Description": html.escape(epica.get("descripcion", "")),
            "System.Tags": ETIQUETA,
        })
        registrar("Epic", epica["titulo"], wid)

        for f in epica["features"]:
            wid, url_f = az.crear("Feature", {
                "System.Title": f["titulo"],
                "System.Description": html.escape(f.get("descripcion", "")),
                "System.Tags": ETIQUETA,
            }, url_epica)
            registrar("Feature", f["titulo"], wid)

            for h in f["historias"]:
                wid, url_h = az.crear(tipo_hu, {
                    "System.Title": h["titulo"],
                    "System.Description": html.escape(h["descripcion"]),
                    "Microsoft.VSTS.Common.AcceptanceCriteria": a_html_lista(h["criterios"]),
                    "System.Tags": ETIQUETA,
                }, url_f)
                registrar(tipo_hu, h["titulo"], wid)

                for t in h["tareas"]:
                    wid, _ = az.crear("Task", {
                        "System.Title": t,
                        "System.Tags": ETIQUETA,
                    }, url_h)
                    registrar("Task", t, wid)
    except RuntimeError as e:
        print("\nSe detuvo por un error:", e)
        print("Lo ya creado quedó registrado en creados.json. Revisa Azure antes de reintentar "
              "para no duplicar.")
        sys.exit(1)

    print(f"\nListo: {len(creados)} work items creados con la etiqueta '{ETIQUETA}'. "
          "Revísalos en Boards > Backlogs.")


if __name__ == "__main__":
    main()
