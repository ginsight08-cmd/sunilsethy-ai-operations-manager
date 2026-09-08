# BPO Operations Excellence

Open BPO, then select **Operations Excellence** below the dashboard heading.
The existing authentication, 15-day trial and subscription gate apply to both
BPO workspaces. Billing behavior is unchanged.

## Workflow

1. Analyze operational data in Performance Dashboard. Overview displays the
   latest findings; copy a finding into a new improvement project.
2. Define the customer need/CTQ, scope, SIPOC, owner and due date.
3. Record the metric, baseline, target and measurement plan.
4. Investigate with 5 Whys and fishbone hypotheses. Record evidence supporting
   the validated root cause. Score FMEA severity, occurrence and detection.
5. Plan containment, corrective action, preventive action and a PDCA pilot.
6. Record the actual result, effectiveness evidence, reviewer, control plan
   and customer-value outcome. Closure requires those records, confirmed
   effectiveness and the Control phase. Review is a recorded user assertion,
   not an independent approval or tamper-proof audit.

## Tools and assumptions

- Workforce capacity = forecast contacts × AHT seconds / 3600. Required staff
  is workload hours divided by paid hours × occupancy × (1 − shrinkage),
  rounded up. Inputs refer to one period. This is not a voice queue service
  level, interval scheduler, forecast model or multi-skill optimizer.
- Pareto aggregates valid nonnegative Error_Count by Error_Category from the
  latest upload and reports excluded rows. Missing categories are Unspecified.
- Inspection yield uses defective units / inspected units. DPMO uses total
  defects / (inspected units × opportunities per unit). Enter these separately;
  employee quality averages are not assumed to be inspection counts.
- Lean cycle efficiency = value-added time / end-to-end lead time.
- FMEA RPN = severity × occurrence × detection, each scored 1–10. High severity
  is highlighted independently. RPN is not an AIAG-VDA Action Priority rating.

## Saving work

Projects are session drafts, isolated by signed-in user and cleared on logout.
Download the JSON backup from Overview before refreshing/leaving the session.
Restore imports validated projects as new records without overwriting existing
ones. There is no cloud project database or cross-user collaboration in this
release. Up to 100 projects and a 1 MB import are supported. Calculator inputs
and operational uploads are not included in the project backup.

## Validation

Run `python -m unittest test_excellence test_excellence_ui -v` from the repo.
The UI tests use a local preview without production accounts or records.

Framework references: https://asq.org/quality-resources/dmaic,
https://asq.org/quality-resources/five-whys,
https://asq.org/quality-resources/fmea,
https://docs.genesys.com/Documentation/WM.
