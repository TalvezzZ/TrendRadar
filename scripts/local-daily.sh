#!/bin/bash
# 本地每日同步：把云端 data 分支的数据拉回本地。
#
# 设计参照 LocaleLens/scripts/local-daily.sh：
#   - 幂等，失败不影响已完成部分
#   - 串成一条：拉取 → 校验 → 记录状态
#   - 日志只留最近 2000 行
#
# 与 LocaleLens 的差别：
#   LocaleLens 还要在本地采统计局（境外 runner 访问不了政府站）；
#   TrendRadar 的采集全在云端，本地只做单向拉取，所以更简单。
#
# 由 launchd 每天定时调用（见 com.trendradar.sync.plist）。

set -uo pipefail

PROJECT="/Users/zhouxinping/PycharmProjects/TrendRadar"
cd "$PROJECT" || exit 1

# launchd 环境的 PATH 很干净，必须显式补上
export PATH="/Users/zhouxinping/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p logs
LOG="logs/local-sync.log"

{
  echo "================================================================"
  echo "TrendRadar 本地同步开始：$(date '+%Y-%m-%d %H:%M:%S %z')"
  echo "================================================================"

  echo
  echo "[1/2] 拉取云端数据"
  if bash scripts/sync-data.sh 2>&1; then
    echo "  ✓ 拉取完成"
  else
    echo "  ✗ 拉取失败（本地已有数据未受影响，下轮重试）"
  fi

  echo
  echo "[2/2] 数据概况"
  NEWS_COUNT=$(find output/news -name '*.db' 2>/dev/null | wc -l | tr -d ' ')
  RSS_COUNT=$(find output/rss -name '*.db' 2>/dev/null | wc -l | tr -d ' ')
  echo "  news 日库: $NEWS_COUNT 个"
  echo "  rss  日库: $RSS_COUNT 个"
  LATEST=$(find output/news -name '*.db' 2>/dev/null | sort | tail -1 | sed 's|.*/||;s|\.db||')
  echo "  最新一天: ${LATEST:-（无）}"

  echo
  echo "结束：$(date '+%Y-%m-%d %H:%M:%S %z')"
  echo
} >> "$LOG" 2>&1

# 日志只留最近 2000 行
if [ -f "$LOG" ]; then
  LINES=$(wc -l < "$LOG" | tr -d ' ')
  if [ "$LINES" -gt 2000 ]; then
    tail -1500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  fi
fi
