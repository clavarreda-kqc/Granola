# Despliegue continuo en Cloud Run

La aplicación es un contenedor sin estado. El manifiesto y el audio se escriben en `/data`; en Cloud Run esa ruta se monta sobre un bucket de Cloud Storage. `GRANOLA_GCS_BUCKET` reserva la futura integración directa con la API de GCS, pero hoy es solo un *stub*: no se debe activar sin montar el bucket.

## Preparación única por el dueño del proyecto

Estos pasos se hacen dentro del proyecto de GCP de Cristian. Granola no recibe ni guarda una llave JSON.

1. En **APIs y servicios**, habilitar Cloud Build, Cloud Run, Artifact Registry y Cloud Storage.
2. En **Artifact Registry**, crear un repositorio Docker llamado `granola` en `us-central1`.
3. En **Cloud Storage**, crear un bucket llamado `granola-recordings` en una región compatible. No hacerlo público.
4. En **Cloud Build > Triggers**, elegir **Connect repository**, instalar/autorizar la app oficial de Cloud Build para GitHub y seleccionar `clavarreda-kqc/Granola`.
5. Dar a la cuenta de servicio que ejecuta Cloud Build los roles `Cloud Run Admin`, `Artifact Registry Writer`, `Service Account User` y `Logs Writer`. Dar a la cuenta de ejecución de Cloud Run acceso de lectura/escritura de objetos al bucket (`Storage Object Admin`). Conviene limitar cada rol al recurso que lo necesita.
6. Crear un trigger regional en `us-central1`:
   - evento: push a una rama;
   - expresión de rama: `^main$`;
   - configuración: archivo de Cloud Build;
   - ruta: `/cloudbuild.yaml`;
   - sustituciones si cambian los nombres: `_REGION`, `_REPOSITORY`, `_SERVICE`, `_BUCKET`.
7. Ejecutar el trigger manualmente una vez. Después, cada merge a `main` construye la imagen, la publica en Artifact Registry y despliega Cloud Run.

El `cloudbuild.yaml` usa por defecto `us-central1`, repositorio `granola`, servicio `granola` y bucket `granola-recordings`.

Referencias oficiales:

- [Conectar un repositorio de GitHub](https://cloud.google.com/build/docs/automating-builds/github/connect-repo-github)
- [Desplegar Cloud Run con Cloud Build](https://docs.cloud.google.com/build/docs/deploying-builds/deploy-cloud-run)
