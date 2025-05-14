#!/bin/bash
# ADR初始化脚本 - 创建新的架构决策记录

set -e

# 检查参数
if [ $# -lt 1 ]; then
  echo "用法: $0 \"ADR标题\""
  echo "例如: $0 \"使用OpenHands适配器替代Agent S实现恢复机制\""
  exit 1
fi

# 获取ADR标题
ADR_TITLE="$1"

# 创建日期格式
DATE=$(date +"%Y%m%d")
FULL_DATE=$(date +"%Y-%m-%d")

# 格式化标题作为文件名
FILENAME=$(echo "$ADR_TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -d ',:;?!@#$%^&*()+={}[]|\\"'"'"'/<>')
ADR_FILENAME="${DATE}_${FILENAME}.md"

# ADR目录
ADR_DIR=".cursor/adr"
mkdir -p "$ADR_DIR"

# 检查文件是否已存在
if [ -f "$ADR_DIR/$ADR_FILENAME" ]; then
  echo "错误: ADR文件 '$ADR_DIR/$ADR_FILENAME' 已存在！"
  exit 1
fi

# 创建ADR文件
cat > "$ADR_DIR/$ADR_FILENAME" << EOF
# ${ADR_TITLE}

## 状态

提议 (${FULL_DATE})

## 背景

[描述为什么需要做这个决策。包括相关上下文和问题陈述。]

## 决策

[描述所选方案及其细节。]

## 替代方案

[描述考虑过的其他方案及其优缺点。]

## 后果

- [列出正面后果]
- [列出负面后果或风险]

## 相关循环

- 循环编号: [关联的Plan-Execute循环编号]
- PR链接: [关联的PR链接]

## 参考

- [相关文档链接]
- [研究资料链接]
EOF

# 添加执行权限
chmod +x "$ADR_DIR/$ADR_FILENAME"

echo "成功创建ADR: $ADR_DIR/$ADR_FILENAME"

# 尝试更新当前循环的plan_request.md文件
if [ -d ".scratchpad_logs" ]; then
  echo "正在寻找最新的plan_request.md文件..."
  LATEST_PLAN_REQUEST=$(find .scratchpad_logs -name "*_plan_request.md" -type f | sort -r | head -n 1)
  
  if [ -n "$LATEST_PLAN_REQUEST" ]; then
    echo "找到最新的plan_request.md文件: $LATEST_PLAN_REQUEST"
    
    if grep -q "\[🔖 ADR LINK\]" "$LATEST_PLAN_REQUEST"; then
      # 更新ADR链接
      sed -i '' "s|\[🔖 ADR LINK\].*|\[🔖 ADR LINK\] $ADR_DIR/$ADR_FILENAME|" "$LATEST_PLAN_REQUEST"
      echo "✅ 已更新当前Plan-Execute循环的ADR链接: $LATEST_PLAN_REQUEST"
    else
      echo "⚠️ 未在当前Plan-Execute循环文件中找到ADR链接字段"
      echo "  建议手动添加: [🔖 ADR LINK] $ADR_DIR/$ADR_FILENAME"
    fi
  else
    echo "⚠️ 未找到plan_request.md文件"
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