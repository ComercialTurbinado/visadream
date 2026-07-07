import os
import io
import csv
import uuid
import json
import base64
import secrets
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Any

import urllib.request
import urllib.parse
import urllib.error

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=()"
    return response


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

# Geração de imagem pode levar vários minutos — retentar se ficar preso.
STALE_GENERATION = timedelta(minutes=10)

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
    "created_at", "nome", "sobrenome", "email", "whatsapp", "whatsapp_pais", "nascimento",
    "pais_nascimento", "idioma",
    "interesse", "area", "formacao", "experiencia", "familia",
    "motivo_viagem", "duracao_viagem", "historico_visto",
    "negocio_tipo", "capital", "ja_empresa", "ja_empresa_pais", "investimento", "tipo_investimento",
    "cidade", "sonho", "visto_principal", "visto_secundario", "probabilidade",
    "elegivel", "motivo_principal", "mensagem_sonho", "pontos_fortes", "pontos_atencao",
    "consentimento_lgpd", "art_status", "art_url", "token",
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


def get_zodiac(birth_str: str, lang: str = "pt") -> dict:
    try:
        bd = datetime.strptime(birth_str, "%Y-%m-%d")
    except Exception:
        return {"sign": "", "element": "", "trait": ""}

    m, d = bd.month, bd.day
    signs = [
        (1, 20, "Capricórnio", "Capricorn", "Terra", "Earth", "determinado e ambicioso", "determined and ambitious"),
        (2, 19, "Aquário", "Aquarius", "Ar", "Air", "inovador e independente", "innovative and independent"),
        (3, 20, "Peixes", "Pisces", "Água", "Water", "intuitivo e criativo", "intuitive and creative"),
        (4, 20, "Áries", "Aries", "Fogo", "Fire", "corajoso e pioneiro", "brave and pioneering"),
        (5, 21, "Touro", "Taurus", "Terra", "Earth", "persistente e confiável", "persistent and reliable"),
        (6, 21, "Gêmeos", "Gemini", "Ar", "Air", "versátil e comunicativo", "versatile and communicative"),
        (7, 23, "Câncer", "Cancer", "Água", "Water", "protetor e empático", "protective and empathetic"),
        (8, 23, "Leão", "Leo", "Fogo", "Fire", "carismático e líder nato", "charismatic natural leader"),
        (9, 23, "Virgem", "Virgo", "Terra", "Earth", "analítico e dedicado", "analytical and dedicated"),
        (10, 23, "Libra", "Libra", "Ar", "Air", "equilibrado e diplomático", "balanced and diplomatic"),
        (11, 22, "Escorpião", "Scorpio", "Água", "Water", "intenso e estratégico", "intense and strategic"),
        (12, 22, "Sagitário", "Sagittarius", "Fogo", "Fire", "aventureiro e otimista", "adventurous and optimistic"),
        (12, 31, "Capricórnio", "Capricorn", "Terra", "Earth", "determinado e ambicioso", "determined and ambitious"),
    ]
    en = (lang or "pt").lower().startswith("en")
    for mo, day, sign_pt, sign_en, el_pt, el_en, trait_pt, trait_en in signs:
        if m < mo or (m == mo and d <= day):
            return {
                "sign": sign_en if en else sign_pt,
                "element": el_en if en else el_pt,
                "trait": trait_en if en else trait_pt,
            }
    return {"sign": "Capricorn" if en else "Capricórnio", "element": "Earth" if en else "Terra",
            "trait": "determined and ambitious" if en else "determinado e ambicioso"}


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


