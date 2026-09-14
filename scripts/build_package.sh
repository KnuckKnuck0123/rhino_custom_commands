#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
rhino_code="/Applications/Rhino 8.app/Contents/Resources/bin/rhinocode"
yak_cli="/Applications/Rhino 8.app/Contents/Resources/bin/yak"
build_root="${1:-$project_root/build/package}"
artifact_dir="$build_root/rh8"

"$rhino_code" project build "$project_root/ArrayStudio.rhproj" \
  --buildversion 0.9.0 --buildtarget '8.*' --buildpath "$build_root"

find "$artifact_dir" -maxdepth 1 -name '*.yak' -delete
if [ -d "$artifact_dir/src" ]; then
  find "$artifact_dir/src" -depth -delete
fi
cp "$project_root/package/manifest.yml" "$artifact_dir/manifest.yml"
cp "$project_root/package/icon.png" "$artifact_dir/icon.png"
cp "$project_root/LICENSE" "$artifact_dir/LICENSE"
cp "$project_root/README.md" "$artifact_dir/README.md"

(cd "$artifact_dir" && "$yak_cli" build --platform any)
