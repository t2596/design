"""审计日志记录功能

实现审计日志的记录功能，包括：
- 认证事件记录
- 数据传输记录
- 证书操作记录
- 生成唯一日志标识符
- 限制详细信息长度（1024 字符）
- 持久化到 PostgreSQL
- 审计日志查询功能
- 审计报告导出功能
"""

import uuid
import json
import csv
import io
from datetime import datetime
from typing import Optional, List, Dict, Any
from src.models.audit import AuditLog
from src.models.enums import EventType
from src.db.postgres import PostgreSQLConnection
from config import PostgreSQLConfig


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, db_connection: PostgreSQLConnection):
        """初始化审计日志记录器
        
        Args:
            db_connection: PostgreSQL 数据库连接
        """
        self.db = db_connection
    
    def _generate_log_id(self) -> str:
        """生成唯一日志标识符
        
        Returns:
            唯一的日志 ID（UUID 格式）
        """
        return str(uuid.uuid4())
    
    def _truncate_details(self, details: str) -> str:
        """限制详细信息长度到 1024 字符
        
        Args:
            details: 原始详细信息
            
        Returns:
            截断后的详细信息（最多 1024 字符）
        """
        if len(details) > 1024:
            return details[:1024]
        return details
    
    def _persist_log(self, log: AuditLog) -> bool:
        """持久化审计日志到 PostgreSQL
        
        Args:
            log: 审计日志对象
            
        Returns:
            是否成功持久化
        """
        query = """
            INSERT INTO audit_logs (log_id, timestamp, event_type, vehicle_id, 
                                   operation_result, details, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            log.log_id,
            log.timestamp,
            log.event_type.value,
            log.vehicle_id,
            log.operation_result,
            log.details,
            log.ip_address
        )
        
        try:
            rows_affected = self.db.execute_update(query, params)
            return rows_affected > 0
        except Exception as e:
            # 记录错误但不抛出异常，避免影响主业务流程
            print(f"Failed to persist audit log: {e}")
            return False
    
    def log_auth_event(
        self,
        vehicle_id: str,
        event_type: EventType,
        result: bool,
        ip_address: Optional[str] = None,
        details: Optional[str] = None
    ) -> str:
        """记录认证事件
        
        Args:
            vehicle_id: 车辆标识
            event_type: 事件类型（AUTHENTICATION_SUCCESS 或 AUTHENTICATION_FAILURE）
            result: 操作结果（True 表示成功，False 表示失败）
            ip_address: IP 地址（可选）
            details: 详细信息（可选）
            
        Returns:
            生成的日志 ID
        """
        log_id = self._generate_log_id()
        
        # 构造详细信息
        if details is None:
            if result:
                details = f"车辆 {vehicle_id} 认证成功"
            else:
                details = f"车辆 {vehicle_id} 认证失败"
        
        details = self._truncate_details(details)
        
        # 创建审计日志对象
        log = AuditLog(
            log_id=log_id,
            timestamp=datetime.now(),
            event_type=event_type,
            vehicle_id=vehicle_id,
            operation_result=result,
            details=details,
            ip_address=ip_address or "unknown"
        )
        
        # 持久化到数据库
        self._persist_log(log)
        
        return log_id
    
    def log_data_transfer(
        self,
        vehicle_id: str,
        data_size: int,
        encrypted: bool,
        ip_address: Optional[str] = None,
        details: Optional[str] = None
    ) -> str:
        """记录数据传输事件
        
        Args:
            vehicle_id: 车辆标识
            data_size: 数据大小（字节）
            encrypted: 是否加密
            ip_address: IP 地址（可选）
            details: 详细信息（可选）
            
        Returns:
            生成的日志 ID
        """
        log_id = self._generate_log_id()
        
        # 构造详细信息
        if details is None:
            encryption_status = "加密" if encrypted else "未加密"
            details = f"车辆 {vehicle_id} 传输数据 {data_size} 字节（{encryption_status}）"
        
        details = self._truncate_details(details)
        
        # 根据加密状态选择事件类型
        event_type = EventType.DATA_ENCRYPTED if encrypted else EventType.DATA_DECRYPTED
        
        # 创建审计日志对象
        log = AuditLog(
            log_id=log_id,
            timestamp=datetime.now(),
            event_type=event_type,
            vehicle_id=vehicle_id,
            operation_result=True,
            details=details,
            ip_address=ip_address or "unknown"
        )
        
        # 持久化到数据库
        self._persist_log(log)
        
        return log_id
    
    def log_certificate_operation(
        self,
        operation: str,
        cert_id: str,
        vehicle_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[str] = None
    ) -> str:
        """记录证书操作事件
        
        Args:
            operation: 操作类型（"issued" 或 "revoked"）
            cert_id: 证书序列号
            vehicle_id: 车辆标识（可选，用于车辆证书）
            ip_address: IP 地址（可选）
            details: 详细信息（可选）
            
        Returns:
            生成的日志 ID
        """
        log_id = self._generate_log_id()
        
        # 根据操作类型选择事件类型
        if operation.lower() == "issued":
            event_type = EventType.CERTIFICATE_ISSUED
            operation_text = "颁发"
        elif operation.lower() == "revoked":
            event_type = EventType.CERTIFICATE_REVOKED
            operation_text = "撤销"
        else:
            # 默认使用 CERTIFICATE_ISSUED
            event_type = EventType.CERTIFICATE_ISSUED
            operation_text = operation
        
        # 构造详细信息
        if details is None:
            details = f"证书 {cert_id} {operation_text}"
            if vehicle_id:
                details += f"（车辆: {vehicle_id}）"
        
        details = self._truncate_details(details)
        
        # 创建审计日志对象
        log = AuditLog(
            log_id=log_id,
            timestamp=datetime.now(),
            event_type=event_type,
            vehicle_id=vehicle_id or "system",
            operation_result=True,
            details=details,
            ip_address=ip_address or "unknown"
        )
        
        # 持久化到数据库
        self._persist_log(log)
        
        return log_id
    
    def query_audit_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        vehicle_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        operation_result: Optional[bool] = None
    ) -> List[AuditLog]:
        """查询审计日志
        
        支持按以下条件过滤：
        - 时间范围（start_time 和 end_time）
        - 车辆标识（vehicle_id）
        - 事件类型（event_type）
        - 操作结果（operation_result）
        
        Args:
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            vehicle_id: 车辆标识（可选）
            event_type: 事件类型（可选）
            operation_result: 操作结果（可选）
            
        Returns:
            符合条件的审计日志列表
        """
        # 构建查询语句
        query = """
            SELECT log_id, timestamp, event_type, vehicle_id, 
                   operation_result, details, ip_address
            FROM audit_logs
            WHERE 1=1
        """
        params = []
        
        # 添加时间范围过滤
        if start_time is not None:
            query += " AND timestamp >= %s"
            params.append(start_time)
        
        if end_time is not None:
            query += " AND timestamp <= %s"
            params.append(end_time)
        
        # 添加车辆标识过滤
        if vehicle_id is not None:
            query += " AND vehicle_id = %s"
            params.append(vehicle_id)
        
        # 添加事件类型过滤
        if event_type is not None:
            query += " AND event_type = %s"
            params.append(event_type.value)
        
        # 添加操作结果过滤
        if operation_result is not None:
            query += " AND operation_result = %s"
            params.append(operation_result)
        
        # 按时间戳降序排序
        query += " ORDER BY timestamp DESC"
        
        try:
            # 执行查询
            rows = self.db.execute_query(query, tuple(params) if params else None)
            
            # 将查询结果转换为 AuditLog 对象
            logs = []
            for row in rows:
                log = AuditLog(
                    log_id=row['log_id'],
                    timestamp=row['timestamp'],
                    event_type=EventType(row['event_type']),
                    vehicle_id=row['vehicle_id'],
                    operation_result=row['operation_result'],
                    details=row['details'],
                    ip_address=row['ip_address']
                )
                logs.append(log)
            
            return logs
        except Exception as e:
            # 记录错误但不抛出异常
            print(f"Failed to query audit logs: {e}")
            return []
    
    def export_audit_report(
        self,
        start_time: datetime,
        end_time: datetime,
        format: str = "json"
    ) -> str:
        """导出审计报告
        
        生成包含指定时间范围内所有审计日志的报告。
        支持 JSON 和 CSV 两种格式。
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            format: 报告格式，"json" 或 "csv"（默认为 "json"）
            
        Returns:
            报告内容（JSON 字符串或 CSV 字符串）
            
        Raises:
            ValueError: 如果格式不支持
        """
        # 验证格式参数
        if format not in ["json", "csv"]:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")
        
        # 查询指定时间范围内的所有日志
        logs = self.query_audit_logs(start_time=start_time, end_time=end_time)
        
        # 根据格式生成报告
        if format == "json":
            return self._export_as_json(logs, start_time, end_time)
        else:  # csv
            return self._export_as_csv(logs, start_time, end_time)
    
    def _export_as_json(
        self,
        logs: List[AuditLog],
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """将审计日志导出为 JSON 格式
        
        Args:
            logs: 审计日志列表
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            JSON 格式的报告字符串
        """
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_logs": len(logs)
            },
            "logs": []
        }
        
        # 转换日志为字典格式
        for log in logs:
            log_dict = {
                "log_id": log.log_id,
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type.value,
                "vehicle_id": log.vehicle_id,
                "operation_result": log.operation_result,
                "details": log.details,
                "ip_address": log.ip_address
            }
            report["logs"].append(log_dict)
        
        # 转换为 JSON 字符串（带缩进以提高可读性）
        return json.dumps(report, ensure_ascii=False, indent=2)
    
    def _export_as_csv(
        self,
        logs: List[AuditLog],
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """将审计日志导出为 CSV 格式
        
        Args:
            logs: 审计日志列表
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            CSV 格式的报告字符串
        """
        # 使用 StringIO 作为 CSV 写入的缓冲区
        output = io.StringIO()
        
        # 定义 CSV 列
        fieldnames = [
            "log_id",
            "timestamp",
            "event_type",
            "vehicle_id",
            "operation_result",
            "details",
            "ip_address"
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        # 写入表头
        writer.writeheader()
        
        # 写入日志数据
        for log in logs:
            writer.writerow({
                "log_id": log.log_id,
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type.value,
                "vehicle_id": log.vehicle_id,
                "operation_result": log.operation_result,
                "details": log.details,
                "ip_address": log.ip_address
            })
        
        # 获取 CSV 字符串
        csv_content = output.getvalue()
        output.close()
        
        return csv_content


# 便捷函数，用于快速创建审计日志记录器
def create_audit_logger(config: PostgreSQLConfig) -> AuditLogger:
    """创建审计日志记录器
    
    Args:
        config: PostgreSQL 配置
        
    Returns:
        审计日志记录器实例
    """
    db_connection = PostgreSQLConnection(config)
    return AuditLogger(db_connection)