SYSTEM_ELIGIBILITY_EN = """You are an expert in US visas and immigration to the United States.
Analyze the questionnaire answers and determine eligibility for a Green Card or US visas.
Consider the main GOAL (travel, live/work, invest, or entrepreneurship) when recommending the visa.

Visas to consider:
- B-1/B-2: Tourism, business, or short visits
- ESTA: Electronic authorization for VWP countries (short trips)
- F-1/M-1: Study (if applicable)
- EB-1A: Extraordinary ability
- EB-1B: Outstanding researchers and professors
- EB-2 NIW: National Interest Waiver
- EB-2: Advanced degree professionals with job offer
- EB-3: Skilled workers with job offer
- EB-5: Investors ($800k–$1.05M)
- E-2: Treaty investor
- O-1: Extraordinary talent
- L-1: Intracompany transfer
- Family-based Green Card (IR/F)

Respond ONLY with valid JSON, no markdown. All user-facing text fields must be in English:
{
  "elegivel": true/false,
  "visto_principal": "most suitable visa name",
  "visto_secundario": "alternative or null",
  "probabilidade": "Alta / Média / Baixa",
  "motivo_principal": "one-sentence reason in English",
  "pontos_fortes": ["point 1", "point 2", "point 3"],
  "pontos_atencao": ["point 1", "point 2"],
  "mensagem_sonho": "personalized inspiring message in English, 2-3 sentences connecting their dream with the visa and chosen city",
  "prompt_imagem": "in English, describe ONLY the visual story elements of this person's American dream to illustrate: their main goal/activity (work, investment or business), the chosen city and its famous landmarks, symbols of success and a few lifestyle details. Describe the scene and journey — do NOT specify any art style or rendering technique."
}"""


def normalize_idioma(data: dict) -> str:
    idioma = (data.get("idioma") or "pt").strip().lower()
    return "en" if idioma.startswith("en") else "pt"


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
            f"País da empresa: {data.get('ja_empresa_pais', '')}\n"
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
        "whatsapp_pais": data.get("whatsapp_pais", ""),
        "nascimento": data.get("nascimento", ""),
        "pais_nascimento": data.get("pais_nascimento", ""),
        "idioma": normalize_idioma(data),
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
        "ja_empresa_pais": data.get("ja_empresa_pais", ""),
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
        "consentimento_lgpd": bool(data.get("consentimento_lgpd")),
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


def validate_token(token: str) -> str:
    token = (token or "").strip()
    if not TOKEN_RE.match(token):
        raise HTTPException(400, "Token inválido.")
    return token


def validate_lead_data(data: dict) -> None:
    """Validação server-side — não bloqueia fila offline no cliente, só na chegada ao servidor."""
    if not data.get("consentimento_lgpd"):
        raise HTTPException(400, "É necessário aceitar a política de privacidade.")
    if not (data.get("pais_nascimento") or "").strip():
        raise HTTPException(400, "País de nascimento é obrigatório.")
    email = (data.get("email") or "").strip()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "E-mail inválido.")
    whatsapp = re.sub(r"\D", "", data.get("whatsapp") or "")
    if len(whatsapp) < 10:
        raise HTTPException(400, "WhatsApp inválido.")
    nome = (data.get("nome") or "").strip()
    sobrenome = (data.get("sobrenome") or "").strip()
    if not nome or not sobrenome:
        raise HTTPException(400, "Nome e sobrenome são obrigatórios.")


def csv_safe(value) -> str:
    """Evita fórmulas maliciosas ao abrir CSV no Excel."""
    s = "" if value is None else str(value)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def run_analysis(data: dict) -> dict:
    data = sanitize_payload(data)
    client = get_openai()
    idioma = normalize_idioma(data)

    zodiac = get_zodiac(data.get("nascimento", ""), idioma)
    interesse = data.get("interesse", "")
    interesse_label = INTERESSE_LABEL.get(interesse, interesse or "Não informado")

    user_prompt = f"""
Analise este perfil para elegibilidade de visto americano:

Nome: {data.get('nome', '')}
Data de nascimento: {data.get('nascimento', '')} (Signo: {zodiac['sign']}, Elemento: {zodiac['element']}, Traço: {zodiac['trait']})
País de nascimento: {data.get('pais_nascimento', '')}
Idioma da interface: {idioma}
OBJETIVO PRINCIPAL: {interesse_label}

{build_interest_section(data)}
Cidade dos sonhos nos EUA: {data.get('cidade', '')}
Sonho / motivação: {data.get('sonho', '')}
"""

    system_prompt = SYSTEM_ELIGIBILITY_EN if idioma == "en" else SYSTEM_ELIGIBILITY
    if idioma == "en":
        user_prompt = user_prompt.replace("Analise este perfil", "Analyze this profile", 1)

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
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


