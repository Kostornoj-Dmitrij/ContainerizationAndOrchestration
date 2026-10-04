# Service: worker (Background Worker)

## Owner
- **Team:** Platform Team
- **Lead:** Алексей Смирнов (alexey@taskflow.io)
- **Slack:** #platform-support

## Description
Фоновый обработчик задач на Python. Отправляет email-уведомления, генерирует отчёты, синхронизирует данные с внешними системами.

## Known issues
- Email-уведомления иногда дублируются
- Генерация больших отчётов может занимать > 10 минут
- Синхронизация с Jira иногда пропускает задачи

## Deployment
Kubernetes (EKS), Celery + Redis.