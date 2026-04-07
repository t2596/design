"""审计报告导出功能使用示例

演示如何使用 export_audit_report 方法导出审计日志报告
"""

from datetime import datetime, timedelta
from src.audit_logger import create_audit_logger
from src.models.enums import EventType
from config import PostgreSQLConfig


def main():
    """主函数"""
    print("=== 审计报告导出功能示例 ===\n")
    
    # 1. 创建审计日志记录器
    config = PostgreSQLConfig(
        host="localhost",
        port=5432,
        database="vehicle_iot",
        user="postgres",
        password="password"
    )
    
    audit_logger = create_audit_logger(config)
    print("✓ 审计日志记录器已创建\n")
    
    # 2. 记录一些示例日志
    print("记录示例日志...")
    
    # 记录认证事件
    audit_logger.log_auth_event(
        vehicle_id="VIN123456789",
        event_type=EventType.AUTHENTICATION_SUCCESS,
        result=True,
        ip_address="192.168.1.100",
        details="车辆认证成功，使用 SM2 证书"
    )
    
    # 记录数据传输
    audit_logger.log_data_transfer(
        vehicle_id="VIN123456789",
        data_size=4096,
        encrypted=True,
        ip_address="192.168.1.100",
        details="传输车辆状态数据，使用 SM4 加密"
    )
    
    # 记录证书操作
    audit_logger.log_certificate_operation(
        operation="issued",
        cert_id="CERT20240101001",
        vehicle_id="VIN123456789",
        ip_address="192.168.1.100",
        details="为车辆颁发新证书"
    )
    
    print("✓ 已记录 3 条示例日志\n")
    
    # 3. 导出 JSON 格式报告
    print("导出 JSON 格式报告...")
    
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now()
    
    json_report = audit_logger.export_audit_report(
        start_time=start_time,
        end_time=end_time,
        format="json"
    )
    
    # 保存到文件
    with open("audit_report.json", "w", encoding="utf-8") as f:
        f.write(json_report)
    
    print(f"✓ JSON 报告已保存到 audit_report.json")
    print(f"  报告大小: {len(json_report)} 字节\n")
    
    # 显示报告预览
    print("JSON 报告预览（前 500 字符）:")
    print("-" * 60)
    print(json_report[:500] + "...")
    print("-" * 60)
    print()
    
    # 4. 导出 CSV 格式报告
    print("导出 CSV 格式报告...")
    
    csv_report = audit_logger.export_audit_report(
        start_time=start_time,
        end_time=end_time,
        format="csv"
    )
    
    # 保存到文件
    with open("audit_report.csv", "w", encoding="utf-8") as f:
        f.write(csv_report)
    
    print(f"✓ CSV 报告已保存到 audit_report.csv")
    print(f"  报告大小: {len(csv_report)} 字节\n")
    
    # 显示报告预览
    print("CSV 报告预览（前 5 行）:")
    print("-" * 60)
    lines = csv_report.split('\n')
    for line in lines[:5]:
        print(line)
    print("-" * 60)
    print()
    
    # 5. 导出特定时间范围的报告
    print("导出特定时间范围的报告...")
    
    # 导出最近 10 分钟的日志
    recent_start = datetime.now() - timedelta(minutes=10)
    recent_end = datetime.now()
    
    recent_report = audit_logger.export_audit_report(
        start_time=recent_start,
        end_time=recent_end,
        format="json"
    )
    
    import json
    report_data = json.loads(recent_report)
    
    print(f"✓ 最近 10 分钟的报告:")
    print(f"  开始时间: {recent_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  结束时间: {recent_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  日志总数: {report_data['report_metadata']['total_logs']}")
    print()
    
    print("=== 示例完成 ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
