# Skills: AI-ассистент триажа баг-репортов TaskFlow

## Общая логика
Workflow обрабатывает входящий тикет через pipeline:
1. Читает документацию сервиса (`/data/docs/<service>.md`).
2. Читает список открытых issues (`/data/issues/open-issues.json`).
3. LLM классифицирует тикет и принимает решение.
4. Результат сохраняется в memory (MCP memory) и в файл `/data/processed/<ticket_id>.json`.

## Skill 1: classify_ticket
Определение типа, сервиса, severity.

**Правила:**
- type: bug | feature | question
- service: 
  - "Save", "кнопка", "UI", "браузер" → web
  - "502", "API", "rate limit", "webhook" → api
  - "email", "notification", "report", "sync" → worker
- severity: 
  - потеря данных / сервис недоступен → critical
  - функциональная поломка → high
  - замедление / визуальный баг → medium
  - косметика → low
- confidence < 0.7 → пометка needs_human_review

## Skill 2: deduplicate
Поиск дубликатов в open-issues.

**Правила:**
- Сравнение title и description с существующими issues.
- Совпадение ключевых слов + одинаковый service → duplicate.
- related_issue = ID найденного issue.

## Skill 3: assign
Назначение owner'а.

**Правила:**
- Читать docs/<service>.md → брать Lead email.
- Если service не определён → assignee = null.

## Skill 4: summarize
Формирование summary для дежурного.

## Порядок действий (know-how)
1. Определить сервис по ключевым словам в title/description.
2. Прочитать документацию сервиса.
3. Прочитать issues.
4. Проверить дубликаты.
5. Определить assignee.
6. Сформировать summary.
7. Вернуть JSON.

## Правила безопасности
- Не создавать issue без severity.
- При confidence < 0.7 - пометка needs_human_review.
- Не использовать write_file агентом (запись выполняется детерминированно отдельной нодой).