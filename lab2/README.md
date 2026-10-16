# Лаба 2 - Мониторинг сервиса: метрики, логи, трейсы

Лабу делал на ВМ (Ubuntu Server 24.04, 10 ГБ RAM, 12 CPU).

# Часть 0 - подготовка

С помощью ИИ сгенерил небольшой сервис на Python FastAPI с четырьмя эндпоинтами:
- GET /health - возвращает ok
- GET /fail - возвращает 500 и увеличивает счётчик ошибок
- GET /slow - спит 1-3 секунды
- GET /load - дёргает сам себя пачкой запросов, чтобы подскочил RPS

Собрал конфиг для kind: три ноды, NodePorts проброшены на хост, чтобы с хоста открывать браузером:

![img.png](screenshots/img.png)

Создал кластер:

![img_1.png](screenshots/img_1.png)

Все три ноды Ready, системные поды поднялись:

![img_2.png](screenshots/img_2.png)

Клонировал репу, перешёл в lab2:

![img_3.png](screenshots/img_3.png)

Собрал образ и загрузил его в kind:

![img_4.png](screenshots/img_4.png)
![img_5.png](screenshots/img_5.png)

Проверил, что образ внутри ноды:

![img_6.png](screenshots/img_6.png)

Поставил чарт api в namespace app:

![img_7.png](screenshots/img_7.png)

Поды поднялись, сервис доступен:

![img_8.png](screenshots/img_8.png)

Потыкал эндпоинты:

![img_9.png](screenshots/img_9.png)

/load дёргает пачку запросов и RPS подскакивает:

![img_10.png](screenshots/img_10.png)

Логи в stdout в JSON с trace_id.

![img_11.png](screenshots/img_11.png)

Метрики Prometheus на /metrics:

![img_12.png](screenshots/img_12.png)

После /load счётчики выросли.

![img_13.png](screenshots/img_13.png)

## Часть 1 - метрики

Добавил репу prometheus-community.

![img_14.png](screenshots/img_14.png)

Запулил values-файл из репы.

![img_15.png](screenshots/img_15.png)

Создал namespace monitoring и поставил kube-prometheus-stack.

![img_16.png](screenshots/img_16.png)

![img_17.png](screenshots/img_17.png)

Все поды Running, сервисы видны.

![img_18.png](screenshots/img_18.png)

Grafana доступна, залогинился:

![img_21.png](screenshots/img_21.png)

Prometheus тоже открывается.

![img_20.png](screenshots/img_20.png)

В Targets увидел ожидаемую картину: почти всё up, но один таргет down (etcd).
Насколько понял, Kind запускает etcd без HTTP-метрик (только HTTPS с mTLS, а у Prometheus нет нужных сертификатов).
Вроде не проблема конфигурации, так что оставил как есть.

![img_23.png](screenshots/img_23.png)

![img_24.png](screenshots/img_24.png)

В values api по умолчанию ServiceMonitor был выключен. Включил, обновил релиз.

![img_25.png](screenshots/img_25.png)

![img_26.png](screenshots/img_26.png)

ServiceMonitor появился, Prometheus его подхватил, оба эндпоинта api up.

![img_27.png](screenshots/img_27.png)

![img_28.png](screenshots/img_28.png)

Метрики побежали. По http_requests_total видно распределение по эндпоинтам и статусам.

![img_29.png](screenshots/img_29.png)

Прогнал циклы /health, /fail, /slow и потом /load.

![img_30.png](screenshots/img_30.png)

Счётчики выросли, по /fail видно 500-е.

![img_32.png](screenshots/img_32.png)

По rate(http_requests_total[1m]) виден рост во время нагрузки.

![img_33.png](screenshots/img_33.png)

Собрал дашборд RED: интенсивность запросов, доля ошибок, p95 времени ответа. Жму /fail -> растёт доля ошибок
жму /slow -> растёт p95, жму /load -> растёт RPS.

![img_34.png](screenshots/img_34.png)

## Часть 2 - логи

Loki поставил через Helm. Сначала с отключённым persistence он крашился, потому что пытался писать в /var/loki, который read-only.

![img_35.png](screenshots/img_35.png)

Включил persistence (5Gi PVC), заодно отключил chunks-cache и results-cache, потому что только память жрут на одном инстансе.

![img_36.png](screenshots/img_36.png)

