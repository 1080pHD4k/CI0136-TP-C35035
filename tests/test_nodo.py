import json
import os
import socket
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import contextlib
import io

from nodo import (
    descargar_remoto,
    iniciar_servidor,
    enviar_json,
    leer_linea,
    listar_remoto,
    recibir_bytes_exactos,
)

PUERTO_PRUEBA_1 = 13160
PUERTO_PRUEBA_2 = 13161


def levantar_servidor_prueba(puerto, carpeta):
    hilo = threading.Thread(
        target=iniciar_servidor,
        args=(puerto, carpeta),
        daemon=True,
    )
    hilo.start()
    time.sleep(0.3)
    return hilo


def pedir(puerto, solicitud):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(("localhost", puerto))
    enviar_json(s, solicitud)
    linea = leer_linea(s)
    respuesta = json.loads(linea)
    return respuesta, s


class TestNodoP2P(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory()
        cls.carpeta = Path(cls.tmp.name)
        cls.tmp2 = TemporaryDirectory()
        cls.carpeta2 = Path(cls.tmp2.name)
        levantar_servidor_prueba(PUERTO_PRUEBA_1, cls.carpeta)
        levantar_servidor_prueba(PUERTO_PRUEBA_2, cls.carpeta2)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
        cls.tmp2.cleanup()

    def test_listar_caso_normal(self):
        (self.carpeta / "a.txt").write_text("hola")
        (self.carpeta / "b.txt").write_text("mundo")

        respuesta, s = pedir(PUERTO_PRUEBA_1, {"comando": "LISTAR"})
        s.close()

        self.assertEqual(respuesta["estado"], "OK")
        self.assertIn("a.txt", respuesta["archivos"])
        self.assertIn("b.txt", respuesta["archivos"])

    def test_obtener_archivo_grande_caso_limite(self):
        contenido_original = b"X" * (5 * 1024 * 1024)
        (self.carpeta / "grande.bin").write_bytes(contenido_original)

        respuesta, s = pedir(
            PUERTO_PRUEBA_1, {"comando": "OBTENER", "archivo": "grande.bin"}
        )
        self.assertEqual(respuesta["estado"], "OK")

        recibido = recibir_bytes_exactos(s, respuesta["tamano"])
        s.close()

        self.assertEqual(len(recibido), len(contenido_original))
        self.assertEqual(recibido, contenido_original)

    def test_obtener_archivo_inexistente_error_controlado(self):
        respuesta, s = pedir(
            PUERTO_PRUEBA_1, {"comando": "OBTENER", "archivo": "no_existe.txt"}
        )
        s.close()

        self.assertEqual(respuesta["estado"], "ERROR")
        self.assertIn("mensaje", respuesta)

    def test_integridad_bytes_propiedad_esencial(self):
        contenido_original = os.urandom(10_000)
        (self.carpeta / "aleatorio.bin").write_bytes(contenido_original)

        respuesta, s = pedir(
            PUERTO_PRUEBA_1, {"comando": "OBTENER", "archivo": "aleatorio.bin"}
        )
        self.assertEqual(respuesta["estado"], "OK")

        recibido = recibir_bytes_exactos(s, respuesta["tamano"])
        s.close()

        self.assertEqual(recibido, contenido_original)

    def test_descarga_en_ambos_sentidos(self):
        contenido_1 = os.urandom(2048)
        contenido_2 = os.urandom(4096)
        (self.carpeta / "de1.bin").write_bytes(contenido_1)
        (self.carpeta2 / "de2.bin").write_bytes(contenido_2)

        with TemporaryDirectory() as d1, TemporaryDirectory() as d2:
            with contextlib.redirect_stdout(io.StringIO()):
                descargar_remoto("nodo1", PUERTO_PRUEBA_2, Path(d1), "de2.bin")
                descargar_remoto("nodo2", PUERTO_PRUEBA_1, Path(d2), "de1.bin")
            self.assertEqual((Path(d1) / "de2.bin").read_bytes(), contenido_2)
            self.assertEqual((Path(d2) / "de1.bin").read_bytes(), contenido_1)

    def test_ruta_no_permitida_rechazada(self):
        respuesta, s = pedir(
            PUERTO_PRUEBA_1, {"comando": "OBTENER", "archivo": "../archivo.txt"}
        )
        s.close()

        self.assertEqual(respuesta["estado"], "ERROR")

    def test_nodo_remoto_no_disponible(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            listar_remoto("nodo1", 13199)

        self.assertIn("no disponible", salida.getvalue())


if __name__ == "__main__":
    unittest.main()
