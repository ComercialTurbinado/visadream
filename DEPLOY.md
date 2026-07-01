# Deploy — VisaDream / D4U

App: FastAPI (Python) + HTML estático. Geração de imagem leva ~40s (medium).

## Arquitetura recomendada
- **Backend (este app):** AWS **Lightsail Container** (always-on, sem cold start, barato)
- **Banco (leads + jobs):** **MongoDB Atlas**
- **Arte (imagens):** **GridFS** no próprio MongoDB, servida por token via `/api/art-image`
- **Anti-bot:** Cloudflare Turnstile
- **CRM:** HubSpot  *(pendente)*

## Variáveis de ambiente
| Var | Obrigatória | Descrição |
|-----|-------------|-----------|
| `OPENAI_API_KEY` | ✅ | Chave da OpenAI |
| `TURNSTILE_SITE_KEY` | recomendada | Site key (pública) do Cloudflare Turnstile |
| `TURNSTILE_SECRET` | recomendada | Secret do Turnstile — ativa o anti-bot |
| `IMAGE_MODEL` | não | Padrão `gpt-image-2` |
| `IMAGE_QUALITY` | não | `medium` (padrão) ou `high` |
| `PORT` | não | Padrão `8002` |
| `MONGODB_URI` | ✅ | Connection string do MongoDB Atlas (leads + jobs + arte) |
| `MONGODB_DB` | não | Nome do banco (padrão `visadream`) |
| `HUBSPOT_TOKEN` | (futuro) | Private app token do HubSpot |
| `ADMIN_PASSWORD` | ✅ (admin) | Senha do painel `/admin` (leads + CSV) |
| `ALLOW_OFFLINE_QUEUE` | recomendada (eventos) | `1` = aceita envios sincronizados da fila offline (`__offline_queue__`) |

> Nunca commitar `.env`. Em produção, setar via env vars do Lightsail/AWS Secrets Manager.

## Modo offline (eventos com internet instável)
- O formulário salva leads no **IndexedDB** do navegador quando não há conexão.
- Um **Service Worker** permite reabrir o formulário sem internet.
- Quando a conexão volta, os cadastros são **enviados automaticamente** (a cada 30s ou ao voltar online).
- Em produção para eventos, defina `ALLOW_OFFLINE_QUEUE=1` no EasyPanel.

## Painel de leads (`/admin`)
- Acesse `https://seu-dominio/admin` com a senha definida em `ADMIN_PASSWORD`.
- Lista todos os leads com respostas do questionário, análise de visto e arte gerada.
- Botão **CSV** exporta todos os campos.
- Leads ficam no MongoDB (`visadream.leads`); fallback local em `leads.json`.

## Subir no AWS Lightsail Container (resumo)
1. `aws lightsail create-container-service --service-name visadream --power small --scale 1`
2. Build & push da imagem:
   - `docker build -t visadream .`
   - `aws lightsail push-container-image --service-name visadream --label app --image visadream`
3. Deploy com o container, porta 8002 pública, e as env vars acima.
4. Endpoint HTTPS já vem com domínio Lightsail (`*.lightsail...`); apontar o domínio da D4U via DNS depois.

## Cloudflare Turnstile (ativar anti-bot)
1. Cloudflare → Turnstile → criar widget para o domínio.
2. Copiar **Site Key** → `TURNSTILE_SITE_KEY`; **Secret** → `TURNSTILE_SECRET`.
3. Redeploy. O widget aparece no passo de dados e passa a ser exigido.

## ⚠️ Pendente antes de produção real
- **Persistência:** hoje `leads.json` (arquivo) e `JOBS` (memória) — em container, somem em redeploy. Migrar para **Supabase** (tabela `leads` + bucket privado + tornar o token persistente).
- **Entrega por e-mail:** enviar o link `/arte?token=...` por e-mail (AWS SES ou Resend) quando a arte ficar pronta.
- **HubSpot:** criar/atualizar contato no `/api/submit`.
- **LGPD:** checkbox de consentimento + política de privacidade + retenção.
