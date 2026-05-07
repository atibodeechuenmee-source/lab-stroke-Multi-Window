"""End-to-end orchestrator for the multi-window stroke pipeline.

ไฟล์นี้ไม่ถือ logic ของแต่ละ stage ไว้เองแล้ว แต่ทำหน้าที่เรียกใช้โมดูล
Stage 01-08 ที่แยกไว้ใน `src/` เพื่อให้ pipeline รวมกับ stage แยกใช้โค้ดชุดเดียวกัน
และลดความเสี่ยงที่ logic สองที่ไม่ตรงกันในอนาคต
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.data_cleaning import DataCleaningConfig, run_data_cleaning
from src.eda import EDAConfig, run_eda
from src.feature_engineering import FeatureEngineeringConfig, run_feature_engineering
from src.feature_importance import FeatureImportanceConfig, run_feature_importance
from src.modeling import ModelingConfig, run_modeling
from src.raw_data import RawDataConfig, run_raw_data_audit
from src.target_cohort import TargetCohortConfig, run_target_cohort
from src.validation import ValidationConfig, run_validation


@dataclass(frozen=True)
class PipelineConfig:
    raw_path: Path = Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx")
    output_dir: Path = Path("output/pipeline_runs/temporal_pipeline")
    patient_id_col: str = "hn"
    visit_date_col: str = "vstdate"
    principal_dx_col: str = "PrincipleDiagnosis"
    comorbidity_dx_col: str = "ComorbidityDiagnosis"


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def stage_dirs(root: Path) -> dict[str, Path]:
    """กำหนด output directory ของแต่ละ stage ให้รวมอยู่ใต้ pipeline run เดียวกัน."""
    return {
        "raw_data": root / "raw_data_output",
        "target_cohort": root / "target_cohort_output",
        "data_cleaning": root / "data_cleaning_output",
        "eda": root / "eda_output",
        "feature_engineering": root / "feature_engineering_output",
        "modeling": root / "model_output",
        "feature_importance": root / "feature_importance_output",
        "validation": root / "validation_output",
    }


def run_pipeline(config: PipelineConfig, skip_modeling: bool = False) -> dict[str, Any]:
    """รัน pipeline รวมโดยเรียกใช้ stage modules แยกตามลำดับ.

    ถ้า `skip_modeling=True` จะหยุดหลัง Stage 05 เพราะ Stage 06-08 ต้องพึ่งผลโมเดล
    """
    dirs = stage_dirs(config.output_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 01: ตรวจ raw data แบบ read-only
    raw_report = run_raw_data_audit(
        RawDataConfig(
            raw_path=config.raw_path,
            output_dir=dirs["raw_data"],
            patient_id_col=config.patient_id_col,
            visit_date_col=config.visit_date_col,
            principal_dx_col=config.principal_dx_col,
            comorbidity_dx_col=config.comorbidity_dx_col,
        )
    )

    # Stage 02: สร้าง target/cohort/reference date/windows จาก raw data
    cohort_report = run_target_cohort(
        TargetCohortConfig(
            input_path=config.raw_path,
            output_dir=dirs["target_cohort"],
            patient_id_col=config.patient_id_col,
            visit_date_col=config.visit_date_col,
            principal_dx_col=config.principal_dx_col,
            comorbidity_dx_col=config.comorbidity_dx_col,
        )
    )

    # Stage 03: clean เฉพาะ pre-reference records ที่ Stage 02 สร้างไว้
    cleaning_report = run_data_cleaning(
        DataCleaningConfig(
            input_path=dirs["target_cohort"] / "pre_reference_records_with_windows.csv",
            output_dir=dirs["data_cleaning"],
            patient_id_col=config.patient_id_col,
            visit_date_col=config.visit_date_col,
            principal_dx_col=config.principal_dx_col,
            comorbidity_dx_col=config.comorbidity_dx_col,
        )
    )

    # Stage 04: EDA และ leakage audit จาก cleaned pre-reference records
    eda_report = run_eda(
        EDAConfig(
            records_path=dirs["data_cleaning"] / "cleaned_pre_reference_records.csv",
            cohort_path=dirs["target_cohort"] / "patient_level_cohort.csv",
            completeness_path=dirs["target_cohort"] / "temporal_completeness_flags.csv",
            attrition_path=dirs["target_cohort"] / "cohort_attrition_report.csv",
            output_dir=dirs["eda"],
        )
    )

    # Stage 05: สร้าง single-shot baseline และ Extract Set 1/2/3
    feature_report = run_feature_engineering(
        FeatureEngineeringConfig(
            records_path=dirs["data_cleaning"] / "cleaned_pre_reference_records.csv",
            output_dir=dirs["feature_engineering"],
        )
    )

    manifest: dict[str, Any] = {
        "raw_path": str(config.raw_path),
        "output_dir": str(config.output_dir),
        "skip_modeling": skip_modeling,
        "stages": {
            "stage_01_raw_data": raw_report,
            "stage_02_target_cohort": cohort_report,
            "stage_03_data_cleaning": cleaning_report,
            "stage_04_eda": eda_report,
            "stage_05_feature_engineering": feature_report,
        },
    }

    if not skip_modeling:
        # Stage 06-08 ใช้ output จาก Stage 05/06/07 ต่อเนื่องกัน
        modeling_report = run_modeling(
            ModelingConfig(
                feature_dir=dirs["feature_engineering"],
                output_dir=dirs["modeling"],
            )
        )
        importance_report = run_feature_importance(
            FeatureImportanceConfig(
                feature_dir=dirs["feature_engineering"],
                model_dir=dirs["modeling"],
                output_dir=dirs["feature_importance"],
            )
        )
        validation_report = run_validation(
            ValidationConfig(
                model_dir=dirs["modeling"],
                feature_importance_dir=dirs["feature_importance"],
                cohort_dir=dirs["target_cohort"],
                eda_dir=dirs["eda"],
                output_dir=dirs["validation"],
            )
        )
        manifest["stages"].update(
            {
                "stage_06_modeling": modeling_report,
                "stage_07_feature_importance": importance_report,
                "stage_08_validation": validation_report,
            }
        )

    write_json(manifest, config.output_dir / "pipeline_manifest.json")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the orchestrated multi-window stroke-risk pipeline.")
    parser.add_argument("--raw-path", default=str(PipelineConfig.raw_path), help="Path to raw EHR Excel/CSV file.")
    parser.add_argument("--output-dir", default=str(PipelineConfig.output_dir), help="Directory for pipeline outputs.")
    parser.add_argument("--patient-id-col", default=PipelineConfig.patient_id_col)
    parser.add_argument("--visit-date-col", default=PipelineConfig.visit_date_col)
    parser.add_argument("--principal-dx-col", default=PipelineConfig.principal_dx_col)
    parser.add_argument("--comorbidity-dx-col", default=PipelineConfig.comorbidity_dx_col)
    parser.add_argument("--skip-modeling", action="store_true", help="Run through Stage 05 only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = PipelineConfig(
        raw_path=Path(args.raw_path),
        output_dir=Path(args.output_dir),
        patient_id_col=args.patient_id_col,
        visit_date_col=args.visit_date_col,
        principal_dx_col=args.principal_dx_col,
        comorbidity_dx_col=args.comorbidity_dx_col,
    )
    manifest = run_pipeline(config, skip_modeling=args.skip_modeling)
    print(json.dumps(manifest, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