def get_lead_by_token(token: str) -> Optional[dict]:
    """Busca lead pelo token (MongoDB ou leads.json local)."""
    if MONGO_ENABLED:
        try:
            db, _ = get_mongo()
            return db.leads.find_one({"token": token})
        except Exception as e:
            print(f"[leads] get by token falhou: {e}")
    if LEADS_FILE.exists():
        try:
            leads = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
            if isinstance(leads, list):
                for lead in leads:
                    if lead.get("token") == token:
                        return lead
        except Exception:
            pass
    return None


def run_art_generation(photo_bytes: Optional[bytes], prompt: str, nome: str = "",
                       cidade: str = "", nascimento: str = "", idioma: str = "pt") -> str:
    """Gera o mural e devolve o nome do arquivo. Com foto: caricatura; sem foto: só o sonho."""
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
        if first_name and photo_bytes else
        f"Hand-letter the name '{first_name}' once as a decorative label in the mural — "
        "do not invent any other name. "
        if first_name else ""
    )

    # Traços de personalidade (sempre positivos) a partir da data de nascimento (signo).
    lang = "en" if (idioma or "").lower().startswith("en") else "pt"
    zodiac = get_zodiac(nascimento, lang)
    if lang == "en":
        personality_clause = (
            f"Sprinkle a couple of tiny uplifting personality doodles/labels in English "
            f"reflecting that this person is '{zodiac['trait']}' — always positive and inspiring. "
            if zodiac.get("trait") else ""
        )
        banner_phrase = "D4U, the company that can make my dream come true!"
        labels_lang = "English"
    else:
        personality_clause = (
            f"Sprinkle a couple of tiny uplifting personality doodles/labels in Portuguese "
            f"reflecting that this person is '{zodiac['trait']}' — always positive and inspiring. "
            if zodiac.get("trait") else ""
        )
        banner_phrase = "D4U, a empresa que pode realizar meu sonho!"
        labels_lang = "Portuguese"

    # O logo entra como imagem de referência quando disponível; senão, só no texto do prompt.
    logo_clause = (
        "The SECOND provided image is the D4U company logo (the letters D and U in dark "
        "navy blue with a golden number 4 between them, and the word IMMIGRATION below). "
        "Redraw THIS logo by hand as a doodle in the SAME colored-marker style as the rest "
        "of the mural, keeping its characteristics clearly recognizable (navy D-4-U with the "
        "gold 4 and the IMMIGRATION wordmark), placed on a little hand-drawn sign or banner "
        "in a corner — integrated into the art, not pasted. "
        if logo_bytes else ""
    )
    logo_text_clause = (
        "Include the D4U company logo (the letters D and U in dark navy blue with a golden "
        "number 4 between them, and the word IMMIGRATION below) drawn by hand as a doodle in "
        "the SAME colored-marker style, on a little hand-drawn sign or banner in a corner. "
        if logo_bytes else ""
    )

    story_clause = (
        f"Illustrate their American dream as a lively story collage of small doodle scenes: {prompt}. "
        "Connect the little scenes with simple sketched arrows, add small icons, stars, "
        "hearts, the chosen city's famous landmarks drawn as doodles, and the US flag. "
    )
    style_tail = (
        f"Add a few short hand-written-style labels in {labels_lang}. {name_clause}{personality_clause}"
        f'Hand-letter a small ribbon/banner with the exact phrase spelled correctly: "{banner_phrase}". '
        f"{logo_clause}"
        "Vibrant marker colors, flat 2D hand-drawn illustration, optimistic and playful, "
        "white background, absolutely no photorealism."
    )

    if photo_bytes:
        protagonist_clause = (
            "Use the FIRST provided image (a real person) as reference to draw a friendly cartoon "
            "CARICATURE of them as the smiling protagonist — keep their hairstyle, hair color, "
            "skin tone and general features recognizable, but illustrated as a cute, tidy "
            "hand-drawn character (not photorealistic). "
            "ONLY the protagonist is drawn as a character with a face. Do NOT draw any other "
            "people or faces — represent family, home and loved ones symbolically instead "
            "(a little house, hearts, a family icon), never as drawn faces. "
        )
        logo_ref_clause = (
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
            f"{protagonist_clause}{story_clause}{style_tail.replace(logo_clause, logo_ref_clause)}"
        )
    else:
        no_face_clause = (
            "Do NOT draw any human faces, people, bodies or caricatures anywhere in the mural — "
            "illustrate the journey purely with symbolic doodles (icons, landmarks, arrows, stars, "
            "hearts, houses, flags, career symbols). "
        )
        full_prompt = (
            "Create a colorful hand-drawn 'Draw My Life' style mural in a TALL VERTICAL 9:16 "
            "portrait composition: a cheerful doodle collage as if sketched with colored markers "
            "on a clean white background, filling the whole vertical frame. "
            f"{no_face_clause}{story_clause}"
            f"Add a few short hand-written-style labels in {labels_lang}. {name_clause}{personality_clause}"
            f'Hand-letter a small ribbon/banner with the exact phrase spelled correctly: "{banner_phrase}". '
            f"{logo_text_clause}"
            "Vibrant marker colors, flat 2D hand-drawn illustration, optimistic and playful, "
            "white background, absolutely no photorealism."
        )

    def make_image_input():
        # 1ª imagem = rosto (caricatura); 2ª = logo D4U (redesenhado no estilo).
        # Recria a cada tentativa pois o stream é consumido.
        if not photo_bytes:
            if logo_bytes:
                logo = io.BytesIO(logo_bytes)
                logo.name = "d4u-logo.png"
                return logo
            return None
        person = io.BytesIO(photo_bytes)
        person.name = "face.png"
        if logo_bytes:
            logo = io.BytesIO(logo_bytes)
            logo.name = "d4u-logo.png"
            return [person, logo]
        return person

    # gpt-image-2 já processa a entrada em alta fidelidade (não aceita input_fidelity);
    # modelos gpt-image-1.x aceitam o parâmetro. Com foto tentamos EDITAR; sem foto, generate.
    q = IMAGE_QUALITY
    if chosen_model.startswith("gpt-image-2"):
        param_variants = [{"quality": q}, {}]
    else:
        param_variants = [{"input_fidelity": "high", "quality": q}, {"quality": q}, {}]

    # 9:16 vertical (a opção retrato nativa do gpt-image é 1024x1536).
    IMG_SIZE = "1024x1536"

    response = None
    if photo_bytes:
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
        if photo_bytes:
            print("[generate-image] usando fallback generate (com foto)")
        else:
            print("[generate-image] gerando mural sem foto")
        edit_input = make_image_input()
        if edit_input and not photo_bytes:
            for extra in param_variants:
                try:
                    response = client.images.edit(
                        model=chosen_model,
                        image=edit_input,
                        prompt=full_prompt,
                        size=IMG_SIZE,
                        **extra,
                    )
                    break
                except Exception as e:
                    print(f"[generate-image] edit logo falhou com {list(extra)}: {e}")
        if response is None:
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


