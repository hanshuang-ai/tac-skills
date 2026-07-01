#!/bin/bash
# check-commit-format.sh
# 校验八字段提交格式完整性
# 输入: commit message 文件路径（$1）或从最近提交读取
# 输出: stdout（校验结果）
# 退出码: 0=通过, 1=格式错误
# 调用方式: Hook PreCommit / commit-msg
# 所在环节: ⑥ 验证与提交

# 获取 commit message
if [ -n "$1" ] && [ -f "$1" ]; then
  MSG=$(cat "$1")
elif [ -n "$1" ]; then
  MSG="$1"
else
  MSG=$(git log -1 --pretty=%B 2>/dev/null)
  if [ -z "$MSG" ]; then
    echo "Usage: $0 <commit-msg-file> 或 $0 <commit-message-string>"
    exit 1
  fi
fi

ERRORS=""

# ── 检查必填字段存在性 ──
REQUIRED_FIELDS="Type IssueId Project Description Aoe RelatedModules TestScope AiCodeReview"

for FIELD in $REQUIRED_FIELDS; do
  if ! echo "$MSG" | grep -q "${FIELD}="; then
    ERRORS="$ERRORS\n  - 缺少必填字段: ${FIELD}"
  fi
done

# ── 检查 Type 取值 ──
TYPE_VALUE=$(echo "$MSG" | grep -oE 'Type=[^ ]+' | head -1 | sed 's/Type=//')
if [ -n "$TYPE_VALUE" ]; then
  case "$TYPE_VALUE" in
    需求|BUG|其他) ;;
    *) ERRORS="$ERRORS\n  - Type 取值无效: '$TYPE_VALUE'（只允许 需求/BUG/其他）" ;;
  esac
fi

# ── 检查字段最小长度 ──
RELATED_MODULES=$(echo "$MSG" | grep -oE 'RelatedModules=[^ ]+' | head -1 | sed 's/RelatedModules=//')
if [ -n "$RELATED_MODULES" ] && [ ${#RELATED_MODULES} -lt 2 ]; then
  ERRORS="$ERRORS\n  - RelatedModules 不少于 2 个字符，当前: '$RELATED_MODULES'"
fi

TEST_SCOPE=$(echo "$MSG" | sed -n 's/.*TestScope=\(.*\)/\1/p' | head -1 | sed 's/ AiCodeReview=.*//')
if [ -n "$TEST_SCOPE" ] && [ ${#TEST_SCOPE} -lt 15 ]; then
  ERRORS="$ERRORS\n  - TestScope 不少于 15 个字符，当前 ${#TEST_SCOPE} 个: '$TEST_SCOPE'"
fi

AI_REVIEW=$(echo "$MSG" | sed -n 's/.*AiCodeReview=\(.*\)/\1/p' | head -1)
if [ -n "$AI_REVIEW" ] && [ ${#AI_REVIEW} -lt 10 ]; then
  ERRORS="$ERRORS\n  - AiCodeReview 不少于 10 个字符，当前 ${#AI_REVIEW} 个: '$AI_REVIEW'"
fi

# ── 检查字段之间是否有空行（Gerrit 解析会出错）──
# 提取从 Type= 到 AiCodeReview= 之间的内容
FIELD_BLOCK=$(echo "$MSG" | sed -n '/^Type=/,/AiCodeReview=/p')
if echo "$FIELD_BLOCK" | grep -q '^$'; then
  ERRORS="$ERRORS\n  - 八字段之间存在空行，Gerrit 会解析错位（字段必须连续书写）"
fi

# 输出结果
if [ -z "$ERRORS" ]; then
  echo "提交格式检查通过"
  exit 0
else
  echo "提交格式检查失败:"
  echo -e "$ERRORS"
  echo ""
  echo "参考格式："
  echo "Type=<类型> IssueId=<ID> Project=<项目> Description=<描述>"
  echo "Aoe=<影响范围> RelatedModules=<关联模块> TestScope=<测试范围>"
  echo "AiCodeReview=<AI审查摘要>"
  exit 1
fi
