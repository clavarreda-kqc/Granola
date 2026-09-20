# Granola para Kaqchikel

Una herramienta de notas de voz para hablantes de kaqchikel. Graba reuniones o conversaciones de minutos u horas, separa hablantes, transcribe, resume y propone próximos pasos. Cuando cada participante lo autoriza, esas grabaciones también ayudan a construir un corpus comunitario para mejorar ASR y TTS en kaqchikel.

## Principio de producto

**Valor primero:** la persona recibe notas y resultados útiles. El corpus es un subproducto consentido, nunca una condición para usar la herramienta.

Cada grabación tiene dos permisos independientes:

1. procesarla para entregar transcripción, resumen y próximos pasos;
2. incorporarla al corpus de entrenamiento mediante un opt-in explícito.

Más detalles en [Gobernanza](docs/GOBERNANZA.md) y la [plantilla de consentimiento](docs/CONSENTIMIENTO.md).

## Alcance inicial

- grabación de audio de minutos u horas;
- diarización de hablantes;
- identificación opcional de hablantes, solo con consentimiento;
- transcripción en kaqchikel;
- resumen y próximos pasos;
- metadatos trazables de consentimiento, dialecto y calidad;
- preparación de datos para ASR y, más adelante, TTS.

## Arquitectura propuesta

```text
app/          Producto de notas: captura, sesiones y resultados
             | audio de sesión
             v
diarization/ Separación de hablantes (base agnóstica al idioma, p. ej. pyannote)
             | segmentos con tiempos y speaker_id local
             v
asr/          Baseline con adaptadores de Meta MMS y ruta de fine-tuning
             | transcripción por segmento
             v
app/          Resumen, próximos pasos y revisión humana
             |
             +--> data/ Metadatos y manifiestos consentidos (nunca audio en Git)
             +--> tts/  Trabajo futuro con voces autorizadas
```

## Estado de los datos y modelos

El punto de partida público es insuficiente para un producto conversacional:

- **Meta MMS** publica checkpoints ASR y TTS para seis variantes: Central, Santa María de Jesús, Santo Domingo Xenacoj, South Central, Western y Yepocapa. El material es de dominio bíblico, de un solo hablante y con licencia CC BY-NC, por lo que no es una base comercial reutilizable tal cual.
- **Whisper** no incluye soporte nativo para kaqchikel. La ruta viable es fine-tuning con datos propios.
- **Mozilla Common Voice** no tiene horas publicadas de kaqchikel.
- **Bloom Speech** aporta 2 h 03 min y 1,154 clips. Reporta un baseline XLS-R con WER de 21%, pero el conjunto es no comercial.

Estos recursos sirven para experimentos y comparación. No definen la licencia del corpus nuevo ni sustituyen datos conversacionales propios.

## Estrategia de corpus

El corpus se construirá con grabaciones comunitarias consentidas, trazabilidad por sesión y revisión lingüística.

| Etapa | Meta orientativa | Objetivo |
|---|---:|---|
| Piloto | 10-20 horas | Validar captura, consentimiento, diarización, esquema y baseline |
| ASR conversacional | 50-100 horas | Lograr un modelo útil en conversaciones reales y medir por variante |
| Cobertura amplia | 100-200+ horas | Ampliar cobertura de las seis variantes y diversidad de hablantes/entornos |
| TTS | 5-10 horas limpias por voz | Entrenar una voz solo con consentimiento explícito para síntesis |

Las cifras son metas de planificación, no garantías de calidad. La evaluación se reportará por dialecto, hablante, dominio y condiciones acústicas.

## Estructura del repositorio

```text
app/             Aplicación y contratos de producto
asr/             Experimentos, evaluación y fine-tuning de ASR
data/            Esquemas y manifiestos; no contiene audio
diarization/    Separación e identificación opcional de hablantes
docs/            Gobernanza, consentimiento y decisiones
tts/            Trabajo futuro de síntesis con voces autorizadas
```

## Próximo hito

Definir un piloto pequeño con representantes comunitarios, cerrar el formulario de consentimiento, acordar el esquema de metadatos y registrar 10-20 horas con revisión lingüística. Después se implementará el primer pipeline reproducible de diarización + baseline MMS + evaluación.

## Operación local

```bash
GRANOLA_DATA_DIR=/tmp/granola python3 app/server.py
python3 app/server.py export --purpose asr --output /tmp/asr.jsonl
python3 app/server.py export --purpose tts --output /tmp/tts.jsonl
```

`POST /api/consent` registra retiros o restricciones por seudónimo con banderas `asr_training` y `tts_voice_training`. `/admin` muestra el estado efectivo del manifiesto. Los exportadores solo incluyen grabaciones con opt-in original y consentimiento vigente. Ver [despliegue continuo](docs/DESPLIEGUE.md).
