#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# 麦麦笔记本 · 后端一键启动脚本
#
# 用法:
#   bash start_backend.sh              # 日常启动
#   bash start_backend.sh --init       # 首次启动（含数据初始化）
#   bash start_backend.sh --reset      # 全量重置后启动
#   bash start_backend.sh --debug      # 调试模式（自动重载）
#   bash start_backend.sh --help       # 显示帮助

set -euo pipefail

# ==================== 常量 ====================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
CONDA_ENV="mai_notebook"
PYTHON_MIN_VERSION="3.10"
VENV_DIR="$BACKEND_DIR/.venv"
ENV_FILE="$BACKEND_DIR/conf/env.py"
DOCKER_COMPOSE_FILE="$BACKEND_DIR/docker-compose.yml"
REQUIREMENTS_FILE="$BACKEND_DIR/requirements.txt"

# Docker 容器名
PG_CONTAINER="mai_notebook_postgres"
REDIS_CONTAINER="mai_notebook_redis"

# 解析参数
FLAG_INIT=false
FLAG_RESET=false
FLAG_DEBUG=false
PYTHON_CMD=""
ENV_TYPE=""

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

header() {
    echo ""
    echo -e "${CYAN}=================================================="
    echo -e "  $1"
    echo -e "==================================================${NC}"
    echo ""
}

# ==================== 帮助信息 ====================

show_help() {
    cat << 'EOF'
麦麦笔记本 · 后端一键启动脚本

用法:
    bash start_backend.sh [选项]

选项:
    --init      首次启动：生成配置 + 数据库迁移 + 初始化数据
    --reset     全量重置：重置数据库/缓存 + 重新配置 + 重新初始化
    --debug     调试模式：启用自动重载（代码修改后自动重启）
    --help      显示此帮助信息

示例:
    bash start_backend.sh              # 日常启动（迁移 + 启动服务）
    bash start_backend.sh --init       # 第一次部署
    bash start_backend.sh --reset      # 全量重置（危险操作，会清空数据）
    bash start_backend.sh --debug      # 开发调试模式
EOF
    exit 0
}

# ==================== 参数解析 ====================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --init)   FLAG_INIT=true ;;
            --reset)  FLAG_RESET=true ;;
            --debug)  FLAG_DEBUG=true ;;
            --help|-h) show_help ;;
            *) warn "未知参数: $1" ;;
        esac
        shift
    done
}

# ==================== Python 环境检测 ====================

