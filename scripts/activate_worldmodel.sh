#!/usr/bin/env bash
# Source this file from bash: source scripts/activate_worldmodel.sh

_WORLD_MODEL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_CONDA_SH="/root/nas/users/luzheng/workspace/enter/etc/profile.d/conda.sh"

if [[ ! -f "${_CONDA_SH}" ]]; then
  echo "Conda initialization file not found: ${_CONDA_SH}" >&2
  return 1
fi

source "${_CONDA_SH}"
conda activate "${_WORLD_MODEL_ROOT}/.conda/envs/WorldModel"
export GH_CONFIG_DIR="${CONDA_PREFIX}/.gh"

unset _CONDA_SH
unset _WORLD_MODEL_ROOT
