# Motor TTS: generación paralela + reproducción secuencial
# ______________________

import asyncio
import os
import tempfile
import time

import edge_tts
import pygame
from pydub import AudioSegment
from pydub.silence import detect_leading_silence

PREFETCH = 3


async def _generar_audio(texto, voz_cfg, ruta):
    comm = edge_tts.Communicate(
        texto,
        voz_cfg["voice"],
        rate=voz_cfg.get("rate", "+0%"),
        volume=voz_cfg.get("volume", "+0%"),
        pitch=voz_cfg.get("pitch", "+0Hz"),
    )
    await comm.save(ruta)


def _recortar_silencio(ruta, umbral_db=-50.0, margen_ms=50):
    try:
        audio = AudioSegment.from_file(ruta, format="mp3")
    except Exception:
        return
    ini = detect_leading_silence(audio, silence_threshold=umbral_db, chunk_size=1)
    fin_rev = detect_leading_silence(audio.reverse(), silence_threshold=umbral_db,
                                     chunk_size=1)
    ini = max(0, ini - margen_ms)
    fin = max(0, len(audio) - (fin_rev - margen_ms))
    if ini >= fin or (fin - ini) < 100:
        return
    audio[ini:fin].export(ruta, format="mp3")


def _reproducir(ruta):
    pygame.mixer.music.load(ruta)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(15)
    pygame.mixer.music.unload()


class TTSEngine:
    """Controla generación y reproducción con pausa/reanudar y salto.

    Los "bloques" son strings. La reproducción se hace de a uno, pero
    la generación se adelanta PREFETCH bloques.
    """

    def __init__(self):
        pygame.mixer.init()
        self.tmp_dir = tempfile.mkdtemp(prefix="audiolibro_")
        self._contador = 0
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    # KEYWORD: reproducir_bloques (punto de entrada)
    def reproducir_bloques(self, bloques, voz_cfg,
                           on_block=None, on_page=None,
                           control=None):
        """Bloques: iterable de tuplas (tipo, payload).

        control: dict con banderas consultadas por el motor:
            - 'stop': bool
            - 'paused': bool
            - 'skip_to': int | None (índice al que saltar dentro de la
                          lista ya generada en esta sesión)
        on_block(idx, texto): callback cuando empieza un bloque.
        on_page(num): callback al cambiar de página.
        """
        if control is None:
            control = {}

        # Materializamos los bloques que ya tenemos en esta iteración.
        # El generador de pdf_stream sigue siendo perezoso, pero aquí
        # necesitamos poder saltar hacia adelante/atrás, así que vamos
        # guardando los ya vistos en una lista.
        ya_vistos = []     # lista de textos de bloques
        cola = asyncio.Queue()
        sem = asyncio.Semaphore(PREFETCH)

        gen = iter(bloques)
        agotado = {"done": False}

        async def producir():
            idx = 0
            try:
                while not agotado["done"] and not control.get("stop"):
                    try:
                        tipo, payload = next(gen)
                    except StopIteration:
                        agotado["done"] = True
                        break

                    if tipo == "__page__":
                        await cola.put(("page", payload))
                        continue

                    async with sem:
                        ruta = os.path.join(self.tmp_dir,
                                            f"b_{idx:06d}.mp3")
                        try:
                            await _generar_audio(payload, voz_cfg, ruta)
                            await asyncio.to_thread(_recortar_silencio, ruta)
                        except Exception:
                            await cola.put(("block", (idx, None)))
                            idx += 1
                            continue
                        await cola.put(("block", (idx, ruta)))
                        idx += 1
            finally:
                await cola.put(("__end__", None))

        productor = self._loop.create_task(producir())

        idx_actual = 0
        saltar_a = None

        try:
            while True:
                if control.get("stop"):
                    break

                if saltar_a is not None:
                    # Drenamos la cola de bloques ya listos hasta idx_actual
                    while not cola.empty():
                        tipo, payload = self._loop.run_until_complete(
                            cola.get())
                        if tipo == "block":
                            b_idx, ruta = payload
                            if ruta and os.path.exists(ruta):
                                try:
                                    os.remove(ruta)
                                except OSError:
                                    pass
                            if b_idx >= saltar_a:
                                idx_actual = b_idx
                                if ruta is None:
                                    break
                                ya_vistos.append(None)
                                _reproducir(ruta)
                                break
                        elif tipo == "__end__":
                            agotado["done"] = True
                            break
                    saltar_a = None
                    continue

                tipo, payload = self._loop.run_until_complete(cola.get())

                if tipo == "__end__":
                    break

                if tipo == "page":
                    if on_page:
                        on_page(payload)
                    continue

                if tipo == "block":
                    b_idx, ruta = payload
                    idx_actual = b_idx

                    # Esperar a que el usuario reanude
                    while control.get("paused") and not control.get("stop"):
                        time.sleep(0.05)

                    if control.get("stop"):
                        if ruta and os.path.exists(ruta):
                            try:
                                os.remove(ruta)
                            except OSError:
                                pass
                        break

                    if ruta is None:
                        continue

                    if on_block:
                        # El texto original no lo tenemos aquí; guardamos
                        # los bloques en ya_vistos a medida que salen.
                        on_block(b_idx, "")

                    _reproducir(ruta)
                    try:
                        os.remove(ruta)
                    except OSError:
                        pass

                    if control.get("skip_to") is not None:
                        saltar_a = control["skip_to"]
                        control["skip_to"] = None
        finally:
            control["stop"] = True
            try:
                self._loop.run_until_complete(productor)
            except Exception:
                pass

    def cerrar(self):
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        try:
            self._loop.close()
        except Exception:
            pass