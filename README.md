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

## Logos de los equipos

Los escudos salen de la federación. Si un equipo no tiene, la página le pone un
círculo con sus iniciales.

**¿Quieres que salga el logo de tu equipo?** No hace falta saber nada de
programación:

1. Entra en la pestaña **Issues** de este repositorio y pulsa **New issue**
   (hace falta una cuenta de GitHub, que es gratis). En la propia página hay un
   enlace al pie, "¿Quieres que salga el logo de tu equipo?", que te lleva directo.
2. En el título escribe **Añadir logo** y el **nombre del equipo** tal como sale
   en la página.
3. Arrastra la imagen del logo al cuadro de texto (mejor PNG y cuadrada).
4. Pulsa el botón verde para enviarlo.

Para quien mantiene la página: guardar la imagen en `logos/` y añadir una regla
en `logos/logos.json`:

    {
      "logo": "jesuitas_valencia.png",     archivo dentro de logos/
      "club": "Jesuitas (Valencia)",       solo informativo
      "empieza": "JESUITAS ",              el nombre del equipo empieza así...
      "contiene": "...",                   ...o contiene esto (uno de los dos)
      "sin": ["SERRA GROSSA"],             textos que lo descartan (otro club parecido)
      "competicion": "jdm-"                opcional: solo en competiciones cuyo
    }                                      identificador empieza así

No distingue mayúsculas ni tildes. Una regla vale para todos los equipos del
club (cadete, infantil...). Los logos propios mandan sobre los de la federación.

## Si la federación cambia su web

El extractor depende del HTML de fvbcv.com. Si deja de encontrar datos, sale
con error y no pisa el JSON publicado; habrá que ajustar `leer_competicion`.

Porfi no la cambiéis :)
