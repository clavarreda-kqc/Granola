# Gobernanza de datos y modelos

## Principios

1. **Valor para el hablante:** procesar una grabación para entregar notas no implica donarla para entrenamiento.
2. **Consentimiento por grabación:** el uso para entrenamiento requiere opt-in explícito en cada sesión.
3. **Finalidad específica:** ASR, identificación de hablantes y clonación o síntesis de voz son permisos distintos.
4. **Minimización:** recopilar solo los metadatos necesarios y evitar datos sensibles en audio, texto y campos libres.
5. **Trazabilidad:** cada segmento debe apuntar a la versión del consentimiento, sus restricciones y su estado de retiro.
6. **Revisión comunitaria:** las decisiones lingüísticas, editoriales y de publicación se revisan con hablantes y especialistas.

## Consentimiento por sesión

Antes de grabar, cada participante debe conocer:

- qué se grabará y con qué propósito;
- quién tendrá acceso;
- qué resultados recibirá;
- si el audio y la transcripción se conservarán;
- que contribuir al entrenamiento es opcional;
- qué licencia se propone para cualquier publicación;
- cómo pedir retiro, sujeto a los límites técnicos explicados abajo.

El sistema registra decisiones independientes:

| Permiso | Valor esperado |
|---|---|
| `process_for_notes` | Requerido para transcribir, resumir y entregar notas |
| `retain_audio` | Sí / no, con plazo de retención |
| `asr_training` | Opt-in explícito |
| `speaker_identification` | Opt-in explícito; no se asume por aceptar diarización |
| `tts_voice_training` | Opt-in explícito y separado, por voz y finalidad |
| `public_release` | Opt-in explícito, con licencia y alcance visibles |

No se incorpora al corpus de entrenamiento una sesión sin consentimiento verificable de todas las personas grabadas. Si el consentimiento es parcial o dudoso, la sesión queda excluida.

## Retiro y ciclo de vida

- Mantener un identificador de consentimiento y un estado: `active`, `withdrawn` o `restricted`.
- Ante retiro, bloquear nuevas versiones del corpus y borrar los artefactos controlados según la política acordada.
- Explicar que un modelo ya entrenado no permite extraer con certeza la contribución de una sola grabación. Cuando aplique, programar reentrenamiento sin los datos retirados.
- Conservar un registro mínimo de auditoría del retiro, sin retener el contenido retirado.

## Metadatos mínimos

### Grabación

- `recording_id` y fecha;
- comunidad y país, con granularidad que no exponga a la persona;
- variante/dialecto declarado y método de validación;
- dominio: reunión, entrevista, conversación, lectura u otro;
- dispositivo, canal, frecuencia de muestreo y entorno acústico;
- duración, idioma(s) y posible code-switching;
- versión del aviso y del consentimiento;
- permisos, restricciones, retención y estado de retiro;
- revisor y estado de QA.

### Hablante

- `speaker_id` seudónimo, nunca el nombre como clave del corpus;
- variante(s) y comunidad lingüística declaradas;
- rango de edad opcional y categorías demográficas voluntarias;
- relación con la grabación: participante, facilitador o lector;
- permiso separado para identificación de hablante y TTS;
- calidad y cantidad de audio atribuible.

Los campos sensibles son opcionales, se justifican antes de recopilarse y tienen acceso restringido. La tabla que vincula identidad real con seudónimo no pertenece al repositorio.

## Revisión comunitaria y control de calidad

La revisión se divide para evitar que una sola persona decida todo:

- **Validación lingüística:** ortografía, segmentación, variante, préstamos, alternancia de código y criterios de transcripción.
- **QA editorial:** consistencia de etiquetas, legibilidad, formatos, errores sistemáticos y muestras de aceptación.
- **Gobernanza comunitaria:** consentimiento, usos permitidos, acceso, conflictos, retiro y publicación.
- **Equipo técnico:** seguridad, versionado, evaluación, documentación de modelos y límites de uso.

Cada lote publicable debe tener criterios de aceptación, muestreo de QA y aprobación registrada. Los resultados de ASR se reportan por variante y contexto, no solo con un promedio global.

## Licencias

- No mezclar automáticamente datasets no comerciales con un corpus que pueda tener uso comercial.
- Mantener origen, licencia y restricciones a nivel de dataset y, cuando sea necesario, de grabación.
- Meta MMS (CC BY-NC) y Bloom Speech no autorizan por sí solos un producto comercial basado en sus datos o derivados. Se usan únicamente dentro del alcance permitido y separados del corpus propio.
- La licencia del corpus comunitario se decide con revisión legal y comunitaria antes de publicar datos.
- Una licencia abierta del audio no equivale a consentimiento para TTS, clonación de voz o identificación biométrica. Esos usos requieren permiso explícito adicional.
- Por defecto, audio y transcripciones permanecen privados. Este repositorio almacena solo esquemas, manifiestos sin contenido sensible y documentación.

## Acceso y seguridad

- Audio, transcripciones y vínculos de identidad viven fuera de Git, cifrados y con acceso por rol.
- Los manifiestos públicos no incluyen nombres, teléfonos, correos ni ubicaciones precisas.
- Los entornos de desarrollo usan muestras sintéticas o expresamente autorizadas.
- Toda exportación registra responsable, propósito, versión y fecha de expiración.

## Decisiones pendientes antes del piloto

- entidad responsable del tratamiento y canal de retiro;
- plazo de retención por tipo de permiso;
- texto final de consentimiento en español y kaqchikel;
- órgano y proceso de revisión comunitaria;
- licencia objetivo y compatibilidad con usos comerciales;
- protocolo para menores, voces identificables y contenido sensible.
