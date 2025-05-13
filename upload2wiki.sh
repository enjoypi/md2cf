#!/bin/bash

# 设置错误处理
set -euo pipefail

# 必需的环境变量列表
REQUIRED_VARS=(CONFLUENCE_HOST CONFLUENCE_TOKEN CONFLUENCE_SPACE)

# 日志函数
log() {
    echo "[$1] $(date '+%Y-%m-%d %H:%M:%S') - $2"
}

debug() { log "DEBUG" "$1"; }
error() { log "ERROR" "$1" >&2; exit 1; }

# 设置环境
setup_environment() {
    # 激活虚拟环境
    [ -d ".venv" ] && { debug "激活虚拟环境"; source .venv/bin/activate || error "无法激活虚拟环境"; }

    # 加载.env文件
    if [ -f ".env" ]; then
        debug "加载环境变量文件"
        while IFS= read -r line || [ -n "$line" ]; do
            # 跳过注释和空行
            [[ $line =~ ^#.*$ || -z $line ]] && continue

            # 提取变量名和值并导出
            var_name="${line%%=*}"
            var_value="${line#*=}"
            var_value=$(echo "$var_value" | sed -e 's/^[[:space:]]*["'\'']//' -e 's/["'\''][[:space:]]*$//')
            export "$var_name=$var_value"
        done < ".env"
    fi

    # 检查必要的环境变量和命令
    for var in "${REQUIRED_VARS[@]}"; do
        [ -z "${!var:-}" ] && error "$var 未设置"
    done

    command -v md2cf &> /dev/null || error "md2cf 命令未找到，请确保已安装并激活了正确的虚拟环境"
}

# 主函数
main() {
    local start_time=$(date +%s)
    debug "脚本开始执行"

    setup_environment
    debug "传递参数: $*"
    debug "开始执行 md2cf 命令..."

    # 执行上传
    md2cf \
        --debug \
        --collapse-single-pages \
        --enable-relative-links \
        --insecure \
        --minor-edit \
        --only-changed \
        --preface-markdown \
        --top-level \
        --skip-empty \
        --use-pages-file \
        "$@" || \
          error "md2cf 命令执行失败"

    debug "脚本执行完成，耗时: $(($(date +%s) - start_time)) 秒"
}

# 执行主函数
main "$@"