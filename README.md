# Nexora

**Nexora convierte ideas en backlogs.** Escribes qué necesitas y obtienes una jerarquía ágil completa (épica, features, historias de usuario con criterios de aceptación y tareas), lista para revisar y gestionar en Azure DevOps.

---

## Cómo funciona

```
necesidad.txt  ──►  generar_backlog.py  ──►  backlog.json  ──►  crear_en_azure.py  ──►  Azure DevOps
 (tu texto)          (IA + tus normas)       (lo revisas)        (crea y enlaza)         (Epic > Feature > HU > Task)
```

1. **Etapa 1, generar:** una IA lee tu necesidad y tus normas de redacción y produce `backlog.json`.
2. **Revisión humana:** abres el JSON, quitas lo que la IA haya inventado y corriges lo que haga falta.
3. **Etapa 2, crear:** el segundo script lee el JSON y crea los work items en Azure DevOps, cada uno enlazado a su padre y etiquetado como `borrador-IA`.

La pausa de revisión es la parte más importante: la IA propone y una persona decide.

---

## Contenido de la carpeta

| Archivo | Para qué sirve |
|---|---|
| `normas.txt` | Reglas de redacción que sigue la IA (formato de HU, criterios, tareas) |
| `necesidad.txt` | Tu texto de entrada: problema, roles y requerimientos |
| `generar_backlog.py` | Etapa 1: genera y valida `backlog.json` |
| `crear_en_azure.py` | Etapa 2: crea la jerarquía en Azure DevOps |
| `backlog.json` | Resultado de la Etapa 1 (se crea al ejecutar) |
| `creados.json` | Registro de los work items creados, con sus IDs (se crea al ejecutar con `--crear`) |

---

## Requisitos

- Python 3.10 o superior
- Una cuenta de Azure DevOps con una organización y un proyecto con proceso **Scrum** o **Agile**. El proceso **Basic** no sirve porque no tiene el nivel Feature.
- Una clave de API de Google AI Studio (tiene capa gratuita con límites)
- Un Personal Access Token (PAT) de Azure DevOps con permiso **Work Items: Read & write**

Instalación de las librerías:

```
python -m pip install google-genai requests
```

---

## Configuración

Las claves se entregan por variables de entorno, nunca dentro del código. En PowerShell:

```powershell
# Etapa 1
$env:GEMINI_API_KEY="tu_clave"
$env:GEMINI_MODEL="nombre-del-modelo-flash-vigente"   # opcional, ver nota

# Etapa 2
$env:AZDO_ORG="nombre_de_la_organizacion"     # dev.azure.com/ESTE_NOMBRE
$env:AZDO_PROJECT="nombre_del_proyecto"
$env:AZDO_PAT="tu_token"
$env:AZDO_PROCESS="scrum"                      # o "agile"
```

En Mac o Linux usa `export NOMBRE="valor"`.

Estas variables duran mientras la terminal esté abierta. Para guardarlas de forma permanente en Windows se usa `setx`, y luego hay que abrir una terminal nueva.

> **Nota sobre el modelo:** los nombres de modelos de IA cambian con frecuencia. Si aparece un error 404 de modelo no encontrado, consulta el nombre Flash vigente en AI Studio y defínelo en `GEMINI_MODEL`.

---

## Uso

### Etapa 1: generar el backlog

1. Escribe tu proyecto en `necesidad.txt` siguiendo la plantilla: proyecto, problema, roles, requerimientos, reglas y fuera del alcance.
2. Ejecuta:
   ```
   python generar_backlog.py
   ```
3. Abre `backlog.json` y revisa que:
   - Cada descripción empiece con "Como... quiero... para...".
   - Cada historia tenga de 3 a 5 criterios Dado/Cuando/Entonces.
   - No haya funciones que tu texto no mencione.

El script valida la estructura y reintenta hasta 3 veces si la IA responde con un formato incorrecto.

### Etapa 2: crear en Azure DevOps

1. Muestra el árbol sin crear nada (modo de prueba, es el comportamiento por defecto):
   ```
   python crear_en_azure.py
   ```
2. Si se ve bien, crea los work items:
   ```
   python crear_en_azure.py --crear
   ```
3. Verifica en **Boards → Backlogs** la jerarquía, los criterios de aceptación y la etiqueta `borrador-IA`.

Para usar otro archivo en lugar de `backlog.json`: `python crear_en_azure.py --archivo otro.json`.

---

## Qué crea en Azure DevOps

| Nivel | Scrum | Agile |
|---|---|---|
| Épica | Epic | Epic |
| Feature | Feature | Feature |
| Historia | Product Backlog Item | User Story |
| Tarea | Task | Task |

- Cada elemento queda enlazado a su padre (relación Parent/Child).
- Las historias llevan sus criterios de aceptación en el campo **Acceptance Criteria**.
- Todo se etiqueta `borrador-IA` para que el equipo sepa qué falta validar. La etiqueta se quita al aprobar cada historia en el refinamiento.
- Área e iteración quedan en la raíz del proyecto (valores por defecto).

---

## Formato de `backlog.json`

```json
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
```

Si editas el archivo a mano, mantén esta estructura y cuida las comillas y las comas.

---

## Normas de redacción

El archivo `normas.txt` controla el estilo de lo que genera la IA. Define, entre otras cosas:

- Una sola épica, de 2 a 5 features, de 1 a 5 historias por feature y de 3 a 5 tareas por historia.
- Historias en formato "Como [rol] quiero [necesidad] para [beneficio]" y cumpliendo INVEST.
- De 3 a 5 criterios de aceptación en formato Dado/Cuando/Entonces, verificables y sin palabras vagas.
- La regla de oro: usar solo lo que está en la necesidad, sin inventar requisitos.

Si el resultado no te convence, ajusta este archivo y vuelve a ejecutar la Etapa 1.

---

## Solución de problemas

| Mensaje | Causa probable | Qué hacer |
|---|---|---|
| `Falta la variable de entorno GEMINI_API_KEY` | La clave no está definida en esa terminal | Definirla de nuevo |
| `404 NOT_FOUND ... model` | El modelo ya no está disponible | Cambiar `GEMINI_MODEL` por el vigente |
| Error de cuota o límite | Límite de la capa gratuita | Esperar unos minutos y reintentar |
| `No se pudo obtener un backlog válido` | La IA respondió mal 3 veces seguidas | Reintentar o simplificar `necesidad.txt` |
| `Faltan variables de entorno: AZDO_...` | Variables de Azure sin definir en esa terminal | Definirlas de nuevo |
| Error 401 o 203 de Azure | Token incorrecto, vencido o sin permiso | Generar otro PAT con Work Items Read & write |
| Error 400 o 404 al crear | Organización o proyecto mal escritos, o proceso que no coincide | Revisar `AZDO_ORG`, `AZDO_PROJECT` y `AZDO_PROCESS` |
| `Fatal error in launcher` al usar `pip` | `pip.exe` apunta a un Python que ya no existe | Usar `python -m pip install ...` |

---
