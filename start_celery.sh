#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# 麦麦笔记本 · Celery 管理脚本
#
# 用法:
#   bash start_celery.sh              # 前台启动 Worker + Beat（默认）
#   bash start_celery.sh start        # 同上
#   bash start_celery.sh stop         # 停止所有 Celery 进程
#   bash start_celery.sh restart      # 重启
#   bash start_celery.sh status       # 查看运行状态
#   bash start_celery.sh logs         # 实时查看日志
#   bash start_celery.sh --help       # 显示帮助

set -euo pipefail

# ==================== 常量 ====================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
CONDA_ENV="mai_notebook"
PYTHON_MIN_VERSION="3.10"
VENV_DIR="$BACKEND_DIR/.venv"

# Celery 配置
CELERY_APP="application.celery:app"
LOG_DIR="$BACKEND_DIR/logs/celery"
LOG_LEVEL="info"
WORKER_CONCURRENCY=4
WORKER_QUEUES="celery"

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

# ==================== 帮助 ====================

show_help() {
    cat << 'EOF'
麦麦笔记本 · Celery 管理脚本

用法:
    bash start_celery.sh [命令]

命令:
    start       前台启动 Worker + Beat（默认，Ctrl+C 停止）
    stop        停止所有 Celery 进程
    restart     重启（先停止再启动）
    status      查看 Celery 进程运行状态
    logs        实时查看 Worker + Beat 日志
    --help      显示此帮助信息

日志文件:
    Worker: backend/logs/celery/worker.log
    Beat:   backend/logs/celery/beat.log
EOF
    exit 0
}

# ==================== Python 环境检测 ====================

# 复用 start_backend.sh 相同的环境检测逻辑
PYTHON_CMD=""

version_ge() {
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

find_conda() {
    if command -v conda &>/dev/null; then
        echo "conda"
        return
    fi
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

    eval "$("$conda_bin" shell.bash hook 2>/dev/null)" || {
        local conda_base
        conda_base="$("$conda_bin" info --base 2>/dev/null)"
        if [[ -f "$conda_base/etc/profile.d/conda.sh" ]]; then
            source "$conda_base/etc/profile.d/conda.sh"
        fi
    }

    if ! "$conda_bin" env list 2>/dev/null | grep -qw "$CONDA_ENV"; then
        err "Conda 环境 '$CONDA_ENV' 不存在，请先运行 start_backend.sh 创建环境"
    fi

    conda activate "$CONDA_ENV" 2>/dev/null || {
        err "无法激活 Conda 环境 '$CONDA_ENV'"
    }

    PYTHON_CMD="$(which python)"
}

find_system_python() {
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

setup_python_env() {
    # 优先 Conda
    local conda_bin
    if conda_bin="$(find_conda)"; then
        setup_conda_env "$conda_bin"
        return
    fi

    # 回退到 uv 虚拟环境
    local venv_python="$VENV_DIR/bin/python"
    if [[ -x "$venv_python" ]]; then
        PYTHON_CMD="$venv_python"
        return
    fi

    # 回退到系统 Python
    local sys_python
    if sys_python="$(find_system_python)"; then
        PYTHON_CMD="$sys_python"
        return
    fi

    err "未找到可用的 Python 环境，请先运行 start_backend.sh 初始化环境"
}

# ==================== Celery 工具 ====================

# 获取 celery 可执行文件路径
find_celery_bin() {
    # 当前 Python 环境的 bin 目录
    local env_bin
    env_bin="$(dirname "$PYTHON_CMD")/celery"
    if [[ -x "$env_bin" ]]; then
        echo "$env_bin"
        return
    fi

    # PATH 中查找
    if command -v celery &>/dev/null; then
        command -v celery
        return
    fi

    err "未找到 celery 可执行文件，请确认已安装: pip install celery"
}

# 获取操作系统类型
get_os_type() {
    local system
    system="$(uname -s | tr '[:upper:]' '[:lower:]')"
    case "$system" in
        darwin) echo "macos" ;;
        *)      echo "linux" ;;
    esac
}

# 确保日志目录存在
ensure_log_dir() {
    mkdir -p "$LOG_DIR"
}

# 查找正在运行的 Celery 进程 PID
get_celery_pids() {
    # worker 进程
    pgrep -f "celery.*${CELERY_APP}.*worker" 2>/dev/null || true
    # beat 进程
    pgrep -f "celery.*${CELERY_APP}.*beat" 2>/dev/null || true
}

# ==================== 命令实现 ====================

do_stop() {
    info "停止 Celery 进程..."

    local pids
    pids="$(get_celery_pids)"

    if [[ -z "$pids" ]]; then
        info "没有正在运行的 Celery 进程"
        return
    fi

    # 先发 SIGTERM 优雅关闭
    echo "$pids" | xargs kill 2>/dev/null || true

    # 等待进程退出
    local timeout=10
    local i=0
    while [[ $i -lt $timeout ]]; do
        pids="$(get_celery_pids)"
        if [[ -z "$pids" ]]; then
            success "所有 Celery 进程已停止"
            return
        fi
        sleep 1
        ((i++))
    done

    # 超时强制杀死
    warn "部分进程未响应，强制终止..."
    echo "$pids" | xargs kill -9 2>/dev/null || true
    success "Celery 进程已强制停止"
}

