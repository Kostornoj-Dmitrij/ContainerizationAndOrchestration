# Service: api (Backend API)

## Owner
- **Team:** Backend Team
- **Lead:** Дмитрий Петров (dmitry@taskflow.io)
- **Slack:** #backend-support

## Description
REST API на Go. Обслуживает все запросы от frontend и внешних интеграций.

## Known issues
- Rate limiting срабатывает слишком агрессивно при экспорте больших отчётов
- Иногда возвращает 502 при нагрузке > 1000 RPS
- Webhook'и иногда приходят с задержкой 30+ секунд

## Deployment
Kubernetes (EKS), PostgreSQL RDS, Redis ElastiCache.