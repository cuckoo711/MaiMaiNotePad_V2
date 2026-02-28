#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# 麦麦笔记本 · 用户前端启动脚本
#
# 用法:
#   bash start_user_web.sh              # 开发模式（默认）
#   bash start_user_web.sh --build      # 生产构建
#   bash start_user_web.sh --preview    # 构建后预览
#   bash start_user_web.sh --help       # 显示帮助

set -euo pipefail

# ==================== 常量 ====================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/mai_f_old"
PROJECT_NAME="用户前端"
NODE_MIN_VERSION="16"

# ==================== 输出工具 ====================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "  ${CYAN}ℹ${NC} $1"; }
success() { echo -e "  ${GREEN}✓${NC} $1"; }
warn()    { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()     { echo -e "  ${RED}✗${NC} $1" >&2; exit 1; }

# ==================== 帮助 ====================

show_help() {
    cat << 'EOF'
麦麦笔记本 · 用户前端启动脚本

用法:
    bash start_user_web.sh [选项]

选项:
    --dev         开发模式，热重载（默认）
    --build       生产环境构建
    --preview     先构建再预览
    --help        显示此帮助信息

说明:
    开发模式默认端口 5173，构建产物输出到 mai_f_old/dist/
EOF
    exit 0
}

# ==================== 环境检测 ====================

version_major_ge() {
    local current="$1"
    local required="$2"
    local current_major="${current%%.*}"
    [[ "$current_major" -ge "$required" ]]
}

check_node() {
    if ! command -v node &>/dev/null; then
        err "未找到 Node.js，请先安装:\n  推荐使用 nvm: https://github.com/nvm-sh/nvm\n  或直接下载: https://nodejs.org/"
    fi

    local node_ver
    node_ver="$(node --version | sed 's/^v//')"

    if ! version_major_ge "$node_ver" "$NODE_MIN_VERSION"; then
        err "Node.js 版本过低: v$node_ver（需要 >= v$NODE_MIN_VERSION）\n  请升级: nvm install --lts"
    fi

    success "Node.js v$node_ver"
}

check_deps() {
    if [[ ! -d "$PROJECT_DIR/node_modules" ]]; then
        warn "未检测到 node_modules，正在安装依赖..."
        npm install --prefix "$PROJECT_DIR"
        success "依赖安装完成"
    else
        success "依赖已就绪"
    fi
}

# ==================== 主流程 ====================

main() {
    local mode="dev"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dev)     mode="dev" ;;
            --build)   mode="build" ;;
            --preview) mode="preview" ;;
            --help|-h) show_help ;;
            *) warn "未知参数: $1" ;;
        esac
        shift
    done

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════╗"
    echo -e "║          麦麦笔记本 · ${PROJECT_NAME}                ║"
    echo -e "╚══════════════════════════════════════════════════╝${NC}"
    echo ""

    check_node
    check_deps

    echo ""
    case "$mode" in
        dev)
            info "启动开发服务器..."
            echo -e "  访问地址: ${GREEN}http://localhost:5173${NC}"
            echo -e "  按 ${YELLOW}Ctrl+C${NC} 停止"
            echo ""
            npm run dev --prefix "$PROJECT_DIR"
            ;;
        build)
            info "执行生产环境构建..."
            npm run build --prefix "$PROJECT_DIR"
            success "构建完成，产物目录: mai_f_old/dist/"
            ;;
        preview)
            info "执行生产构建 + 预览..."
            npm run build --prefix "$PROJECT_DIR"
            success "构建完成，启动预览服务器..."
            npm run preview --prefix "$PROJECT_DIR"
            ;;
    esac
}

main "$@"
