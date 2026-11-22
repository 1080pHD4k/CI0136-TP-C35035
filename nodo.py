import argparse
import json
import socket
import sys
import threading
from pathlib import Path

CARNE = "C35035"
VARIANTE = "P2P"

def parsear_argumentos():
    parser = argparse.ArgumentParser(description="Nodo P2P - Compartidor de archivos")
    parser.add_argument("--id", required=True, help="Identificador del nodo (ej: nodo1)")
    parser.add_argument("--puerto", type=int, required=True, help="Puerto en el que este nodo escucha")
    parser.add_argument("--remoto", type=int, required=True, help="Puerto del nodo remoto")
    return parser.parse_args()

def es_nombre_seguro(nombre):
    if not nombre:
        return False
    if "/" in nombre or "\\" in nombre:
        return False
    if nombre in ("..", "."):
        return False
    if ".." in Path(nombre).parts:
        return False
    if Path(nombre).is_absolute():
        return False
    return True

def manejar_cliente(conexion, direccion, carpeta_compartidos, id_nodo="nodo"):
    conexion.settimeout(10)
    comando = None
    nombre_archivo = ""
    resultado = "sin solicitud"
    try:
        linea = leer_linea(conexion)
        if linea is None:
            return
        try:
            solicitud = json.loads(linea)
        except json.JSONDecodeError:
            resultado = "ERROR comando no reconocido"
            enviar_json(conexion, {"estado": "ERROR", "mensaje": "comando no reconocido"})
            return

        comando = solicitud.get("comando")
        if comando == "LISTAR":
            archivos = [f.name for f in carpeta_compartidos.iterdir() if f.is_file()]
            enviar_json(conexion, {"estado": "OK", "archivos": archivos})
            resultado = f"OK {len(archivos)} archivos"
        elif comando == "OBTENER":
            nombre_archivo = solicitud.get("archivo", "")
            if not es_nombre_seguro(nombre_archivo):
                resultado = "ERROR nombre inválido"
                enviar_json(conexion, {"estado": "ERROR", "mensaje": "nombre inválido"})
                return

            ruta = carpeta_compartidos / nombre_archivo
            if not ruta.is_file():
                resultado = "ERROR archivo no encontrado"
                enviar_json(conexion, {"estado": "ERROR", "mensaje": "archivo no encontrado"})
                return

            contenido = ruta.read_bytes()
            enviar_json(conexion, {"estado": "OK", "tamano": len(contenido)})
            conexion.sendall(contenido)
            resultado = f"OK {len(contenido)} bytes"
        else:
            resultado = "ERROR comando no reconocido"
            enviar_json(conexion, {"estado": "ERROR", "mensaje": "comando no reconocido"})
    except Exception as e:
        resultado = f"ERROR {e}"
    finally:
        conexion.close()
        print(f"{id_nodo} <- {direccion[0]}:{direccion[1]} | {comando} {nombre_archivo} | {resultado}")

def recibir_bytes_exactos(conexion, cantidad):
    datos = b""
    while len(datos) < cantidad:
        faltan = cantidad - len(datos)
        fragmento = conexion.recv(min(faltan, 65536))
        if not fragmento:
            raise ConnectionError("conexión cerrada antes de terminar")
        datos += fragmento
    return datos

def leer_linea(conexion):
    buffer = b""
    while b"\n" not in buffer:
        fragmento = conexion.recv(1)
        if not fragmento:
            return None
        buffer += fragmento
    linea, _, _ = buffer.partition(b"\n")
    return linea.decode("utf-8")


def enviar_json(conexion, objeto):
    datos = (json.dumps(objeto) + "\n").encode("utf-8")
    conexion.sendall(datos)

