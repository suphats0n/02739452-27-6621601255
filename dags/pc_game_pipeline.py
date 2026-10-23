"""Fault-tolerant multi-source PC game analytics pipeline."""

from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

from etl.load import load_transformed, record_pipeline_run
from etl.quality import validate_data_quality as check_quality
from etl.transform import transform_sources
from ingestion.cheapshark import extract_result as extract_cheapshark_result
from ingestion.freetogame import extract_result as extract_freetogame_result
from ingestion.wikipedia import extract_result as extract_wikipedia_result

DAG_ID = "pc_game_analytics_pipeline"


def _extract(extractor, **context):
    ti = context["ti"]
    result = extractor()
    ti.log.info(
        "Extracted source=%s status=%s count=%s error=%s",
        result["source"],
        result["status"],
        result["count"],
        result.get("error"),
    )
    return result


def _extract_freetogame(**context):
    return _extract(extract_freetogame_result, **context)


def _extract_cheapshark(**context):
    return _extract(extract_cheapshark_result, **context)


def _extract_wikipedia(**context):
    return _extract(extract_wikipedia_result, **context)


def _transform(**context):
    ti = context["ti"]
    results = [
        ti.xcom_pull(task_ids=f"extract_sources.{task_id}")
        for task_id in ("extract_freetogame", "extract_cheapshark", "extract_wikipedia")
    ]
    transformed = transform_sources(results)
    ti.log.info(
        "Transformed %s source records into %s canonical games",
        len(transformed["records"]),
        len(transformed["games"]),
    )
    return transformed


def _quality(**context):
    transformed = context["ti"].xcom_pull(task_ids="transform_and_normalize")
    result = check_quality(transformed, minimum_valid_records=100)
    context["ti"].log.info("Data quality result: %s", result)
    return result


def _branch(**context):
    quality = context["ti"].xcom_pull(task_ids="validate_data_quality")
    if quality and quality.get("passed"):
        return "load_postgresql"
    return "quality_rejected"


def _load(**context):
    transformed = context["ti"].xcom_pull(task_ids="transform_and_normalize")
    result = load_transformed(transformed)
    context["ti"].log.info("PostgreSQL upsert complete: %s", result)
    return result


def _record_status(**context):
    ti = context["ti"]
    source_results = []
    for source in ("freetogame", "cheapshark", "wikipedia"):
        result = ti.xcom_pull(task_ids=f"extract_sources.extract_{source}")
        source_results.append(
            result
            or {
                "source": source,
                "status": "failed",
                "count": 0,
                "records": [],
                "error": "Extraction task did not produce a result.",
            }
        )
    transformed = ti.xcom_pull(task_ids="transform_and_normalize") or {}
    quality = ti.xcom_pull(task_ids="validate_data_quality") or {"passed": False}
    load_result = ti.xcom_pull(task_ids="load_postgresql") or {}
    load_task = context["dag_run"].get_task_instance("load_postgresql")
    load_succeeded = load_task and load_task.state == "success"
    succeeded_sources = sum(result.get("status") != "failed" for result in source_results)
    if load_succeeded and succeeded_sources == len(source_results):
        status = "success"
    elif load_succeeded:
        status = "partial_success"
    else:
        status = "failed"
    errors = [
        f'{result.get("source")}: {result.get("error")}'
        for result in source_results
        if result.get("error")
    ]
    errors.extend(quality.get("errors") or [])
    record_pipeline_run(
        run_id=context["dag_run"].run_id,
        dag_id=DAG_ID,
        status=status,
        started_at=context["dag_run"].start_date,
        metrics={
            "extracted_count": transformed.get("extracted_count", 0),
            "loaded_records": load_result.get("loaded_records", 0),
        },
        source_results=source_results,
        quality=quality,
        error_summary="; ".join(errors) or None,
    )
    ti.log.info(
        "Recorded pipeline run=%s status=%s loaded=%s",
        context["dag_run"].run_id,
        status,
        load_result.get("loaded_records", 0),
    )
    if status == "failed":
        raise AirflowException("Pipeline failed: " + ("; ".join(errors) or "PostgreSQL load did not succeed"))


default_args = {
    "owner": "02739452",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id=DAG_ID,
    description="Parallel extraction, quality-gated normalization, and idempotent PostgreSQL upserts",
    default_args=default_args,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule="0 2 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["exam", "pc-games", "etl"],
) as dag:
    with TaskGroup(group_id="extract_sources") as extract_sources:
        extract_freetogame = PythonOperator(
            task_id="extract_freetogame", python_callable=_extract_freetogame
        )
        extract_cheapshark = PythonOperator(
            task_id="extract_cheapshark", python_callable=_extract_cheapshark
        )
        extract_wikipedia = PythonOperator(
            task_id="extract_wikipedia", python_callable=_extract_wikipedia
        )

    transform_and_normalize = PythonOperator(
        task_id="transform_and_normalize", python_callable=_transform
    )
    validate_data_quality = PythonOperator(
        task_id="validate_data_quality", python_callable=_quality
    )
    branch_on_quality = BranchPythonOperator(
        task_id="branch_on_quality", python_callable=_branch
    )
    load_postgresql = PythonOperator(
        task_id="load_postgresql", python_callable=_load
    )
    quality_rejected = EmptyOperator(task_id="quality_rejected")
    record_pipeline_status = PythonOperator(
        task_id="record_pipeline_status",
        python_callable=_record_status,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    extract_sources >> transform_and_normalize >> validate_data_quality >> branch_on_quality
    branch_on_quality >> [load_postgresql, quality_rejected]
    [load_postgresql, quality_rejected] >> record_pipeline_status