Loki поднялся, PVC создался.

![img_40.png](screenshots/img_40.png)

Для сбора логов поставил Grafana Alloy:

![img_41.png](screenshots/img_41.png)

Alloy поднялся на двух нодах, в логах видно, что он открывает стримы к подам.

![img_42.png](screenshots/img_42.png)

![img_43.png](screenshots/img_43.png)

Проверил, что Loki реально получает данные, дёрнул API. Сначала список лейблов, потом запрос по namespace=app.

![img_44.png](screenshots/img_44.png)

Дёрнул /fail и поискал в логах по intentional failure, нашёл строку с level ERROR и trace_id.

![img_45.png](screenshots/img_45.png)

Подключил Loki как datasource в Grafana.

![img_46.png](screenshots/img_46.png)

И в Explore сделал тот же запрос, видно логи с ошибками, по которым уже можно ходить глазами.

![img_47.png](screenshots/img_47.png)

## Часть 3 - трейсы

Добавил репу jaegertracing.

![img_48.png](screenshots/img_48.png)

Поставил Jaeger в monitoring через свой values-файл.

![img_49.png](screenshots/img_49.png)

![img_50.png](screenshots/img_50.png)

Изначально Jaeger был ClusterIP и с Windows-хоста не открывался. Добавил NodePort-сервис.

![img_51.png](screenshots/img_51.png)

![img_52.png](screenshots/img_52.png)

Дёрнул /slow и /fail несколько раз.

![img_53.png](screenshots/img_53.png)

В Jaeger видны трейсы. get_fail с ошибками:

![img_54.png](screenshots/img_54.png)

Разворачиваю трейс fail, видно корневой спан и вложенные.

![img_55.png](screenshots/img_55.png)

get_slow с длинным вложенным спаном slow-op, в котором и ушло время.

![img_56.png](screenshots/img_56.png)

![img_57.png](screenshots/img_57.png)

Взял trace_id из лога в Grafana.

![img_58.png](screenshots/img_58.png)

И по нему нашёл тот же трейс в Jaeger, связка лог - трейс работает.

![img_59.png](screenshots/img_59.png)

## Часть 4 - алерты

Обновил values kube-prometheus-stack: добавил три правила и webhook-получателя.

![img_60.png](screenshots/img_60.png)

PrometheusRule создался.

![img_61.png](screenshots/img_61.png)

Три правила в Prometheus:

![img_62.png](screenshots/img_62.png)

Проверяю алерт ApiHighErrorRate, дёргаю /fail. В Prometheus правило в firing.

![img_63.png](screenshots/img_63.png)

В Alertmanager виден:

![img_64.png](screenshots/img_64.png)

На webhook.site прилетел POST с JSON.

![img_65.png](screenshots/img_65.png)

Проверил ApiDown. Удалил ServiceMonitor на минуту, чтобы Prometheus потерял таргет.

![img_66.png](screenshots/img_66.png)
![img_67.png](screenshots/img_67.png)

Алерт в firing, в Alertmanager появился, POST ушёл на webhook.

![img_68.png](screenshots/img_68.png)

![img_69.png](screenshots/img_69.png)

![img_70.png](screenshots/img_70.png)

Вернул ServiceMonitor и алерт перешёл в resolved.

![img_73.png](screenshots/img_73.png)

![img_74.png](screenshots/img_74.png)

Проверил третий алерт ApiHighLatencyP95. Добавил в /fail искусственную задержку (для проверки) и повызывал его параллельно.

![img_75.png](screenshots/img_75.png)

![img_76.png](screenshots/img_76.png)

Оба алерта (error rate и latency) одновременно firing.

![img_77.png](screenshots/img_77.png)

JSON на webhook:

![img_78.png](screenshots/img_78.png)

И потом resolved тоже дошло.

![img_79.png](screenshots/img_79.png)

Поверх Alertmanager поставил Karma из wiremind-репы.

![img_80.png](screenshots/img_80.png)
![img_81.png](screenshots/img_81.png)

Karma поднялась, но ClusterIP пробросил через port-forward.

![img_82.png](screenshots/img_82.png)

![img_83.png](screenshots/img_83.png)

Дёргаю /fail, чтобы алерты загорелись.

![img_84.png](screenshots/img_84.png)

В Karma видно оба сработавших алерта в одном окне:

![img_85.png](screenshots/img_85.png)