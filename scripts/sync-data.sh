#!/bin/bash
# 把 GitHub Actions 采集的数据同步回本地。
#
# 数据存在仓库的 data 分支（master 只有代码，.gitignore 也排除了 output/*.db）。
#
# 同步语义：
#   - tar 解包是「覆盖同名文件、保留多余文件」，本地独有数据不会丢
#   - 但同一天同一文件，云端版本会覆盖本地版本 → 同步前自动备份
#   - 加 --dry-run 可以先看会发生什么，不实际改动
#   - 加 --no-backup 跳过备份（省空间）
#
# 同步内容：
#   output/news/*.db      按天分库的热点新闻
#   output/rss/*.db       按天分库的 RSS
#   output/memory.db      长期记忆
#   output/ai_analysis.db AI 分析结果
#
# 用法：
#   bash scripts/sync-data.sh              # 同步
#   bash scripts/sync-data.sh --dry-run    # 只看差异
#   bash scripts/sync-data.sh --no-backup  # 不备份

set -uo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT" || exit 1

DRY_RUN=false
DO_BACKUP=true
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --no-backup) DO_BACKUP=false ;;
  esac
done

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "✗ 当前目录不是 git 仓库"
  exit 1
fi

# 要同步的路径（相对仓库根）
SYNC_PATHS="output/news output/rss output/memory.db output/ai_analysis.db"

# ---- 带重试的 git 操作 ----
# 网络偶发抖动时自动退避重试，不必人工介入。
git_retry() {
  local desc="$1"; shift
  local attempt=1
  local max=4
  while [ "$attempt" -le "$max" ]; do
    if "$@" 2>/tmp/git-retry-err; then
      return 0
    fi
    local err
    err=$(tail -1 /tmp/git-retry-err 2>/dev/null | tr -d '\r')
    if [ "$attempt" -lt "$max" ]; then
      local wait=$((attempt * 5))
      echo "  ⟳ $desc 失败（${err:0:60}），${wait}s 后重试 $attempt/$max"
      sleep "$wait"
    else
      echo "  ✗ $desc 失败 $max 次：${err:0:120}"
      return 1
    fi
    attempt=$((attempt + 1))
  done
}

# ---- 代理自动探测 ----
# 本机直连 GitHub 经常超时（实测 <1000 bytes/sec 后断开），
# 但 launchd 定时任务不会继承终端里的代理环境变量，所以在脚本里自己探。
# 只在本地端口确实开着时才用，探不到就直连，不硬编码假设。
if [ -z "${https_proxy:-}" ] && [ -z "${HTTPS_PROXY:-}" ]; then
  for port in 7897 7890 1087 1080 8080; do
    if nc -z -G 1 127.0.0.1 "$port" 2>/dev/null; then
      export https_proxy="http://127.0.0.1:$port"
      export http_proxy="http://127.0.0.1:$port"
      echo "  使用本地代理 127.0.0.1:$port"
      break
    fi
  done
fi

echo "→ 检查 data 分支是否存在…"
# 先探测远端有没有 data 分支：没建立时不必重试 4 次白等 30 秒
if ! git ls-remote --exit-code --heads origin data >/dev/null 2>&1; then
  echo "  ○ 远端还没有 data 分支"
  echo "    需要先在 crawler.yml 里启用「发布到 data 分支」这一步，跑一次云端采集后才会出现。"
  echo "    本地数据未做任何改动。"
  exit 0
fi

echo "→ 拉取 data 分支…"
if ! git_retry "拉取 data 分支" git fetch --depth=1 origin data; then
  echo "✗ 拉取失败（分支存在但拉不下来，多半是网络问题）"
  echo "  检查：git ls-remote --heads origin"
  exit 1
fi

REMOTE_SHA=$(git rev-parse FETCH_HEAD)
LOCAL_MARK=".sync-state"
echo "  data 分支版本: ${REMOTE_SHA:0:8}"
if [ -f "$LOCAL_MARK" ] && [ "$(cat "$LOCAL_MARK")" = "$REMOTE_SHA" ]; then
  echo "  ○ 已是最新，无需同步"
  exit 0
fi

# ---- 差异预览 ----
echo
echo "→ 差异预览…"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git archive FETCH_HEAD | tar -x -C "$TMP"

CHANGED=0
NEW=0
for p in $SYNC_PATHS; do
  [ -e "$TMP/$p" ] || continue
  if [ -d "$TMP/$p" ]; then
    while IFS= read -r f; do
      rel="${f#$TMP/}"
      if [ ! -f "$rel" ]; then
        NEW=$((NEW + 1))
      elif ! cmp -s "$f" "$rel"; then
        CHANGED=$((CHANGED + 1))
      fi
    done < <(find "$TMP/$p" -type f 2>/dev/null)
  else
    rel="${p}"
    if [ ! -f "$TMP/$rel" ]; then
      :
    elif [ ! -f "$rel" ]; then
      NEW=$((NEW + 1))
    elif ! cmp -s "$TMP/$rel" "$rel"; then
      CHANGED=$((CHANGED + 1))
    fi
  fi
done

echo "  新增文件: $NEW"
echo "  内容变化: $CHANGED"
echo "  本地独有: 保留不动"

if [ "$NEW" -eq 0 ] && [ "$CHANGED" -eq 0 ]; then
  echo "  ○ 没有实际变化"
  [ "$DRY_RUN" = false ] && echo "$REMOTE_SHA" > "$LOCAL_MARK"
  exit 0
fi

if [ "$DRY_RUN" = true ]; then
  echo
  echo "（--dry-run，未做任何改动）"
  exit 0
fi

# ---- 备份 ----
if [ "$DO_BACKUP" = true ] && [ -d output ]; then
  STAMP=$(date '+%Y%m%d-%H%M%S')
  BACKUP="$PROJECT/output-backup-$STAMP"
  mkdir -p "$BACKUP"
  for p in $SYNC_PATHS; do
    if [ -e "$p" ]; then
      mkdir -p "$BACKUP/$(dirname "$p")"
      cp -R "$p" "$BACKUP/$p" 2>/dev/null
    fi
  done
  echo
  echo "→ 已备份到 $BACKUP"
  echo "  确认没问题后可以删：rm -rf $BACKUP"
fi

# ---- 应用 ----
echo
echo "→ 解包…"
git archive FETCH_HEAD | tar -x -C .
echo "$REMOTE_SHA" > "$LOCAL_MARK"

echo
echo "✓ 同步完成"
du -sh output/news output/rss output/memory.db output/ai_analysis.db 2>/dev/null | sed 's/^/  /'
echo
echo "最近 7 天新增的日库："
find output/news output/rss -name '*.db' -newermt '-7 days' 2>/dev/null | sort | tail -10 | sed 's/^/  /'
