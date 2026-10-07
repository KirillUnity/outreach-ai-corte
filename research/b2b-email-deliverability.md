# B2B email deliverability (шпаргалка на собес)

Связанные файлы (не копипаста): [email-deliverability-2024.md](email-deliverability-2024.md) (SPF/DKIM/DMARC чеклист), [email-finding-strategies.md](email-finding-strategies.md) (RCPT TO), [warmup-mechanics.md](warmup-mechanics.md).

**Самопроверка:** почему open rate плохая KPI в 2024+? → Apple Mail Privacy Protection и прокси-пиксели делают «открытие» не равно «человек прочитал». Смотри bounce, complaint, reply.

---

## Русский

### Inbox vs spam

Письмо попадает во входящие не потому, что текст «не спамный», а потому что **репутация домена и IP** плюс **аутентификация** совпали с политикой приёмника (Gmail, Microsoft). PTR (обратная DNS на исходящий IP) должен указывать на hostname, который сам резолвится в этот IP. Без PTR крупные MX часто режут или кладут в спам даже легитимный маркетинг.

**SPF** говорит, каким хостам разрешено слать от имени домена (`v=spf1 … -all`). Несколько TXT `v=spf1` — ошибка. Лимит ~10 DNS lookup. **DKIM** — подпись тела/заголовков ключом из DNS (`selector._domainkey`). **DMARC** требует alignment: домен в From совпадает с доменом SPF и/или DKIM. Политика `p=none` (мониторинг) → `quarantine` → `reject`. Кортекс проверяет записи DNS; он **не** подписывает DKIM за вас.

### Почему не свой RCPT TO

Живой SMTP (`HELO` / `MAIL FROM` / `RCPT TO`) на чужой MX выглядит как разведка списка. После серии зондов IP попадает в блок. Catch-all отвечает 250 на любой ящик — проверка бессмысленна. Cortex: `SMTPVerifier` только мок. Детали: [email-finding-strategies.md](email-finding-strategies.md).

### Warmup vs Instantly / Mailreach

Продукты вроде Instantly/Lemwarm крутят объём и engagement, чтобы «прогреть» ящик. Кривая типична: мало писем в первую неделю, рост, мониторинг bounce. В Cortex **WarmupEmulator** — симуляция peer-сети в Postgres (sent/open/reply/bounce), **без SMTP**. Это демо репутации и UI, не замена SaaS-прогрева. Sequence (день 18) — форма кампании (steps/enroll/tick), тоже без отправки.

### Метрики

| Метрика | Зачем | Ловушка |
|---------|--------|---------|
| Bounce | битые ящики, плохой список | не путать soft/hard |
| Complaint | «это спам» | убивает репутацию быстрее bounce |
| Reply | реальный интерес | редкая, но честная |
| Open | proxy engagement | **MPP (2021+)**: Apple заранее грузит пиксель → open ~100% у части базы |

Инвесторский слайд: cost per run, hold/send/reject mix, reply — не vanity opens.

### Как это устроено в Cortex

- **Live DNS:** `GET /deliverability/check/{domain}` — SPF/DKIM/DMARC/MX, кэш TTL, CLI.
- **Snapshot:** таблица `domain_health`; нода агента `check_deliverability` читает снимок, не обязательно живой DNS на каждый прогон.
- **WarmupEmulator:** mailbox + events, `tick` / n8n `warmup_tick.json`.
- **Finder:** паттерны + опционально Hunter/Apollo; SMTP выключен.

На собесе: «мы моделируем политику и прогрев; прод-отправка — отдельный риск и отдельный спринт».

---

## English

Inbox placement is **domain/IP reputation + SPF/DKIM/DMARC alignment**, not adjective-free copy. PTR should match the sending host. **Do not** probe foreign MX with RCPT TO (spam intel; catch-all lies). Cortex mocks SMTP verification.

Warmup SaaS (Instantly, Lemwarm) ramps volume; our **WarmupEmulator** is a Postgres peer simulation for the portfolio — no real mail. **Open rate** is a weak KPI after Apple Mail Privacy Protection (prefetch pixels). Prefer bounce, complaint, reply.

Two deliverability paths: live DNS checker vs `domain_health` snapshot used by the LangGraph node. Human approval stays on so we never auto-SMTP.
