# Vóley CV

Página sencilla para ver cómo va un equipo de la Federación de Voleibol de la
Comunidad Valenciana (fvbcv.com): puesto, clasificación del grupo y calendario.

- `index.html` — toda la página (sin dependencias). Lee `data/data.json`.
- `scraper/scrape.py` — descarga los datos de fvbcv.com y genera `data/data.json`.
  Una petición por competición (vista "calendario" de la federación).
- `.github/workflows/actualizar.yml` — ejecuta el extractor cada 2 horas y
  guarda el JSON si ha cambiado.

## Probar en local

    pip install beautifulsoup4
    python3 scraper/scrape.py          # regenera data/data.json
    python3 -m http.server 8000        # abrir http://localhost:8000

## Publicar en GitHub Pages

1. Crear un repositorio público vacío en GitHub y subir esto:

       git remote add origin git@github.com:USUARIO/voley.git
       git push -u origin main

2. En el repositorio: Settings → Pages → Source: "Deploy from a branch",
   rama `main`, carpeta `/ (root)`.
3. Settings → Actions → General → Workflow permissions: "Read and write".
4. Pestaña Actions → "Actualizar datos" → Run workflow, para comprobar que
   la actualización automática funciona.

GitHub desactiva las tareas programadas tras 60 días sin actividad en el
repositorio (por ejemplo en verano); se reactivan desde la pestaña Actions.

## Si la federación cambia su web

El extractor depende del HTML de fvbcv.com. Si deja de encontrar datos, sale
con error y no pisa el JSON publicado; habrá que ajustar `leer_competicion`.
