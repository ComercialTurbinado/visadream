/** Países para telefone (DDI + máscara) e país de nascimento. */
window.VisaDreamPhone = (function () {
  const PHONE_COUNTRIES = [
    { code: 'BR', flag: '🇧🇷', ddi: '+55', mask: '(##) #####-####', min: 10, name: { pt: 'Brasil', en: 'Brazil' } },
    { code: 'US', flag: '🇺🇸', ddi: '+1', mask: '(###) ###-####', min: 10, name: { pt: 'EUA', en: 'USA' } },
    { code: 'PT', flag: '🇵🇹', ddi: '+351', mask: '### ### ###', min: 9, name: { pt: 'Portugal', en: 'Portugal' } },
    { code: 'AR', flag: '🇦🇷', ddi: '+54', mask: '## ####-####', min: 10, name: { pt: 'Argentina', en: 'Argentina' } },
    { code: 'MX', flag: '🇲🇽', ddi: '+52', mask: '## #### ####', min: 10, name: { pt: 'México', en: 'Mexico' } },
    { code: 'CO', flag: '🇨🇴', ddi: '+57', mask: '### ### ####', min: 10, name: { pt: 'Colômbia', en: 'Colombia' } },
    { code: 'CL', flag: '🇨🇱', ddi: '+56', mask: '# #### ####', min: 9, name: { pt: 'Chile', en: 'Chile' } },
    { code: 'PE', flag: '🇵🇪', ddi: '+51', mask: '### ### ###', min: 9, name: { pt: 'Peru', en: 'Peru' } },
    { code: 'UY', flag: '🇺🇾', ddi: '+598', mask: '## ### ###', min: 8, name: { pt: 'Uruguai', en: 'Uruguay' } },
    { code: 'PY', flag: '🇵🇾', ddi: '+595', mask: '### ### ###', min: 9, name: { pt: 'Paraguai', en: 'Paraguay' } },
    { code: 'BO', flag: '🇧🇴', ddi: '+591', mask: '# ### ####', min: 8, name: { pt: 'Bolívia', en: 'Bolivia' } },
    { code: 'VE', flag: '🇻🇪', ddi: '+58', mask: '###-#######', min: 10, name: { pt: 'Venezuela', en: 'Venezuela' } },
    { code: 'EC', flag: '🇪🇨', ddi: '+593', mask: '## ### ####', min: 9, name: { pt: 'Equador', en: 'Ecuador' } },
    { code: 'ES', flag: '🇪🇸', ddi: '+34', mask: '### ## ## ##', min: 9, name: { pt: 'Espanha', en: 'Spain' } },
    { code: 'IT', flag: '🇮🇹', ddi: '+39', mask: '### ### ####', min: 9, name: { pt: 'Itália', en: 'Italy' } },
    { code: 'FR', flag: '🇫🇷', ddi: '+33', mask: '# ## ## ## ##', min: 9, name: { pt: 'França', en: 'France' } },
    { code: 'DE', flag: '🇩🇪', ddi: '+49', mask: '#### #######', min: 10, name: { pt: 'Alemanha', en: 'Germany' } },
    { code: 'GB', flag: '🇬🇧', ddi: '+44', mask: '#### ######', min: 10, name: { pt: 'Reino Unido', en: 'United Kingdom' } },
    { code: 'CA', flag: '🇨🇦', ddi: '+1', mask: '(###) ###-####', min: 10, name: { pt: 'Canadá', en: 'Canada' } },
    { code: 'CN', flag: '🇨🇳', ddi: '+86', mask: '### #### ####', min: 11, name: { pt: 'China', en: 'China' } },
    { code: 'IN', flag: '🇮🇳', ddi: '+91', mask: '##### #####', min: 10, name: { pt: 'Índia', en: 'India' } },
    { code: 'JP', flag: '🇯🇵', ddi: '+81', mask: '##-####-####', min: 10, name: { pt: 'Japão', en: 'Japan' } },
    { code: 'KR', flag: '🇰🇷', ddi: '+82', mask: '##-####-####', min: 10, name: { pt: 'Coreia do Sul', en: 'South Korea' } },
    { code: 'AU', flag: '🇦🇺', ddi: '+61', mask: '### ### ###', min: 9, name: { pt: 'Austrália', en: 'Australia' } },
    { code: 'IL', flag: '🇮🇱', ddi: '+972', mask: '##-###-####', min: 9, name: { pt: 'Israel', en: 'Israel' } },
    { code: 'AE', flag: '🇦🇪', ddi: '+971', mask: '## ### ####', min: 9, name: { pt: 'Emirados Árabes', en: 'UAE' } },
  ];

  const BIRTH_COUNTRIES = [
    { code: 'BR', flag: '🇧🇷', name: { pt: 'Brasil', en: 'Brazil' } },
    { code: 'US', flag: '🇺🇸', name: { pt: 'Estados Unidos', en: 'United States' } },
    { code: 'PT', flag: '🇵🇹', name: { pt: 'Portugal', en: 'Portugal' } },
    { code: 'AR', flag: '🇦🇷', name: { pt: 'Argentina', en: 'Argentina' } },
    { code: 'MX', flag: '🇲🇽', name: { pt: 'México', en: 'Mexico' } },
    { code: 'CO', flag: '🇨🇴', name: { pt: 'Colômbia', en: 'Colombia' } },
    { code: 'CL', flag: '🇨🇱', name: { pt: 'Chile', en: 'Chile' } },
    { code: 'PE', flag: '🇵🇪', name: { pt: 'Peru', en: 'Peru' } },
    { code: 'UY', flag: '🇺🇾', name: { pt: 'Uruguai', en: 'Uruguay' } },
    { code: 'PY', flag: '🇵🇾', name: { pt: 'Paraguai', en: 'Paraguay' } },
    { code: 'BO', flag: '🇧🇴', name: { pt: 'Bolívia', en: 'Bolivia' } },
    { code: 'VE', flag: '🇻🇪', name: { pt: 'Venezuela', en: 'Venezuela' } },
    { code: 'EC', flag: '🇪🇨', name: { pt: 'Equador', en: 'Ecuador' } },
    { code: 'ES', flag: '🇪🇸', name: { pt: 'Espanha', en: 'Spain' } },
    { code: 'IT', flag: '🇮🇹', name: { pt: 'Itália', en: 'Italy' } },
    { code: 'FR', flag: '🇫🇷', name: { pt: 'França', en: 'France' } },
    { code: 'DE', flag: '🇩🇪', name: { pt: 'Alemanha', en: 'Germany' } },
    { code: 'GB', flag: '🇬🇧', name: { pt: 'Reino Unido', en: 'United Kingdom' } },
    { code: 'CA', flag: '🇨🇦', name: { pt: 'Canadá', en: 'Canada' } },
    { code: 'CN', flag: '🇨🇳', name: { pt: 'China', en: 'China' } },
    { code: 'IN', flag: '🇮🇳', name: { pt: 'Índia', en: 'India' } },
    { code: 'JP', flag: '🇯🇵', name: { pt: 'Japão', en: 'Japan' } },
    { code: 'KR', flag: '🇰🇷', name: { pt: 'Coreia do Sul', en: 'South Korea' } },
    { code: 'AU', flag: '🇦🇺', name: { pt: 'Austrália', en: 'Australia' } },
    { code: 'IL', flag: '🇮🇱', name: { pt: 'Israel', en: 'Israel' } },
    { code: 'OTHER', flag: '🌍', name: { pt: 'Outro país', en: 'Other country' } },
  ];

  function getPhoneCountry(code) {
    return PHONE_COUNTRIES.find(c => c.code === code) || PHONE_COUNTRIES[0];
  }

  function applyMask(digits, mask) {
    let out = '';
    let i = 0;
    for (const ch of mask) {
      if (i >= digits.length) break;
      if (ch === '#') out += digits[i++];
      else out += ch;
    }
    return out;
  }

  function formatPhoneInput(value, countryCode) {
    const digits = String(value || '').replace(/\D/g, '');
    const c = getPhoneCountry(countryCode);
    return applyMask(digits, c.mask);
  }

  function fullPhoneNumber(countryCode, localDigits) {
    const c = getPhoneCountry(countryCode);
    const digits = String(localDigits || '').replace(/\D/g, '');
    return c.ddi + digits;
  }

  function isValidPhone(countryCode, localDigits) {
    const c = getPhoneCountry(countryCode);
    const digits = String(localDigits || '').replace(/\D/g, '');
    return digits.length >= c.min;
  }

  function populatePhoneSelect(selectEl, lang) {
    if (!selectEl) return;
    const prev = selectEl.value || 'BR';
    selectEl.innerHTML = PHONE_COUNTRIES.map(c =>
      `<option value="${c.code}">${c.flag} ${c.ddi}</option>`
    ).join('');
    selectEl.value = PHONE_COUNTRIES.some(c => c.code === prev) ? prev : 'BR';
  }

  function populateBirthSelect(selectEl, lang) {
    if (!selectEl) return;
    const prev = selectEl.value || 'BR';
    selectEl.innerHTML = BIRTH_COUNTRIES.map(c =>
      `<option value="${c.code}">${c.flag} ${c.name[lang] || c.name.pt}</option>`
    ).join('');
    selectEl.value = BIRTH_COUNTRIES.some(c => c.code === prev) ? prev : 'BR';
  }

  function birthCountryLabel(code, lang) {
    const c = BIRTH_COUNTRIES.find(x => x.code === code);
    return c ? (c.name[lang] || c.name.pt) : code;
  }

  return {
    PHONE_COUNTRIES,
    BIRTH_COUNTRIES,
    getPhoneCountry,
    formatPhoneInput,
    fullPhoneNumber,
    isValidPhone,
    populatePhoneSelect,
    populateBirthSelect,
    birthCountryLabel,
  };
})();
