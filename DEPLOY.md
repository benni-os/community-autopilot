# 🚀 Community Autopilot — Deploy Guide

## 📋 Pre-requirements

1. **GitHub Account** com acesso à org `benni-os`
2. **NEMESIS API Key** (obter em https://nemesis.benni.os/settings/api-keys)
3. **GitHub Token** com scope `issues:write`
4. **Cluster Kubernetes** (opcional, para deploy K8s)

---

## 🔐 Step 1: Configurar GitHub Secrets

### 1.1. Gerar GitHub Token

1. Acesse: https://github.com/settings/tokens
2. Clique em **Generate new token (classic)**
3. Marque o scope: `issues:write`
4. Nome: `community-autopilot-token`
5. Expirac̃ao: `90 days` (ou `No expiration`)
6. **Copie o token** (ex: `ghp_xxxxxxxxxxxxxxxxxxxx`)

### 1.2. Adicionar Secrets no Repositrio

1. Acesse: https://github.com/benni-os/community-autopilot/settings/secrets/actions
2. Clique em **New repository secret**

Adicione os seguintes secrets:

| Secret name | Valor |
|---|---|
| `AUTOPILOT_GITHUB_TOKEN` | `ghp_xxxxxxxxxxxxxxxxxxxx` (token do passo 1.1) |
| `NEMESIS_URL` | `https://nemesis.benni.os` |
| `NEMESIS_API_KEY` | `your_nemesis_api_key` |
| `TENANT_ID` | `benni-os` |
| `SLACK_WEBHOOK_URL` | (opcional) `https://hooks.slack.com/services/xxx` |

### 1.3. Validar Secrets

Os secrets esto corretos se:
- ✅ Todos os 5 secrets aparecem na lista
- ✅ `AUTOPILOT_GITHUB_TOKEN` comea com `ghp_`
- ✅ `NEMESIS_URL` é uma URL válida

---

## 🐳 Step 2: GitHub Actions Auto-Deploy

Ao fazer push na branch `main`, o workflow `deploy.yml` vai automaticamente:

1. **Build da imagem Docker**
2. **Login no ghcr.io** (GitHub Container Registry)
3. **Push da imagem** para `ghcr.io/benni-os/community-autopilot:latest`

### 2.1. Verificar Build

1. Acesse: https://github.com/benni-os/community-autopilot/actions
2. Clique no workflow **Deploy Docker Image**
3. Verifique se todos os steps esto ✅ verdes

### 2.2. Verificar Imagem

```bash
docker pull ghcr.io/benni-os/community-autopilot:latest
docker run --rm ghcr.io/benni-os/community-autopilot:latest --help
```

**Esperado:**
```
Usage: python -m community_autopilot.cli [OPTIONS] COMMAND [ARGS]
```

---

## ☸️ Step 3: Deploy Kubernetes (Opcional)

### 3.1. Aplicar Secrets

```bash
# Criar namespace (se não existir)
kubectl create namespace benni-os

# Aplicar secrets do Kubernetes
kubectl apply -f k8s/secret.yaml -n benni-os
```

### 3.2. Aplicar CronJob

```bash
# Deploy do CronJob (roda a cada 6h)
kubectl apply -f k8s/cronjob.yaml -n benni-os
```

### 3.3. Verificar Deploy

```bash
# Ver pods
kubectl get pods -n benni-os -l app=community-autopilot

# Ver CronJobs
kubectl get cronjobs -n benni-os

# Ver logs do último job
kubectl logs -n benni-os -l job-name=community-autopilot --tail=100
```

### 3.4. (Opcional) Deploy como Daemon/Webhook

```bash
# Deploy contnuo (webhook endpoint)
kubectl apply -f k8s/deployment.yaml -n benni-os
kubectl apply -f k8s/service.yaml -n benni-os

# Verificar service
kubectl get svc -n benni-os community-autopilot
```

---

## 🔍 Step 4: Monitorar

### 4.1. Logs em Tempo Real

```bash
kubectl logs -n benni-os -l app=community-autopilot -f
```

### 4.2. Eventos NEMESIS

```bash
curl -H "Authorization: Bearer $NEMESIS_API_KEY" \
  "https://nemesis.benni.os/v1/events?tenant_id=benni-os&event_type=watcher.scan_complete" \
  | jq '.data[0]'
```

**Esperado:**
```json
{
  "trace_id": "autopilot-xxxxxxxxxxxx",
  "event_type": "watcher.scan_complete",
  "objective": "Scan all repos for unanswered issues",
  "evidence": {"repos": ["mcp-forge", "benni-nexus", "benni-os"], "issues_found": 0}
}
```

### 4.3. Snapshots

```bash
curl -H "Authorization: Bearer $NEMESIS_API_KEY" \
  "https://nemesis.benni.os/v1/snapshots?tenant_id=benni-os" \
  | jq '.data[0]'
```

---

## 🛠️ Troubleshooting

### Problema: Workflow falha com "unauthorized"

**Soluco:**
1. Verifique se `AUTOPILOT_GITHUB_TOKEN` está correto
2. Regere o token em https://github.com/settings/tokens
3. Atualize o secret

### Problema: NEMESIS timeout

**Soluco:**
1. Verifique se `NEMESIS_URL` está acessvel
2. Teste localmente: `curl $NEMESIS_URL/health`
3. Verifique se `NEMESIS_API_KEY` é válido

### Problema: CronJob não roda

**Soluco:**
```bash
# Verificar eventos do CronJob
kubectl describe cronjob community-autopilot -n benni-os

# Verificar jobs antigos
kubectl get jobs -n benni-os

# Forcar execuco manual
kubectl create job --from=cronjob/community-autopilot manual-run -n benni-os
```

---

## ✅ Checklist Final

- [ ] GitHub secrets configurados
- [ ] Workflow `deploy.yml` executou com sucesso
- [ ] Imagem Docker disponível em `ghcr.io/benni-os/community-autopilot:latest`
- [ ] (Opcional) K8s CronJob aplicado e rodando
- [ ] (Opcional) Eventos NEMESIS aparecendo
- [ ] (Opcional) Snapshots salvos

---

## 📞 Suporte

Em caso de dúvidas, abra uma issue em: https://github.com/benni-os/community-autopilot/issues

**Benni OS Team** — Building the future of autonomous AI operations.
