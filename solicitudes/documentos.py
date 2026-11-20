"""Qué documentación se acepta en una solicitud (HU-16).

No sabe nada de Flask: recibe el nombre y el contenido del archivo y devuelve
el adjunto listo para guardar, o el motivo por el que se rechaza.
"""
import os

from werkzeug.utils import secure_filename

MAX_BYTES = 2 * 1024 * 1024  # 2 MB

# Extensión -> cómo empieza un archivo de ese tipo. Así no alcanza con
# renombrar un archivo cualquiera a ".pdf" para que pase.
FIRMAS = {
    ".pdf": b"%PDF-",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}
MIMES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def validar_documento(nombre, contenido):
    """Devuelve (adjunto, error). Si hay error, el adjunto es None."""
    nombre_limpio = secure_filename(nombre or "")
    extension = os.path.splitext(nombre_limpio)[1].lower()

    if extension not in FIRMAS:
        return None, "El documento debe ser un archivo PDF, PNG o JPG."
    if len(contenido) == 0:
        return None, "El archivo está vacío."
    if len(contenido) > MAX_BYTES:
        return None, "El archivo supera el máximo de 2 MB."
    if not contenido.startswith(FIRMAS[extension]):
        return None, f"El archivo no parece ser un {extension[1:].upper()} válido."

    adjunto = {
        "nombre": nombre_limpio,
        "tipo": MIMES[extension],
        "tamano": len(contenido),
        "contenido": contenido,
    }
    return adjunto, None
