import duckdb
from pathlib import Path
from loguru import logger
from typing import List, Tuple, Set, Optional
from config import config


class DBManager:
    
    def delete_table(self, table_name: str):
        query = f"DROP TABLE IF EXISTS {table_name}"
        try:
            self.execute_query(query)
            logger.info(f"Tabela {table_name} excluída com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao excluir a tabela {table_name}: {e}")
            raise
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DUCKDB_PATH
        self.con = None
        self._connect()
        
    def _connect(self):
        try:
            self.con = duckdb.connect(str(self.db_path))
            logger.info(f"DuckDB conectado: {self.db_path}")
        except Exception as e:
            logger.error(f"Erro ao conectar DuckDB: {e}")
            raise
            
    def execute_query(self, query: str, params: tuple = None):
        try:
            if params:
                self.con.execute(query, params)
            else:
                self.con.execute(query)
            logger.debug(f"Query executada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao executar query: {e}")
            raise
            
    def get_existing_records(
        self, 
        table_name: str, 
        columns: List[str],
        exclude_data_extracao: bool = True
    ) -> Set[Tuple]:

        try:
            compare_columns = [col for col in columns if col != 'data_extracao'] if exclude_data_extracao else columns
            
            columns_str = ", ".join(compare_columns)
            
            query = f"""
                SELECT DISTINCT {columns_str}
                FROM {table_name}
            """
            
            result = self.con.execute(query).fetchall()
            
            logger.info(f"Registros únicos encontrados em '{table_name}': {len(result)}")
            logger.debug(f"Colunas usadas na comparação: {compare_columns}")
            
            return set(result)
            
        except Exception as e:
            logger.warning(f"Tabela '{table_name}' ainda não existe ou erro: {e}")
            return set()
            
    def insert_batch(
        self, 
        table_name: str, 
        columns: List[str], 
        data: List[Tuple]
    ):

        if not data:
            logger.warning("Nenhum dado para inserir")
            return
            
        try:
            placeholders = ", ".join(["?"] * len(columns))
            columns_str = ", ".join(columns)
            
            query = f"""
                INSERT INTO {table_name} ({columns_str})
                VALUES ({placeholders})
            """
            
            self.con.executemany(query, data)
            logger.success(f"{len(data)} registros inseridos em '{table_name}'")
            
        except Exception as e:
            logger.error(f"Erro ao inserir dados: {e}")
            raise
            
    def get_table_count(self, table_name: str) -> int:

        try:
            query = f"SELECT COUNT(*) FROM {table_name}"
            result = self.con.execute(query).fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Erro ao contar registros: {e}")
            return 0
            
    def get_distinct_count(self, table_name: str, columns: List[str]) -> int:

        try:
            columns_str = ", ".join(columns)
            query = f"""
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT {columns_str}
                    FROM {table_name}
                )
            """
            result = self.con.execute(query).fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Erro ao contar registros distintos: {e}")
            return 0
    
    def check_duplicates(self, table_name: str, columns: List[str]) -> dict:

        try:
            total = self.get_table_count(table_name)
            distinct = self.get_distinct_count(table_name, columns)
            duplicates = total - distinct
            
            return {
                'total_registros': total,
                'registros_unicos': distinct,
                'duplicatas': duplicates,
                'tem_duplicatas': duplicates > 0
            }
        except Exception as e:
            logger.error(f"Erro ao verificar duplicatas: {e}")
            return {}
    
    def remove_duplicates(self, table_name: str, columns: List[str], keep: str = 'first'):

        try:
            columns_str = ", ".join(columns)
            order = "ASC" if keep == 'first' else "DESC"
            
            query = f"""
                CREATE OR REPLACE TEMP TABLE temp_{table_name} AS
                SELECT * FROM (
                    SELECT *, 
                        ROW_NUMBER() OVER (
                            PARTITION BY {columns_str} 
                            ORDER BY data_extracao {order}
                        ) as rn
                    FROM {table_name}
                ) WHERE rn = 1
            """
            
            self.con.execute(query)
            
            self.con.execute(f"DELETE FROM {table_name}")
            
            self.con.execute(f"""
                INSERT INTO {table_name}
                SELECT * FROM temp_{table_name}
                WHERE rn = 1
            """)
            
            columns_select = ", ".join([col for col in columns] + ['data_extracao'])
            self.con.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT {columns_select}
                FROM temp_{table_name}
            """)
            
            logger.success(f"Duplicatas removidas de '{table_name}'")
            
        except Exception as e:
            logger.error(f"Erro ao remover duplicatas: {e}")
            raise
            
    def close(self):
        if self.con:
            self.con.close()
            logger.info("Conexão DuckDB fechada")
            
    def create_table(self, table_name: str, schema: str):
        query = f'CREATE TABLE IF NOT EXISTS {table_name} ({schema})'
        self.execute_query(query)
        logger.info(f'Tabela {table_name} criada/verificada')
    
    def insert_records(self, table_name: str, columns: List[str], data: List[Tuple]):
        self.insert_batch(table_name, columns, data)

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


db_manager = DBManager()