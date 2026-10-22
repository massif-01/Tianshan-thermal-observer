#!/bin/bash

# Build script for tegrastats-api wheel package
# Author: Thomas Hiddenpeak
# Description: 自动构建和打包tegrastats-api项目

set -e  # 出错时退出

echo "🚀 开始构建 tegrastats-api wheel 包..."

# 清理之前的构建
if [ -d "dist" ]; then
    echo "🧹 清理之前的构建文件..."
    rm -rf dist/
fi

if [ -d "build" ]; then
    echo "🧹 清理构建目录..."
    rm -rf build/
fi

# 检查构建工具
echo "🔍 检查构建工具..."
if ! python -c "import build" 2>/dev/null; then
    echo "📦 安装构建工具..."
    pip install build
fi

# 构建项目
echo "🔨 构建源码包和wheel包..."
python -m build

# 显示构建结果
echo ""
echo "✅ 构建完成！生成的包："
ls -la dist/

echo ""
echo "📦 包信息："
for file in dist/*.whl; do
    if [ -f "$file" ]; then
        echo "Wheel包: $(basename "$file")"
        python -m zipfile -l "$file" | head -20
    fi
done

echo ""
echo "🎯 安装测试："
echo "  pip install dist/$(ls dist/*.whl | head -1 | xargs basename)"
echo ""
echo "🚀 发布到PyPI："
echo "  pip install twine"
echo "  twine upload dist/*"
echo ""
echo "📋 本地测试安装："
echo "  pip uninstall tegrastats-api -y"
echo "  pip install dist/$(ls dist/*.whl | head -1 | xargs basename)"
echo "  tegrastats-api --help"

echo ""
echo "🎉 构建流程完成！"