def descargar_remoto(id_nodo, puerto_remoto, carpeta_descargas, nombre_archivo):
    origen = f"{id_nodo} -> {puerto_remoto} | OBTENER {nombre_archivo}"
    destino = carpeta_descargas / nombre_archivo
    if destino.exists():
        if input("El archivo ya existe. ¿Sobrescribir? (s/n): ").strip().lower() != "s":
            print(f"{origen} | Cancelado")
            return
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect(("localhost", puerto_remoto))
            enviar_json(s, {"comando": "OBTENER", "archivo": nombre_archivo})

            linea = leer_linea(s)
            if linea is None:
                print(f"{origen} | Error: sin respuesta del nodo remoto")
                return
            respuesta = json.loads(linea)

            if respuesta.get("estado") != "OK":
                print(f"{origen} | Error: {respuesta.get('mensaje')}")
                return

            tamano = respuesta["tamano"]
            contenido = recibir_bytes_exactos(s, tamano)

            carpeta_descargas.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(contenido)
            print(f"{origen} | OK: Descargado {nombre_archivo} ({len(contenido)} bytes)")
    except socket.timeout:
        print(f"{origen} | Error: tiempo agotado")
    except ConnectionRefusedError:
        print(f"{origen} | Error: nodo remoto no disponible")
    except Exception as e:
        print(f"{origen} | Error: {e}")

def listar_remoto(id_nodo, puerto_remoto):
    origen = f"{id_nodo} -> {puerto_remoto} | LISTAR"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect(("localhost", puerto_remoto))
            enviar_json(s, {"comando": "LISTAR"})
            linea = leer_linea(s)
            if linea is None:
                print(f"{origen} | Error: sin respuesta del nodo remoto")
                return
            respuesta = json.loads(linea)
            if respuesta.get("estado") == "OK":
                print(f"{origen} | OK")
                print("Remotos:", respuesta.get("archivos"))
            else:
                print(f"{origen} | Error: {respuesta.get('mensaje')}")
    except socket.timeout:
        print(f"{origen} | Error: tiempo agotado")
    except ConnectionRefusedError:
        print(f"{origen} | Error: nodo remoto no disponible")
    except Exception as e:
        print(f"{origen} | Error: {e}")

def iniciar_servidor(puerto, carpeta_compartidos, id_nodo="nodo"):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("0.0.0.0", puerto))
    servidor.listen(5)
    print(f"Escuchando en puerto {puerto}")

    while True:
        conexion, direccion = servidor.accept()
        hilo = threading.Thread(
            target=manejar_cliente,
            args=(conexion, direccion, carpeta_compartidos, id_nodo),
            daemon=True,
        )
        hilo.start()


def menu(id_nodo, puerto_remoto, carpeta_compartidos, carpeta_descargas):
    while True:
        print()
        print("1. Listar locales")
        print("2. Listar remotos")
        print("3. Descargar")
        print("4. Salir")
        opcion = input("Opción: ").strip()

        if opcion == "1":
            archivos = [f.name for f in carpeta_compartidos.iterdir() if f.is_file()]
            print("Locales:", archivos)
        elif opcion == "2":
            listar_remoto(id_nodo, puerto_remoto)
        elif opcion == "3":
            nombre_archivo = input("Archivo: ").strip()
            if nombre_archivo:
                descargar_remoto(id_nodo, puerto_remoto, carpeta_descargas, nombre_archivo)
            else:
                print("Nombre inválido")
        elif opcion == "4":
            sys.exit(0)
        else:
            print("Opción inválida")


def main():
    args = parsear_argumentos()
    print(f"Carné: {CARNE} | Variante: {VARIANTE}")
    print(f"Nodo {args.id}, puerto {args.puerto}, remoto {args.remoto}")

    carpeta_compartidos = Path(args.id) / "compartidos"
    carpeta_compartidos.mkdir(parents=True, exist_ok=True)
    print("Archivos compartidos:", [f.name for f in carpeta_compartidos.iterdir() if f.is_file()])

    hilo_servidor = threading.Thread(
        target=iniciar_servidor,
        args=(args.puerto, carpeta_compartidos, args.id),
        daemon=True,
    )
    hilo_servidor.start()

    carpeta_descargas = Path(args.id) / "descargas"
    menu(args.id, args.remoto, carpeta_compartidos, carpeta_descargas)


if __name__ == "__main__":
    main()
