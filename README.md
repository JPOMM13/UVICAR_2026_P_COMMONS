# M2M SIMs API - Guía de Despliegue en Kubernetes

Este proyecto expone una API REST para listar y consultar información detallada de las SIMs de la plataforma SmartM2M (M2M LATAM).

## 🚀 Especificaciones Técnicas

- **Intervalo de actualización**: Cada 24 horas automáticamente.
- **Resiliencia**: Si la consulta falla o no hay datos cargados, el sistema reintenta automáticamente cada 10 minutos hasta obtener el listado con éxito.
- **Persistencia**: Utiliza un archivo local `sims_cache.json` para mantener los datos entre reinicios del Pod (si se configura un volumen).
- **Puerto**: 5001 (interno del contenedor).

## 🔑 Configuración de Secretos (Kubernetes)

Antes de desplegar, es **obligatorio** crear el secreto con las credenciales de SmartM2M. Ejecuta el siguiente comando en tu cluster:

```bash
kubectl create secret generic m2m-secrets \
  --from-literal=SMARTM2M_USER='tu_usuario@uvicar.com.pe' \
  --from-literal=SMARTM2M_PASS='tu_password_aqui'
```

*Nota: Reemplaza los valores con las credenciales reales de la plataforma.*

## ☸️ Despliegue

1. **Construir y subir la imagen**:
   Edita `deploy.sh` con el nombre de tu Azure Container Registry (ACR) y ejecútalo:
   ```bash
   ./deploy.sh
   ```

2. **Aplicar manifiestos**:
   El script de despliegue aplicará automáticamente el archivo `k8s-manifests.yaml`, que incluye:
   - **Deployment**: Configura 1 réplica, monta un volumen temporal para la caché y define las sondas de salud (Liveness/Readiness).
   - **Service**: Expone la API internamente en el puerto 80.

## 📡 Endpoints de la API

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/sims` | Obtiene el listado completo de SIMs con todos sus detalles. |
| `GET` | `/api/status` | Muestra el estado de la última actualización y el conteo de SIMs. |
| `POST` | `/api/sims/refresh` | Fuerza una actualización inmediata en segundo plano. |
| `GET` | `/health` | Endpoint para monitoreo de salud (K8s). |

## 🛠 Estructura del Proyecto

- `app_sims.py`: Lógica principal en Flask y scraping.
- `Dockerfile`: Configuración de la imagen de producción (basada en Python 3.11-slim y Gunicorn).
- `requirements.txt`: Dependencias del proyecto.
- `k8s-manifests.yaml`: Definición de recursos de Kubernetes.