def _job_has_art(job: Optional[dict]) -> bool:
    """True se o job já tem arte persistida — nunca regenerar nesses casos."""
    if not job:
        return False
    if job.get("art_file_id"):
        return True
    art_url = (job.get("art_url") or "").strip()
    if art_url.startswith("/static/results/"):
        name = art_url.rsplit("/", 1)[-1]
        if name and (RESULTS_DIR / name).exists():
            return True
    return False


def _resolve_art_params(job: dict, token: str) -> tuple[str, str, str, str, str]:
    """Monta prompt e metadados para geração (job + lead legado)."""
    prompt = (job.get("prompt_imagem") or "").strip()
    nome = job.get("nome", "")
    cidade = job.get("cidade", "")
    nascimento = job.get("nascimento", "")
    idioma = job.get("idioma", "pt")

    if not prompt or not cidade or not nascimento:
        lead = get_lead_by_token(token)
        if lead:
            nome = nome or lead.get("nome", "")
            cidade = cidade or lead.get("cidade", "")
            nascimento = nascimento or lead.get("nascimento", "")
            idioma = idioma or lead.get("idioma", "pt")
            if not prompt:
                sonho = (lead.get("sonho") or "").strip()
                prompt = f"Dream life in {cidade}: {sonho}" if cidade else sonho

    if not prompt:
        prompt = f"Dream life in {cidade}" if cidade else "American dream journey"

    return prompt, nome, cidade, nascimento, idioma


