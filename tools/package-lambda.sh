#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

mkdir -p "${DIST_DIR}"

cp "${ROOT_DIR}/lambda/app.py" "${TMP_DIR}/app.py"
cp "${ROOT_DIR}/lambda/page_generator.py" "${TMP_DIR}/page_generator.py"

# Normalize timestamps to make zip output deterministic.
TZ=UTC touch -t 200001010000 "${TMP_DIR}/app.py" "${TMP_DIR}/page_generator.py"

zip -X -j "${DIST_DIR}/lambda-api.zip" "${TMP_DIR}/app.py" > /dev/null
zip -X -j "${DIST_DIR}/lambda-page-generator.zip" "${TMP_DIR}/page_generator.py" > /dev/null

echo "Wrote:"
echo "  ${DIST_DIR}/lambda-api.zip"
echo "  ${DIST_DIR}/lambda-page-generator.zip"