do_status() {
    echo ""
    info "Celery 进程状态:"
    echo ""

    local worker_pids beat_pids
    worker_pids="$(pgrep -f "celery.*${CELERY_APP}.*worker" 2>/dev/null || true)"
    beat_pids="$(pgrep -f "celery.*${CELERY_APP}.*beat" 2>/dev/null || true)"

    if [[ -n "$worker_pids" ]]; then
        echo -e "  ${GREEN}●${NC} Worker 运行中 (PID: $(echo $worker_pids | tr '\n' ' '))"
    else
        echo -e "  ${RED}●${NC} Worker 未运行"
    fi

    if [[ -n "$beat_pids" ]]; then
        echo -e "  ${GREEN}●${NC} Beat   运行中 (PID: $(echo $beat_pids | tr '\n' ' '))"
    else
        echo -e "  ${RED}●${NC} Beat   未运行"
    fi

    echo ""

    # 显示日志文件信息
    if [[ -f "$LOG_DIR/worker.log" ]]; then
        local worker_size
        worker_size="$(du -h "$LOG_DIR/worker.log" | cut -f1)"
        info "Worker 日志: $LOG_DIR/worker.log ($worker_size)"
    fi
    if [[ -f "$LOG_DIR/beat.log" ]]; then
        local beat_size
        beat_size="$(du -h "$LOG_DIR/beat.log" | cut -f1)"
        info "Beat 日志:   $LOG_DIR/beat.log ($beat_size)"
    fi
    echo ""
}

do_logs() {
    ensure_log_dir

    # 确保日志文件存在
    touch "$LOG_DIR/worker.log" "$LOG_DIR/beat.log"

    info "实时查看 Celery 日志（Ctrl+C 退出）..."
    echo ""
    tail -f "$LOG_DIR/worker.log" "$LOG_DIR/beat.log"
}

do_start() {
    header "启动 Celery"

    # 检查是否已在运行
    local pids
    pids="$(get_celery_pids)"
    if [[ -n "$pids" ]]; then
        warn "Celery 已在运行 (PID: $(echo $pids | tr '\n' ' '))"
        warn "如需重启请使用: bash start_celery.sh restart"
        exit 1
    fi

    local celery_bin os_type
    celery_bin="$(find_celery_bin)"
    os_type="$(get_os_type)"

    ensure_log_dir

    info "操作系统: $(uname -s) $(uname -m)"
    info "Python:   $PYTHON_CMD"
    info "Celery:   $celery_bin"
    info "日志目录: $LOG_DIR"
    echo ""

    # 构建 Worker 命令
    local worker_cmd=("$celery_bin" -A "$CELERY_APP" worker
        --loglevel="$LOG_LEVEL"
        --logfile="$LOG_DIR/worker.log"
        -Q "$WORKER_QUEUES"
    )
    if [[ "$os_type" == "macos" ]]; then
        worker_cmd+=(--pool=solo)
        # macOS 需要设置此环境变量避免 fork 安全警告
        export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
    else
        worker_cmd+=(--concurrency="$WORKER_CONCURRENCY" --pool=prefork)
    fi

    # 构建 Beat 命令
    local beat_cmd=("$celery_bin" -A "$CELERY_APP" beat
        --loglevel="$LOG_LEVEL"
        --logfile="$LOG_DIR/beat.log"
        --scheduler=django_celery_beat.schedulers:DatabaseScheduler
    )

    # 启动 Worker（后台）
    info "启动 Worker..."
    (cd "$BACKEND_DIR" && "${worker_cmd[@]}" &)
    WORKER_PID=$!
    success "Worker 已启动 (PID: $WORKER_PID)"

    # 启动 Beat（后台）
    info "启动 Beat..."
    (cd "$BACKEND_DIR" && "${beat_cmd[@]}" &)
    BEAT_PID=$!
    success "Beat 已启动 (PID: $BEAT_PID)"

    echo ""
    echo -e "  Celery 已启动，按 ${YELLOW}Ctrl+C${NC} 停止"
    echo -e "  Worker 日志: ${CYAN}tail -f $LOG_DIR/worker.log${NC}"
    echo -e "  Beat 日志:   ${CYAN}tail -f $LOG_DIR/beat.log${NC}"
    echo ""

    # 前台等待，监控子进程
    trap 'do_stop; exit 0' SIGINT SIGTERM

    while true; do
        # 检查进程是否还活着
        if ! kill -0 "$WORKER_PID" 2>/dev/null && ! kill -0 "$BEAT_PID" 2>/dev/null; then
            err "Worker 和 Beat 都已退出，请检查日志"
        fi
        sleep 2
    done
}

# ==================== 主流程 ====================

main() {
    local cmd="${1:-start}"

    case "$cmd" in
        --help|-h) show_help ;;
        status)    do_status; exit 0 ;;
        logs)      do_logs; exit 0 ;;
        stop)      do_stop; exit 0 ;;
    esac

    # start 和 restart 需要 Python 环境
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════╗"
    echo -e "║        麦麦笔记本 · Celery 管理脚本             ║"
    echo -e "╚══════════════════════════════════════════════════╝${NC}"
    echo ""

    setup_python_env
    success "Python 环境: $PYTHON_CMD"

    case "$cmd" in
        start)   do_start ;;
        restart) do_stop; do_start ;;
        *) warn "未知命令: $cmd"; show_help ;;
    esac
}

main "$@"
