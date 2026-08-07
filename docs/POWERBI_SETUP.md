# Power BI Setup

Import these PostgreSQL views:

- `reporting.vw_dtc_detail`
- `reporting.vw_environment_signal_detail`
- `reporting.vw_pipeline_status`
- `reporting.vw_ecu_health`
- `reporting.vw_release_summary`
- `reporting.vw_data_quality`

Create a one-to-many relationship from `vw_dtc_detail[dtc_event_id]` to `vw_environment_signal_detail[dtc_event_id]`.

Use `vw_dtc_detail` for DTC counts and occurrence totals. Do not calculate DTC totals from the signal view.

For Power BI Service refresh, configure the PostgreSQL gateway/data-source credentials and set the `POWERBI_*` values in the local `.env`. The service principal must have access to the workspace and semantic model.
