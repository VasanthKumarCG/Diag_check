# Field Extension Map

## Existing structured facts retained

- Report: file_id, report_id, file_name, file_path, VIN, SW I-Step, SA codes.
- ECU: ECU name, hardware, bootloader, software, coding, diagnostic address, calibration, network, secure boot, OTA state.
- DTC: event ID, ECU, code, description, normalized category, status, counters, priority, severity, first/last detected, confirmation, possible cause, recommended check, risk score, extended JSON attributes.
- Environment: signal ID, signal name, text value, numeric value, event timestamp.
- Operations: file hash, process run, quality issues, rows loaded, process status and error message.

## New approved-reference fields

- Vehicle model, software variant, release sequence/date/type and baseline flag.
- ECU relationship, communication network, direction and criticality.
- ECU department, team, owner and escalation path.
- Risk threshold, band, response SLA and approver.

## New knowledge fields

- Source type/ID/name/URI and approval status.
- Primary ECU, related ECUs and DTC codes.
- Root cause, corrective action, fix release and validation result.
- Chunk text, metadata, embedding model and dimension.
- Retrieval audit, AI response and engineer feedback.

Do not infer missing factual fields using an LLM. Populate them from approved source systems or controlled engineering input.
