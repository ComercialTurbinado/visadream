import os
import io
import csv
import uuid
import json
import base64
import secrets
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Any

import urllib.request
import urllib.parse
import urllib.error

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


def _client_ip(request: Request) -> str:
    """IP real do cliente — honra X-Forwarded-For (atrás de proxy/Lightsail/ALB)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


# Rate limiting por IP (em memória; para múltiplas instâncias, usar Redis depois).
limiter = Limiter(key_func=_client_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def verify_turnstile(token: str, remoteip: str = "") -> bool:
    """Valida o Cloudflare Turnstile. Desativado (passa direto) quando não há
    TURNSTILE_SECRET — assim local/dev funciona; em produção, setar a chave ativa."""
    if token == "__offline_queue__" and OFFLINE_QUEUE_ENABLED:
        return True
    secret = os.environ.get("TURNSTILE_SECRET", "")
    if not secret:
        return True
    if not token:
        return False
    try:
        data = urllib.parse.urlencode(
            {"secret": secret, "response": token, "remoteip": remoteip}
        ).encode()
        req = urllib.request.Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify", data=data
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return bool(json.loads(r.read()).get("success"))
    except Exception as e:
        print(f"[turnstile] erro: {e}")
        return False

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

RESULTS_DIR = Path("static/results")
RESULTS_DIR.mkdir(exist_ok=True)

LEADS_FILE = Path("leads.json")

# Modelo de imagem. gpt-image-2 gera murais bem mais ricos/detalhados (porém mais
# lento, ~2-3min em qualidade alta). Processa a entrada em alta fidelidade sozinho.
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-2")
# Qualidade: "medium" (mais rápido/barato) ou "high" (mais detalhado/lento).
IMAGE_QUALITY = os.environ.get("IMAGE_QUALITY", "medium")

# Logo real sobreposto na arte (mantém o logo 100% fiel, sem o modelo redesenhá-lo).
# Usa a versão azul-marinho, que fica legível sobre o badge branco.
LOGO_FILE = Path("assets/D4U-a.png")

# ── Integrações opcionais (ativam só quando as env vars existem) ──────────────
MONGODB_URI = os.environ.get("MONGODB_URI", "")
MONGODB_DB = os.environ.get("MONGODB_DB", "visadream")
MONGO_ENABLED = bool(MONGODB_URI)
HUBSPOT_TOKEN = os.environ.get("HUBSPOT_TOKEN", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip().strip('"').strip("'")
if ADMIN_PASSWORD:
    print(f"[admin] ADMIN_PASSWORD configurado (len={len(ADMIN_PASSWORD)})")

CSV_COLUMNS = [
    "created_at", "nome", "sobrenome", "email", "whatsapp", "nascimento",
    "interesse", "area", "formacao", "experiencia", "familia",
    "motivo_viagem", "duracao_viagem", "historico_visto",
    "negocio_tipo", "capital", "ja_empresa", "investimento", "tipo_investimento",
    "cidade", "sonho", "visto_principal", "visto_secundario", "probabilidade",
    "elegivel", "motivo_principal", "mensagem_sonho", "pontos_fortes", "pontos_atencao",
    "art_status", "art_url", "token",
]

OFFLINE_QUEUE_ENABLED = os.environ.get("ALLOW_OFFLINE_QUEUE", "").strip().lower() in ("1", "true", "yes", "on")
_mongo_db = None
_mongo_fs = None


def get_mongo():
    """(db, gridfs) com import/conexão tardios. tlsCAFile=certifi resolve o CA do macOS."""
    global _mongo_db, _mongo_fs
    if _mongo_db is None:
        import certifi
        import gridfs
        from pymongo import MongoClient
        client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=8000)
        _mongo_db = client[MONGODB_DB]
        _mongo_fs = gridfs.GridFS(_mongo_db, collection="artes")
    return _mongo_db, _mongo_fs


def hubspot_upsert(data: dict, token: str = "") -> None:
    """Cria/atualiza o contato no HubSpot (campos padrão). Dormente sem HUBSPOT_TOKEN."""
    if not HUBSPOT_TOKEN:
        return
    email = (data.get("email") or "").strip()
    if not email:
        return
    body = json.dumps({"properties": {
        "email": email,
        "firstname": data.get("nome", ""),
        "lastname": data.get("sobrenome", ""),
        "phone": data.get("whatsapp", ""),
    }}).encode()
    headers = {"Authorization": f"Bearer {HUBSPOT_TOKEN}", "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(
            "https://api.hubapi.com/crm/v3/objects/contacts", data=body, headers=headers)
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as e:
        if e.code == 409:  # contato já existe → atualiza por e-mail
            try:
                url = ("https://api.hubapi.com/crm/v3/objects/contacts/"
                       f"{urllib.parse.quote(email)}?idProperty=email")
                upd = urllib.request.Request(url, data=body, headers=headers, method="PATCH")
                urllib.request.urlopen(upd, timeout=10)
            except Exception as e2:
                print(f"[hubspot] update falhou: {e2}")
        else:
            print(f"[hubspot] erro {e.code}: {e}")
    except Exception as e:
        print(f"[hubspot] erro: {e}")


def get_openai():
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def get_zodiac(birth_str: str) -> dict:
    try:
        bd = datetime.strptime(birth_str, "%Y-%m-%d")
    except Exception:
        return {"sign": "", "element": "", "trait": ""}

    m, d = bd.month, bd.day
    signs = [
        (1, 20, "Capricórnio", "Terra", "determinado e ambicioso"),
        (2, 19, "Aquário",     "Ar",    "inovador e independente"),
        (3, 20, "Peixes",      "Água",  "intuitivo e criativo"),
        (4, 20, "Áries",       "Fogo",  "corajoso e pioneiro"),
        (5, 21, "Touro",       "Terra", "persistente e confiável"),
        (6, 21, "Gêmeos",      "Ar",    "versátil e comunicativo"),
        (7, 23, "Câncer",      "Água",  "protetor e empático"),
        (8, 23, "Leão",        "Fogo",  "carismático e líder nato"),
        (9, 23, "Virgem",      "Terra", "analítico e dedicado"),
        (10,23, "Libra",       "Ar",    "equilibrado e diplomático"),
        (11,22, "Escorpião",   "Água",  "intenso e estratégico"),
        (12,22, "Sagitário",   "Fogo",  "aventureiro e otimista"),
        (12,31, "Capricórnio", "Terra", "determinado e ambicioso"),
    ]
    for mo, day, sign, element, trait in signs:
        if m < mo or (m == mo and d <= day):
            return {"sign": sign, "element": element, "trait": trait}
    return {"sign": "Capricórnio", "element": "Terra", "trait": "determinado e ambicioso"}


SYSTEM_ELIGIBILITY = """Você é um especialista em vistos americanos e imigração para os EUA.
Analise as respostas do questionário e determine a elegibilidade para Green Card ou vistos americanos.
Leve em conta o OBJETIVO principal informado (viajar, morar/trabalhar, investir ou empreender) ao recomendar o visto.

