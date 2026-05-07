#!/bin/bash

# Configuración - REEMPLAZA ESTOS VALORES
ACR_NAME="<tu_registro_azure>" # Solo el nombre, ej: uvicarreg
IMAGE_NAME="m2m-sims-api"
IMAGE_TAG="latest"

echo "🚀 Iniciando proceso de despliegue consolidado..."

# 1. Login en Azure y ACR
echo "🔐 Autenticando en Azure ACR..."
az acr login --name $ACR_NAME

# 2. Construcción de la imagen Docker
echo "📦 Construyendo imagen Docker..."
docker build -t $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG -f Dockerfile .

# 3. Push de la imagen a ACR
echo "📤 Subiendo imagen a Azure Container Registry..."
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG

# 4. Actualizar el manifiesto con el nombre del ACR correcto
echo "📝 Ajustando manifiestos de Kubernetes..."
# Usamos una sintaxis compatible con macOS/Linux para sed
sed -i.bak "s/<tu-registro-azure>/$ACR_NAME/g" k8s-manifests.yaml && rm k8s-manifests.yaml.bak

# 5. Aplicar secretos si no existen
echo "🔑 Verificando secretos..."
kubectl get secret m2m-secrets > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "⚠️  El secreto m2m-secrets no existe. Por favor, créalo antes de continuar."
    echo "Comando: kubectl create secret generic m2m-secrets --from-literal=SMARTM2M_USER='...' --from-literal=SMARTM2M_PASS='...'"
    exit 1
fi

# 6. Despliegue en el Cluster
echo "☸️ Desplegando en Kubernetes..."
kubectl apply -f k8s-manifests.yaml

echo "✅ Proceso completado con éxito!"
echo "Puedes verificar el estado con: kubectl get pods -l app=$IMAGE_NAME"
