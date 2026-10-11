#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-api-docker}"
OUTPUT_DIR="${OUTPUT_DIR:-/var/lib/node_exporter/textfile}"
OUTPUT_FILE="${OUTPUT_DIR}/${CONTAINER_NAME}.prom"
INTERVAL="${INTERVAL:-10}"

mkdir -p "$OUTPUT_DIR"

# утилита для деления usec -> sec
div_usec() {
  awk -v v="$1" 'BEGIN { printf "%.6f", v/1000000 }'
}

while true; do
  CID=$(docker inspect "$CONTAINER_NAME" --format '{{.Id}}' 2>/dev/null || true)
  if [ -z "$CID" ]; then
    rm -f "$OUTPUT_FILE"
    sleep "$INTERVAL"
    continue
  fi

  CGROUP="/sys/fs/cgroup/system.slice/docker-${CID}.scope"
  if [ ! -d "$CGROUP" ]; then
    rm -f "$OUTPUT_FILE"
    sleep "$INTERVAL"
    continue
  fi

  MEM_CURRENT=$(cat "$CGROUP/memory.current" 2>/dev/null || echo 0)
  MEM_MAX=$(cat "$CGROUP/memory.max" 2>/dev/null || echo 0)
  [ "$MEM_MAX" = "max" ] && MEM_MAX=0

  CPU_USAGE_USEC=$(awk '/^usage_usec/{print $2}' "$CGROUP/cpu.stat" 2>/dev/null || echo 0)
  CPU_THROTTLED_USEC=$(awk '/^throttled_usec/{print $2}' "$CGROUP/cpu.stat" 2>/dev/null || echo 0)
  NR_THROTTLED=$(awk '/^nr_throttled/{print $2}' "$CGROUP/cpu.stat" 2>/dev/null || echo 0)

  PIDS_CURRENT=$(cat "$CGROUP/pids.current" 2>/dev/null || echo 0)
  PIDS_MAX=$(cat "$CGROUP/pids.max" 2>/dev/null || echo 0)
  [ "$PIDS_MAX" = "max" ] && PIDS_MAX=0

  OOM_KILLS=$(awk '/^oom_kill /{print $2}' "$CGROUP/memory.events" 2>/dev/null || echo 0)
  MEM_MAX_EVENTS=$(awk '/^max /{print $2}' "$CGROUP/memory.events" 2>/dev/null || echo 0)

  cat > "${OUTPUT_FILE}.tmp" <<EOF
# HELP api_docker_memory_working_set_bytes Working set памяти контейнера (из cgroup v2 memory.current)
# TYPE api_docker_memory_working_set_bytes gauge
api_docker_memory_working_set_bytes{container="${CONTAINER_NAME}"} ${MEM_CURRENT}

# HELP api_docker_memory_limit_bytes Лимит памяти контейнера (memory.max)
# TYPE api_docker_memory_limit_bytes gauge
api_docker_memory_limit_bytes{container="${CONTAINER_NAME}"} ${MEM_MAX}

# HELP api_docker_cpu_usage_seconds_total Накопленное CPU-время в секундах (cpu.stat usage_usec)
# TYPE api_docker_cpu_usage_seconds_total counter
api_docker_cpu_usage_seconds_total{container="${CONTAINER_NAME}"} $(div_usec "$CPU_USAGE_USEC")

# HELP api_docker_cpu_throttled_seconds_total Накопленное время CFS throttling в секундах
# TYPE api_docker_cpu_throttled_seconds_total counter
api_docker_cpu_throttled_seconds_total{container="${CONTAINER_NAME}"} $(div_usec "$CPU_THROTTLED_USEC")

# HELP api_docker_cpu_throttled_periods_total Количество throttled периодов CFS
# TYPE api_docker_cpu_throttled_periods_total counter
api_docker_cpu_throttled_periods_total{container="${CONTAINER_NAME}"} ${NR_THROTTLED}

# HELP api_docker_pids_current Текущее число задач в cgroup
# TYPE api_docker_pids_current gauge
api_docker_pids_current{container="${CONTAINER_NAME}"} ${PIDS_CURRENT}

# HELP api_docker_pids_max Лимит задач в cgroup
# TYPE api_docker_pids_max gauge
api_docker_pids_max{container="${CONTAINER_NAME}"} ${PIDS_MAX}

# HELP api_docker_oom_kills_total Количество OOM-kill событий в cgroup
# TYPE api_docker_oom_kills_total counter
api_docker_oom_kills_total{container="${CONTAINER_NAME}"} ${OOM_KILLS}
EOF
  mv "${OUTPUT_FILE}.tmp" "$OUTPUT_FILE"

  sleep "$INTERVAL"
done