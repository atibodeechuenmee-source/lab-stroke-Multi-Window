from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


STROKE_PATTERN = re.compile(r"^I6[0-9][0-9A-Z]*$", re.IGNORECASE)


@dataclass(frozen=True)
class Config:
    input_path: Path = Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx")
    output_dir: Path = Path("output/target_cohort_output")
    horizon_days: int = 90


def require_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {', '.join(missing)}")


def build_stroke_flag(df: pd.DataFrame) -> pd.Series:
    diagnosis = df["PrincipleDiagnosis"].astype("string").str.strip().fillna("")
    return diagnosis.str.contains(STROKE_PATTERN, regex=True, na=False).astype(int)


def load_target_source(config: Config) -> pd.DataFrame:
    if not config.input_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {config.input_path}")

    df = pd.read_excel(config.input_path)
    require_columns(df, ("hn", "vstdate", "PrincipleDiagnosis"))
    df["vstdate"] = pd.to_datetime(df["vstdate"], errors="coerce")
    df["stroke_flag"] = build_stroke_flag(df)
    return df


def build_record_level_target(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["hn", "vstdate", "PrincipleDiagnosis", "stroke_flag"]
    record_target = df[columns].copy()
    record_target["has_required_patient_fields"] = record_target["hn"].notna() & record_target["vstdate"].notna()
    return record_target


def choose_patient_index(group: pd.DataFrame, max_date: pd.Timestamp, horizon_days: int) -> tuple[dict[str, object] | None, str]:
    group = group.dropna(subset=["vstdate"]).sort_values("vstdate")
    if group.empty:
        return None, "no_valid_visit_date"

    stroke_rows = group[group["stroke_flag"] == 1]
    if not stroke_rows.empty:
        event_date = stroke_rows["vstdate"].min()
        prior_rows = group[group["vstdate"] < event_date]
        if prior_rows.empty:
            return None, "positive_no_prior_visit"

        index_row = prior_rows.iloc[-1]
        days_to_event = int((event_date - index_row["vstdate"]).days)
        if 1 <= days_to_event <= horizon_days:
            return (
                {
                    "hn": index_row["hn"],
                    "index_date": index_row["vstdate"],
                    "event_date": event_date,
                    "days_to_event": days_to_event,
                    "stroke_3m": 1,
                    "record_count": len(group),
                    "history_record_count": int((group["vstdate"] <= index_row["vstdate"]).sum()),
                },
                "included_positive_within_horizon",
            )
        return None, "positive_outside_horizon"

    eligible = group[group["vstdate"] <= max_date - pd.Timedelta(days=horizon_days)]
    if eligible.empty:
        return None, "negative_insufficient_followup"

    index_row = eligible.iloc[-1]
    return (
        {
            "hn": index_row["hn"],
            "index_date": index_row["vstdate"],
            "event_date": pd.NaT,
            "days_to_event": pd.NA,
            "stroke_3m": 0,
            "record_count": len(group),
            "history_record_count": int((group["vstdate"] <= index_row["vstdate"]).sum()),
        },
        "included_negative",
    )


def build_patient_level_cohort(df: pd.DataFrame, horizon_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = df.dropna(subset=["hn"]).copy()
    max_date = source["vstdate"].max()
    rows: list[dict[str, object]] = []
    exclusion_records: list[dict[str, object]] = []

    for hn, group in source.groupby("hn", sort=False):
        row, reason = choose_patient_index(group, max_date, horizon_days)
        if row is None:
            exclusion_records.append({"hn": hn, "reason": reason, "record_count": len(group)})
            continue
        row["cohort_reason"] = reason
        rows.append(row)

    cohort = pd.DataFrame(rows)
    exclusions = pd.DataFrame(exclusion_records)
    return cohort, exclusions


def summarize_record_level(record_target: pd.DataFrame) -> dict[str, object]:
    valid_records = record_target["has_required_patient_fields"]
    positives = int(record_target["stroke_flag"].sum())
    total = int(len(record_target))
    return {
        "record_count": total,
        "valid_patient_record_count": int(valid_records.sum()),
        "invalid_patient_record_count": int((~valid_records).sum()),
        "positive_record_count": positives,
        "negative_record_count": int(total - positives),
        "record_level_prevalence_percent": round(positives / max(total, 1) * 100, 2),
        "invalid_vstdate_count": int(record_target["vstdate"].isna().sum()),
        "missing_hn_count": int(record_target["hn"].isna().sum()),
    }


def summarize_patient_level(cohort: pd.DataFrame, exclusions: pd.DataFrame) -> dict[str, object]:
    if cohort.empty:
        positives = 0
        negatives = 0
    else:
        positives = int(cohort["stroke_3m"].sum())
        negatives = int((cohort["stroke_3m"] == 0).sum())

    exclusion_counts = (
        exclusions["reason"].value_counts(dropna=False).rename_axis("reason").reset_index(name="patient_count")
        if not exclusions.empty
        else pd.DataFrame(columns=["reason", "patient_count"])
    )
    return {
        "patient_cohort_count": int(len(cohort)),
        "positive_patient_count": positives,
        "negative_patient_count": negatives,
        "patient_level_prevalence_percent": round(positives / max(len(cohort), 1) * 100, 2),
        "excluded_patient_count": int(len(exclusions)),
        "exclusion_counts": exclusion_counts.to_dict(orient="records"),
    }


def write_outputs(
    record_target: pd.DataFrame,
    cohort: pd.DataFrame,
    exclusions: pd.DataFrame,
    payload: dict[str, object],
    config: Config,
) -> dict[str, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "record_level_target": config.output_dir / "record_level_target.csv",
        "patient_level_cohort": config.output_dir / "patient_level_90d_cohort.csv",
        "exclusion_summary": config.output_dir / "patient_level_90d_exclusions.csv",
        "cohort_summary": config.output_dir / "target_cohort_summary.json",
        "report": config.output_dir / "target_cohort_report.md",
    }

    record_target.to_csv(output_paths["record_level_target"], index=False, encoding="utf-8-sig")
    cohort.to_csv(output_paths["patient_level_cohort"], index=False, encoding="utf-8-sig")
    exclusions.to_csv(output_paths["exclusion_summary"], index=False, encoding="utf-8-sig")
    output_paths["cohort_summary"].write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Target & Cohort Report",
        "",
        f"- Run at: {payload['run_at']}",
        f"- Raw data: `{payload['raw_data_path']}`",
        f"- Stroke definition: `{payload['stroke_definition']}`",
        f"- Horizon days: {payload['horizon_days']}",
        "",
        "## Record-Level Target",
        "",
    ]
    for key, value in payload["record_level_summary"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Patient-Level 90-Day Cohort", ""])
    for key, value in payload["patient_level_summary"].items():
        if key == "exclusion_counts":
            continue
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Exclusions", ""])
    exclusion_counts = payload["patient_level_summary"]["exclusion_counts"]
    if exclusion_counts:
        for item in exclusion_counts:
            lines.append(f"- {item['reason']}: {item['patient_count']}")
    else:
        lines.append("- none")

    lines.extend(["", "## Outputs", ""])
    for key, path in output_paths.items():
        lines.append(f"- {key}: `{path}`")

    output_paths["report"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_paths


def run(config: Config) -> dict[str, object]:
    df = load_target_source(config)
    record_target = build_record_level_target(df)
    cohort, exclusions = build_patient_level_cohort(df, config.horizon_days)

    payload: dict[str, object] = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_data_path": str(config.input_path),
        "stroke_definition": "PrincipleDiagnosis ICD-10 I60-I69*",
        "horizon_days": config.horizon_days,
        "checks": {
            "principle_diagnosis_excluded_from_features": True,
            "patient_level_features_must_use_history_at_or_before_index_date": True,
        },
        "record_level_summary": summarize_record_level(record_target),
        "patient_level_summary": summarize_patient_level(cohort, exclusions),
    }
    output_paths = write_outputs(record_target, cohort, exclusions, payload, config)
    payload["outputs"] = {key: str(path) for key, path in output_paths.items()}
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Define stroke target and patient-level 90-day cohort.")
    parser.add_argument("--input", default=str(Config.input_path), help="Path to the raw Excel file.")
    parser.add_argument("--output-dir", default=str(Config.output_dir), help="Directory for target/cohort outputs.")
    parser.add_argument("--horizon-days", type=int, default=Config.horizon_days, help="Prediction horizon in days.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = Config(input_path=Path(args.input), output_dir=Path(args.output_dir), horizon_days=args.horizon_days)
    payload = run(config)
    record_summary = payload["record_level_summary"]
    patient_summary = payload["patient_level_summary"]
    print("Target and cohort definition completed")
    print(f"Record rows: {record_summary['record_count']:,}")
    print(f"Record stroke prevalence: {record_summary['record_level_prevalence_percent']}%")
    print(f"Patient cohort rows: {patient_summary['patient_cohort_count']:,}")
    print(f"Patient 90-day stroke prevalence: {patient_summary['patient_level_prevalence_percent']}%")
    print(f"Output directory: {config.output_dir}")


if __name__ == "__main__":
    main()