Vistos a considerar:
- B-1/B-2: Turismo, negócios ou visita de curta duração
- ESTA: Autorização eletrônica para países do VWP (viagens curtas)
- F-1/M-1: Estudo (se aplicável ao perfil)
- EB-1A: Habilidade extraordinária (prêmios, publicações, liderança)
- EB-1B: Pesquisadores e professores destacados
- EB-2 NIW: National Interest Waiver (profissionais com impacto nacional)
- EB-2: Profissionais com grau avançado + oferta de emprego
- EB-3: Trabalhadores qualificados com oferta de emprego
- EB-5: Investidores ($800k–$1,05M)
- E-2: Investidor de tratado (capital menor, negócio ativo nos EUA)
- O-1: Talento extraordinário (artistas, atletas, executivos)
- L-1: Transferência corporativa intraempresarial (quem já tem empresa)
- Green Card familiar (IR/F): por cônjuge, pais, filhos ou irmãos cidadãos/residentes
- Para quem quer apenas MORAR sem oferta de trabalho: considere via familiar, EB-5/E-2 por investimento, ou aposentadoria com renda própria

Responda APENAS com JSON válido, sem markdown:
{
  "elegivel": true/false,
  "visto_principal": "nome do visto mais adequado",
  "visto_secundario": "alternativa ou null",
  "probabilidade": "Alta / Média / Baixa",
  "motivo_principal": "razão em 1 frase",
  "pontos_fortes": ["ponto 1", "ponto 2", "ponto 3"],
  "pontos_atencao": ["ponto 1", "ponto 2"],
  "mensagem_sonho": "mensagem personalizada e inspiradora de 2-3 frases conectando o sonho dele com o visto e a cidade escolhida",
  "prompt_imagem": "in English, describe ONLY the visual story elements of this person's American dream to illustrate: their main goal/activity (work, investment or business), the chosen city and its famous landmarks, symbols of success and a few lifestyle details. Describe the scene and journey — do NOT specify any art style or rendering technique."
}"""


@app.get("/", response_class=HTMLResponse)
async def root():
    return Path("static/index.html").read_text(encoding="utf-8")


INTERESSE_LABEL = {
    "viajar": "Viajar para os EUA",
    "morar_trabalhar": "Morar e Trabalhar nos EUA",
    "empreender": "Empreender / Abrir empresa",
    "investir": "Investir",
}


def build_interest_section(data: dict) -> str:
    """Monta a parte do prompt específica do objetivo escolhido."""
    interesse = data.get("interesse", "")

    if interesse == "viajar":
        return (
            f"Motivo da viagem: {data.get('motivo_viagem', '')}\n"
            f"Duração pretendida: {data.get('duracao_viagem', '')}\n"
            f"Histórico de visto americano: {data.get('historico_visto', '')}\n"
        )
    if interesse == "morar_trabalhar":
        return (
            f"Área de atuação: {data.get('area', '')}\n"
            f"Nível de formação: {data.get('formacao', '')}\n"
            f"Anos de experiência na área: {data.get('experiencia', '')}\n"
            f"Familiar próximo cidadão/residente nos EUA: {data.get('familia', '')}\n"
        )
    if interesse == "empreender":
        return (
            f"Tipo de negócio que quer tocar nos EUA: {data.get('negocio_tipo', '')}\n"
            f"Capital disponível para começar: {data.get('capital', '')}\n"
            f"Já tem empresa: {data.get('ja_empresa', '')}\n"
        )
    if interesse == "investir":
        return (
            f"Capacidade de investimento: {data.get('investimento', '')}\n"
            f"Onde pretende investir: {data.get('tipo_investimento', '')}\n"
        )
    return ""


def save_lead(data: dict, result: dict) -> None:
    """Grava o lead no MongoDB (se configurado) ou no leads.json local. Nunca quebra a análise."""
    lead = {
        "token": data.get("token", ""),
        "nome": data.get("nome", ""),
        "sobrenome": data.get("sobrenome", ""),
        "email": data.get("email", ""),
        "whatsapp": data.get("whatsapp", ""),
        "nascimento": data.get("nascimento", ""),
        "interesse": data.get("interesse", ""),
        "area": data.get("area", ""),
        "formacao": data.get("formacao", ""),
        "experiencia": data.get("experiencia", ""),
        "familia": data.get("familia", ""),
        "motivo_viagem": data.get("motivo_viagem", ""),
        "duracao_viagem": data.get("duracao_viagem", ""),
        "historico_visto": data.get("historico_visto", ""),
        "negocio_tipo": data.get("negocio_tipo", ""),
        "capital": data.get("capital", ""),
        "ja_empresa": data.get("ja_empresa", ""),
        "investimento": data.get("investimento", ""),
        "tipo_investimento": data.get("tipo_investimento", ""),
        "cidade": data.get("cidade", ""),
        "sonho": data.get("sonho", ""),
        "visto_principal": result.get("visto_principal", ""),
        "visto_secundario": result.get("visto_secundario") or "",
        "probabilidade": result.get("probabilidade", ""),
        "elegivel": result.get("elegivel", None),
        "motivo_principal": result.get("motivo_principal", ""),
        "mensagem_sonho": result.get("mensagem_sonho", ""),
        "pontos_fortes": result.get("pontos_fortes") or [],
        "pontos_atencao": result.get("pontos_atencao") or [],
    }

    if MONGO_ENABLED:
        try:
            db, _ = get_mongo()
            db.leads.insert_one({"created_at": datetime.now(), **lead})
            return
        except Exception as e:
            print(f"[leads] mongo falhou, salvando local: {e}")

    # Fallback local (leads.json)
    try:
        rec = {"timestamp": datetime.now().isoformat(timespec="seconds"), **lead}
        leads = []
        if LEADS_FILE.exists():
            try:
                leads = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
                if not isinstance(leads, list):
                    leads = []
            except json.JSONDecodeError:
                leads = []
        leads.append(rec)
        LEADS_FILE.write_text(json.dumps(leads, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[leads] falha ao salvar lead: {e}")


def sanitize_payload(data: dict, max_len: int = 300) -> dict:
    """Limita o payload: só aceita str/num/bool, corta strings e o nº de campos.
    Evita prompts gigantes (custo), poluição do lead e entrada maliciosa."""
    out = {}
    for k, v in list((data or {}).items())[:40]:
        if not isinstance(k, str) or len(k) > 40:
            continue
        if isinstance(v, str):
            out[k] = v.strip()[:max_len]
        elif isinstance(v, (int, float, bool)) or v is None:
            out[k] = v
    return out


def run_analysis(data: dict) -> dict:
    data = sanitize_payload(data)
    client = get_openai()

    zodiac = get_zodiac(data.get("nascimento", ""))
    interesse = data.get("interesse", "")
    interesse_label = INTERESSE_LABEL.get(interesse, interesse or "Não informado")

    user_prompt = f"""
