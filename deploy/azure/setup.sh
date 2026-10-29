#!/usr/bin/env bash
# One-time Azure setup for de-assistant. Run after `az login`.
#
# Creates (all inside one resource group, free-tier friendly):
#   - an Azure Container Apps environment (no Log Analytics, so no log charges)
#   - the de-assistant container app, pulling the public GHCR image, scale-to-zero
#   - a GitHub Actions identity (OIDC, no stored passwords) that may redeploy only this resource group
# Then stores the IDs as GitHub repo secrets/variables so every push to main redeploys.
#
# Delete everything later with: az group delete -n "$RG" --yes
set -euo pipefail

RG=${RG:-de-assistant-rg}
LOC=${LOC:-centralindia}
ENV_NAME=${ENV_NAME:-de-assistant-env}
APP=${APP:-de-assistant}
IMAGE=${IMAGE:-ghcr.io/mittalmayank842/de-assistant:latest}
REPO=${REPO:-mittalmayank842/de-assistant}

SUB=$(az account show --query id -o tsv)
TENANT=$(az account show --query tenantId -o tsv)
echo "Subscription: $SUB"

az extension add --name containerapp --upgrade -y --only-show-errors
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

az group create -n "$RG" -l "$LOC" -o none

az containerapp env create -n "$ENV_NAME" -g "$RG" -l "$LOC" --logs-destination none -o none

az containerapp create -n "$APP" -g "$RG" --environment "$ENV_NAME" \
  --image "$IMAGE" --target-port 8000 --ingress external \
  --cpu 0.5 --memory 1.0Gi --min-replicas 0 --max-replicas 1 \
  --env-vars PIPELINE_HOME=/nonexistent -o none

FQDN=$(az containerapp show -n "$APP" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)
echo "App URL: https://$FQDN"

# GitHub Actions identity, federated with this repo's main branch (no client secret).
CLIENT_ID=$(az ad app create --display-name "gh-$APP-deploy" --query appId -o tsv)
az ad sp create --id "$CLIENT_ID" -o none 2>/dev/null || true
sleep 20  # let the service principal propagate before the role assignment
az role assignment create --assignee "$CLIENT_ID" --role Contributor \
  --scope "/subscriptions/$SUB/resourceGroups/$RG" -o none
az ad app federated-credential create --id "$CLIENT_ID" --parameters "{
  \"name\": \"github-main\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"repo:$REPO:ref:refs/heads/main\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}" -o none

gh secret set AZURE_CLIENT_ID -R "$REPO" -b "$CLIENT_ID"
gh secret set AZURE_TENANT_ID -R "$REPO" -b "$TENANT"
gh secret set AZURE_SUBSCRIPTION_ID -R "$REPO" -b "$SUB"
gh variable set AZURE_APP -R "$REPO" -b "$APP"
gh variable set AZURE_RG -R "$REPO" -b "$RG"
gh variable set AZURE_URL -R "$REPO" -b "https://$FQDN"

echo "Waiting for the first start (scale from zero)..."
for i in $(seq 1 40); do
  if curl -sf "https://$FQDN/health"; then echo; echo "Live: https://$FQDN/health"; exit 0; fi
  sleep 6
done
echo "App created but /health did not answer yet; check: az containerapp logs show -n $APP -g $RG"
