#!/bin/bash
# tac-check-team-status-expiry.sh
# 扫描 persistent-assets/governance/team-status.md 中的失效日期，列出过期 / 7 天内即将过期条目
# 输入:
#   $1 (可选): team-status 文件路径，默认 <repo-root>/persistent-assets/governance/team-status.md
# 选项:
#   --session-banner   以"会话开始横幅"格式输出（紧凑），适合 SessionStart hook 注入
#   --strict           有过期条目时退出码 1，适合 pre-commit hook 阻断
# 输出:
#   stdout：分类列出过期 / 即将过期条目
# 退出码:
#   0 = 无过期（或非 strict 模式）
#   1 = strict 模式下有过期条目
# 调用方式: 手动 / SessionStart hook / pre-commit hook
# 所在环节: 跨环节，团队协作

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET=""
SESSION_BANNER=0
STRICT=0

# 解析参数
for arg in "$@"; do
  case "$arg" in
    --session-banner) SESSION_BANNER=1 ;;
    --strict)         STRICT=1 ;;
    -*)               echo "未知选项: $arg" >&2; exit 2 ;;
    *)                TARGET="$arg" ;;
  esac
done

[ -z "$TARGET" ] && TARGET="$PROJECT_ROOT/persistent-assets/governance/team-status.md"

if [ ! -f "$TARGET" ]; then
  if [ "$SESSION_BANNER" -eq 1 ]; then
    # SessionStart 模式下文件不存在不报错，静默返回
    exit 0
  fi
  echo "未找到团队状态文件: $TARGET" >&2
  exit 0
fi

TODAY=$(date +%Y-%m-%d)

# 提取所有条目（行首为 "- [失效 YYYY-MM-DD｜...]"）
# 注意："｜" 是全角竖线 U+FF5C
EXPIRED=()
UPCOMING=()
ACTIVE=()
TOTAL=0

# 当前正在扫描的分类（## 标题）
current_section=""

while IFS= read -r line; do
  # 识别分类标题
  if [[ "$line" =~ ^##[[:space:]]+(模块阶段|接口迁移|发布节奏|其他) ]]; then
    current_section="${BASH_REMATCH[1]}"
    continue
  fi
  # 识别条目（含失效日期）
  if [[ "$line" =~ ^-[[:space:]]\[失效[[:space:]]+([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
    expire_date="${BASH_REMATCH[1]}"
    TOTAL=$((TOTAL + 1))
    entry="[$current_section] $line"

    if [[ "$expire_date" < "$TODAY" ]] || [[ "$expire_date" == "$TODAY" ]]; then
      EXPIRED+=("$entry")
    else
      # 计算距今天数
      if command -v python3 &>/dev/null; then
        days_left=$(python3 -c "
from datetime import datetime
d1 = datetime.strptime('$TODAY', '%Y-%m-%d')
d2 = datetime.strptime('$expire_date', '%Y-%m-%d')
print((d2-d1).days)
" 2>/dev/null)
        if [ -n "$days_left" ] && [ "$days_left" -le 7 ]; then
          UPCOMING+=("[$days_left 天后过期] $entry")
        else
          ACTIVE+=("$entry")
        fi
      else
        ACTIVE+=("$entry")
      fi
    fi
  fi
done < "$TARGET"

# 输出
if [ "$SESSION_BANNER" -eq 1 ]; then
  # 紧凑横幅模式
  if [ "$TOTAL" -eq 0 ]; then
    exit 0
  fi
  printf "=== 团队当前状态（%s）===\n" "$TARGET"
  for e in "${ACTIVE[@]}"; do echo "  $e"; done
  for e in "${UPCOMING[@]}"; do echo "  ⚠️ $e"; done
  if [ "${#EXPIRED[@]}" -gt 0 ]; then
    echo ""
    echo "❌ 已过期，请清理:"
    for e in "${EXPIRED[@]}"; do echo "  $e"; done
  fi
  echo ""
else
  # 详细模式
  printf "团队状态过期检查（%s）：扫描文件 %s，共 %s 条\n" "$TODAY" "$TARGET" "$TOTAL"
  echo ""

  if [ "${#EXPIRED[@]}" -gt 0 ]; then
    echo "❌ 已过期（${#EXPIRED[@]} 条，需清理或更新）:"
    for e in "${EXPIRED[@]}"; do echo "  $e"; done
    echo ""
  fi

  if [ "${#UPCOMING[@]}" -gt 0 ]; then
    echo "⚠️ 即将过期（${#UPCOMING[@]} 条，7 天内）:"
    for e in "${UPCOMING[@]}"; do echo "  $e"; done
    echo ""
  fi

  if [ "${#ACTIVE[@]}" -gt 0 ]; then
    echo "✅ 活跃条目（${#ACTIVE[@]} 条）:"
    for e in "${ACTIVE[@]}"; do echo "  $e"; done
    echo ""
  fi

  if [ "${#EXPIRED[@]}" -eq 0 ] && [ "${#UPCOMING[@]}" -eq 0 ]; then
    echo "无过期或即将过期条目"
  fi
fi

# 退出码
if [ "$STRICT" -eq 1 ] && [ "${#EXPIRED[@]}" -gt 0 ]; then
  exit 1
fi
exit 0