def _needs_art_without_photo(job: dict) -> bool:
    """Cadastro sem foto (ou legado) que ainda não tem arte no GridFS."""
    if _job_has_art(job):
        return False
    if job.get("has_photo") is True:
        return False
    if job.get("status") == "failed":
        return False
    if job.get("has_photo") is False:
        return True
    # Legado: sem foto marcava status "done" sem arte.
    return job.get("status") == "done" and not job.get("art_file_id")


def _generation_is_stale(job: dict) -> bool:
    """Job preso em processing/generating sem arte há tempo demais."""
    if not job or job.get("status") not in ("processing", "generating"):
        return False
    started = job.get("generation_started_at")
    if isinstance(started, datetime):
        return datetime.now() - started > STALE_GENERATION
    return True


def _try_claim_art_generation(token: str) -> bool:
    """Reserva a geração para um único worker (evita chamadas duplicadas à OpenAI)."""
    job = job_get(token)
    if not job or _job_has_art(job):
        return False
    if job.get("status") == "generating" and not _generation_is_stale(job):
        return False
    if job.get("status") == "processing":
        started = job.get("generation_started_at")
        if isinstance(started, datetime) and datetime.now() - started <= STALE_GENERATION:
            return False

    now = datetime.now()
    if MONGO_ENABLED:
        try:
            db, _ = get_mongo()
            result = db.art_jobs.update_one(
                {
                    "_id": token,
                    "$or": [
                        {"art_file_id": {"$exists": False}},
                        {"art_file_id": None},
                        {"art_file_id": ""},
                    ],
                },
                {"$set": {"status": "generating", "generation_started_at": now}},
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[art-job] claim falhou: {e}")
            return False
    job = JOBS.get(token)
    if not job or _job_has_art(job):
        return False
    if job.get("status") == "generating" and not _generation_is_stale(job):
        return False
    job["status"] = "generating"
    job["generation_started_at"] = now
    return True


def _spawn_art_job(token: str, photo_bytes: Optional[bytes], prompt: str,
                   nome: str, cidade: str, nascimento: str, idioma: str = "pt") -> None:
    """Thread dedicada — BackgroundTasks do FastAPI pode morrer em tarefas longas."""
    threading.Thread(
        target=_art_job,
        args=(token, photo_bytes, prompt, nome, cidade, nascimento, idioma),
        daemon=True,
        name=f"art-{token[:8]}",
    ).start()


def _enqueue_art_generation(token: str, photo_bytes: Optional[bytes], prompt: str,
                            nome: str, cidade: str, nascimento: str,
                            idioma: str = "pt") -> None:
    if _job_has_art(job_get(token)):
        return
    if not _try_claim_art_generation(token):
        return
    print(f"[art-job] enfileirando geração para {token[:8]}… (foto={bool(photo_bytes)})")
    _spawn_art_job(token, photo_bytes, prompt, nome, cidade, nascimento, idioma)


def _discard_generated_file(filename: str) -> None:
    try:
        (RESULTS_DIR / filename).unlink()
    except Exception:
        pass


def _save_art_to_job(token: str, filename: str) -> None:
    """Persiste a arte gerada e atualiza o job — só se ainda não existir arte."""
    job = job_get(token)
    if _job_has_art(job):
        print(f"[art-job] arte já existia para {token[:8]}…, descartando nova geração")
        _discard_generated_file(filename)
        return

    local_path = RESULTS_DIR / filename
    art_url = f"/api/art-image?token={token}"

    if MONGO_ENABLED:
        try:
            db, fs = get_mongo()
            with open(local_path, "rb") as f:
                file_id = fs.put(f.read(), filename=filename, contentType="image/png", token=token)
            result = db.art_jobs.update_one(
                {
                    "_id": token,
                    "$or": [
                        {"art_file_id": {"$exists": False}},
                        {"art_file_id": None},
                        {"art_file_id": ""},
                    ],
                },
                {"$set": {"status": "done", "art_file_id": str(file_id), "art_url": art_url}},
            )
            if result.modified_count == 0:
                print(f"[art-job] outra requisição salvou antes — descartando duplicata")
                try:
                    fs.delete(file_id)
                except Exception:
                    pass
                _discard_generated_file(filename)
                return
            try:
                local_path.unlink()
            except Exception:
                pass
            return
        except Exception as e:
            print(f"[art-job] gridfs falhou, mantendo local: {e}")

    if _job_has_art(job_get(token)):
        _discard_generated_file(filename)
        return
    job_update(token, {"status": "done", "art_url": f"/static/results/{filename}"})


def _art_job(token: str, photo_bytes: Optional[bytes], prompt: str,
             nome: str, cidade: str, nascimento: str, idioma: str = "pt") -> None:
    """Roda em thread: gera a arte, guarda no GridFS (se Mongo) e atualiza o job."""
    job = job_get(token)
    if _job_has_art(job):
        print(f"[art-job] arte já existe para {token[:8]}…, geração ignorada")
        return
    try:
        print(f"[art-job] OpenAI iniciada para {token[:8]}…")
        filename = run_art_generation(photo_bytes, prompt, nome, cidade, nascimento, idioma)
        print(f"[art-job] OpenAI concluída para {token[:8]}… → {filename}")
        _save_art_to_job(token, filename)
    except Exception as e:
        print(f"[art-job] falha ao gerar arte ({token[:8]}…): {e}")
        job = job_get(token)
        if not _job_has_art(job):
            job_update(token, {"status": "failed"})


def _maybe_start_art_generation(token: str, job: dict) -> None:
    """Dispara geração em thread quando a arte ainda não existe (sem foto)."""
    if _job_has_art(job):
        return
    if not _needs_art_without_photo(job):
        return
    prompt, nome, cidade, nascimento, idioma = _resolve_art_params(job, token)
    _enqueue_art_generation(token, None, prompt, nome, cidade, nascimento, idioma)


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
    validate_lead_data(data)

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
    prompt_img = result.get("prompt_imagem") or \
        f"Dream life in {data.get('cidade', '')}: {data.get('sonho', '')}"
    job_create(token, {
        "nome": result.get("nome", ""),
        "elegivel": result.get("elegivel", None),
        "mensagem": result.get("mensagem_sonho", ""),
        "idioma": normalize_idioma(data),
        "cidade": data.get("cidade", ""),
        "nascimento": data.get("nascimento", ""),
        "prompt_imagem": prompt_img,
        "has_photo": bool(photo_bytes),
        "status": "processing",
        "art_url": f"/api/art-image?token={token}",
    })
    save_lead({**data, "token": token}, result)
    background_tasks.add_task(hubspot_upsert, data, token)

    # Geração da arte em thread dedicada (não trava a resposta).
    _enqueue_art_generation(
        token, photo_bytes, prompt_img,
        data.get("nome", ""), data.get("cidade", ""), data.get("nascimento", ""),
        normalize_idioma(data),
    )

    return JSONResponse({"token": token})


def _wants_html_page(request: Request) -> bool:
    """True quando o cliente é um navegador (não <img src=…> nem fetch de imagem)."""
    accept = (request.headers.get("accept") or "").lower()
    if not accept:
        return False
    first = accept.split(",")[0].strip()
    if first.startswith("image/"):
        return False
    return "text/html" in accept


def _arte_page_url(token: str) -> str:
    return f"/arte?token={token}"


def _serve_art_response(job: dict) -> Response:
    """Devolve a arte já existente (GridFS ou arquivo local). Nunca gera aqui."""
    if job.get("art_file_id"):
        try:
            from bson import ObjectId
            _, fs = get_mongo()
            data = fs.get(ObjectId(job["art_file_id"])).read()
            return Response(
                content=data,
                media_type="image/png",
                headers={"Content-Disposition": 'inline; filename="minha-arte-d4u.png"'},
            )
        except Exception as e:
            print(f"[art-image] erro ao ler GridFS: {e}")
            raise HTTPException(404, "Arte não encontrada.")

    art_url = (job.get("art_url") or "").strip()
    if art_url.startswith("/static/results/"):
        path = RESULTS_DIR / art_url.rsplit("/", 1)[-1]
        if path.is_file():
            return Response(
                content=path.read_bytes(),
                media_type="image/png",
                headers={"Content-Disposition": 'inline; filename="minha-arte-d4u.png"'},
            )

    raise HTTPException(404, "Arte não encontrada.")


@app.get("/api/art-status")
async def art_status(token: str, background_tasks: BackgroundTasks):
    token = validate_token(token)
    job = job_get(token)
    if not job:
        raise HTTPException(404, "Link inválido ou expirado.")

    _maybe_start_art_generation(token, job)
    job = job_get(token) or job

    status = job.get("status", "")
    art_url = job.get("art_url") or f"/api/art-image?token={token}"
    if _job_has_art(job):
        status = "done"
    elif status != "failed":
        status = "processing"

    # Devolve só o necessário — nunca e-mail/telefone.
    payload = {
        "nome": job.get("nome", ""),
        "elegivel": job.get("elegivel"),
        "mensagem": job.get("mensagem", ""),
        "status": status,
        "art_url": None if status == "failed" and not _job_has_art(job) else art_url,
        "page_url": _arte_page_url(token),
    }
    if job.get("idioma"):
        payload["idioma"] = job["idioma"]
    return JSONResponse(payload)


@app.get("/api/art-image")
async def art_image(token: str, request: Request, background_tasks: BackgroundTasks):
    """Serve a arte existente. Só gera se ainda não houver nenhuma (sem foto)."""
    token = validate_token(token)
    if not MONGO_ENABLED:
        raise HTTPException(404, "Indisponível.")
    job = job_get(token)
    if not job:
        raise HTTPException(404, "Arte não encontrada.")

    if _job_has_art(job):
        return _serve_art_response(job)

    # Link aberto no navegador → mesma tela pós-cadastro com mosaic e infos do cliente.
    if _wants_html_page(request):
        _maybe_start_art_generation(token, job)
        return RedirectResponse(url=_arte_page_url(token), status_code=302)

    if job.get("has_photo") is False and job.get("status") in ("processing", "generating"):
        raise HTTPException(
            503,
            "Arte em geração. Tente novamente em instantes.",
            headers={"Retry-After": "8"},
        )
    if not _needs_art_without_photo(job):
        raise HTTPException(404, "Arte não encontrada.")
    _maybe_start_art_generation(token, job)
    raise HTTPException(
        503,
        "Arte em geração. Tente novamente em instantes.",
        headers={"Retry-After": "8"},
    )


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
        if row.get("consentimento_lgpd") is True:
            row["consentimento_lgpd"] = "Sim"
        elif row.get("consentimento_lgpd") is False:
            row["consentimento_lgpd"] = "Não"
        writer.writerow({col: csv_safe(row.get(col, "")) for col in CSV_COLUMNS})
    return buf.getvalue()


@app.get("/api/admin/status")
async def admin_status():
    """Indica se o painel está configurado (sem expor a senha)."""
    return JSONResponse({"configured": bool(ADMIN_PASSWORD)})


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
