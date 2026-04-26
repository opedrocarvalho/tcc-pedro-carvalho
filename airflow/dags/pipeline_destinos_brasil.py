
import os
from datetime import datetime, timedelta

import pendulum
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

LOCAL_TZ       = pendulum.timezone("America/Sao_Paulo")
HOST_BASE      = os.environ.get("HOST_PIPELINE_PATH",
                                "/c/projetos/web_scraping/pipededados_opensource")
SCRAPER_IMAGE  = "pipeline_scraper"
DBT_IMAGE      = "pipeline_dbt"
NETWORK        = "pipeline_network"

MOUNT_DUCKDB = Mount(
    source=f"{HOST_BASE}/data/duckdb",
    target="/app/data/duckdb",
    type="bind",
)
MOUNT_SCRIPTS = Mount(
    source=f"{HOST_BASE}/scripts",
    target="/app/scripts",
    type="bind",
)
MOUNT_DBT = Mount(
    source=f"{HOST_BASE}/dbt",
    target="/usr/app/dbt",
    type="bind",
)

SCRAPER_ENV = {
    "DUCKDB_PATH"      : "/app/data/duckdb/destinosbrasil.duckdb",
    "LOG_PATH"         : "/app/logs",
    "POSTGRES_HOST"    : "postgres",
    "POSTGRES_PORT"    : "5432",
    "POSTGRES_DB"      : "destinosbrasil",
    "POSTGRES_USER"    : "pipeline",
    "POSTGRES_PASSWORD": "pipeline",
}

SCRAPERS = [
    "bleu-selectour.py",
    "comptoir-des-voyages.py",
    "ikarus-tour.py",
    "jetmar.py",
    "journey-latin-america.py",
    "newmarket-holidays.py",
    "panam.py",
    "sol_ferias.py",
    "transalpino.py",
    "turismo-costanera.py",
]

default_args = {
    "owner"          : "airflow",
    "retries"        : 1,
    "retry_delay"    : timedelta(minutes=10),
    "execution_timeout": timedelta(hours=2),
}

with DAG(
    dag_id="pipeline_destinos_brasil",
    description="Scraping → DuckDB → Postgres raw → dbt staging/marts",
    default_args=default_args,
    schedule_interval="0 6 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=LOCAL_TZ),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=23),
    tags=["pipeline", "scraper", "dbt"],
) as dag:

    scraper_tasks = []
    for script in SCRAPERS:
        task_id = "scraper__" + script.replace(".py", "").replace("-", "_")
        task = DockerOperator(
            task_id=task_id,
            image=SCRAPER_IMAGE,
            command=f"python /app/scripts/scrapers/{script}",
            environment=SCRAPER_ENV,
            mounts=[MOUNT_DUCKDB, MOUNT_SCRIPTS],
            network_mode=NETWORK,
            auto_remove=True,
            docker_url="unix://var/run/docker.sock",
        )
        scraper_tasks.append(task)

    export_duckdb = DockerOperator(
        task_id="export_duckdb_to_postgres",
        image=SCRAPER_IMAGE,
        command="python /app/scripts/export/duckdb_to_postgres.py",
        environment=SCRAPER_ENV,
        mounts=[MOUNT_DUCKDB, MOUNT_SCRIPTS],
        network_mode=NETWORK,
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
    )

    dbt_seed = DockerOperator(
        task_id="dbt_seed",
        image=DBT_IMAGE,
        command="dbt seed --target docker",
        mounts=[MOUNT_DBT],
        network_mode=NETWORK,
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        working_dir="/usr/app/dbt",
    )

    dbt_run_staging = DockerOperator(
        task_id="dbt_run_staging",
        image=DBT_IMAGE,
        command="dbt run --select staging --target docker",
        mounts=[MOUNT_DBT],
        network_mode=NETWORK,
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        working_dir="/usr/app/dbt",
    )

    dbt_run_marts = DockerOperator(
        task_id="dbt_run_marts",
        image=DBT_IMAGE,
        command="dbt run --select marts --target docker",
        mounts=[MOUNT_DBT],
        network_mode=NETWORK,
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        working_dir="/usr/app/dbt",
    )

    dbt_test = DockerOperator(
        task_id="dbt_test",
        image=DBT_IMAGE,
        command="dbt test --target docker",
        mounts=[MOUNT_DBT],
        network_mode=NETWORK,
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        working_dir="/usr/app/dbt",
    )

    for i in range(len(scraper_tasks) - 1):
        scraper_tasks[i] >> scraper_tasks[i + 1]

    scraper_tasks[-1] >> export_duckdb >> dbt_seed >> dbt_run_staging >> dbt_run_marts >> dbt_test