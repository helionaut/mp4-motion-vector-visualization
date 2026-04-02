#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="${MMV_IMAGE_NAME:-mp4-motion-vector-visualization-env:local}"
DOCKER_BIN="${DOCKER_BIN:-docker}"

CACHE_ROOT="${MMV_CACHE_ROOT:-/home/helionaut/srv/research-cache/18afd661ce11}"
DOWNLOADS_DIR="${MMV_DOWNLOADS_DIR:-${CACHE_ROOT}/downloads}"
DATASETS_DIR="${MMV_DATASETS_DIR:-${CACHE_ROOT}/datasets}"
TOOLCHAINS_DIR="${MMV_TOOLCHAINS_DIR:-${CACHE_ROOT}/toolchains}"
BUILDS_DIR="${MMV_BUILDS_DIR:-${CACHE_ROOT}/builds}"
ARTIFACTS_DIR="${MMV_ARTIFACTS_DIR:-${CACHE_ROOT}/artifacts}"
LOGS_DIR="${MMV_LOGS_DIR:-${CACHE_ROOT}/logs}"
DOCKER_STATE_DIR="${MMV_DOCKER_STATE_DIR:-${CACHE_ROOT}/docker}"

CACHE_DIRS=(
  "${CACHE_ROOT}"
  "${DOWNLOADS_DIR}"
  "${DATASETS_DIR}"
  "${TOOLCHAINS_DIR}"
  "${BUILDS_DIR}"
  "${ARTIFACTS_DIR}"
  "${LOGS_DIR}"
  "${DOCKER_STATE_DIR}"
)

usage() {
  cat <<'EOF'
Usage: scripts/run_in_docker.sh <command> [args...]

Commands:
  doctor            Print the resolved Docker/cache contract.
  dry-run           Print the docker build/run commands without executing them.
  build             Build the repo-local environment image.
  run [cmd ...]     Run a command inside the environment (default: bash).
  ffmpeg-version    Run ffmpeg -version inside the environment.
EOF
}

ensure_cache_dirs() {
  mkdir -p "${CACHE_DIRS[@]}"
}

docker_available() {
  command -v "${DOCKER_BIN}" >/dev/null 2>&1
}

tty_args=()
if [[ -t 0 && -t 1 ]]; then
  tty_args=(-it)
fi

build_cmd=(
  "${DOCKER_BIN}" build
  --build-arg "USER_ID=$(id -u)"
  --build-arg "GROUP_ID=$(id -g)"
  --tag "${IMAGE_NAME}"
  --file "${REPO_ROOT}/Dockerfile"
  "${REPO_ROOT}"
)

run_cmd=(
  "${DOCKER_BIN}" run
  --rm
  "${tty_args[@]}"
  --workdir /workspace
  --volume "${REPO_ROOT}:/workspace"
  --volume "${CACHE_ROOT}:/cache-root"
  --env "MMV_CACHE_ROOT=/cache-root"
  --env "MMV_DOWNLOADS_DIR=/cache-root/downloads"
  --env "MMV_DATASETS_DIR=/cache-root/datasets"
  --env "MMV_TOOLCHAINS_DIR=/cache-root/toolchains"
  --env "MMV_BUILDS_DIR=/cache-root/builds"
  --env "MMV_ARTIFACTS_DIR=/cache-root/artifacts"
  --env "MMV_LOGS_DIR=/cache-root/logs"
  --env "MMV_DOCKER_STATE_DIR=/cache-root/docker"
  "${IMAGE_NAME}"
)

print_contract() {
  cat <<EOF
Repo root: ${REPO_ROOT}
Docker binary: ${DOCKER_BIN}
Docker available: $(docker_available && echo yes || echo no)
Image name: ${IMAGE_NAME}
Cache root: ${CACHE_ROOT}
Downloads dir: ${DOWNLOADS_DIR}
Datasets dir: ${DATASETS_DIR}
Toolchains dir: ${TOOLCHAINS_DIR}
Builds dir: ${BUILDS_DIR}
Artifacts dir: ${ARTIFACTS_DIR}
Logs dir: ${LOGS_DIR}
Docker state dir: ${DOCKER_STATE_DIR}
EOF
}

require_docker() {
  if docker_available; then
    return 0
  fi

  cat >&2 <<EOF
Docker CLI not found. Install Docker or point DOCKER_BIN at a compatible CLI before using '${1}'.
You can still inspect the contract with:
  scripts/run_in_docker.sh doctor
  scripts/run_in_docker.sh dry-run
EOF
  exit 1
}

print_dry_run() {
  ensure_cache_dirs
  print_contract
  printf 'Build command:'
  printf ' %q' "${build_cmd[@]}"
  printf '\n'
  printf 'Run command:'
  printf ' %q' "${run_cmd[@]}"
  if [[ "$#" -eq 0 ]]; then
    printf ' %q' bash
  else
    printf ' %q' "$@"
  fi
  printf '\n'
}

cmd="${1:-}"
if [[ -z "${cmd}" ]]; then
  usage >&2
  exit 1
fi
shift

case "${cmd}" in
  doctor)
    ensure_cache_dirs
    print_contract
    ;;
  dry-run)
    print_dry_run "${@:-bash}"
    ;;
  build)
    require_docker "build"
    ensure_cache_dirs
    "${build_cmd[@]}"
    ;;
  run)
    require_docker "run"
    ensure_cache_dirs
    "${build_cmd[@]}"
    if [[ "${1:-}" == "--" ]]; then
      shift
    fi
    if [[ "$#" -eq 0 ]]; then
      "${run_cmd[@]}" bash
    else
      "${run_cmd[@]}" "$@"
    fi
    ;;
  ffmpeg-version)
    require_docker "ffmpeg-version"
    ensure_cache_dirs
    "${build_cmd[@]}"
    "${run_cmd[@]}" ffmpeg -version
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
