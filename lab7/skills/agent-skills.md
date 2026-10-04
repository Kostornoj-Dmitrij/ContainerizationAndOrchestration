# Skills: AI-ассистент триажа баг-репортов TaskFlow

## Общая логика
Workflow обрабатывает входящий тикет через детерминированный pipeline:
1. Webhook принимает тикет (title, description, ticket_id).
2. MCP filesystem читает документацию сервиса (`/data/docs/<service>.md`) - сервис определяется по ключевым словам.
3. MCP filesystem читает список открытых issues (`/data/issues/open-issues.json`).
4. AI Agent (LLM) получает весь контекст и классифицирует тикет, определяет дубликаты и assignee, формирует summary.
5. MCP memory сохраняет entity в knowledge graph (для накопления обработанных тикетов).
6. MCP filesystem записывает результат в `/data/processed/<ticket_id>.json`.
7. Webhook возвращает JSON клиенту.

## Toolkit
Агент имеет доступ к 5 инструментам через 2 MCP-сервера:

| Tool              | MCP-сервер | Что делает                       | Вход                       |
|-------------------|------------|----------------------------------|----------------------------|
| `read_file`       | filesystem | Читает файл                      | `path` (string)            |
| `write_file`      | filesystem | Пишет файл                       | `path`, `content` (string) |
| `list_directory`  | filesystem | Список файлов в директории       | `path` (string)            |
| `create_entities` | memory     | Создаёт entity в knowledge graph | `entities` (array)         |
| `read_graph`      | memory     | Читает граф памяти               | -                          |

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
- Сравнить title и description тикета с title каждого issue.
- Достаточно 2-3 общих ключевых слов + одинаковый service.
- Пример: "API 502" и "API возвращает 502" → duplicate.
- related_issue = ID найденного issue.
- Если совпадений нет → action="new_bug".

## Skill 3: assign
Назначение owner'а.

**Правила:**
- Читать docs/<service>.md → брать Lead email.
- Если service не определён → assignee = null.

## Skill 4: summarize
Формирование summary для дежурного.

**Правила:**
- 2-3 предложения на русском.
- Что случилось + что делать.
- Без технического жаргона - дежурный может быть не из команды сервиса.
- Пример: "Пользователь сообщает о 502 при экспорте отчёта в проектах >1000 задач. Совпадает с известным issue TF-102. Рекомендуется проверить rate limit на API."

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