#!/usr/bin/env bash
# Azure AI backend for de-assistant. Run after setup.sh.
#
# Creates:
#   - Azure OpenAI: gpt-5-mini (chat) + text-embedding-3-small
#   - Azure AI Search (free tier): hybrid BM25 + vector index
#   - Key Vault holding both keys
# The container app reads the keys through Key Vault references and its managed identity,
# so no key is stored in the app config, the repo or GitHub.
set -euo pipefail
RG=${RG:-de-assistant-rg}; AI_LOC=${AI_LOC:-koreacentral}; APP=${APP:-deassist-api}
SUF=${SUF:-$(az account show --query id -o tsv | shasum | cut -c1-6)}
AOAI=deassist-aoai-$SUF; SEARCH=deassist-search-$SUF; KV=deassist-kv-$SUF

az provider register --namespace Microsoft.CognitiveServices --wait
az provider register --namespace Microsoft.Search --wait
az provider register --namespace Microsoft.KeyVault --wait

az cognitiveservices account create -n "$AOAI" -g "$RG" -l "$AI_LOC" --kind OpenAI --sku S0 --custom-domain "$AOAI" --yes -o none
az cognitiveservices account deployment create -n "$AOAI" -g "$RG" --deployment-name chat \
  --model-name gpt-5-mini --model-version 2025-08-07 --model-format OpenAI --sku-name GlobalStandard --sku-capacity 50 -o none
az cognitiveservices account deployment create -n "$AOAI" -g "$RG" --deployment-name text-embedding-3-small \
  --model-name text-embedding-3-small --model-version 1 --model-format OpenAI --sku-name GlobalStandard --sku-capacity 20 -o none

az search service create -n "$SEARCH" -g "$RG" -l "$AI_LOC" --sku free -o none

az keyvault create -n "$KV" -g "$RG" -l "$AI_LOC" --enable-rbac-authorization true -o none
KVID=$(az keyvault show -n "$KV" --query id -o tsv)
az role assignment create --assignee-object-id "$(az ad signed-in-user show --query id -o tsv)" \
  --assignee-principal-type User --role "Key Vault Secrets Officer" --scope "$KVID" -o none
sleep 30
az keyvault secret set --vault-name "$KV" -n azure-openai-key -o none \
  --value "$(az cognitiveservices account keys list -n "$AOAI" -g "$RG" --query key1 -o tsv)"
az keyvault secret set --vault-name "$KV" -n azure-search-key -o none \
  --value "$(az search admin-key show --service-name "$SEARCH" -g "$RG" --query primaryKey -o tsv)"

# Let the app's managed identity read the secrets, then wire them in as Key Vault references.
PID=$(az containerapp show -n "$APP" -g "$RG" --query identity.principalId -o tsv)
az role assignment create --assignee-object-id "$PID" --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" --scope "$KVID" -o none
sleep 60
az containerapp secret set -n "$APP" -g "$RG" --secrets \
  "aoai-key=keyvaultref:https://$KV.vault.azure.net/secrets/azure-openai-key,identityref:system" \
  "search-key=keyvaultref:https://$KV.vault.azure.net/secrets/azure-search-key,identityref:system" -o none
az containerapp update -n "$APP" -g "$RG" -o none --set-env-vars \
  "AZURE_OPENAI_ENDPOINT=https://$AOAI.openai.azure.com" "AZURE_SEARCH_ENDPOINT=https://$SEARCH.search.windows.net" \
  AZURE_OPENAI_KEY=secretref:aoai-key AZURE_SEARCH_KEY=secretref:search-key
echo "Done. The search index is built on the first docs query (or POST /index)."
