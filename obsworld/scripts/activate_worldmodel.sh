#!/usr/bin/env bash
# Source this file from bash: source scripts/activate_worldmodel.sh
#
# The env prefix (.conda/envs/WorldModel) travels intact with the repo; only the
# conda *base* used to run `conda activate` differs per machine. We auto-detect it
# from a candidate list so the script works after migration without editing.
# Override explicitly with: WORLDMODEL_CONDA_SH=/path/to/etc/profile.d/conda.sh

_WORLD_MODEL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

_CONDA_CANDIDATES=(
  "${WORLDMODEL_CONDA_SH:-}"                                        # explicit override
  "/mnt/data/public_tools/miniconda3/etc/profile.d/conda.sh"       # current node (public base)
  "/root/nas/users/luzheng/workspace/enter/etc/profile.d/conda.sh" # original node
)
if command -v conda >/dev/null 2>&1; then                          # already-initialized conda
  _CONDA_CANDIDATES+=("$(conda info --base 2>/dev/null)/etc/profile.d/conda.sh")
fi

_CONDA_SH=""
for _c in "${_CONDA_CANDIDATES[@]}"; do
  if [[ -n "${_c}" && -f "${_c}" ]]; then _CONDA_SH="${_c}"; break; fi
done

if [[ -z "${_CONDA_SH}" ]]; then
  echo "WorldModel: no conda.sh found. Set WORLDMODEL_CONDA_SH=/path/to/etc/profile.d/conda.sh" >&2
  return 1
fi

source "${_CONDA_SH}"
conda activate "${_WORLD_MODEL_ROOT}/.conda/envs/WorldModel" || return 1
export GH_CONFIG_DIR="${CONDA_PREFIX}/.gh"

unset _CONDA_SH _WORLD_MODEL_ROOT _CONDA_CANDIDATES _c
