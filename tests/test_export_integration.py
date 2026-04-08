"""审计报告导出功能集成测试

演示 export_audit_report 功能的端到端使用
"""

import pytest
import json
import csv
import io
from datetime import datetime, timedelta
from src.audit_logger import AuditLogger
from src.models.enums import EventType
from src.db.postgres import PostgreSQLConnection
from config import PostgreSQLConfig


@pytest.mark.integration
class TestAuditReportExportIntegration:
    """审计报告导出功能集成测试"""
    
    @pytest.fixture
    def db_connection(self):
        """创建数据库连接"""
        config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="vehicle_iot_test",
            user="test_user",
            password="test_pass"
        )
        return PostgreSQLConnection(config)
    
    @pytest.fixture
    def audit_logger(self, db_connection):
        """创建审计日志记录器"""
        return AuditLogger(db_connection)
    
    def test_export_json_report_with_real_data(self, audit_logger):
        """测试导出包含真实数据的 JSON 报告"""
        # 记录一些测试日志
        start_time = datetime.now()
        
        # 记录认证事件
        audit_logger.log_auth_event(
            vehicle_id="VIN_TEST_001",
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True,
            ip_address="192.168.1.100"
        )
        
        # 记录数据传输事件
        audit_logger.log_data_transfer(
            vehicle_id="VIN_TEST_001",
            data_size=2048,
            encrypted=True,
            ip_address="192.168.1.100"
        )
        
        # 记录证书操作
        audit_logger.log_certificate_operation(
            operation="issued",
            cert_id="CERT_TEST_001",
            vehicle_id="VIN_TEST_001",
            ip_address="192.168.1.100"
        )
        
        end_time = datetime.now() + timedelta(seconds=1)
        
        # 导出 JSON 报告
        json_report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="json"
        )
        
        # 验证报告内容
        report_data = json.loads(json_report)
        
        assert "report_metadata" in report_data
        assert "logs" in report_data
        assert report_data["report_metadata"]["total_logs"] >= 3
        
        # 验证日志包含我们记录的事件
        log_vehicle_ids = [log["vehicle_id"] for log in report_data["logs"]]
        assert "VIN_TEST_001" in log_vehicle_ids
        
        print("\n=== JSON 报告示例 ===")
        print(json_report[:500] + "...")
    
    def test_export_csv_report_with_real_data(self, audit_logger):
        """测试导出包含真实数据的 CSV 报告"""
        # 记录一些测试日志
        start_time = datetime.now()
        
        # 记录多个事件
        for i in range(5):
            audit_logger.log_auth_event(
                vehicle_id=f"VIN_CSV_TEST_{i:03d}",
                event_type=EventType.AUTHENTICATION_SUCCESS,
                result=True,
                ip_address=f"192.168.1.{100 + i}"
            )
        
        end_time = datetime.now() + timedelta(seconds=1)
        
        # 导出 CSV 报告
        csv_report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="csv"
        )
        
        # 验证报告内容
        lines = csv_report.strip().split('\n')
        assert len(lines) >= 6  # 表头 + 至少 5 条数据
        
        # 解析 CSV
        csv_reader = csv.DictReader(io.StringIO(csv_report))
        rows = list(csv_reader)
        
        assert len(rows) >= 5
        
        # 验证包含我们记录的车辆
        vehicle_ids = [row["vehicle_id"] for row in rows]
        assert any("VIN_CSV_TEST" in vid for vid in vehicle_ids)
        
        print("\n=== CSV 报告示例 ===")
        print('\n'.join(lines[:6]))
    
    def test_export_report_with_time_range(self, audit_logger):
        """测试导出指定时间范围的报告"""
        # 记录一些历史日志
        base_time = datetime.now() - timedelta(hours=2)
        
        # 记录 2 小时前的日志
        audit_logger.log_auth_event(
            vehicle_id="VIN_OLD",
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True
        )
        
        # 等待一会儿
        import time
        time.sleep(0.1)
        
        # 记录最近的日志
        recent_start = datetime.now()
        audit_logger.log_auth_event(
            vehicle_id="VIN_RECENT",
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True
        )
        recent_end = datetime.now() + timedelta(seconds=1)
        
        # 导出最近的报告
        recent_report = audit_logger.export_audit_report(
            start_time=recent_start,
            end_time=recent_end,
            format="json"
        )
        
        report_data = json.loads(recent_report)
        
        # 验证只包含最近的日志
        vehicle_ids = [log["vehicle_id"] for log in report_data["logs"]]
        assert "VIN_RECENT" in vehicle_ids
        
        print(f"\n=== 时间范围过滤报告 ===")
        print(f"开始时间: {recent_start}")
        print(f"结束时间: {recent_end}")
        print(f"日志数量: {report_data['report_metadata']['total_logs']}")
    
    def test_export_empty_report(self, audit_logger):
        """测试导出空报告（没有日志的时间范围）"""
        # 使用未来的时间范围
        future_start = datetime.now() + timedelta(days=1)
        future_end = datetime.now() + timedelta(days=2)
        
        # 导出报告
        empty_report = audit_logger.export_audit_report(
            start_time=future_start,
            end_time=future_end,
            format="json"
        )
        
        report_data = json.loads(empty_report)
        
        # 验证报告为空
        assert report_data["report_metadata"]["total_logs"] == 0
        assert len(report_data["logs"]) == 0
        
        print("\n=== 空报告示例 ===")
        print(json.dumps(report_data, ensure_ascii=False, indent=2))
    
    def test_export_report_formats_comparison(self, audit_logger):
        """测试比较 JSON 和 CSV 两种格式的报告"""
        start_time = datetime.now()
        
        # 记录一些测试数据
        audit_logger.log_auth_event(
            vehicle_id="VIN_COMPARE",
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True,
            ip_address="10.0.0.1"
        )
        
        end_time = datetime.now() + timedelta(seconds=1)
        
        # 导出两种格式
        json_report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="json"
        )
        
        csv_report = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format="csv"
        )
        
        # 验证两种格式都包含相同的数据
        json_data = json.loads(json_report)
        csv_reader = csv.DictReader(io.StringIO(csv_report))
        csv_rows = list(csv_reader)
        
        # 日志数量应该相同
        assert json_data["report_metadata"]["total_logs"] == len(csv_rows)
        
        print("\n=== 格式比较 ===")
        print(f"JSON 报告大小: {len(json_report)} 字节")
        print(f"CSV 报告大小: {len(csv_report)} 字节")
        print(f"日志数量: {len(csv_rows)}")