Analise este perfil para elegibilidade de visto americano:

Nome: {data.get('nome', '')}
Data de nascimento: {data.get('nascimento', '')} (Signo: {zodiac['sign']}, Elemento: {zodiac['element']}, Traço: {zodiac['trait']})
OBJETIVO PRINCIPAL: {interesse_label}

{build_interest_section(data)}
Cidade dos sonhos nos EUA: {data.get('cidade', '')}
Sonho / motivação: {data.get('sonho', '')}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_ELIGIBILITY},
            {"role": "user",   "content": user_prompt},
        ],
    )

    result = json.loads(response.choices[0].message.content)
    result["zodiac"] = zodiac
    result["nome"] = data.get("nome", "")
    result["cidade"] = data.get("cidade", "")
    result["sonho"] = data.get("sonho", "")

    return result


def pad_to_9x16(image_path: Path) -> None:
    """Completa a arte para o ratio 9:16 exato com faixas brancas (o fundo do mural já
    é branco, então fica quase imperceptível). Falha silenciosa."""
    try:
        from PIL import Image

        im = Image.open(image_path).convert("RGB")
        w, h = im.size
        target_h = round(w * 16 / 9)
        if h >= target_h:
            return
        canvas = Image.new("RGB", (w, target_h), (255, 255, 255))
        canvas.paste(im, (0, (target_h - h) // 2))
        canvas.save(image_path)
    except Exception as e:
        print(f"[generate-image] falha ao ajustar 9:16: {e}")


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


def run_art_generation(photo_bytes: bytes, prompt: str, nome: str = "",
                       cidade: str = "", nascimento: str = "") -> str:
    """Gera o mural a partir dos bytes da foto (em memória) e devolve o nome do arquivo."""
    client = get_openai()
    chosen_model = IMAGE_MODEL

    # Limita os campos de texto (custo do prompt / poluição).
    prompt = (prompt or "").strip()[:1500]
    nome = (nome or "").strip()[:80]
    cidade = (cidade or "").strip()[:80]
    nascimento = (nascimento or "").strip()[:10]

    logo_bytes = LOGO_FILE.read_bytes() if LOGO_FILE.exists() else None

    first_name = (nome or "").strip().split(" ")[0] if nome else ""
    name_clause = (
        f"The only readable text that is a person's name must be '{first_name}', "
        "hand-lettered once as the protagonist's label — do not invent any other name. "
        if first_name else ""
    )

    # Traços de personalidade (sempre positivos) a partir da data de nascimento (signo).
    zodiac = get_zodiac(nascimento)
    personality_clause = (
        f"Sprinkle a couple of tiny uplifting personality doodles/labels in Portuguese "
        f"reflecting that this person is '{zodiac['trait']}' — always positive and inspiring. "
        if zodiac.get("trait") else ""
    )

    # O logo entra como SEGUNDA imagem de referência: o modelo o redesenha no estilo do
    # mural (como a caricatura), mantendo as características — não é colado.
    logo_clause = (
        "The SECOND provided image is the D4U company logo (the letters D and U in dark "
        "navy blue with a golden number 4 between them, and the word IMMIGRATION below). "
        "Redraw THIS logo by hand as a doodle in the SAME colored-marker style as the rest "
        "of the mural, keeping its characteristics clearly recognizable (navy D-4-U with the "
        "gold 4 and the IMMIGRATION wordmark), placed on a little hand-drawn sign or banner "
        "in a corner — integrated into the art, not pasted. "
        if logo_bytes else ""
    )

    full_prompt = (
        "Create a colorful hand-drawn 'Draw My Life' style mural in a TALL VERTICAL 9:16 "
        "portrait composition: a cheerful doodle collage as if sketched with colored markers "
        "on a clean white background, filling the whole vertical frame. "
        "Use the FIRST provided image (a real person) as reference to draw a friendly cartoon "
        "CARICATURE of them as the smiling protagonist — keep their hairstyle, hair color, "
        "skin tone and general features recognizable, but illustrated as a cute, tidy "
        "hand-drawn character (not photorealistic). "
        "ONLY the protagonist is drawn as a character with a face. Do NOT draw any other "
        "people or faces — represent family, home and loved ones symbolically instead "
        "(a little house, hearts, a family icon), never as drawn faces. "
        f"Illustrate their American dream as a lively story collage of small doodle scenes: {prompt}. "
        "Connect the little scenes with simple sketched arrows, add small icons, stars, "
        "hearts, the chosen city's famous landmarks drawn as doodles, and the US flag. "
        f"Add a few short hand-written-style labels in Portuguese. {name_clause}{personality_clause}"
        "Hand-letter a small ribbon/banner with the exact Portuguese phrase spelled "
        "correctly: \"D4U, a empresa que pode realizar meu sonho!\". "
        f"{logo_clause}"
        "Vibrant marker colors, flat 2D hand-drawn illustration, optimistic and playful, "
        "white background, absolutely no photorealism."
    )

    def make_image_input():
        # 1ª imagem = rosto (caricatura); 2ª = logo D4U (redesenhado no estilo).
        # Recria a cada tentativa pois o stream é consumido.
        person = io.BytesIO(photo_bytes)
        person.name = "face.png"
        if logo_bytes:
            logo = io.BytesIO(logo_bytes)
            logo.name = "d4u-logo.png"
            return [person, logo]
        return person

    # gpt-image-2 já processa a entrada em alta fidelidade (não aceita input_fidelity);
    # modelos gpt-image-1.x aceitam o parâmetro. Em todos os casos tentamos EDITAR (usa o
    # rosto pra caricatura); só geramos sem foto como último recurso.
    q = IMAGE_QUALITY
    if chosen_model.startswith("gpt-image-2"):
        param_variants = [{"quality": q}, {}]
    else:
        param_variants = [{"input_fidelity": "high", "quality": q}, {"quality": q}, {}]

    # 9:16 vertical (a opção retrato nativa do gpt-image é 1024x1536).
    IMG_SIZE = "1024x1536"

    response = None
    for extra in param_variants:
        try:
            response = client.images.edit(
                model=chosen_model,
                image=make_image_input(),
                prompt=full_prompt,
                size=IMG_SIZE,
                **extra,
            )
            break
        except Exception as e:
            print(f"[generate-image] edit falhou com {list(extra)}: {e}")

    if response is None:
        print("[generate-image] usando fallback sem foto")
        response = client.images.generate(
            model=chosen_model,
            prompt=full_prompt,
            size=IMG_SIZE,
            quality=IMAGE_QUALITY,
        )

    img_data = response.data[0]

    # Salva imagem
    filename = f"result_{uuid.uuid4().hex}.png"
    result_path = RESULTS_DIR / filename

    if hasattr(img_data, "b64_json") and img_data.b64_json:
        result_path.write_bytes(base64.b64decode(img_data.b64_json))
    elif hasattr(img_data, "url") and img_data.url:
        import urllib.request
        urllib.request.urlretrieve(img_data.url, str(result_path))
    else:
        raise HTTPException(500, "Não foi possível obter a imagem gerada.")

    pad_to_9x16(result_path)

    return filename


# ── Entrega da arte por token ─────────────────────────────────────────────────
# Store de jobs: MongoDB (coleção art_jobs) quando configurado; senão, memória local.
JOBS: dict = {}


def job_create(token: str, fields: dict) -> None:
    if MONGO_ENABLED:
        try:
            db, _ = get_mongo()
            db.art_jobs.insert_one({"_id": token, "created": datetime.now(), **fields})
            return
        except Exception as e:
            print(f"[jobs] mongo insert falhou: {e}")
    JOBS[token] = fields


def job_get(token: str):
    if MONGO_ENABLED:
        try:
            db, _ = get_mongo()
            return db.art_jobs.find_one({"_id": token})
        except Exception as e:
            print(f"[jobs] mongo get falhou: {e}")
            return None
    return JOBS.get(token)


def job_update(token: str, fields: dict) -> None:
    if MONGO_ENABLED:
        try:
            db, _ = get_mongo()
            db.art_jobs.update_one({"_id": token}, {"$set": fields})
            return
        except Exception as e:
            print(f"[jobs] mongo update falhou: {e}")
            return
    if token in JOBS:
        JOBS[token].update(fields)


def _art_job(token: str, photo_bytes: bytes, prompt: str,
             nome: str, cidade: str, nascimento: str) -> None:
    """Roda em background: gera a arte, guarda no GridFS (se Mongo) e atualiza o job."""
    try:
        filename = run_art_generation(photo_bytes, prompt, nome, cidade, nascimento)
        local_path = RESULTS_DIR / filename

        if MONGO_ENABLED:
            try:
                _, fs = get_mongo()
                with open(local_path, "rb") as f:
                    file_id = fs.put(f.read(), filename=filename, contentType="image/png", token=token)
                job_update(token, {"status": "done", "art_file_id": str(file_id),
                                   "art_url": f"/api/art-image?token={token}"})
                try:
                    local_path.unlink()  # não guarda PII localmente
                except Exception:
                    pass
                return
            except Exception as e:
                print(f"[art-job] gridfs falhou, mantendo local: {e}")

        job_update(token, {"status": "done", "art_url": f"/static/results/{filename}"})
    except Exception as e:
        print(f"[art-job] falha ao gerar arte: {e}")
        job_update(token, {"status": "failed"})


@app.get("/api/config")
async def config():
    # Só a site key (pública). O segredo do Turnstile NUNCA sai do servidor.
    return JSONResponse({
        "turnstile_site_key": os.environ.get("TURNSTILE_SITE_KEY", ""),
        "offline_queue": OFFLINE_QUEUE_ENABLED,
    })


@app.post("/api/submit")
@limiter.limit("6/minute;40/hour")
async def submit(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: str = Form(...),
    photo: Optional[UploadFile] = File(None),
    cf_turnstile_response: str = Form(""),
):
    # Anti-bot: bloqueia automação que queimaria crédito da OpenAI.
    if not verify_turnstile(cf_turnstile_response, _client_ip(request)):
        raise HTTPException(403, "Verificação de segurança falhou. Recarregue e tente de novo.")

    try:
        data = sanitize_payload(json.loads(payload))
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(400, "Dados inválidos.")

    # Foto é opcional — valida tipo e tamanho quando enviada.
    photo_bytes = None
    if photo is not None and (photo.content_type or photo.filename):
        if (photo.content_type or "").lower() not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(400, "Formato de imagem inválido. Use JPG, PNG ou WEBP.")
        photo_bytes = await photo.read()
        if not photo_bytes or len(photo_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(400, "Imagem ausente ou muito grande (máx. 8MB).")

    # Análise (rápida) + cadastro do lead.
    result = run_analysis(data)

    token = secrets.token_urlsafe(24)
    job_create(token, {
        "nome": result.get("nome", ""),
        "elegivel": result.get("elegivel", None),
        "mensagem": result.get("mensagem_sonho", ""),
        "status": "processing" if photo_bytes else "done",
    })
    save_lead({**data, "token": token}, result)
    background_tasks.add_task(hubspot_upsert, data, token)

    # Geração da arte em background (não trava a resposta).
    if photo_bytes:
        prompt_img = result.get("prompt_imagem") or \
            f"Dream life in {data.get('cidade', '')}: {data.get('sonho', '')}"
        background_tasks.add_task(
            _art_job, token, photo_bytes, prompt_img,
            data.get("nome", ""), data.get("cidade", ""), data.get("nascimento", ""),
        )

    return JSONResponse({"token": token})


@app.get("/api/art-status")
async def art_status(token: str):
    job = job_get(token)
    if not job:
        raise HTTPException(404, "Link inválido ou expirado.")
    # Devolve só o necessário — nunca e-mail/telefone.
    return JSONResponse({
        "nome": job.get("nome", ""),
        "elegivel": job.get("elegivel"),
        "mensagem": job.get("mensagem", ""),
        "status": job.get("status"),
        "art_url": job.get("art_url"),
    })


@app.get("/api/art-image")
async def art_image(token: str):
    """Serve a arte guardada no GridFS — acesso só com o token (gated)."""
    if not MONGO_ENABLED:
        raise HTTPException(404, "Indisponível.")
    job = job_get(token)
    if not job or not job.get("art_file_id"):
        raise HTTPException(404, "Arte não encontrada.")
    try:
        from bson import ObjectId
        _, fs = get_mongo()
        data = fs.get(ObjectId(job["art_file_id"])).read()
    except Exception as e:
        print(f"[art-image] erro: {e}")
        raise HTTPException(404, "Arte não encontrada.")
    return Response(content=data, media_type="image/png",
                    headers={"Content-Disposition": 'inline; filename="minha-arte-d4u.png"'})


@app.get("/arte", response_class=HTMLResponse)
async def arte_page():
    return Path("static/arte.html").read_text(encoding="utf-8")


# ── Admin (dashboard de leads) ────────────────────────────────────────────────

def verify_admin(request: Request) -> bool:
    """Autenticação simples via Bearer token (= ADMIN_PASSWORD)."""
    if not ADMIN_PASSWORD:
        return False
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        if not token:
            return False
        return secrets.compare_digest(token, ADMIN_PASSWORD)
    return False


def _lead_created_at(lead: dict) -> datetime:
    if isinstance(lead.get("created_at"), datetime):
        return lead["created_at"]
    ts = lead.get("timestamp", "")
    if ts:
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            pass
    return datetime.min


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    return value


def enrich_lead_with_art(lead: dict) -> dict:
    """Junta dados do lead com status/URL da arte gerada."""
    out = {k: _serialize_value(v) for k, v in lead.items() if k != "_id"}
    token = out.get("token", "")
    if token:
        job = job_get(token)
        if job:
            out["art_status"] = job.get("status", "")
            out["art_url"] = job.get("art_url", "")
            if not out.get("mensagem_sonho"):
                out["mensagem_sonho"] = job.get("mensagem", "")
    out.setdefault("art_status", "")
    out.setdefault("art_url", "")
    if "created_at" not in out and out.get("timestamp"):
        out["created_at"] = out["timestamp"]
    return out


def list_all_leads() -> list[dict]:
    """Lista todos os leads (MongoDB ou leads.json local)."""
    if MONGO_ENABLED:
        try:
            db, _ = get_mongo()
            docs = list(db.leads.find().sort("created_at", -1))
            return [{**doc, "_id": str(doc["_id"])} for doc in docs]
        except Exception as e:
            print(f"[admin] mongo list falhou: {e}")
    if not LEADS_FILE.exists():
        return []
    try:
        leads = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
        if not isinstance(leads, list):
            return []
        leads.sort(key=_lead_created_at, reverse=True)
        return leads
    except Exception as e:
        print(f"[admin] falha ao ler leads.json: {e}")
        return []


def leads_to_csv(leads: list[dict]) -> str:
    """Gera CSV com todos os campos dos leads."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for raw in leads:
        row = enrich_lead_with_art(raw)
        for key in ("pontos_fortes", "pontos_atencao"):
            val = row.get(key)
            if isinstance(val, list):
                row[key] = "; ".join(str(v) for v in val)
        row["interesse"] = INTERESSE_LABEL.get(row.get("interesse", ""), row.get("interesse", ""))
        if row.get("elegivel") is True:
            row["elegivel"] = "Sim"
        elif row.get("elegivel") is False:
            row["elegivel"] = "Não"
        writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})
    return buf.getvalue()


@app.get("/api/admin/status")
async def admin_status():
    """Indica se o painel está configurado (sem expor a senha)."""
    return JSONResponse({"configured": bool(ADMIN_PASSWORD), "password_len": len(ADMIN_PASSWORD) if ADMIN_PASSWORD else 0})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    if not ADMIN_PASSWORD:
        raise HTTPException(503, "Painel admin não configurado (defina ADMIN_PASSWORD).")
    return Path("static/admin.html").read_text(encoding="utf-8")


@app.post("/api/admin/login")
@limiter.limit("20/minute")
async def admin_login(request: Request, body: dict = Body(...)):
    """Valida a senha (POST evita problemas com caracteres especiais no header)."""
    if not ADMIN_PASSWORD:
        raise HTTPException(503, "Painel admin não configurado.")
    pwd = str(body.get("password", "")).strip()
    if not pwd or not secrets.compare_digest(pwd, ADMIN_PASSWORD):
        raise HTTPException(401, "Senha incorreta.")
    return JSONResponse({"ok": True})


@app.get("/api/admin/leads")
@limiter.limit("60/minute")
async def admin_list_leads(request: Request):
    if not ADMIN_PASSWORD:
        raise HTTPException(503, "Painel admin não configurado.")
    if not verify_admin(request):
        raise HTTPException(401, "Senha incorreta.")
    leads = [enrich_lead_with_art(l) for l in list_all_leads()]
    return JSONResponse(leads)


@app.get("/api/admin/leads.csv")
@limiter.limit("10/minute")
async def admin_export_csv(request: Request):
    if not ADMIN_PASSWORD:
        raise HTTPException(503, "Painel admin não configurado.")
    if not verify_admin(request):
        raise HTTPException(401, "Senha incorreta.")
    csv_data = leads_to_csv(list_all_leads())
    filename = f"visadream-leads-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8002))
    # Auto-reload DESLIGADO por padrão: o watchfiles fica instável neste ambiente
    # e derruba o servidor. O index.html é lido a cada request, então edições no
    # front aparecem só recarregando a página. Mudanças no main.py exigem reiniciar.
    # Para ativar o reload em desenvolvimento:  RELOAD=1 python main.py
    reload = os.environ.get("RELOAD", "").strip().lower() in ("1", "true", "yes", "on")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
        reload_includes=["main.py", "static/index.html", "static/admin.html"] if reload else None,
        reload_excludes=["venv/*", "venv", "static/results/*", "uploads/*"] if reload else None,
    )
