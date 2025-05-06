#!/usr/bin/env bash

# adr_init.sh - 创建新的架构决策记录(ADR)文件
# 用法: ./tools/adr_init.sh "决策标题"

set -e

# 检查参数
if [ "$#" -lt 1 ]; then
    echo "错误: 缺少决策标题"
    echo "用法: $0 \"决策标题\""
    exit 1
fi

# 变量定义
TITLE="$1"
DATE=$(date +"%Y%m%d")
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | sed 's/[^a-z0-9_]//g')
FILENAME="${DATE}_${SLUG}.md"
ADR_DIR=".cursor/adr"
ADR_PATH="${ADR_DIR}/${FILENAME}"

# 计算ADR编号 (基于现有ADR文件数量)
ADR_COUNT=$(find "$ADR_DIR" -name "*.md" -not -name "README.md" | wc -l)
ADR_NUMBER=$(printf "%04d" $((ADR_COUNT + 1)))

# 创建ADR文件
cat > "$ADR_PATH" << EOF
# ADR-${ADR_NUMBER}: ${TITLE}

## 状态
提议

## 背景
<!-- 描述问题和上下文 -->

## 决策
<!-- 描述所做的决定 -->

## 后果
<!-- 描述决策带来的影响、风险和机会 -->

## 相关循环
<!-- 关联的Plan-Execute循环编号和PR链接 -->
EOF

echo "✅ 已创建新的ADR: ${ADR_PATH}"

# 如果存在当前循环的plan_request.md文件，尝试更新ADR链接
LATEST_PLAN_REQUEST=$(ls -t .scratchpad_logs/*_plan_request.md 2>/dev/null | head -n 1)
if [[ -n "$LATEST_PLAN_REQUEST" && -f "$LATEST_PLAN_REQUEST" ]]; then
    # 检查是否已有ADR链接字段
    if grep -q "\[🔖 ADR LINK\]" "$LATEST_PLAN_REQUEST"; then
        # 更新ADR链接
        sed -i '' "s|\[🔖 ADR LINK\].*|\[🔖 ADR LINK\]     ${ADR_PATH}|" "$LATEST_PLAN_REQUEST"
        echo "✅ 已更新当前Plan-Execute循环的ADR链接: ${LATEST_PLAN_REQUEST}"
    else
        echo "⚠️ 未在当前Plan-Execute循环文件中找到ADR链接字段"
        echo "  建议手动添加: [🔖 ADR LINK]     ${ADR_PATH}"
    fi
fi

# 提示后续步骤
echo ""
echo "请继续编辑ADR文件，填写相关内容："
echo "1. 背景 - 为什么需要做这个决策？"
echo "2. 决策 - 具体选择了什么方案？"
echo "3. 后果 - 这个决策会带来什么影响？"
echo ""
echo "完成后，记得更新ADR的状态为'已接受'并提交变更。" 