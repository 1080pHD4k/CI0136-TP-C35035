# Protocolo - C35035

## DETALES
- Comunicación por TCP en localhost. 
- Cada conexión atiende una sola solicitud.

Las solicitudes y las cabeceras de respuesta son un objeto JSON en una línea terminada en \n.

## LISTAR

Solicitud:
```
{"comando":"LISTAR"}
```

Respuesta:
```
{"estado":"OK","archivos":["notas.txt","imagen.bin"]}
```

## OBTENER

Solicitud:
```
{"comando":"OBTENER","archivo":"notas.txt"}
```

Respuesta:

```
{"estado":"OK","tamano":120}
<120 bytes>
```

## Errores


```
{"estado":"ERROR","mensaje":"archivo no encontrado"}
```

Respuestas:
- `comando no reconocido`
- `nombre inválido`: el nombre tiene separadores, es una ruta absoluta o el archivo está fuera de `compartidos/`.
- `archivo no encontrado`
