#!/usr/bin/env bash
set -euo pipefail

CGROUP_NAME=lab1
CGROUP="/sys/fs/cgroup/${CGROUP_NAME}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="${REPO_ROOT}/lab1/api"
VENV="${API_DIR}/.venv"
UVICORN="${VENV}/bin/uvicorn"
PYTHON="${VENV}/bin/python3"
SECCOMP_RUNNER="${REPO_ROOT}/lab1/seccomp_runner.py"

MEMORY_MAX="256M"
CPU_MAX="50000 100000"
PIDS_MAX="64"

SECCOMP_DENY="mount"

sudo mkdir -p "${CGROUP}"
echo "${MEMORY_MAX}"   | sudo tee "${CGROUP}/memory.max" >/dev/null
echo "${CPU_MAX}"      | sudo tee "${CGROUP}/cpu.max"    >/dev/null
echo "${PIDS_MAX}"     | sudo tee "${CGROUP}/pids.max"   >/dev/null

echo "cgroup ${CGROUP}:"
echo "  memory.max = $(cat ${CGROUP}/memory.max)"
echo "  cpu.max    = $(cat ${CGROUP}/cpu.max)"
echo "  pids.max   = $(cat ${CGROUP}/pids.max)"
echo

sudo bash -c "
set -euo pipefail

echo \$\$ > ${CGROUP}/cgroup.procs

exec unshare --pid --mount --mount-proc --net --uts --ipc --user --map-root-user --fork \\
  bash -c '
    set -euo pipefail
    hostname lab1-api
    ip link set lo up
    cd ${API_DIR}
    exec setpriv --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs \\
      ${PYTHON} ${SECCOMP_RUNNER} --deny ${SECCOMP_DENY} -- \\
      ${UVICORN} main:app --host 0.0.0.0 --port 8000
  '
"