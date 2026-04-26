import os
import sys
import shutil
import tempfile
import duckdb
from pathlib import Path
from loguru import logger

sys.path.append('/app/scripts/utils')
from config import config

POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT     = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB       = os.getenv("POSTGRES_DB", "destinosbrasil")
POSTGRES_USER     = os.getenv("POSTGRES_USER", "pipeline")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pipeline")

TABELAS = [
    "Turismo_Costanera",
    "Transalpino",
    "Comptoir_Des_Voyages",
    "Bleu_Selectour",
    "Ikarus_Tours",
    "Jetmar",
    "Journey_Latin_America",
    "Newmarket_Holidays",
    "Panam",
    "Sol_Ferias",
]


def exportar_tabela(con: duckdb.DuckDBPyConnection, tabela: str) -> int:
    destino = f"pg.raw.{tabela.lower()}"

    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {destino} AS
        SELECT * FROM {tabela} WHERE 1=0
    """)

    con.execute(f"""
        INSERT INTO {destino}
        SELECT src.*
        FROM {tabela} src
        WHERE NOT EXISTS (
            SELECT 1 FROM {destino} tgt
            WHERE tgt.data_extracao = src.data_extracao
        )
    """)

    resultado = con.execute(f"SELECT COUNT(*) FROM {destino}").fetchone()
    return resultado[0] if resultado else 0


def main():
    logger.info("Iniciando export DuckDB → PostgreSQL (schema raw)")

    pg_conn_str = (
        f"host={POSTGRES_HOST} "
        f"port={POSTGRES_PORT} "
        f"dbname={POSTGRES_DB} "
        f"user={POSTGRES_USER} "
        f"password={POSTGRES_PASSWORD}"
    )

    tmp_fd, tmp_path_str = tempfile.mkstemp(suffix='.duckdb')
    os.close(tmp_fd)
    tmp_path = Path(tmp_path_str)

    try:
        shutil.copy2(str(config.DUCKDB_PATH), str(tmp_path))
        logger.info(f"DuckDB copied to: {tmp_path}")
    except Exception as e:
        logger.error(f"Failed to copy DuckDB: {e}")
        tmp_path.unlink(missing_ok=True)
        raise

    try:
        con = duckdb.connect(str(tmp_path))
        logger.info(f"DuckDB connected: {tmp_path}")
    except Exception as e:
        logger.error(f"Failed to connect DuckDB: {e}")
        tmp_path.unlink(missing_ok=True)
        raise

    try:
        con.execute(f"INSTALL postgres; LOAD postgres;")
        con.execute(f"ATTACH '{pg_conn_str}' AS pg (TYPE POSTGRES)")
        logger.info("PostgreSQL conectado via DuckDB ATTACH")
    except Exception as e:
        logger.error(f"Erro ao conectar PostgreSQL: {e}")
        raise

    total_exportado = 0

    for tabela in TABELAS:
        try:
            existe = con.execute(f"""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = '{tabela}'
            """).fetchone()[0]

            if not existe:
                logger.warning(f"Tabela '{tabela}' não encontrada no DuckDB — pulando")
                continue

            registros = exportar_tabela(con, tabela)
            logger.success(f"{tabela} → raw.{tabela.lower()} ({registros} registros no destino)")
            total_exportado += 1

        except Exception as e:
            logger.error(f"Erro ao exportar '{tabela}': {e}")

    con.close()
    logger.info(f"Export concluído — {total_exportado}/{len(TABELAS)} tabelas exportadas")


if __name__ == "__main__":
    main()
