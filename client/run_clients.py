#!/usr/bin/env python3
"""
多客户端启动脚本

使用方法：
    python3 run_clients.py --num 5                           # 启动5个客户端
    python3 run_clients.py --num 10 --interval 5             # 启动10个客户端，每5秒发送
    python3 run_clients.py --num 3 --gateway 192.168.1.100  # 指定Gateway地址
    python3 run_clients.py --stop                            # 停止所有客户端
    python3 run_clients.py --status                          # 查看客户端状态
"""

import argparse
import subprocess
import sys
import time
import os

# 默认配置
DEFAULT_GATEWAY_HOST = "8.160.179.59"
DEFAULT_GATEWAY_PORT = "32677"
DEFAULT_NUM_CLIENTS = 3
DEFAULT_INTERVAL = 10
DEFAULT_MODE = "continuous"
DEFAULT_PREFIX = "CLOUD-VIN"


def run_command(cmd, check=True):
    """运行shell命令"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def build_image():
    """构建客户端镜像"""
    print("🔨 构建客户端镜像...")
    
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    cmd = f"cd {project_root} && docker build -f client/Dockerfile -t vehicle-client:latest ."
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print("✓ 镜像构建完成")
        return True
    else:
        print(f"✗ 镜像构建失败: {stderr}")
        return False


def start_clients(num_clients, gateway_host, gateway_port, mode, interval, prefix):
    """启动多个客户端"""
    print(f"\n🚀 启动 {num_clients} 个客户端...")
    print(f"   Gateway: {gateway_host}:{gateway_port}")
    print(f"   模式: {mode}, 间隔: {interval}秒")
    print()
    
    started = 0
    failed = 0
    
    for i in range(1, num_clients + 1):
        vehicle_id = f"{prefix}-{i:03d}"
        container_name = f"vehicle-client-{i}"
        
        # 停止并删除已存在的容器
        run_command(f"docker rm -f {container_name}", check=False)
        
        # 启动新容器
        cmd = f"""docker run -d \
            --name {container_name} \
            --network host \
            -e GATEWAY_HOST={gateway_host} \
            -e GATEWAY_PORT={gateway_port} \
            vehicle-client:latest \
            --vehicle-id {vehicle_id} \
            --mode {mode} \
            --interval {interval}"""
        
        success, stdout, stderr = run_command(cmd)
        
        if success:
            print(f"✓ 客户端 {i:2d}: {vehicle_id:20s} (容器: {container_name})")
            started += 1
        else:
            print(f"✗ 客户端 {i:2d}: 启动失败 - {stderr}")
            failed += 1
        
        # 避免同时启动太多
        time.sleep(0.3)
    
    print()
    print(f"✓ 成功启动 {started} 个客户端")
    if failed > 0:
        print(f"✗ 失败 {failed} 个客户端")
    
    return started, failed


def stop_clients():
    """停止所有客户端"""
    print("🛑 停止所有客户端...")
    
    # 获取所有客户端容器
    success, stdout, stderr = run_command(
        "docker ps -q --filter name=vehicle-client",
        check=False
    )
    
    if not stdout.strip():
        print("没有运行中的客户端")
        return
    
    # 停止所有容器
    cmd = "docker stop $(docker ps -q --filter name=vehicle-client)"
    success, stdout, stderr = run_command(cmd, check=False)
    
    if success:
        print("✓ 所有客户端已停止")
    else:
        print(f"✗ 停止失败: {stderr}")


def remove_clients():
    """删除所有客户端容器"""
    print("🗑️  删除所有客户端容器...")
    
    cmd = "docker rm -f $(docker ps -aq --filter name=vehicle-client)"
    success, stdout, stderr = run_command(cmd, check=False)
    
    if success:
        print("✓ 所有客户端容器已删除")
    else:
        print("没有客户端容器需要删除")


def show_status():
    """显示客户端状态"""
    print("📊 客户端状态:")
    print()
    
    # 显示运行中的容器
    cmd = "docker ps --filter name=vehicle-client --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    success, stdout, stderr = run_command(cmd, check=False)
    
    if stdout.strip():
        print(stdout)
    else:
        print("没有运行中的客户端")
    
    print()
    
    # 统计
    cmd = "docker ps -q --filter name=vehicle-client | wc -l"
    success, stdout, stderr = run_command(cmd, check=False)
    running_count = int(stdout.strip()) if stdout.strip() else 0
    
    print(f"运行中的客户端: {running_count}")


def show_logs(client_num):
    """显示客户端日志"""
    container_name = f"vehicle-client-{client_num}"
    print(f"📋 查看客户端 {client_num} 的日志 (Ctrl+C 退出):")
    print()
    
    cmd = f"docker logs -f {container_name}"
    subprocess.run(cmd, shell=True)


def main():
    parser = argparse.ArgumentParser(
        description="多客户端启动和管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  启动5个客户端:
    python3 run_clients.py --num 5
  
  启动10个客户端，每5秒发送一次:
    python3 run_clients.py --num 10 --interval 5
  
  指定Gateway地址:
    python3 run_clients.py --num 3 --gateway 192.168.1.100 --port 8000
  
  停止所有客户端:
    python3 run_clients.py --stop
  
  查看状态:
    python3 run_clients.py --status
  
  查看日志:
    python3 run_clients.py --logs 1
        """
    )
    
    # 操作参数
    parser.add_argument("--num", type=int, default=DEFAULT_NUM_CLIENTS,
                        help=f"客户端数量 (默认: {DEFAULT_NUM_CLIENTS})")
    parser.add_argument("--gateway", default=DEFAULT_GATEWAY_HOST,
                        help=f"Gateway地址 (默认: {DEFAULT_GATEWAY_HOST})")
    parser.add_argument("--port", default=DEFAULT_GATEWAY_PORT,
                        help=f"Gateway端口 (默认: {DEFAULT_GATEWAY_PORT})")
    parser.add_argument("--mode", choices=["continuous", "once"], default=DEFAULT_MODE,
                        help=f"运行模式 (默认: {DEFAULT_MODE})")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help=f"发送间隔（秒） (默认: {DEFAULT_INTERVAL})")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX,
                        help=f"车辆ID前缀 (默认: {DEFAULT_PREFIX})")
    
    # 管理命令
    parser.add_argument("--stop", action="store_true",
                        help="停止所有客户端")
    parser.add_argument("--remove", action="store_true",
                        help="删除所有客户端容器")
    parser.add_argument("--status", action="store_true",
                        help="显示客户端状态")
    parser.add_argument("--logs", type=int, metavar="N",
                        help="查看第N个客户端的日志")
    parser.add_argument("--rebuild", action="store_true",
                        help="重新构建镜像")
    
    args = parser.parse_args()
    
    # 执行管理命令
    if args.stop:
        stop_clients()
        return
    
    if args.remove:
        remove_clients()
        return
    
    if args.status:
        show_status()
        return
    
    if args.logs:
        show_logs(args.logs)
        return
    
    if args.rebuild:
        if not build_image():
            sys.exit(1)
        return
    
    # 启动客户端
    print("=" * 50)
    print("多客户端启动工具")
    print("=" * 50)
    
    # 构建镜像
    if not build_image():
        sys.exit(1)
    
    # 启动客户端
    started, failed = start_clients(
        args.num,
        args.gateway,
        args.port,
        args.mode,
        args.interval,
        args.prefix
    )
    
    if started > 0:
        print()
        print("=" * 50)
        print("管理命令:")
        print("  查看状态: python3 run_clients.py --status")
        print("  查看日志: python3 run_clients.py --logs 1")
        print("  停止所有: python3 run_clients.py --stop")
        print("  删除所有: python3 run_clients.py --remove")
        print("=" * 50)


if __name__ == "__main__":
    main()
