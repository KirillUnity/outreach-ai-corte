# Email Deliverability — Best Practices 2024

## Аутентификация

### SPF

- Одна SPF-запись на домен (RFC 7208); несколько TXT `v=spf1` — ошибка.
- Использовать `-all` для hardfail в продакшене после инвентаризации отправителей.
- Не более 10 DNS lookup (`include` / `a` / `mx` / `ptr` / `exists` / `redirect`).
- `include:` вместо длинных `ip4` где провайдер публикует свой SPF.

### DKIM

- Минимум 1024-bit RSA (лучше 2048).
- Отдельный селектор для каждой системы (google, mailchimp, mandrill, …).
- Ротация ключей раз в 6–12 месяцев; пустой `p=` — отзыв ключа.
- Ed25519 быстрее, но менее распространён у приёмников.

### DMARC

- Начинать с `p=none` для мониторинга (2–4 недели) + `rua`.
- Переходить на `p=quarantine`, затем `p=reject`.
- Обязательно `rua` для агрегированных отчётов.
- `pct=100` после полного тестирования alignment.

### MX

- Должны быть настроены: иначе нет пути для ответов на outreach.
- Обычно Google Workspace или Microsoft 365.

## Прогрев почты

- День 1–7: 5–10 писем/день, только тёплые контакты.
- День 8–14: 15–25 писем, микс тёплых и холодных.
- День 15–21: 30–50 писем, только высокий engagement.
- День 22–30: 50–100 писем, production.
- Мониторинг: open rate > 50%, reply rate > 3%, bounce < 2%.

## Репутация домена

- Субдомен для cold outreach (`mail.yourdomain.com`), не смешивать с transactional.
- Мониторить blacklists (MXToolbox, Spamhaus).
- Google Postmaster Tools для репутации.

## Сравнение инструментов

- Instantly — ~$37/мес, встроенный warmup.
- Smartlead — ~$39/мес, интеграции.
- Lemwarm — ~$29/мес, только warmup.
- Собственный стек — без SaaS-платы, нужен SMTP и дисциплина объёма.

## Cortex

Live check: `GET /api/v1/deliverability/check/{domain}`. Агент по-прежнему гейтит отправку по **снимку** `DomainHealth` (`app.services.deliverability_checker`), а не по каждому DNS-запросу в графе.
