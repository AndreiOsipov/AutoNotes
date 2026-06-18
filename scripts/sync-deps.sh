#!/usr/bin/env bash
# Выбор torch-backend для uv sync.
#
# Приоритет:
#   1. AUTONOTES_TORCH_EXTRA (cpu | cuda130 | rocm)
#   2. UV_TORCH_BACKEND (cpu | cu130 | rocm | auto) — совместимость с uv pip
#   3. Автоопределение: nvidia-smi → cuda130, rocm-smi → rocm, иначе cpu
#
# Примеры:
#   ./scripts/sync-deps.sh
#   AUTONOTES_TORCH_EXTRA=cuda130 ./scripts/sync-deps.sh
#   ./scripts/sync-deps.sh --group dev

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

detect_extra() {
    if command -v nvidia-smi >/dev/null 2>&1; then
        echo "cuda130"
        return
    fi
    if command -v rocm-smi >/dev/null 2>&1; then
        echo "rocm"
        return
    fi
    echo "cpu"
}

resolve_extra() {
    if [[ -n "${AUTONOTES_TORCH_EXTRA:-}" ]]; then
        echo "$AUTONOTES_TORCH_EXTRA"
        return
    fi

    case "${UV_TORCH_BACKEND:-}" in
        cpu) echo "cpu" ;;
        cu130|cuda130) echo "cuda130" ;;
        rocm) echo "rocm" ;;
        auto) detect_extra ;;
        "") detect_extra ;;
        *)
            echo "Unknown UV_TORCH_BACKEND=${UV_TORCH_BACKEND}. Use cpu, cu130, rocm, or auto." >&2
            exit 1
            ;;
    esac
}

EXTRA="$(resolve_extra)"
echo "Using torch extra: ${EXTRA}"
exec uv sync --extra "${EXTRA}" "$@"
