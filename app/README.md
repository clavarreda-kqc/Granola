# App: captura y consentimiento

Primer corte funcional: una web móvil sin dependencias ni proceso de compilación. Usa `MediaRecorder` del navegador y un servidor Python estándar. La elección reduce fricción para un piloto en teléfonos y mantiene el PR pequeño; no pretende ser todavía la arquitectura de producción.

## Ejecutar

Requiere Python 3.11+ y un navegador moderno. El micrófono funciona en `localhost` o HTTPS.

```bash
python3 app/server.py
# abrir http://localhost:8000
```

Flujo verificable:

1. Completar el consentimiento antes de acceder al grabador.
2. Elegir por separado entrenamiento ASR y uso de voz TTS.
3. Grabar y detener.
4. Revisar `data/local/recordings.jsonl` y `data/local/recordings/`.

Los audios y metadatos reales de ejecución están ignorados por Git.

## Pruebas

```bash
python3 -m unittest discover -s app/tests -v
```

Las pruebas validan el enum de las seis variantes MMS, la presencia de permisos booleanos explícitos y la escritura conjunta de audio local + manifiesto JSONL.

## Límites de este corte

- almacenamiento local de un solo nodo, sin autenticación ni cifrado;
- el texto sigue siendo el borrador en español `consent-v0.1-draft`, pendiente de revisión comunitaria/legal y traducción por variante;
- no implementa retiro, vencimiento de retención, carga remota, transcripción ni diarización;
- una sesión registra a una persona. El soporte multipersona deberá exigir consentimiento verificable de cada participante antes de integrar una sesión al corpus.