# 比较版本号: version_ge "3.11.2" "3.10" => true
version_ge() {
    # 如果 $1 >= $2 返回 0
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

find_conda() {
    # 检查 PATH 中的 conda
    if command -v conda &>/dev/null; then
        echo "conda"
        return
    fi
    # 常见安装路径
    local candidates=(
        "$HOME/miniconda3/condabin/conda"
        "$HOME/anaconda3/condabin/conda"
        "$HOME/miniforge3/condabin/conda"
        "/opt/homebrew/Caskroom/miniconda/base/condabin/conda"
    )
    for c in "${candidates[@]}"; do
        if [[ -x "$c" ]]; then
            echo "$c"
            return
        fi
    done
    return 1
}

setup_conda_env() {
    local conda_bin="$1"

    # 初始化 conda shell 集成
    eval "$("$conda_bin" shell.bash hook 2>/dev/null)" || {
        # 回退方案
        local conda_base
        conda_base="$("$conda_bin" info --base 2>/dev/null)"
        if [[ -f "$conda_base/etc/profile.d/conda.sh" ]]; then
            source "$conda_base/etc/profile.d/conda.sh"
        fi
    }

    # 检查环境是否存在
    if ! "$conda_bin" env list 2>/dev/null | grep -qw "$CONDA_ENV"; then
        warn "Conda 环境 '$CONDA_ENV' 不存在，正在创建..."
        "$conda_bin" create -n "$CONDA_ENV" "python>=${PYTHON_MIN_VERSION}" -y
        success "Conda 环境创建完成"
    fi

    # 激活环境
    conda activate "$CONDA_ENV" 2>/dev/null || {
        err "无法激活 Conda 环境 '$CONDA_ENV'"
    }

    PYTHON_CMD="$(which python)"
    ENV_TYPE="conda"
    local ver
    ver="$("$PYTHON_CMD" --version 2>&1 | awk '{print $2}')"
    success "Python 环境就绪: $ver (Conda: $CONDA_ENV)"
}

find_system_python() {
    # 查找版本达标的系统 Python
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver="$("$cmd" --version 2>&1 | awk '{print $2}')"
            if version_ge "$ver" "$PYTHON_MIN_VERSION"; then
                echo "$cmd"
                return
            fi
        fi
    done
    return 1
}

setup_uv_venv() {
    local sys_python="$1"

    # 虚拟环境中的 python 路径
    local venv_python="$VENV_DIR/bin/python"

    if [[ -x "$venv_python" ]]; then
        success "虚拟环境已存在: $VENV_DIR"
        PYTHON_CMD="$venv_python"
        ENV_TYPE="uv"
        return
    fi

    # 安装 uv（如果没有）
    if ! command -v uv &>/dev/null; then
        info "正在安装 uv..."
        "$sys_python" -m pip install uv --quiet 2>/dev/null || {
            # pip 不可用时用官方安装脚本
            curl -LsSf https://astral.sh/uv/install.sh | sh
        }
        # 刷新 PATH
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    fi
    success "uv 已就绪"

    info "使用 uv 创建虚拟环境: $VENV_DIR"
    uv venv "$VENV_DIR" --python "$sys_python"

    if [[ ! -x "$venv_python" ]]; then
        err "虚拟环境创建失败"
    fi

    PYTHON_CMD="$venv_python"
    ENV_TYPE="uv"
    success "虚拟环境创建完成"
}

setup_python_env() {
    header "检测 Python 环境"

    # 优先 Conda
    local conda_bin
    if conda_bin="$(find_conda)"; then
        info "检测到 Conda: $conda_bin"
        setup_conda_env "$conda_bin"
        return
    fi

    # 回退到系统 Python + uv
    warn "未检测到 Conda，尝试系统 Python + uv"
    local sys_python
    if sys_python="$(find_system_python)"; then
        info "系统 Python: $sys_python ($($sys_python --version 2>&1))"
        setup_uv_venv "$sys_python"
        local ver
        ver="$("$PYTHON_CMD" --version 2>&1 | awk '{print $2}')"
        success "Python 环境就绪: $ver (uv 虚拟环境)"
        return
    fi

    err "未找到 Python >= $PYTHON_MIN_VERSION\n  方式一（推荐）: 安装 Miniconda https://docs.anaconda.com/miniconda/\n  方式二: 安装 Python https://www.python.org/downloads/"
}

# ==================== 依赖安装 ====================

install_dependencies() {
    header "检查 Python 依赖"

    # 快速检测核心包
    if "$PYTHON_CMD" -c "import django, rest_framework, psycopg2, channels, uvicorn" 2>/dev/null; then
        success "所有核心依赖已就绪"
        return
    fi

    warn "检测到缺失依赖，正在安装..."
    if [[ "$ENV_TYPE" == "uv" ]] && command -v uv &>/dev/null; then
        uv pip install -r "$REQUIREMENTS_FILE" --python "$PYTHON_CMD"
    else
        "$PYTHON_CMD" -m pip install -r "$REQUIREMENTS_FILE"
    fi
    success "依赖安装完成"
}

# ==================== Docker 服务 ====================

check_docker() {
    header "检查 Docker"

    if ! command -v docker &>/dev/null; then
        err "未找到 Docker，请先安装:\n  macOS/Windows: https://www.docker.com/products/docker-desktop/\n  Linux: https://docs.docker.com/engine/install/"
    fi

    if ! docker info &>/dev/null; then
        err "Docker 未运行，请先启动 Docker Desktop 或 Docker 服务"
    fi
    success "Docker 已就绪"

    # 检测 docker compose 命令
    if docker compose version &>/dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        err "未找到 docker compose 命令"
    fi
    success "Docker Compose 已就绪 ($COMPOSE_CMD)"
}

wait_for_healthy() {
    local name="$1"
    local timeout="${2:-30}"
    local i=0
    while [[ $i -lt $timeout ]]; do
        local status
        status="$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "none")"
        if [[ "$status" == "healthy" ]]; then
            return 0
        fi
        sleep 1
        ((i++))
    done
    return 1
}

start_docker_services() {
    header "启动 Docker 服务"

    # 1. 检查容器状态
    local pg_exists=false
    local redis_exists=false
    local pg_status="not_found"
    local redis_status="not_found"

    if docker inspect "$PG_CONTAINER" &>/dev/null; then
        pg_exists=true
        pg_status="$(docker inspect --format='{{.State.Status}}' "$PG_CONTAINER" 2>/dev/null)"
    fi

    if docker inspect "$REDIS_CONTAINER" &>/dev/null; then
        redis_exists=true
        redis_status="$(docker inspect --format='{{.State.Status}}' "$REDIS_CONTAINER" 2>/dev/null)"
    fi

    # 如果都正在运行，检查是否属于当前 Compose 项目（可选，这里简单处理：只要运行就认为正常）
    if [[ "$pg_status" == "running" && "$redis_status" == "running" ]]; then
        success "PostgreSQL 和 Redis 容器已在运行"
        
        # 即使容器在运行，也需要读取密码供后续使用
        # 确保变量已初始化
        PG_PASSWORD="${PG_PASSWORD:-}"
        REDIS_PASSWORD="${REDIS_PASSWORD:-}"

        if [[ -z "${PG_PASSWORD:-}" ]]; then
            # 从 env.py 中读取已有密码（如果存在）
            if [[ -f "$ENV_FILE" ]]; then
                PG_PASSWORD="$("$PYTHON_CMD" -c "
import sys; sys.path.insert(0, '$BACKEND_DIR')
try:
    from conf.env import DATABASE_PASSWORD; print(DATABASE_PASSWORD)
except: pass
" 2>/dev/null || echo "")"
                REDIS_PASSWORD="$("$PYTHON_CMD" -c "
import sys; sys.path.insert(0, '$BACKEND_DIR')
try:
    from conf.env import REDIS_PASSWORD; print(REDIS_PASSWORD)
except: pass
" 2>/dev/null || echo "")"
            fi
        fi
        
        return
    fi

    # 如果有任何一个存在（无论是否运行），提示用户处理冲突
    if [[ "$pg_exists" == "true" || "$redis_exists" == "true" ]]; then
        warn "检测到容器已存在但状态不一致（可能导致命名冲突）："
        if [[ "$pg_exists" == "true" ]]; then
            info "  - PostgreSQL ($PG_CONTAINER): $pg_status"
        else
            info "  - PostgreSQL ($PG_CONTAINER): 未找到"
        fi
        if [[ "$redis_exists" == "true" ]]; then
            info "  - Redis      ($REDIS_CONTAINER): $redis_status"
        else
            info "  - Redis      ($REDIS_CONTAINER): 未找到"
        fi
        
        echo ""
        warn "如果启动失败（Error response from daemon: Conflict），建议选择重建。"
        echo -n "  是否删除旧容器并重新启动？(y/n) [默认 y]: "
        read -r reply
        if [[ "$reply" == "y" || "$reply" == "Y" || -z "$reply" ]]; then
            info "正在删除旧容器..."
            docker rm -f "$PG_CONTAINER" "$REDIS_CONTAINER" 2>/dev/null || true
            success "旧容器已删除"
        else
            info "尝试保留现有容器..."
        fi
    fi

    # 生成或读取密码
    # 确保变量已初始化
    PG_PASSWORD="${PG_PASSWORD:-}"
    REDIS_PASSWORD="${REDIS_PASSWORD:-}"

    if [[ -z "${PG_PASSWORD:-}" ]]; then
        # 从 env.py 中读取已有密码（如果存在）
        if [[ -f "$ENV_FILE" ]]; then
            PG_PASSWORD="$("$PYTHON_CMD" -c "
import sys; sys.path.insert(0, '$BACKEND_DIR')
try:
    from conf.env import DATABASE_PASSWORD; print(DATABASE_PASSWORD)
except: pass
" 2>/dev/null || echo "")"
            REDIS_PASSWORD="$("$PYTHON_CMD" -c "
import sys; sys.path.insert(0, '$BACKEND_DIR')
try:
    from conf.env import REDIS_PASSWORD; print(REDIS_PASSWORD)
except: pass
" 2>/dev/null || echo "")"
        fi
    fi

    # 如果还是没有密码，生成新的
    if [[ -z "${PG_PASSWORD:-}" ]]; then
        local passwords
        passwords="$("$PYTHON_CMD" "$BACKEND_DIR/scripts/setup_config.py" --gen-password)"
        PG_PASSWORD="$(echo "$passwords" | head -1)"
        REDIS_PASSWORD="$(echo "$passwords" | tail -1)"
        info "已自动生成数据库和 Redis 密码"
    fi

    export POSTGRES_PASSWORD="$PG_PASSWORD"
    export REDIS_PASSWORD="$REDIS_PASSWORD"

    $COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" up -d

    # 等待 PostgreSQL
    info "等待 PostgreSQL 就绪..."
    if wait_for_healthy "$PG_CONTAINER" 15; then
        success "PostgreSQL 已就绪"
    elif docker exec "$PG_CONTAINER" pg_isready -U mai_notebook -d mai_notebook &>/dev/null; then
        success "PostgreSQL 已就绪"
    else
        err "PostgreSQL 启动超时，请检查: docker logs $PG_CONTAINER"
    fi

    # 等待 Redis
    info "等待 Redis 就绪..."
    if wait_for_healthy "$REDIS_CONTAINER" 15; then
        success "Redis 已就绪"
    elif docker exec "$REDIS_CONTAINER" redis-cli -a "$REDIS_PASSWORD" ping 2>/dev/null | grep -q PONG; then
        success "Redis 已就绪"
    else
        err "Redis 启动超时，请检查: docker logs $REDIS_CONTAINER"
    fi
}

# ==================== 配置文件管理 ====================

setup_config() {
    # 首次启动或全量重置时，运行交互式配置
    if [[ "$FLAG_INIT" == true ]] || [[ "$FLAG_RESET" == true ]] || [[ ! -f "$ENV_FILE" ]]; then
        header "生成配置文件"

        if [[ -f "$ENV_FILE" ]] && [[ "$FLAG_INIT" == true ]]; then
            warn "配置文件已存在: $ENV_FILE"
            echo -n "  是否重新生成？(y/n): "
            read -r reply
            if [[ "$reply" != "y" && "$reply" != "Y" ]]; then
                info "跳过配置生成"
                return
            fi
        fi

        # 调用 Python 交互式配置脚本
        "$PYTHON_CMD" "$BACKEND_DIR/scripts/setup_config.py" \
            --pg-pass "$PG_PASSWORD" \
            --redis-pass "$REDIS_PASSWORD"
    else
        success "配置文件已存在: $ENV_FILE"
    fi
}

# ==================== 数据库迁移 ====================

run_migrations() {
    header "数据库迁移"

    info "执行 makemigrations..."
    "$PYTHON_CMD" "$BACKEND_DIR/manage.py" makemigrations

    info "执行 migrate..."
    "$PYTHON_CMD" "$BACKEND_DIR/manage.py" migrate

    success "数据库迁移完成"
}

# ==================== 数据初始化 ====================

init_data() {
    header "初始化系统数据"
    "$PYTHON_CMD" "$BACKEND_DIR/manage.py" init -y
    "$PYTHON_CMD" "$BACKEND_DIR/manage.py" init_area
    "$PYTHON_CMD" "$BACKEND_DIR/manage.py" init_ai_models
    success "系统数据初始化完成"
}

# ==================== 全量重置 ====================

run_full_reset() {
    header "全量重置"
    warn "即将执行全量重置，所有数据将被清空！"
    "$PYTHON_CMD" "$BACKEND_DIR/scripts/full_reset.py"
}

# ==================== 启动后端 ====================

start_backend() {
    header "启动后端服务"

    if [[ "$FLAG_DEBUG" == true ]]; then
        echo -e "  ${YELLOW}🔧 调试模式${NC}（自动重载已启用）"
        echo ""
    fi

    echo -e "  访问地址:  ${GREEN}http://localhost:8000${NC}"
    echo -e "  API 文档:  ${GREEN}http://localhost:8000/swagger/${NC}"
    echo -e "  ReDoc:     ${GREEN}http://localhost:8000/redoc/${NC}"
    echo ""
    echo -e "  按 ${YELLOW}Ctrl+C${NC} 停止服务"
    echo ""

    cd "$BACKEND_DIR"
    
    if [[ "$FLAG_DEBUG" == true ]]; then
        # 调试模式：启用自动重载
        "$PYTHON_CMD" main.py --reload
    else
        # 正常模式
        "$PYTHON_CMD" main.py
    fi
}

# ==================== 清理 ====================

cleanup() {
    echo ""
    info "正在停止服务..."
    info "再见 👋"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ==================== 主流程 ====================

main() {
    parse_args "$@"

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════╗"
    echo -e "║        麦麦笔记本 · 后端一键启动脚本            ║"
    echo -e "╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    info "操作系统: $(uname -s) $(uname -m)"
    info "工作目录: $SCRIPT_DIR"

    # 1. Python 环境
    setup_python_env

    # 2. 依赖安装
    install_dependencies

    # 3. Docker 服务
    check_docker
    start_docker_services

    # 4. 配置文件
    setup_config

    # 5. 全量重置（如果指定）
    if [[ "$FLAG_RESET" == true ]]; then
        run_full_reset
    fi

    # 6. 数据库迁移
    run_migrations

    # 7. 数据初始化（首次启动或重置时）
    if [[ "$FLAG_INIT" == true ]] || [[ "$FLAG_RESET" == true ]]; then
        init_data
    fi

    # 8. 启动后端
    start_backend
}

main "$@"
