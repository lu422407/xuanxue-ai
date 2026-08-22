#!/bin/bash
set -e

echo "=== 术数 AI 引擎：初始化 GitHub 子模块 ==="
cd "$(dirname "$0")/.."

# 注意：蓝图中的 wlhyl/bifafu 与 cheekhan/curved-array 已失效（404），
# 已替换为可用的 dalurenpython 与 daliuren-web-engine。
add_submodule() {
    local url=$1
    local path=$2
    if [ ! -d "$path/.git" ]; then
        echo "添加子模块: $path"
        git submodule add "$url" "$path" 2>/dev/null || true
    else
        echo "已存在: $path"
    fi
}

add_submodule https://github.com/SylarLong/iztro.git third_party/iztro
add_submodule https://github.com/x-haose/py-iztro.git third_party/py-iztro
add_submodule https://github.com/Renhuai123/ziwei-doushu.git third_party/ziwei-doushu
add_submodule https://github.com/Bald0Wang/DeepSeek-Oracle.git third_party/DeepSeek-Oracle
add_submodule https://github.com/dglijin-oss/chinese-metaphysics-skills.git third_party/chinese-metaphysics-skills
add_submodule https://github.com/lu422407/ZhouYiLab.git third_party/ZhouYiLab
add_submodule https://github.com/wlhyl/dalurenpython.git third_party/dalurenpython
add_submodule https://github.com/d1210182010/daliuren-web-engine.git third_party/daliuren-web-engine

echo "=== 初始化子模块 ==="
git submodule update --init --recursive

echo "=== 安装 Python 依赖 ==="
python -m pip install -r requirements.txt

if [ -d "third_party/py-iztro" ]; then
    python -m pip install -e third_party/py-iztro || python -m pip install py-iztro
fi

echo "=== 复制知识库文件 ==="
mkdir -p knowledge/liuren
if [ -f "third_party/chinese-metaphysics-skills/liuren-skill/SKILL.md" ]; then
    cp third_party/chinese-metaphysics-skills/liuren-skill/SKILL.md knowledge/liuren/
    echo "OK 已复制六壬 SKILL.md"
fi

mkdir -p prompts/oracle_reference
if [ -d "third_party/DeepSeek-Oracle" ]; then
    find third_party/DeepSeek-Oracle -type f \( -name "*.md" -o -name "*.txt" \) | \
        grep -i prompt | head -20 | while read f; do
        cp "$f" prompts/oracle_reference/ 2>/dev/null || true
    done
    echo "OK 已复制 DeepSeek-Oracle prompts"
fi

mkdir -p knowledge/ziwei/classical
if [ -d "third_party/ziwei-doushu" ]; then
    find third_party/ziwei-doushu -type f \( -name "*.md" -o -name "*.txt" \) | \
        grep -iE "古典|classical|古籍|原文|古本" | head -20 | while read f; do
        cp "$f" knowledge/ziwei/classical/ 2>/dev/null || true
    done
    echo "OK 已复制 ziwei-doushu 古籍"
fi

echo "=== 检查 ZhouYiLab 编译环境 ==="
if [ "$(uname -s)" = "Darwin" ]; then
    # macOS：ZhouYiLab 强依赖 libc++ 的 std 模块，必须用 Homebrew LLVM 的 clang，
    # 不能用 GCC 或 Apple Clang（见 HANDOVER.md §4.1）
    if [ "$(uname -m)" = "arm64" ] && [ -d /opt/homebrew/opt/llvm ]; then
        LLVM_DIR=/opt/homebrew/opt/llvm
    elif [ -d /usr/local/opt/llvm ]; then
        LLVM_DIR=/usr/local/opt/llvm
    else
        LLVM_DIR=""
        echo "WARN 未找到 Homebrew LLVM（brew install llvm），跳过 ZhouYiLab 编译"
    fi
    if [ -n "$LLVM_DIR" ]; then
        echo "使用 LLVM: $LLVM_DIR，编译 example_zhouyi_cli（奇门/六爻引擎依赖）"
        (cd third_party/ZhouYiLab && \
            CC="$LLVM_DIR/bin/clang" CXX="$LLVM_DIR/bin/clang++" \
            cmake -B build_llvm -G Ninja \
                -DCMAKE_C_COMPILER="$LLVM_DIR/bin/clang" \
                -DCMAKE_CXX_COMPILER="$LLVM_DIR/bin/clang++" \
                -DBUILD_EXAMPLES=ON \
                -DZHOUYILAB_MODULE_MODE=LOCAL \
                -DCMAKE_BUILD_TYPE=Release && \
            cmake --build build_llvm --target example_zhouyi_cli) \
            || echo "WARN ZhouYiLab 编译失败，奇门/六爻引擎将不可用（其余功能不受影响）"
    fi
elif command -v g++ &> /dev/null; then
    GCC_VERSION=$(g++ --version | head -1)
    echo "GCC: $GCC_VERSION"
    if echo "$GCC_VERSION" | grep -qE "1[4-9]|2[0-9]"; then
        echo "OK GCC 版本支持 C++23"
    else
        echo "WARN GCC 版本可能不支持 C++23，需要 14+"
    fi
else
    echo "WARN 未找到 g++/clang，ZhouYiLab 需要手动编译（Windows 建议用 MSYS2/LLVM，见 docs/ZHOUEYILAB_BUILD_GUIDE.md）"
fi

echo ""
echo "=== 初始化完成 ==="
echo "下一步:"
echo "1. 若上一步未编译 ZhouYiLab: 参考 docs/ZHOUEYILAB_BUILD_GUIDE.md 编译 example_zhouyi_cli"
echo "2. 测试: python -m pytest tests/ -q"