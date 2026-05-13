"""性能测试（8.3）

启动多个车辆客户端模拟器，并发发送数据，采集性能指标生成报告。

用法:
    python test_performance.py --clients 100 --duration 600 --interval 1
"""

import os
import sys
import time
import json
import uuid
import argparse
import threading
import statistics
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from client.vehicle_client import VehicleClient  # noqa: E402

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_TOKEN", "dev-token-12345")
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

# 设计要求
REQUIREMENTS = {
    "auth_latency_ms": 500,
    "sm4_throughput_mbps": 100,
    "sm2_sign_tps": 1000,
    "sm2_verify_tps": 2000,
    "session_query_ms": 5,
}


class Stats:
    def __init__(self):
        self.sent = 0
        self.failed = 0
        self.latencies = []
        self.lock = threading.Lock()

    def record(self, latency_ms, ok):
        with self.lock:
            if ok:
                self.sent += 1
                self.latencies.append(latency_ms)
            else:
                self.failed += 1


def run_client(vid, duration, interval, stats):
    """单个客户端线程：注册 + 循环发送数据"""
    try:
        host = GATEWAY_URL.replace("http://", "").replace("https://", "").split(":")[0]
        port = int(GATEWAY_URL.rsplit(":", 1)[-1]) if ":" in GATEWAY_URL.replace("http://", "") else 8000
        client = VehicleClient(vehicle_id=vid, gateway_host=host, gateway_port=port, api_token=API_TOKEN)
        client.generate_keypair()
        client.request_certificate()
        # 注册
        requests.post(
            f"{GATEWAY_URL}/api/auth/register",
            json={"vehicle_id": vid, "certificate_serial": client.certificate.serial_number,
                  "public_key": client.public_key.hex()},
            headers=HEADERS, timeout=10,
        )
    except Exception as e:
        print(f"[{vid}] 初始化失败: {e}")
        return

    end_time = time.time() + duration
    while time.time() < end_time:
        t0 = time.time()
        try:
            data = client.simulate_data_collection()
            ok = client.send_vehicle_data(data)
        except Exception:
            ok = False
        stats.record((time.time() - t0) * 1000, ok)
        time.sleep(interval)


def sample_metrics(duration, samples):
    """周期采集指标 API"""
    end_time = time.time() + duration
    while time.time() < end_time:
        try:
            r = requests.get(f"{GATEWAY_URL}/api/metrics/realtime", headers=HEADERS, timeout=5)
            if r.status_code == 200:
                samples.append(r.json())
        except Exception:
            pass
        time.sleep(10)


def generate_report(stats, metrics_samples, duration, clients):
    print("\n" + "=" * 60)
    print("  性能测试报告")
    print("=" * 60)
    total = stats.sent + stats.failed
    print(f"并发客户端数:     {clients}")
    print(f"持续时间:         {duration} 秒")
    print(f"总请求数:         {total}")
    print(f"成功请求:         {stats.sent}")
    print(f"失败请求:         {stats.failed}")
    print(f"成功率:           {stats.sent / total * 100:.2f}%" if total else "N/A")

    if stats.latencies:
        print(f"\n响应延迟 (ms):")
        print(f"  平均:   {statistics.mean(stats.latencies):.2f}")
        print(f"  中位数: {statistics.median(stats.latencies):.2f}")
        print(f"  P95:    {sorted(stats.latencies)[int(len(stats.latencies) * 0.95)]:.2f}")
        print(f"  最大:   {max(stats.latencies):.2f}")

    if metrics_samples:
        last = metrics_samples[-1]
        print(f"\n网关最终指标快照:")
        print(f"  {json.dumps(last, ensure_ascii=False, indent=2)}")

    print(f"\n对比设计要求:")
    for k, v in REQUIREMENTS.items():
        print(f"  {k:30s} 目标={v}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", type=int, default=100, help="并发客户端数")
    parser.add_argument("--duration", type=int, default=600, help="持续时间(秒)")
    parser.add_argument("--interval", type=float, default=1.0, help="发送间隔(秒)")
    args = parser.parse_args()

    print(f"启动 {args.clients} 个客户端，持续 {args.duration} 秒")
    stats = Stats()
    metrics_samples = []

    # 启动指标采集线程
    threading.Thread(target=sample_metrics, args=(args.duration, metrics_samples), daemon=True).start()

    # 启动客户端线程
    threads = []
    for i in range(args.clients):
        vid = f"PERF_{uuid.uuid4().hex[:8]}"
        t = threading.Thread(target=run_client, args=(vid, args.duration, args.interval, stats), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.05)  # 错峰启动

    # 等待完成
    for t in threads:
        t.join(timeout=args.duration + 30)

    generate_report(stats, metrics_samples, args.duration, args.clients)


if __name__ == "__main__":
    main()
