#!/bin/sh
# Builds dist/Storylines-<version>.zip: only the addon files, inside a "Storylines" folder,
# ready to unzip into Interface/AddOns. The version is read from Storylines.toc.
set -e
cd "$(dirname "$0")/.."
version=$(sed -n 's/^## Version: *//p' Storylines.toc | tr -d '\r')
mkdir -p dist
out="dist/Storylines-$version.zip"
rm -f "$out"
# Files the .toc loads, plus the readme. Uses committed content only (git archive).
files="Storylines.toc README.md $(grep -v '^#' Storylines.toc | grep -v '^[[:space:]]*$' | tr '\\' '/' | tr -d '\r')"
git archive --format=zip --prefix=Storylines/ -o "$out" HEAD $files
echo "Built $out"
