from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


Status = Literal["pending", "ready", "skipped", "passed", "failed", "not_implemented"]


ROOT_DIR = Path(__file__).resolve().parents[1]
PIPELINE_OUTPUT_DIR = ROOT_DIR / "output" / "pipeline_runs"


@dataclass(frozen=True)
class PipelineStage:
    order: int
    key: str
    name: str
    doc_path: Path
    inputs: tuple[Path, ...] = field(default_factory=tuple)
    outputs: tuple[Path, ...] = field(default_factory=tuple)
    command: tuple[str, ...] | None = None
    implemented: bool = True


STAGES: tuple[PipelineStage, ...] = (
    PipelineStage(
        order=1,
        key="raw-data",
        name="Raw Data",
        doc_path=Path("docs/pipeline/01-raw-data.md"),
        inputs=(Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx"), Path("src/raw_data.py")),
        outputs=(
            Path("output/raw_data_output/raw_schema_summary.csv"),
            Path("output/raw_data_output/raw_missing_summary.csv"),
            Path("output/raw_data_output/column_availability_checklist.csv"),
            Path("output/raw_data_output/raw_data_report.json"),
        ),
        command=(sys.executable, "src/raw_data.py"),
    ),
    PipelineStage(
        order=2,
        key="target-and-cohort",
        name="Target & Cohort Definition",
        doc_path=Path("docs/pipeline/02-target-and-cohort.md"),
        inputs=(
            Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx"),
            Path("src/target_cohort.py"),
        ),
        outputs=(
            Path("output/target_cohort_output/record_level_target.csv"),
            Path("output/target_cohort_output/patient_level_90d_cohort.csv"),
            Path("output/target_cohort_output/patient_level_90d_exclusions.csv"),
            Path("output/target_cohort_output/target_cohort_summary.json"),
        ),
        command=(sys.executable, "src/target_cohort.py"),
    ),
    PipelineStage(
        order=3,
        key="data-cleaning",
        name="Data Cleaning",
        doc_path=Path("docs/pipeline/03-data-cleaning.md"),
        inputs=(Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx"), Path("src/data_cleaning.py")),
        outputs=(
            Path("data/interim/cleaned_stroke_records.csv"),
            Path("output/data_cleaning_output/cleaning_log.csv"),
            Path("output/data_cleaning_output/missing_summary_after_cleaning.csv"),
            Path("output/data_cleaning_output/range_summary_after_cleaning.csv"),
            Path("output/data_cleaning_output/cleaning_report.json"),
        ),
        command=(sys.executable, "src/data_cleaning.py"),
    ),
    PipelineStage(
        order=4,
        key="eda",
        name="EDA",
        doc_path=Path("docs/pipeline/04-eda.md"),
        inputs=(Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx"), Path("src/eda.py")),
        outputs=(
            Path("output/eda_output/column_types.csv"),
            Path("output/eda_output/missing_summary.csv"),
            Path("output/eda_output/numeric_summary.csv"),
            Path("output/eda_output/percentile_summary.csv"),
            Path("output/eda_output/outlier_summary_iqr.csv"),
            Path("output/eda_output/patient_level_target_distribution.csv"),
            Path("output/eda_output/eda_findings_summary.md"),
        ),
        command=(sys.executable, "src/eda.py"),
    ),
    PipelineStage(
        order=5,
        key="feature-engineering",
        name="Feature Engineering",
        doc_path=Path("docs/pipeline/05-feature-engineering.md"),
        inputs=(
            Path("data/interim/cleaned_stroke_records.csv"),
            Path("src/feature_engineering.py"),
        ),
        outputs=(
            Path("data/processed/patient_level_90d_stroke.csv"),
            Path("output/feature_engineering_output/feature_list.csv"),
            Path("output/feature_engineering_output/feature_generation_log.csv"),
            Path("output/feature_engineering_output/feature_engineering_report.json"),
        ),
        command=(sys.executable, "src/feature_engineering.py"),
    ),
    PipelineStage(
        order=6,
        key="modeling",
        name="Modeling",
        doc_path=Path("docs/pipeline/06-modeling.md"),
        inputs=(
            Path("data/processed/patient_level_90d_stroke.csv"),
            Path("src/modeling.py"),
        ),
        outputs=(
            Path("output/model_output/patient_level_90d_cv_metrics_summary.csv"),
            Path("output/model_output/patient_level_90d_holdout_metrics.csv"),
            Path("output/model_output/patient_level_90d_model_report.txt"),
        ),
        command=(sys.executable, "src/modeling.py"),
    ),
    PipelineStage(
        order=7,
        key="feature-importance",
        name="Feature Importance",
        doc_path=Path("docs/pipeline/07-feature-importance.md"),
        inputs=(
            Path("data/processed/patient_level_90d_stroke.csv"),
            Path("output/model_output/patient_level_90d_holdout_metrics.csv"),
            Path("src/feature_importance.py"),
        ),
        outputs=(
            Path("output/model_output/patient_level_90d_feature_importance_comparison.csv"),
            Path("output/model_output/patient_level_90d_feature_importance_comparison.png"),
            Path("output/model_output/patient_level_90d_shap_importance_xgboost.csv"),
            Path("output/model_output/patient_level_90d_feature_importance_report.txt"),
        ),
        command=(sys.executable, "src/feature_importance.py"),
    ),
    PipelineStage(
        order=8,
        key="validation",
        name="Validation",
        doc_path=Path("docs/pipeline/08-validation.md"),
        inputs=(Path("output/model_output"),),
        outputs=(
            Path("output/model_output/patient_level_90d_holdout_metrics.csv"),
            Path("output/model_output/patient_level_90d_cv_metrics_summary.csv"),
            Path("output/model_output/patient_level_90d_model_report.txt"),
        ),
        command=None,
    ),
    PipelineStage(
        order=9,
        key="deployment-optional",
        name="Deployment Optional",
        doc_path=Path("docs/pipeline/09-deployment-optional.md"),
        inputs=(Path("docs/pipeline/09-deployment-optional.md"),),
        outputs=(),
        command=None,
        implemented=False,
    ),
)


def resolve(path: Path) -> Path:
    return ROOT_DIR / path


def path_exists(path: Path) -> bool:
    absolute_path = resolve(path)
    if absolute_path.is_dir():
        return any(absolute_path.iterdir())
    return absolute_path.exists()


def check_paths(paths: tuple[Path, ...]) -> list[dict[str, object]]:
    return [
        {
            "path": str(path),
            "exists": path_exists(path),
        }
        for path in paths
    ]


def missing_paths(paths: tuple[Path, ...]) -> list[str]:
    return [str(path) for path in paths if not path_exists(path)]


def stage_to_record(stage: PipelineStage, status: Status, message: str) -> dict[str, object]:
    return {
        "order": stage.order,
        "key": stage.key,
        "name": stage.name,
        "status": status,
        "message": message,
        "doc": str(stage.doc_path),
        "inputs": check_paths(stage.inputs),
        "outputs": check_paths(stage.outputs),
        "command": list(stage.command) if stage.command else None,
    }


def select_stages(selected: str) -> list[PipelineStage]:
    if selected == "all":
        return list(STAGES)
    matches = [stage for stage in STAGES if stage.key == selected]
    if not matches:
        valid = ", ".join(["all", *[stage.key for stage in STAGES]])
        raise ValueError(f"Unknown stage '{selected}'. Valid stages: {valid}")
    return matches


def run_stage(stage: PipelineStage, dry_run: bool) -> dict[str, object]:
    missing_inputs = missing_paths(stage.inputs)
    if missing_inputs:
        return stage_to_record(stage, "failed", f"Missing inputs: {', '.join(missing_inputs)}")

    if not stage.implemented:
        return stage_to_record(stage, "not_implemented", "Stage has a plan document but no production code yet.")

    if stage.command is None:
        missing_outputs = missing_paths(stage.outputs)
        if missing_outputs:
            return stage_to_record(
                stage,
                "pending",
                f"No command configured. Expected outputs are missing: {', '.join(missing_outputs)}",
            )
        return stage_to_record(stage, "passed", "Expected outputs already exist.")

    if dry_run:
        command = " ".join(stage.command)
        return stage_to_record(stage, "ready", f"Dry run only. Command ready: {command}")

    completed = subprocess.run(
        stage.command,
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            **stage_to_record(stage, "failed", f"Command failed with exit code {completed.returncode}."),
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }

    missing_outputs = missing_paths(stage.outputs)
    if missing_outputs:
        return {
            **stage_to_record(
                stage,
                "failed",
                f"Command completed, but expected outputs are missing: {', '.join(missing_outputs)}",
            ),
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }

    return {
        **stage_to_record(stage, "passed", "Command completed and expected outputs exist."),
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def write_manifest(records: list[dict[str, object]], dry_run: bool) -> Path:
    PIPELINE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_path = PIPELINE_OUTPUT_DIR / f"pipeline_manifest_{timestamp}.json"
    payload = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "dry_run": dry_run,
        "overview_doc": "docs/pipeline/00-pipeline-overview.md",
        "records": records,
    }
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def print_summary(records: list[dict[str, object]], manifest_path: Path) -> None:
    print("Pipeline summary")
    for record in records:
        print(f"- {record['order']}. {record['name']}: {record['status']} - {record['message']}")
    print(f"Manifest: {manifest_path.relative_to(ROOT_DIR)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run or inspect the stroke prediction pipeline overview.")
    parser.add_argument(
        "--stage",
        default="all",
        help="Stage key to run/check, or 'all'. Example: eda, feature-importance, validation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check configured stages without running stage commands.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    stages = select_stages(args.stage)
    records = [run_stage(stage, dry_run=args.dry_run) for stage in stages]
    manifest_path = write_manifest(records, dry_run=args.dry_run)
    print_summary(records, manifest_path)

    failed = any(record["status"] == "failed" for record in records)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
