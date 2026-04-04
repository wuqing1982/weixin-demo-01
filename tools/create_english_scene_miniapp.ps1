$root = '"'"'E:\202603\english-scene-miniapp'"'"'
$dirs = @(
  "$root\pages\home",
  "$root\pages\library",
  "$root\pages\scene_runtime",
  "$root\pages\create_scene",
  "$root\pages\task_center",
  "$root\pages\my_scenes",
  "$root\pages\profile",
  "$root\pages\login",
  "$root\pages\shared",
  "$root\services",
  "$root\utils"
)
$dirs | ForEach-Object { New-Item -ItemType Directory -Force $_ | Out-Null }
