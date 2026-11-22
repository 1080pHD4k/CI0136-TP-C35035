# CI-0136 — Tarea Programada Individual: Compartidor de Archivos P2P (Proyecto B)

- **Carné:** C35035
- **Nombre:** Stephanie Monge Ortiz

## 1. Entorno y dependencias

- Python 3.12.3, probado en Ubuntu Linux.
- Dependencias: solo biblioteca estándar de Python (socket, threading, json, pathlib ,argparse, unittest)

## 2. Ejecución

Se necesitan dos terminales abiertas en la raíz del repositorio, no hay un orden particular pero la demo y las pruebas que hice siguieron el siguiente orden:

**Terminal 1:**
```bash
python3 nodo.py --id nodo1 --puerto 12160 --remoto 12161
```

**Terminal 2:**
```bash
python3 nodo.py --id nodo2 --puerto 12161 --remoto 12160
```

Argumentos:
- `--id`: identificador del nodo (usa su propia carpeta nodo1/ o nodo2/ como carpeta compartida/descargas).
- `--puerto`: puerto en el que este nodo escucha.
- `--remoto`: puerto del nodo al que este le hará solicitudes.

**Salida esperada de cada nodo:**
```
Carné: C35035 | Variante: B
Nodo nodo1, puerto 12160, remoto 12161
Archivos compartidos: ['ejemplo1.txt', 'notas.txt', 'ejemplo.txt']
Escuchando en puerto 12160

1. Listar locales
2. Listar remotos
3. Descargar
4. Salir
```

## 3. Preparación de datos

Los archivos de muestra ya están incluidosen nodo1/compartidos/notas.txt y nodo2/compartidos/imagen.bin. Si se necesitan regenerar:

```bash
echo "Archivo de prueba del nodo 1." > nodo1/compartidos/notas.txt
python3 -c "import os; open('nodo2/compartidos/imagen.bin','wb').write(os.urandom(2048))"
```

No se requiere ningún otro paso de configuración adicional

## 4. Guion de comprobación

ya con ambos nodos corriendo:

**Caso normal:**
- En nodo2, opción 3, archivo notas.txt → debe imprimir Descargado notas.txt y crear nodo2/descargas/notas.txt, funciona en ambos sentidos
- En nodo1, opción 2- listar remotos → debe mostrar los archivos dentro de nodo2/compartidos
- En nodo1, opción 3, archivo imagen.bin → debe imprimir Descargado imagen.bin (2048 bytes) y crear nodo1/descargas/imagen.bin.
- Para verificar integridad: diff nodo2/compartidos/imagen.bin nodo1/descargas/imagen.bin && echo IDÉNTICOS → debe imprimir IDÉNTICOS para confirmar.

**Caso límite/concurrente:**
- Generar un archivo de 60 KB con `python3 -c "import os; open('nodo2/compartidos/grande.bin','wb').write(os.urandom(60*1024))"` y descargarlo igual que el segundo punto en el caso normal, debe completarse sin errores y el diff debe confirmar IDÉNTICOS. Esto lo que hace es que fuerza múltiples iteraciones del ciclo de lectura de bytes.

**Casos de error:**
- En nodo1, opción 3, archivo no_existe.txt → debe imprimir `Error: archivo no encontrado`.
- Cerrar nodo2 (Ctrl+C) y en nodo1 elegir opción 2 → debe imprimir `Error: nodo remoto no disponible`.

## 5. Pruebas automatizadas

```bash
python3 -m unittest discover -s tests -v
```

Las pruebas levantan dos servidores en hilos, en los puertos de prueba 13160 y 13161, y los detienen automáticamente al terminar el proceso de unittest. Son 7 pruebas: listado normal, transferencia de archivo grande, solicitud de archivo inexistente, integridad de bytes, descarga en ambos sentidos, ruta no permitida y nodo remoto no disponible.

## 6. Finalización y reinicio limpio

En cada terminal, elegir la opción 4 (Salir) o presionar `Ctrl+C`, los puertos quedan libres de inmediato para volver a ejecutar el programa. Si algún puerto queda ocupado:

```bash
lsof -i :12160
lsof -i :12161
kill <PID>
```
Para repetir la demo desde cero, basta con volver a correr los dos comandos del punto 2. Los archivos en la carpeta `descargas/` se pueden borrar manualmente si se necesita.

## 7. Arquitectura, decisión de diseño, limitaciones y uso de IA

```
┌─────────────────────────┐        TCP (JSON + bytes)        ┌─────────────────────────┐
│   nodo1 (puerto 12160)   │ <------------------------------>│   nodo2 (puerto 12161)   │
│  hilo servidor (escucha) │                                 │  hilo servidor (escucha) │
│  hilo principal (menú,   │                                 │  hilo principal         |  
└─────────────────────────┘                                  └─────────────────────────┘
```

Ambos nodos ejecutan nodo.py diferenciados por sus argumentos de línea de comandos. Como se usa P2P cada nodo es a la vez servidor y cliente.

**Decisión de diseño:** la transferencia de archivos usa una cabecera JSON de una línea `{"estado":"OK","tamano":N}` seguida de N bytes, en vez de codificar el archivo dentro del JSON. Esto evita el costo de convertir binario a texto pero obliga a implementar lectura en ciclo con `recv()` hasta completar el tamaño. 

**Limitaciones conocidas:**
- No hay cifrado ni autenticación entre nodos.
- No soporta reanudar descargas interrumpidas.
- No hay un limite explicito de tamaño de archivo.
- El nodo remoto se tiene que configurar manualmente con `--remoto`

**Uso de IA:** se utilizó Claude (Anthropic) como asistente para la creación del **diagrama** de este archivo README.md en la sección 7 y apoyo parcial en la redacción del mismo. También se utilizó como ayuda para detectar y corregir errores de código. El código fue escrito, ejecutado, probado y verificado personalmente por mí.