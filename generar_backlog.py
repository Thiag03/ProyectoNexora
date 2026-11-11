import json
import os
import sys

from google import genai

MODELO = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
REINTENTOS = 3

PLANTILLA = """{{NORMAS}}

TAREA
A partir de la siguiente necesidad, genera el backlog siguiendo las normas.
Responde SOLO con un JSON válido, sin texto adicional ni bloques de código,
con exactamente esta estructura:

{
  "epica": {
    "titulo": "",
    "descripcion": "",
    "features": [
      {
        "titulo": "",
        "descripcion": "",
        "historias": [
          {
            "titulo": "",
            "descripcion": "Como ... quiero ... para ...",
            "criterios": ["Dado ..., cuando ..., entonces ..."],
            "tareas": [""]
          }
        ]
      }
    ]
  }
}

NECESIDAD
{{NECESIDAD}}
"""


def validar(datos):
    """Devuelve (errores, avisos). Los errores impiden continuar."""
    errores, avisos = [], []

    epica = datos.get("epica")
    if not isinstance(epica, dict) or not epica.get("titulo"):
        return ["Falta epica.titulo"], avisos

    features = epica.get("features")
    if not isinstance(features, list) or not features:
        return ["La épica no tiene features"], avisos

    for i, f in enumerate(features, 1):
        if not f.get("titulo"):
            errores.append(f"Feature {i} sin título")
        historias = f.get("historias")
        if not isinstance(historias, list) or not historias:
            errores.append(f"Feature {i} sin historias")
            continue
        for j, h in enumerate(historias, 1):
            ref = f"Feature {i}, HU {j}"
            if not h.get("titulo"):
                errores.append(f"{ref} sin título")
            desc = h.get("descripcion", "")
            if not desc.startswith("Como "):
                avisos.append(f"{ref}: la descripción no empieza con 'Como'")
            criterios = h.get("criterios")
            if not isinstance(criterios, list) or not criterios:
                errores.append(f"{ref} sin criterios de aceptación")
            elif not 3 <= len(criterios) <= 5:
                avisos.append(f"{ref}: tiene {len(criterios)} criterios (ideal 3 a 5)")
            tareas = h.get("tareas")
            if not isinstance(tareas, list) or not tareas:
                errores.append(f"{ref} sin tareas")

    return errores, avisos


def limpiar_json(texto):
    """Quita bloques ```json si el modelo los agregó."""
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def main():
    archivo_necesidad = sys.argv[1] if len(sys.argv) > 1 else "necesidad.txt"

    if "GEMINI_API_KEY" not in os.environ:
        sys.exit("Falta la variable de entorno GEMINI_API_KEY.")

    normas = open("normas.txt", encoding="utf-8").read()
    necesidad = open(archivo_necesidad, encoding="utf-8").read().strip()
    if not necesidad:
        sys.exit(f"{archivo_necesidad} está vacío.")

    prompt = PLANTILLA.replace("{{NORMAS}}", normas).replace("{{NECESIDAD}}", necesidad)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    datos, ultimo_error = None, ""
    for intento in range(1, REINTENTOS + 1):
        print(f"Generando (intento {intento}/{REINTENTOS}) con {MODELO}...")
        extra = ""
        if ultimo_error:
            extra = f"\n\nTu respuesta anterior tuvo este problema: {ultimo_error}. Corrígelo."
        r = client.models.generate_content(
            model=MODELO,
            contents=prompt + extra,
            config={"response_mime_type": "application/json"},
        )
        try:
            candidato = json.loads(limpiar_json(r.text))
        except (json.JSONDecodeError, TypeError) as e:
            ultimo_error = f"JSON mal formado ({e})"
            print("  ->", ultimo_error)
            continue

        errores, avisos = validar(candidato)
        for a in avisos:
            print("  Aviso:", a)
        if errores:
            ultimo_error = "; ".join(errores)
            print("  Errores:", ultimo_error)
            continue

        datos = candidato
        break

    if datos is None:
        sys.exit("No se pudo obtener un backlog válido. Revisa normas.txt o la necesidad.")

    with open("backlog.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    epica = datos["epica"]
    n_f = len(epica["features"])
    n_h = sum(len(f["historias"]) for f in epica["features"])
    print(f"\nListo: 1 épica, {n_f} features, {n_h} historias. Revisa backlog.json "
          "y corrígelo a mano antes de pasar a Azure DevOps.")


if __name__ == "__main__":
    main()
