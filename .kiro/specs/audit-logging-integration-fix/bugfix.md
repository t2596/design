# Bugfix Requirements Document

## Introduction

The vehicle IoT security gateway system has a fully implemented audit logging infrastructure (AuditLogger class, API endpoints, database table, and frontend interface), but audit logs are not being recorded because the audit logging functions are not being called in the actual operations. This results in an empty `audit_logs` table and no data displayed in the Web interface audit log query page.

The bug affects three critical operation areas:
- Vehicle authentication and registration operations
- Certificate management operations (issuance and revocation)
- Data transmission operations (encrypted and unencrypted)

This bugfix will integrate the existing AuditLogger methods into the operation endpoints to ensure all security-relevant events are properly logged.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a vehicle registers successfully via `/api/auth/register` THEN the system does not call `audit_logger.log_auth_event()` and no authentication event is recorded in the audit_logs table

1.2 WHEN a vehicle registration fails via `/api/auth/register` THEN the system does not call `audit_logger.log_auth_event()` and no authentication failure event is recorded in the audit_logs table

1.3 WHEN encrypted vehicle data is received via `/api/auth/data/secure` THEN the system does not call `audit_logger.log_data_transfer()` and no data transfer event is recorded in the audit_logs table

1.4 WHEN unencrypted vehicle data is received via `/api/auth/data` THEN the system does not call `audit_logger.log_data_transfer()` and no data transfer event is recorded in the audit_logs table

1.5 WHEN a certificate is issued via `/api/certificates/issue` THEN the system does not call `audit_logger.log_certificate_operation()` and no certificate issuance event is recorded in the audit_logs table

1.6 WHEN a certificate is revoked via `/api/certificates/revoke` THEN the system does not call `audit_logger.log_certificate_operation()` and no certificate revocation event is recorded in the audit_logs table

### Expected Behavior (Correct)

2.1 WHEN a vehicle registers successfully via `/api/auth/register` THEN the system SHALL call `audit_logger.log_auth_event()` with EventType.AUTHENTICATION_SUCCESS and record the authentication event in the audit_logs table

2.2 WHEN a vehicle registration fails via `/api/auth/register` THEN the system SHALL call `audit_logger.log_auth_event()` with EventType.AUTHENTICATION_FAILURE and record the authentication failure event in the audit_logs table

2.3 WHEN encrypted vehicle data is received via `/api/auth/data/secure` THEN the system SHALL call `audit_logger.log_data_transfer()` with encrypted=True and record the data transfer event in the audit_logs table

2.4 WHEN unencrypted vehicle data is received via `/api/auth/data` THEN the system SHALL call `audit_logger.log_data_transfer()` with encrypted=False and record the data transfer event in the audit_logs table

2.5 WHEN a certificate is issued via `/api/certificates/issue` THEN the system SHALL call `audit_logger.log_certificate_operation()` with operation="issued" and record the certificate issuance event in the audit_logs table

2.6 WHEN a certificate is revoked via `/api/certificates/revoke` THEN the system SHALL call `audit_logger.log_certificate_operation()` with operation="revoked" and record the certificate revocation event in the audit_logs table

### Unchanged Behavior (Regression Prevention)

3.1 WHEN audit logging functions are called THEN the system SHALL CONTINUE TO return successful responses for the main operations even if audit logging fails

3.2 WHEN the AuditLogger class methods are called THEN the system SHALL CONTINUE TO generate unique log IDs using UUID format

3.3 WHEN the AuditLogger class methods are called THEN the system SHALL CONTINUE TO truncate details to 1024 characters maximum

3.4 WHEN the AuditLogger class methods are called THEN the system SHALL CONTINUE TO persist logs to the PostgreSQL audit_logs table

3.5 WHEN audit logs are queried via `/api/audit/logs` THEN the system SHALL CONTINUE TO support filtering by time range, vehicle_id, event_type, and operation_result

3.6 WHEN audit reports are exported via `/api/audit/export` THEN the system SHALL CONTINUE TO support JSON and CSV formats

3.7 WHEN vehicle registration operations complete THEN the system SHALL CONTINUE TO return VehicleRegisterResponse with session_id and session_key

3.8 WHEN certificate operations complete THEN the system SHALL CONTINUE TO return appropriate certificate information in the response

3.9 WHEN data transmission operations complete THEN the system SHALL CONTINUE TO save vehicle data to the vehicle_data table
