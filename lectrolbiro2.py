import asyncio
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

import edge_tts
import PyPDF2
import pygame
from pydub import AudioSegment
from pydub.silence import detect_leading_silence

# ============================================================
# CONFIGURACIÓN
# ============================================================
PDF_PATH = r"C:\Users\cgcab\Downloads\Proyecto Hail Mary - Andy Weir.pdf"
PAGINA_INICIO = 54
PAGINA_FIN =400 

VOZ = "es-MX-JorgeNeural"
RATE = "-10%"
VOLUME = "+0%"

PAUSA_PARRAFO = 0.15          # pausa entre bloques (segundos)
MAX_CHARS_POR_BLOQUE = 350    # divide párrafos más largos que esto
PREFETCH = 3                  # cuántos bloques adelantar en paralelo

FRASES_IGNORAR = [
    r"librer[ií]a\s+crisol",
    r"p[aá]g(?:ina)?\.?\s*\d+",
    r"pag\.?\s*\d+",
]

# ============================================================
# LIMPIEZA Y EXTRACCIÓN
# ============================================================

def limpiar_texto(texto: str) -> str:
    for patron in FRASES_IGNORAR:
        texto = re.sub(patron, " ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"[ \t]+", " ", texto)
    return texto.strip()


# ============================================================
# LECTURA EN STREAMING (2 páginas máx. en memoria)
# ============================================================

def _cierra_parrafo(texto: str) -> bool:
    """True si el texto termina en algo que cierra oración/párrafo."""
    t = texto.rstrip()
    if not t:
        return True
    return t[-1] in ".!?;:»\"')]…"


def bloques_desde_pdf(pdf_path, inicio, fin, max_chars=MAX_CHARS_POR_BLOQUE):
    """Generador: yield de bloques listos para sintetizar.

    Solo mantiene en memoria:
      - el buffer de continuación (último párrafo sin cerrar)
      - la página recién extraída
    """
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        total = len(reader.pages)
        fin = min(fin if fin is not None else total, total)

        buffer = ""  # resto de párrafo que continuará en la próxima página

        for i in range(inicio - 1, fin):
            pag = reader.pages[i].extract_text() or ""
            pag = limpiar_texto(pag)
            if not pag:
                continue

            # Unir con el buffer pendiente si lo había
            if buffer:
                if _cierra_parrafo(buffer):
                    # El buffer ya era un párrafo completo → emitirlo antes
                    for b in dividir_parrafo_largo(buffer, max_chars):
                        yield b
                    buffer = pag
                else:
                    # Continúa el párrafo entre páginas
                    buffer = buffer.rstrip() + " " + pag.lstrip()
            else:
                buffer = pag

            # Dividir el buffer actual en párrafos cerrados + resto
            texto_norm = re.sub(r"\r\n", "\n", buffer)
            texto_norm = re.sub(r"\n\s*\n+", "\n\n", texto_norm)
            partes = texto_norm.split("\n\n")

            # Todas las partes menos la última están cerradas
            for p in partes[:-1]:
                p_limpio = re.sub(r"\s+", " ", p.replace("\n", " ")).strip()
                if p_limpio:
                    for b in dividir_parrafo_largo(p_limpio, max_chars):
                        yield b

            # La última parte puede continuar en la siguiente página
            buffer = partes[-1] if len(partes) > 1 else texto_norm
            buffer = re.sub(r"\s+", " ", buffer.replace("\n", " ")).strip()

            # Si el buffer ya cierra párrafo y es corto, lo emitimos ya
            # (evita arrastrar basura entre páginas)
            if buffer and _cierra_parrafo(buffer) and len(buffer) < max_chars:
                for b in dividir_parrafo_largo(buffer, max_chars):
                    yield b
                buffer = ""

        # Al terminar, emitir lo que quede en el buffer
        if buffer.strip():
            for b in dividir_parrafo_largo(buffer.strip(), max_chars):
                yield b

# ============================================================
# DIVISIÓN EN PÁRRAFOS Y BLOQUES
# ============================================================

def dividir_en_parrafos(texto: str):
    texto = re.sub(r"\r\n", "\n", texto)
    texto = re.sub(r"\n\s*\n+", "\n\n", texto)

    parrafos = []
    for p in texto.split("\n\n"):
        p_limpio = re.sub(r"\s*\n\s*", " ", p)
        p_limpio = re.sub(r"\s+", " ", p_limpio).strip()
        if p_limpio:
            parrafos.append(p_limpio)
    return parrafos


def dividir_parrafo_largo(parrafo: str, max_chars: int):
    """Divide un párrafo por oraciones, agrupándolas hasta max_chars.

    Respeta . ! ? … y también ; y : como cortes secundarios.
    """
    if len(parrafo) <= max_chars:
        return [parrafo]

    # Cortar en oraciones conservando el signo
    oraciones = re.split(r"(?<=[.!?…])\s+", parrafo)
    # Si no se pudo dividir bien, cortar por ; y :
    if len(oraciones) == 1:
        oraciones = re.split(r"(?<=[;:])\s+", parrafo)

    bloques = []
    actual = ""
    for oracion in oraciones:
        if not actual:
            actual = oracion
        elif len(actual) + 1 + len(oracion) <= max_chars:
            actual += " " + oracion
        else:
            bloques.append(actual)
            actual = oracion
    if actual:
        bloques.append(actual)

    # Caso extremo: una sola "oración" gigante → partir por palabras
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


# ============================================================
# TTS + AUDIO
# ============================================================

async def generar_audio(texto: str, ruta_mp3: str):
    communicate = edge_tts.Communicate(texto, VOZ, rate=RATE, volume=VOLUME)
    await communicate.save(ruta_mp3)


def recortar_silencio(ruta_mp3: str, umbral_db: float = -50.0, margen_ms: int = 50):
    audio = AudioSegment.from_file(ruta_mp3, format="mp3")
    inicio = detect_leading_silence(audio, silence_threshold=umbral_db, chunk_size=1)
    reverso = audio.reverse()
    fin_rev = detect_leading_silence(reverso, silence_threshold=umbral_db, chunk_size=1)
    inicio = max(0, inicio - margen_ms)
    fin = max(0, len(audio) - (fin_rev - margen_ms))
    if inicio >= fin or (fin - inicio) < 100:
        return
    audio[inicio:fin].export(ruta_mp3, format="mp3")


def reproducir(ruta_mp3: str):
    pygame.mixer.music.load(ruta_mp3)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(10)
    pygame.mixer.music.unload()


# ============================================================
# PRODUCTOR / CONSUMIDOR
# ============================================================

async def productor_audios(bloques_iter, tmp_dir, cola: asyncio.Queue, sem):
    async def procesar_bloque(idx, texto):
        async with sem:
            ruta = os.path.join(tmp_dir, f"bloque_{idx:06d}.mp3")
            try:
                await generar_audio(texto, ruta)
                await asyncio.to_thread(recortar_silencio, ruta)
            except Exception as e:
                print(f"  [!] Error generando bloque {idx}: {e}")
                await cola.put((idx, None))
                return
            await cola.put((idx, ruta))

    tareas = []
    for idx, texto in enumerate(bloques_iter):
        tareas.append(asyncio.create_task(procesar_bloque(idx, texto)))
    await asyncio.gather(*tareas)
    await cola.put((-1, None))

def reproducir_stream(bloques_iter, tmp_dir):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cola: asyncio.Queue = asyncio.Queue()
    sem = asyncio.Semaphore(PREFETCH)

    productor_task = loop.create_task(
        productor_audios(bloques_iter, tmp_dir, cola, sem)
    )

    contador = 0
    try:
        while True:
            idx, ruta = loop.run_until_complete(cola.get())
            if idx == -1:
                break
            if ruta is None:
                continue
            contador += 1
            print(f"  ▶️  Reproduciendo bloque {contador}")
            reproducir(ruta)
            try:
                os.remove(ruta)
            except OSError:
                pass
            if PAUSA_PARRAFO > 0:
                time.sleep(PAUSA_PARRAFO)
    finally:
        loop.run_until_complete(productor_task)
        loop.close()

# ============================================================
# MAIN
# ============================================================

def main():
    if not Path(PDF_PATH).exists():
        print(f"No existe el archivo: {PDF_PATH}")
        sys.exit(1)

    pygame.mixer.init()

    tmp_dir = tempfile.mkdtemp(prefix="audiolibro_")
    try:
        # Contamos bloques sobre la marcha (no los materializamos todos)
        print("Iniciando streaming de páginas...")
        reproducir_stream(
            bloques_desde_pdf(PDF_PATH, PAGINA_INICIO, PAGINA_FIN),
            tmp_dir,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n✅ Lectura completada correctamente.")

if __name__ == "__main__":
    main()