#!/usr/bin/env bash
# =============================================================================
# 2 核 2G Ubuntu：Swap、流水线执行后 /tmp 清理（需 root 或 sudo）
# =============================================================================
set -euo pipefail

log() { echo "[$(date -Iseconds)] $*"; }

require_root_for_swap() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    log "ERROR: Swap 创建与 fstab 写入需要 root，请使用: sudo bash $0"
    exit 1
  fi
}

check_swap() {
  if swapon --show 2>/dev/null | grep -q .; then
    log "INFO: 系统已有 Swap 分区或文件："
    swapon --show
    return 0
  fi
  if [[ -f /proc/swaps ]] && grep -v '^Filename' /proc/swaps 2>/dev/null | grep -q .; then
    log "INFO: /proc/swaps 显示已有交换区，跳过创建。"
    cat /proc/swaps
    return 0
  fi
  return 1
}

setup_swap_4g() {
  if check_swap; then
    return 0
  fi
  require_root_for_swap
  local swapfile="/swapfile_aitesta_4g"
  log "INFO: 未发现活动 Swap，将创建 4G 交换文件: ${swapfile}"
  if [[ -f "${swapfile}" ]]; then
    log "WARN: ${swapfile} 已存在，尝试直接 swapon"
    chmod 600 "${swapfile}" || true
    swapon "${swapfile}" 2>/dev/null || true
    if swapon --show | grep -q "${swapfile}"; then
      log "INFO: 已启用已有 ${swapfile}"
      _ensure_fstab "${swapfile}"
      return 0
    fi
  fi
  log "INFO: fallocate / dd 创建 4G 文件（视文件系统而定）…"
  if fallocate -l 4G "${swapfile}" 2>/dev/null; then
    :
  else
    log "WARN: fallocate 不可用，使用 dd（较慢）"
    dd if=/dev/zero of="${swapfile}" bs=1M count=4096 status=progress
  fi
  chmod 600 "${swapfile}"
  mkswap "${swapfile}"
  swapon "${swapfile}"
  _ensure_fstab "${swapfile}"
  log "INFO: Swap 已启用并完成 fstab 配置。"
  free -h
}

_ensure_fstab() {
  local swapfile="$1"
  local line="${swapfile} none swap sw 0 0"
  if grep -qF "${swapfile}" /etc/fstab 2>/dev/null; then
    log "INFO: /etc/fstab 已包含 ${swapfile}"
    return 0
  fi
  echo "${line}" >> /etc/fstab
  log "INFO: 已追加 fstab 行: ${line}"
}

cleanup_tmp_artifacts() {
  log "INFO: 清理 /tmp 下常见构建与缓存残留（跳过不存在的目录）…"
  local patterns=(
    "/tmp/pip-*"
    "/tmp/npm-*"
    "/tmp/pytest-of-*"
    "/tmp/playwright*"
  )
  for p in "${patterns[@]}"; do
    if compgen -G "${p}" >/dev/null; then
      log "INFO: 删除匹配: ${p}"
      rm -rf ${p}
    fi
  done
  log "INFO: 同步 drop_caches 仅提示（需 root 且非必须）：echo 3 > /proc/sys/vm/drop_caches"
  log "INFO: /tmp 清理逻辑执行完毕。df -h /tmp:"
  df -h /tmp 2>/dev/null || df -h /
}

main() {
  log "=== AITesta 2C2G 服务器优化脚本 ==="
  log "当前内存与 Swap:"
  free -h || true
  if ! check_swap; then
    setup_swap_4g
  fi
  cleanup_tmp_artifacts
  log "=== 全部步骤结束 ==="
}

main "$@"
