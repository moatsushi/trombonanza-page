function doPost(event) {
  try {
    const data = JSON.parse(event.postData.contents || '{}');
    const scriptProperties = PropertiesService.getScriptProperties();
    const expectedSecret = scriptProperties.getProperty('CONTACT_SHARED_SECRET');
    const contactRecipient = scriptProperties.getProperty('CONTACT_RECIPIENT');

    if (!expectedSecret || !contactRecipient || data.secret !== expectedSecret) {
      return jsonResponse({ok: false, error: 'unauthorized'});
    }

    const name = normalize(data.name);
    const email = normalize(data.email);
    const message = normalize(data.message);
    const rateKey = normalize(data.rateKey);
    if (!name || name.length > 80 || !validEmail(email) || message.length < 5 || message.length > 4000) {
      return jsonResponse({ok: false, error: 'invalid_input'});
    }
    if (!consumeRateLimit(rateKey)) {
      return jsonResponse({ok: false, error: 'rate_limited'});
    }

    const safeName = name.replace(/[\r\n]+/g, ' ').slice(0, 80);
    const body = [
      'TROMBONANZA公式サイトからお問い合わせがありました。',
      '',
      `お名前: ${name}`,
      `メールアドレス: ${email}`,
      '',
      'お問い合わせ内容:',
      message,
    ].join('\n');

    MailApp.sendEmail({
      to: contactRecipient,
      replyTo: email,
      subject: `[Webお問い合わせ] ${safeName}`,
      body: body,
      name: 'TROMBONANZA お問い合わせ',
    });
    return jsonResponse({ok: true});
  } catch (error) {
    console.error(error);
    return jsonResponse({ok: false, error: 'internal_error'});
  }
}

function normalize(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function validEmail(value) {
  return value.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function consumeRateLimit(key) {
  if (!/^[a-f0-9]{64}$/.test(key)) return false;

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return false;
  try {
    const cache = CacheService.getScriptCache();
    const cacheKey = `contact-${key}`;
    const count = Number(cache.get(cacheKey) || 0);
    if (count >= 5) return false;
    cache.put(cacheKey, String(count + 1), 60);
    return true;
  } finally {
    lock.releaseLock();
  }
}

function jsonResponse(value) {
  return ContentService
    .createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}
