/** Traduções PT/EN — UI do questionário VisaDream. */
window.VisaDreamI18n = (function () {
  const STORAGE_KEY = 'visadream_lang';
  let lang = localStorage.getItem(STORAGE_KEY) || 'pt';
  if (lang !== 'en') lang = 'pt';

  const STRINGS = {
    'page.title': { pt: 'VisaDream — Descubra seu caminho para os EUA', en: 'VisaDream — Discover your path to the USA' },
    'conn.online': { pt: 'Online', en: 'Online' },
    'conn.offline': { pt: 'Offline', en: 'Offline' },
    'conn.syncing': { pt: 'Sincronizando…', en: 'Syncing…' },
    'step.label': { pt: 'Passo {n} de 4', en: 'Step {n} of 4' },
    'step1.title': { pt: 'Você quer...', en: 'You want to...' },
    'step1.sub': { pt: 'Escolha seu principal objetivo nos EUA.', en: 'Choose your main goal in the USA.' },
    'step2.title.default': { pt: 'Detalhes', en: 'Details' },
    'step2.sub.default': { pt: 'Toque nas opções que combinam com você.', en: 'Tap the options that fit you.' },
    'step3.title': { pt: 'Seu sonho americano 🌟', en: 'Your American dream 🌟' },
    'step3.sub': { pt: 'Vamos criar uma arte personalizada do seu sonho.', en: "We'll create personalized art of your dream." },
    'step4.title': { pt: 'Quase lá! 🎁', en: 'Almost there! 🎁' },
    'step4.sub': { pt: 'Preencha seus dados para receber sua análise de visto e sua arte personalizada.', en: 'Fill in your details to receive your visa analysis and personalized art.' },
    'step4.firstName': { pt: 'Nome', en: 'First name' },
    'step4.lastName': { pt: 'Sobrenome', en: 'Last name' },
    'step4.email': { pt: 'E-mail', en: 'Email' },
    'step4.whatsapp': { pt: 'WhatsApp / telefone', en: 'WhatsApp / phone' },
    'step4.birthDate': { pt: 'Data de nascimento', en: 'Date of birth' },
    'step4.birthCountry': { pt: 'País de nascimento', en: 'Country of birth' },
    'step4.consent': { pt: 'Li e aceito a <a href="https://d4uimmigration.com/politica-de-privacidade" target="_blank" rel="noopener" class="underline" style="color:var(--gold)">política de privacidade</a> e autorizo o uso dos meus dados para contato sobre imigração. <span style="color:var(--gold)">*</span>', en: 'I have read and accept the <a href="https://d4uimmigration.com/politica-de-privacidade" target="_blank" rel="noopener" class="underline" style="color:var(--gold)">privacy policy</a> and authorize the use of my data for immigration contact. <span style="color:var(--gold)">*</span>' },
    'ph.firstName': { pt: 'Seu nome', en: 'Your first name' },
    'ph.lastName': { pt: 'Seu sobrenome', en: 'Your last name' },
    'ph.email': { pt: 'voce@email.com', en: 'you@email.com' },
    'btn.back': { pt: '← Voltar', en: '← Back' },
    'btn.continue': { pt: 'Continuar →', en: 'Continue →' },
    'btn.submit': { pt: 'Receber minha análise →', en: 'Get my analysis →' },
    'loading.title': { pt: 'Analisando seu perfil...', en: 'Analyzing your profile...' },
    'loading.msg': { pt: 'Consultando especialistas em imigração via IA...', en: 'Consulting immigration specialists via AI...' },
    'loading.s1': { pt: 'Analisando elegibilidade para vistos...', en: 'Analyzing visa eligibility...' },
    'loading.s2': { pt: 'Calculando probabilidade de aprovação...', en: 'Calculating approval probability...' },
    'loading.s3': { pt: 'Criando sua arte personalizada...', en: 'Creating your personalized art...' },
    'offline.badge': { pt: 'Salvo neste dispositivo', en: 'Saved on this device' },
    'offline.title': { pt: 'Recebemos seus dados!', en: 'We received your data!' },
    'offline.msg': { pt: 'A internet está instável ou indisponível. Seu cadastro foi guardado com segurança neste aparelho e será enviado automaticamente assim que a conexão voltar.', en: 'The internet is unstable or unavailable. Your registration was saved securely on this device and will be sent automatically when the connection returns.' },
    'offline.sync': { pt: 'Tentar enviar agora', en: 'Try sending now' },
    'offline.new': { pt: 'Novo cadastro', en: 'New registration' },
    'offline.banner.sync': { pt: 'Sincronizar', en: 'Sync' },
    'offline.banner.wait': { pt: 'Aguardando internet para sincronizar.', en: 'Waiting for internet to sync.' },
    'offline.banner.pending': { pt: 'Cadastros pendentes', en: 'Pending registrations' },
    'offline.banner.one': { pt: '1 cadastro pendente', en: '1 pending registration' },
    'offline.banner.many': { pt: '{n} cadastros pendentes', en: '{n} pending registrations' },
    'offline.banner.syncOnline': { pt: 'Toque em Sincronizar ou aguarde o envio automático.', en: 'Tap Sync or wait for automatic upload.' },
    'offline.banner.noNet': { pt: 'Sem internet — os dados estão salvos neste aparelho.', en: 'No internet — data is saved on this device.' },
    'photo.label': { pt: 'Sua foto (opcional) 📸', en: 'Your photo (optional) 📸' },
    'photo.upload': { pt: '📷 Enviar minha foto', en: '📷 Upload my photo' },
    'photo.hint': { pt: '✨ Seu brinde fica muito mais legal com a sua foto!', en: '✨ Your gift looks much better with your photo!' },
    'photo.camera': { pt: 'No celular você pode tirar na hora pela câmera.', en: 'On mobile you can take a photo with your camera.' },
    'photo.change': { pt: 'Trocar foto', en: 'Change photo' },
    'dream.city': { pt: 'Em qual cidade você sonha em viver?', en: 'Which US city do you dream of living in?' },
    'dream.what': { pt: 'Qual é o seu sonho? Toque numa ideia:', en: 'What is your dream? Tap an idea:' },
    'dream.otherCity': { pt: 'Qual cidade você sonha em conhecer?', en: 'Which city do you dream of visiting?' },
    'dream.otherDream': { pt: 'Conte seu sonho com suas palavras', en: 'Tell us your dream in your words' },
    'dream.other': { pt: '✨ Outro', en: '✨ Other' },
    'err.selectGoal': { pt: 'Escolha um objetivo para continuar.', en: 'Choose a goal to continue.' },
    'err.fillFields': { pt: 'Responda todas as perguntas desta etapa.', en: 'Answer all questions in this step.' },
    'err.areaOther': { pt: 'Conte sua área em "Outro".', en: 'Tell us your field under "Other".' },
    'err.formacaoOther': { pt: 'Conte sua formação em "Outro".', en: 'Tell us your education under "Other".' },
    'err.companyCountry': { pt: 'Selecione o país da empresa.', en: 'Select the country of the company.' },
    'err.cityPick': { pt: 'Escolha a cidade dos seus sonhos.', en: 'Choose your dream city.' },
    'err.cityOther': { pt: 'Informe a cidade em "Outro".', en: 'Enter the city under "Other".' },
    'err.dreamOther': { pt: 'Conte seu sonho em "Outro".', en: 'Tell us your dream under "Other".' },
    'err.dreamPick': { pt: 'Escolha ou escreva seu sonho.', en: 'Choose or write your dream.' },
    'err.firstName': { pt: 'Por favor, informe seu nome.', en: 'Please enter your first name.' },
    'err.lastName': { pt: 'Por favor, informe seu sobrenome.', en: 'Please enter your last name.' },
    'err.email': { pt: 'Informe um e-mail válido.', en: 'Enter a valid email.' },
    'err.phone': { pt: 'Informe um telefone válido com DDD/código do país.', en: 'Enter a valid phone with area/country code.' },
    'err.birthDate': { pt: 'Informe sua data de nascimento.', en: 'Enter your date of birth.' },
    'err.birthCountry': { pt: 'Selecione seu país de nascimento.', en: 'Select your country of birth.' },
    'err.consent': { pt: 'É necessário aceitar a política de privacidade.', en: 'You must accept the privacy policy.' },
    'err.captcha': { pt: 'Confirme que você não é um robô.', en: 'Please confirm you are not a robot.' },
    'err.generic': { pt: 'Ocorreu um erro: {msg}', en: 'An error occurred: {msg}' },
    'err.retry': { pt: 'tente novamente', en: 'try again' },
    'alert.noConn': { pt: 'Ainda sem conexão com o servidor. Os dados continuam salvos neste aparelho.', en: 'Still no connection to the server. Data remains saved on this device.' },
    'alert.captchaSync': { pt: 'Confirme o captcha de segurança no formulário e toque em Sincronizar novamente.', en: 'Complete the security captcha on the form and tap Sync again.' },
  };

  const BRANCH_COPY = {
    viajar: { pt: { titulo: 'Sua viagem', sub: 'Conte um pouco sobre o que você planeja.' }, en: { titulo: 'Your trip', sub: 'Tell us a bit about what you are planning.' } },
    morar_trabalhar: { pt: { titulo: 'Morar e trabalhar', sub: 'Formação e vínculos definem o melhor caminho pra você.' }, en: { titulo: 'Live and work', sub: 'Education and ties define the best path for you.' } },
    empreender: { pt: { titulo: 'Seu negócio', sub: 'Vamos entender o porte e o estágio do seu empreendimento.' }, en: { titulo: 'Your business', sub: "Let's understand the size and stage of your venture." } },
    investir: { pt: { titulo: 'Seu investimento', sub: 'O valor e o tipo definem o visto ideal.' }, en: { titulo: 'Your investment', sub: 'Amount and type define the ideal visa.' } },
  };

  const INTEREST_CARDS = {
    viajar: { pt: { title: 'Viajar', sub: 'Turismo, negócios ou visita aos Estados Unidos' }, en: { title: 'Travel', sub: 'Tourism, business or visiting the United States' } },
    morar_trabalhar: { pt: { title: 'Morar / Trabalhar', sub: 'Viver e trabalhar legalmente nos EUA' }, en: { title: 'Live / Work', sub: 'Live and work legally in the USA' } },
    empreender: { pt: { title: 'Empreender', sub: 'Abrir uma empresa ou expandir seu negócio para os EUA' }, en: { title: 'Entrepreneurship', sub: 'Start a company or expand your business to the USA' } },
    investir: { pt: { title: 'Investir', sub: 'Aplicar capital e ter renda em dólar' }, en: { title: 'Invest', sub: 'Deploy capital and earn in US dollars' } },
  };

  const LABELS = {
    motivo_viagem: { pt: 'Motivo da viagem', en: 'Trip purpose' },
    duracao_viagem: { pt: 'Duração pretendida', en: 'Intended duration' },
    historico_visto: { pt: 'Já teve visto americano?', en: 'Have you had a US visa before?' },
    area: { pt: 'Área de atuação', en: 'Field of work' },
    formacao: { pt: 'Nível de formação', en: 'Education level' },
    experiencia: { pt: 'Anos de experiência na área', en: 'Years of experience' },
    familia: { pt: 'Tem familiar próximo cidadão ou residente nos EUA?', en: 'Do you have close family who are US citizens or residents?' },
    investimento: { pt: 'Capacidade de investimento', en: 'Investment capacity' },
    tipo_investimento: { pt: 'Onde pretende investir?', en: 'Where do you plan to invest?' },
    negocio_tipo: { pt: 'Que tipo de negócio você quer tocar nos EUA?', en: 'What type of business do you want to run in the USA?' },
    capital: { pt: 'Capital disponível para começar', en: 'Available capital to start' },
    ja_empresa: { pt: 'Você já tem empresa hoje?', en: 'Do you already have a company?' },
    ja_empresa_pais: { pt: 'Em qual país está a empresa?', en: 'In which country is the company?' },
  };

  const OPTION_LABELS = {
    'Turismo': { pt: '🏖️ Turismo', en: '🏖️ Tourism' },
    'Negócios': { pt: '💼 Negócios', en: '💼 Business' },
    'Visitar família': { pt: '👨‍👩‍👧 Família', en: '👨‍👩‍👧 Family visit' },
    'Evento / Conferência': { pt: '🎤 Evento', en: '🎤 Event / Conference' },
    'Até 90 dias': { pt: 'Até 90 dias', en: 'Up to 90 days' },
    '3 a 6 meses': { pt: '3 a 6 meses', en: '3 to 6 months' },
    'Mais de 6 meses': { pt: 'Mais de 6 meses', en: 'More than 6 months' },
    'Sim, válido ou recente': { pt: '✅ Sim, válido ou recente', en: '✅ Yes, valid or recent' },
    'Sim, mas expirado': { pt: '📅 Sim, mas expirado', en: '📅 Yes, but expired' },
    'Nunca tive': { pt: '🆕 Nunca tive', en: '🆕 Never had one' },
    'Já foi negado': { pt: '⚠️ Já foi negado', en: '⚠️ Was denied before' },
    'Tecnologia': { pt: '💻 Tecnologia', en: '💻 Technology' },
    'Saúde': { pt: '🩺 Saúde', en: '🩺 Healthcare' },
    'Finanças': { pt: '📊 Finanças', en: '📊 Finance' },
    'Engenharia': { pt: '🏗️ Engenharia', en: '🏗️ Engineering' },
    'Educação': { pt: '🎓 Educação', en: '🎓 Education' },
    'Outro': { pt: '✨ Outro', en: '✨ Other' },
    'Ensino Médio': { pt: 'Ensino Médio', en: 'High school' },
    'Graduação': { pt: 'Graduação', en: "Bachelor's degree" },
    'Pós / MBA': { pt: 'Pós / MBA', en: 'Graduate / MBA' },
    'Mestrado ou Doutorado': { pt: 'Mestrado / PhD', en: "Master's / PhD" },
    'Menos de 2 anos': { pt: 'Menos de 2 anos', en: 'Less than 2 years' },
    '2 a 5 anos': { pt: '2 a 5 anos', en: '2 to 5 years' },
    '5 a 10 anos': { pt: '5 a 10 anos', en: '5 to 10 years' },
    'Mais de 10 anos': { pt: 'Mais de 10 anos', en: 'More than 10 years' },
    'Não tenho familiares nos EUA': { pt: '🚫 Não tenho', en: '🚫 I do not' },
    'Sim, familiar próximo cidadão/residente': { pt: '👨‍👩‍👧 Sim, familiar próximo', en: '👨‍👩‍👧 Yes, close relative' },
    'Sim, cônjuge americano(a) ou residente': { pt: '💍 Sim, cônjuge americano(a)', en: '💍 Yes, American spouse' },
    'Menos de $50k': { pt: '💰 Menos de $50k', en: '💰 Under $50k' },
    '$50k a $200k': { pt: '💰💰 $50k–$200k', en: '💰💰 $50k–$200k' },
    '$200k a $800k': { pt: '💰💰💰 $200k–$800k', en: '💰💰💰 $200k–$800k' },
    'Acima de $800k': { pt: '🏆 Acima de $800k', en: '🏆 Over $800k' },
    'Imóveis': { pt: '🏠 Imóveis', en: '🏠 Real estate' },
    'Negócio próprio': { pt: '🏪 Negócio', en: '🏪 Own business' },
    'Fundos / Ações': { pt: '📈 Fundos', en: '📈 Funds / Stocks' },
    'Ainda decidindo': { pt: '🤔 Decidindo', en: '🤔 Still deciding' },
    'Tecnologia / Startup': { pt: '💻 Tecnologia', en: '💻 Technology' },
    'Comércio / Varejo': { pt: '🛍️ Comércio', en: '🛍️ Retail' },
    'Serviços': { pt: '🛠️ Serviços', en: '🛠️ Services' },
    'Restaurante / Food': { pt: '🍔 Food', en: '🍔 Food' },
    'Franquia': { pt: '🏬 Franquia', en: '🏬 Franchise' },
    'Sim': { pt: 'Sim', en: 'Yes' },
    'Não, vou começar do zero': { pt: 'Não, do zero', en: 'No, from scratch' },
    'New York': { pt: '🗽 New York', en: '🗽 New York' },
    'Miami': { pt: '🌴 Miami', en: '🌴 Miami' },
    'Los Angeles': { pt: '🎬 L.A.', en: '🎬 L.A.' },
    'San Francisco': { pt: '🌉 San Francisco', en: '🌉 San Francisco' },
    'Chicago': { pt: '🏙️ Chicago', en: '🏙️ Chicago' },
    'Orlando': { pt: '🎢 Orlando', en: '🎢 Orlando' },
  };

  const DREAM_SUGGESTIONS = {
    viajar: {
      pt: ['Conhecer os principais pontos turísticos dos EUA', 'Fazer uma viagem inesquecível com a família', 'Participar de um evento ou conferência', 'Explorar novas culturas e lugares'],
      en: ['Visit the main tourist spots in the USA', 'Take an unforgettable trip with my family', 'Attend an event or conference', 'Explore new cultures and places'],
    },
    morar_trabalhar: {
      pt: ['Construir uma carreira sólida e viver bem nos EUA', 'Dar mais oportunidades e qualidade de vida pra minha família', 'Realizar o sonho de morar legalmente nos Estados Unidos', 'Ter um novo recomeço numa cidade que eu amo'],
      en: ['Build a solid career and live well in the USA', 'Give my family more opportunities and quality of life', 'Fulfill my dream of living legally in the United States', 'Start fresh in a city I love'],
    },
    investir: {
      pt: ['Fazer meu patrimônio render em dólar com segurança', 'Comprar imóveis e construir renda passiva nos EUA', 'Diversificar meus investimentos fora do Brasil', 'Conquistar o green card através de investimento'],
      en: ['Grow my wealth safely in US dollars', 'Buy property and build passive income in the USA', 'Diversify my investments outside Brazil', 'Earn a green card through investment'],
    },
    empreender: {
      pt: ['Abrir minha startup e escalar pro mundo todo', 'Expandir meu negócio do Brasil para os EUA', 'Construir um negócio do zero com liberdade total', 'Criar um produto que impacte milhões de pessoas'],
      en: ['Launch my startup and scale worldwide', 'Expand my business from Brazil to the USA', 'Build a business from scratch with total freedom', 'Create a product that impacts millions of people'],
    },
  };

  const OUTRO_PLACEHOLDERS = {
    area: { pt: 'Qual é a sua área de atuação?', en: 'What is your field of work?' },
    formacao: { pt: 'Qual é o seu nível de ensino?', en: 'What is your education level?' },
    cidade: { pt: 'Qual cidade você sonha em conhecer?', en: 'Which city do you dream of visiting?' },
    sonho: { pt: 'Conte seu sonho com suas palavras', en: 'Tell us your dream in your words' },
  };

  function t(key, vars) {
    const item = STRINGS[key];
    let text = item ? (item[lang] || item.pt) : key;
    if (vars) {
      Object.keys(vars).forEach(k => { text = text.replace(`{${k}}`, vars[k]); });
    }
    return text;
  }

  function getLang() { return lang; }

  function setLang(next) {
    lang = next === 'en' ? 'en' : 'pt';
    localStorage.setItem(STORAGE_KEY, lang);
    document.documentElement.lang = lang === 'en' ? 'en' : 'pt-BR';
    document.title = t('page.title');
    applyLanguage();
    if (typeof window.onLanguageChange === 'function') window.onLanguageChange(lang);
  }

  function applyLanguage() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const html = el.getAttribute('data-i18n-html') === '1';
      const val = t(key);
      if (html) el.innerHTML = val;
      else el.textContent = val;
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });

    document.querySelectorAll('[data-i18n-step]').forEach(el => {
      el.textContent = t('step.label', { n: el.getAttribute('data-i18n-step') });
    });

    Object.keys(LABELS).forEach(group => {
      document.querySelectorAll(`label[data-label="${group}"]`).forEach(el => {
        const star = el.querySelector('[data-req]') ? ' <span style="color:var(--gold)">*</span>' : '';
        el.innerHTML = (LABELS[group][lang] || LABELS[group].pt) + star;
      });
    });
    const companyCountryLabel = document.querySelector('label[data-i18n="ja_empresa_pais"]');
    if (companyCountryLabel) companyCountryLabel.textContent = t('ja_empresa_pais');

    document.querySelectorAll('.option-btn[data-value]').forEach(btn => {
      const lbl = OPTION_LABELS[btn.dataset.value];
      if (lbl) btn.textContent = lbl[lang] || lbl.pt;
    });

    document.querySelectorAll('.interest-card[data-interesse]').forEach(card => {
      const data = INTEREST_CARDS[card.dataset.interesse];
      if (!data) return;
      const copy = data[lang] || data.pt;
      const titleEl = card.querySelector('[data-i18n-interest-title]');
      const subEl = card.querySelector('[data-i18n-interest-sub]');
      if (titleEl) titleEl.textContent = copy.title;
      if (subEl) subEl.textContent = copy.sub;
    });

    Object.keys(OUTRO_PLACEHOLDERS).forEach(group => {
      const inp = document.getElementById(group + '-outro');
      if (inp) inp.placeholder = OUTRO_PLACEHOLDERS[group][lang] || OUTRO_PLACEHOLDERS[group].pt;
    });

    document.querySelectorAll('#lang-pt, #lang-en').forEach(btn => {
      btn.classList.toggle('active', btn.id === (lang === 'en' ? 'lang-en' : 'lang-pt'));
    });

    if (window.VisaDreamPhone) {
      VisaDreamPhone.populatePhoneSelect(document.getElementById('f-phone-country'), lang);
      VisaDreamPhone.populateBirthSelect(document.getElementById('f-pais-nascimento'), lang);
      VisaDreamPhone.populateBirthSelect(document.getElementById('ja_empresa-pais'), lang);
    }
  }

  function branchCopy(interesse) {
    const b = BRANCH_COPY[interesse];
    return b ? (b[lang] || b.pt) : { titulo: t('step2.title.default'), sub: t('step2.sub.default') };
  }

  function dreamSuggestions(interesse) {
    const d = DREAM_SUGGESTIONS[interesse] || DREAM_SUGGESTIONS.morar_trabalhar;
    return d[lang] || d.pt;
  }

  const ARTE_STRINGS = {
    'arte.page.title': { pt: 'Sua arte — VisaDream · D4U', en: 'Your art — VisaDream · D4U' },
    'arte.loading': { pt: 'Carregando…', en: 'Loading…' },
    'arte.error.title': { pt: 'Link inválido ou expirado', en: 'Invalid or expired link' },
    'arte.error.sub': { pt: 'Refaça o questionário para gerar um novo acesso.', en: 'Complete the questionnaire again to get a new access link.' },
    'arte.error.back': { pt: 'Voltar ao início', en: 'Back to start' },
    'arte.result.badge': { pt: 'Seu resultado', en: 'Your result' },
    'arte.title.eligible': { pt: '{nome}, você tem perfil! 🎉', en: '{nome}, you have a strong profile! 🎉' },
    'arte.title.received': { pt: '{nome}, recebemos seus dados! 🙌', en: '{nome}, we received your details! 🙌' },
    'arte.msg.eligibleDefault': { pt: 'Você tem perfil para realizar o seu sonho americano!', en: 'You have a profile to pursue your American dream!' },
    'arte.msg.notEligible': { pt: 'Estamos com os seus dados e em breve alguém da nossa equipe da D4U vai entrar em contato com você. 💛', en: 'We have your details and someone from the D4U team will contact you soon. 💛' },
    'arte.gen.title': { pt: '✨ Sua arte está sendo gerada…', en: '✨ Your art is being created…' },
    'arte.gen.sub': { pt: 'Estamos pintando cada detalhe do seu sonho. Volte a esta tela em instantes!', en: 'We are drawing every detail of your dream. Check back here in a moment!' },
    'arte.download': { pt: '⬇️ Baixar minha arte', en: '⬇️ Download my art' },
    'arte.download.hint': { pt: 'Guarde este link — você pode voltar aqui quando quiser para baixar sua arte.', en: 'Save this link — you can come back anytime to download your art.' },
    'arte.download.filename': { pt: 'minha-arte-d4u.png', en: 'my-art-d4u.png' },
    'arte.failed': { pt: 'Não foi possível gerar sua arte agora. Nossa equipe já está com seus dados e vai te ajudar. 💛', en: 'We could not generate your art right now. Our team already has your details and will help you. 💛' },
    'arte.cta.title': { pt: 'Quer transformar esse sonho em realidade? 🚀', en: 'Ready to turn this dream into reality? 🚀' },
    'arte.cta.sub': { pt: 'A D4U Immigration tem 91% de taxa de sucesso e garantia de devolução do dinheiro.', en: 'D4U Immigration has a 91% success rate and a money-back guarantee.' },
    'arte.cta.btn': { pt: 'Falar com especialista →', en: 'Talk to a specialist →' },
    'arte.img.alt': { pt: 'Sua arte personalizada', en: 'Your personalized art' },
  };

  function normalizeLang(code) {
    return (code || '').toLowerCase().startsWith('en') ? 'en' : 'pt';
  }

  function arteT(key, langCode, vars) {
    const l = normalizeLang(langCode || lang);
    const item = ARTE_STRINGS[key];
    let text = item ? (item[l] || item.pt) : key;
    if (vars) Object.keys(vars).forEach(k => { text = text.replace(`{${k}}`, vars[k]); });
    return text;
  }

  function applyArtePage(langCode) {
    const l = normalizeLang(langCode || lang);
    document.documentElement.lang = l === 'en' ? 'en' : 'pt-BR';
    document.title = arteT('arte.page.title', l);
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const val = arteT(key, l);
      if (el.getAttribute('data-i18n-html') === '1') el.innerHTML = val;
      else el.textContent = val;
    });
    const img = document.getElementById('art-final');
    if (img) img.alt = arteT('arte.img.alt', l);
    const dl = document.getElementById('download-btn');
    if (dl) dl.setAttribute('download', arteT('arte.download.filename', l));
  }

  return {
    t, getLang, setLang, applyLanguage, branchCopy, dreamSuggestions, OPTION_LABELS,
    arteT, applyArtePage, normalizeLang,
  };
})();
