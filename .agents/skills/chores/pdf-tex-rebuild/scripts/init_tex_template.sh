#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <destination>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="${SCRIPT_DIR}/../assets/templates/single-column-bilingual"
DESTINATION="$1"

if [[ -e "${DESTINATION}" ]] && [[ -n "$(find "${DESTINATION}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
  echo "Destination is not empty: ${DESTINATION}" >&2
  exit 3
fi

mkdir -p "${DESTINATION}"
cp -a "${TEMPLATE_DIR}/." "${DESTINATION}/"
echo "Initialized bilingual single-column TeX template at ${DESTINATION}"
