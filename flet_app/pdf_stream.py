# Lectura de PDF en ventana deslizante (2 páginas máx en memoria)
# ______________________

import re
import pypdf

MAX_CHARS = 350


def _cierra_parrafo(texto: str) -> bool:
    t = texto.rstrip()
    if not t:
        return True
    return t[-1] in ".!?;:»\"')]…"


def limpiar_texto(texto: str, patrones_ignorar) -> str:
    for patron in patrones_ignorar:
        texto = re.sub(patron, " ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"[ \t]+", " ", texto)
    return texto.strip()


def dividir_parrafo_largo(parrafo: str, max_chars: int):
    if len(parrafo) <= max_chars:
        return [parrafo]

    oraciones = re.split(r"(?<=[.!?…])\s+", parrafo)
    if len(oraciones) == 1:
        oraciones = re.split(r"(?<=[;:])\s+", parrafo)

    bloques = []
    actual = ""
    for o in oraciones:
        if not actual:
            actual = o
        elif len(actual) + 1 + len(o) <= max_chars:
            actual += " " + o
        else:
            bloques.append(actual)
            actual = o
    if actual:
        bloques.append(actual)

    resultado = []
    for b in bloques:
        if len(b) <= max_chars * 1.5:
            resultado.append(b)
        else:
            palabras = b.split()
            temp = ""
            for w in palabras:
                if not temp:
                    temp = w
                elif len(temp) + 1 + len(w) <= max_chars:
                    temp += " " + w
                else:
                    resultado.append(temp)
                    temp = w
            if temp:
                resultado.append(temp)
    return resultado


# KEYWORD: bloques_desde_pdf (generador principal)
def bloques_desde_pdf(pdf_path, page_start, page_end, patrones_ignorar,
                      max_chars=MAX_CHARS):
    """Genera bloques listos para sintetizar. page_end=0 -> hasta el final."""
    with open(pdf_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        total = len(reader.pages)
        fin = total if not page_end else min(page_end, total)
        inicio = max(1, page_start)

        buffer = ""
        for i in range(inicio - 1, fin):
            pag = reader.pages[i].extract_text() or ""
            pag = limpiar_texto(pag, patrones_ignorar)
            if not pag:
                yield ("__page__", i + 1)
                continue

            if buffer:
                if _cierra_parrafo(buffer):
                    for b in dividir_parrafo_largo(buffer, max_chars):
                        yield ("block", b)
                    buffer = pag
                else:
                    buffer = buffer.rstrip() + " " + pag.lstrip()
            else:
                buffer = pag

            texto_norm = re.sub(r"\r\n", "\n", buffer)
            texto_norm = re.sub(r"\n\s*\n+", "\n\n", texto_norm)
            partes = texto_norm.split("\n\n")

            for p in partes[:-1]:
                p_limpio = re.sub(r"\s+", " ", p.replace("\n", " ")).strip()
                if p_limpio:
                    for b in dividir_parrafo_largo(p_limpio, max_chars):
                        yield ("block", b)

            buffer = partes[-1] if len(partes) > 1 else texto_norm
            buffer = re.sub(r"\s+", " ", buffer.replace("\n", " ")).strip()

            if buffer and _cierra_parrafo(buffer) and len(buffer) < max_chars:
                for b in dividir_parrafo_largo(buffer, max_chars):
                    yield ("block", b)
                buffer = ""

            yield ("__page__", i + 1)

        if buffer.strip():
            for b in dividir_parrafo_largo(buffer.strip(), max_chars):
                yield ("block", b)