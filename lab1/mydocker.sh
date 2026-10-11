#!/usr/bin/env bash
set -euo pipefail

CGROUP=/sys/fs/cgroup/lab1
sudo mkdir -p "$CGROUP"
echo 128M | sudo tee "$CGROUP/memory.max" >/dev/null
echo "50000 100000" | sudo tee "$CGROUP/cpu.max" >/dev/null
echo 64 | sudo tee "$CGROUP/pids.max" >/dev/null

sudo unshare --pid --mount --net --uts --ipc --user --map-root-user --fork \
  bash -c '
    hostname lab1-api
    mount -t proc proc /proc
    ip link set lo up
    exec setpriv --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs \
      python3 /app/seccomp_runner.py -- uvicorn main:app --host 0.0.0.0 --port 8000
  ' &

PID=$!
echo "$PID" | sudo tee "$CGROUP/cgroup.procs" >/dev/null
wait "$PID"