# Стратегии поиска email

## Источники (по приоритету)

1. **LinkedIn (confidence 0.9)** — если человек сам указал адрес в профиле.
2. **Hunter.io (confidence 0.6–0.9)** — API-провайдер с агрегированной базой контактов (score/100, cap 0.9).
3. **Apollo (confidence 0.6–0.85)** — B2B-база; клиент зарезервирован настройками, не обязателен в Day 17.
4. **Паттерны (confidence 0.4–0.85)** — генерация local-part по имени + домен компании.
5. **SMTP-верификация (только подтверждение)** — в этом репозитории **мок**. Живой `RCPT TO` не реализуем.

## Формула confidence

- Источник: LinkedIn ≥ Hunter (cap 0.9) > pattern.
- Тип паттерна: `{first}.{last}` (0.85) > `{first}{last}` (0.75) > `{f}{last}` (0.70) > `{first}` (0.5) > прочие (0.4).
- SMTP mock: `valid` → +0.1 (ceiling 1.0), `invalid` → 0, `catchall` → min(confidence, 0.3).

Primary ставится только если `confidence >= min_confidence_to_use` (по умолчанию 0.6). В БД сохраняем от `min_confidence_to_save` (0.3).

## SMTP-верификация — почему опасно

- `HELO` + `MAIL FROM` + `RCPT TO` на чужой MX выглядит как разведка списка рассылки.
- Провайдеры (Google, Microsoft) после серии зондов кладут IP в блок / reputation sink.
- Catch-all домены отвечают 250 на любой ящик — проверка бессмысленна и всё равно шумит.
- Решение: Hunter / NeverBounce / ZeroBounce, а не свой SMTP-зонд с прод-IP.

## Паттерны email по индустриям

- Tech startup: `{first}@domain.com`
- Enterprise: `{first}.{last}@domain.com`
- Агентства: `{f}{last}@domain.com`
- Европа: `{first}.{last}@domain.com`
- США: `{first}{last}@domain.com`

Цифры — эмпирика из публичных отчётов Hunter/Clearbit, не гарантия для конкретного тенанта.

## Что делать с catch-all

- SMTP бесполезен: любой local-part «существует».
- Confidence режем до 0.3 — primary не ставим автоматически (`min_use=0.6`).
- Отправку не запрещаем полностью: лучше warmed mailbox + ручной review, чем слепой drop охвата.

## Best practices

- Держать 2–3 candidates на персону (LinkedIn + Hunter + top pattern).
- Primary после верификации или явного `POST .../set-primary`.
- Не слать на confidence &lt; 0.6 без человека в петле.
- Логировать `source` для аналитики hit-rate по провайдеру.
