# Datos

Este directorio define la salida del pipeline. En ejecución, el servidor crea:

- `data/local/recordings/<recording_id>.webm`: audio privado, fuera de Git;
- `data/local/recordings.jsonl`: un registro estructurado por audio con seudónimo, variante MMS, municipio, duración, fecha, ruta y permisos separados.

`data/local/` está ignorado por Git. No colocar audio real ni vínculos entre identidad y seudónimo en el repositorio.
