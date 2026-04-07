"""审计日志查询 API

提供审计日志查询和导出功能。

验证需求: 12.1, 12.2, 12.3, 12.4, 12.5
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Response
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from src.db.postgres import PostgreSQLConnection
from config.database import PostgreSQLConfig
from src.audit_logger import AuditLogger
from src.models.enums import EventType
from src.api.main import verify_token

router = APIRouter()


class AuditLogEntry(BaseModel):
    """审计日志条目"""
    log_id: str
    timestamp: datetime
    event_type: str
    vehicle_id: str
    operation_result: bool
    details: str
    ip_address: str


class AuditLogListResponse(BaseModel):
    """审计日志列表响应"""
    total: int
    logs: List[AuditLogEntry]


@router.get("/logs", response_model=AuditLogListResponse)
async def query_audit_logs(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    vehicle_id: Optional[str] = Query(None, description="车辆标识"),
    event_type: Optional[str] = Query(None, description="事件类型"),
    operation_result: Optional[bool] = Query(None, description="操作结果"),
    limit: int = Query(100, description="返回记录数限制"),
    user: str = Depends(verify_token)
):
    """查询审计日志
    
    支持按以下条件过滤：
    - 时间范围（start_time 和 end_time）
    - 车辆标识（vehicle_id）
    - 事件类型（event_type）
    - 操作结果（operation_result）
    
    参数:
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        vehicle_id: 车辆标识（可选）
        event_type: 事件类型（可选）
        operation_result: 操作结果（可选）
        limit: 返回记录数限制
        
    返回:
        AuditLogListResponse: 审计日志列表
        
    验证需求: 12.1, 12.2, 12.3, 12.4
    """
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        audit_logger = AuditLogger(db_conn)
        
        # 转换事件类型字符串为枚举
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = EventType(event_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的事件类型: {event_type}"
                )
        
        # 查询审计日志
        logs = audit_logger.query_audit_logs(
            start_time=start_time,
            end_time=end_time,
            vehicle_id=vehicle_id,
            event_type=event_type_enum,
            operation_result=operation_result
        )
        
        # 限制返回记录数
        logs = logs[:limit]
        
        # 转换为响应模型
        log_entries = []
        for log in logs:
            entry = AuditLogEntry(
                log_id=log.log_id,
                timestamp=log.timestamp,
                event_type=log.event_type.value,
                vehicle_id=log.vehicle_id,
                operation_result=log.operation_result,
                details=log.details,
                ip_address=log.ip_address
            )
            log_entries.append(entry)
        
        db_conn.close()
        
        return AuditLogListResponse(
            total=len(log_entries),
            logs=log_entries
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"查询审计日志失败: {str(e)}"
        )


@router.get("/export")
async def export_audit_report(
    start_time: datetime = Query(..., description="开始时间"),
    end_time: datetime = Query(..., description="结束时间"),
    format: str = Query("json", description="导出格式（json 或 csv）"),
    user: str = Depends(verify_token)
):
    """导出审计报告
    
    生成包含指定时间范围内所有审计日志的报告。
    支持 JSON 和 CSV 两种格式。
    
    参数:
        start_time: 开始时间
        end_time: 结束时间
        format: 报告格式（json 或 csv）
        
    返回:
        审计报告文件
        
    验证需求: 12.5
    """
    try:
        if format not in ["json", "csv"]:
            raise HTTPException(
                status_code=400,
                detail="不支持的格式，请使用 json 或 csv"
            )
        
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        audit_logger = AuditLogger(db_conn)
        
        # 导出审计报告
        report_content = audit_logger.export_audit_report(
            start_time=start_time,
            end_time=end_time,
            format=format
        )
        
        db_conn.close()
        
        # 设置响应头
        if format == "json":
            media_type = "application/json"
            filename = f"audit_report_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.json"
        else:  # csv
            media_type = "text/csv"
            filename = f"audit_report_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.csv"
        
        return Response(
            content=report_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"导出审计报告失败: {str(e)}"
        )
