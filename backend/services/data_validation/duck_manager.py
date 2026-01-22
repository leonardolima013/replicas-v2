import duckdb
import os
import pandas as pd
import re
import json
from backend.services.data_validation.mapping_service import get_brand_mapping_service

# Pasta onde os ficheiros .duckdb ficam guardados
TEMP_DIR = "temp_data"

def _python_fix_barcode(barcode_input) -> str:
    """
    Função auxiliar que será injetada no DuckDB.
    Recebe um valor (pode ser int, float ou string) e retorna o barcode corrigido.
    """
    if barcode_input is None:
        return ""
    
    # 1. Tratamento inicial de tipo (remove notação científica se vier como float)
    try:
        # Se for float (ex: 7.89E12), converte para int primeiro para remover o .0
        if isinstance(barcode_input, float):
            barcode = str(int(barcode_input))
        else:
            barcode = str(barcode_input).strip()
    except:
        return ""

    # 2. A Lógica de Negócio (EAN-13 Checksum)
    try:
        # Remove caracteres especiais básicos antes de validar
        barcode = re.sub(r'[^0-9]', '', barcode)

        # Verifica se o código contém apenas dígitos
        if not barcode.isdigit():
            return ""
        
        # Verifica se o tamanho é menor que 12 ou maior que 13
        if len(barcode) < 12 or len(barcode) > 13:
            return ""
        
        # Se já tiver 13 dígitos, assume-se que o código está completo
        if len(barcode) == 13:
            return barcode

        # Caso o código tenha exatamente 12 dígitos, calcula o dígito verificador
        soma = 0
        for i, digito in enumerate(barcode):
            fator = 1 if i % 2 == 0 else 3
            soma += int(digito) * fator

        digito_verificador = (10 - (soma % 10)) % 10
        return barcode + str(digito_verificador)
    except:
        return ""

class DuckSession:
    def __init__(self, project_id: str):
        self.db_path = os.path.join(TEMP_DIR, f"{project_id}.duckdb")
    
    def _get_conn(self, read_only=False):
        """Abre uma conexão segura com o ficheiro."""
        return duckdb.connect(self.db_path, read_only=read_only)
    
    def _get_columns_from_conn(self, conn, table_name: str = "raw_data"):
        """Retorna colunas usando uma conexão existente (evita conflitos)."""
        columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
        return [col[0] for col in columns_info]

    def load_csv_auto(self, csv_path: str, table_name: str = "raw_data"):
        """Usa-se apenas no Upload inicial."""
        conn = self._get_conn(read_only=False)
        try:
            query = f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{csv_path}', ALL_VARCHAR=TRUE);"
            conn.execute(query)
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path) # Limpa o CSV original para poupar espaço
            conn.close()

    def get_preview(self, page: int = 1, limit: int = 50, table_name: str = "raw_data"):
        """Lógica de Paginação Inteligente."""
        conn = self._get_conn(read_only=True)
        try:
            # 1. Contar total de linhas (Instantâneo no DuckDB)
            total_rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            # 2. Descobrir nomes das colunas
            columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
            columns = [col[0] for col in columns_info]

            # 3. Calcular o 'salto' (Offset)
            offset = (page - 1) * limit
            
            # 4. Buscar apenas a fatia necessária
            query = f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}"
            
            # Converter para formato JSON (Lista de Dicionários)
            df = conn.execute(query).fetchdf()
            rows = df.to_dict(orient="records")

            return {
                "total_rows": total_rows,
                "columns": columns,
                "rows": rows
            }
        finally:
            conn.close()

    def execute_user_query(self, sql: str):
        """Executa SQL de limpeza enviado pelo utilizador."""
        conn = self._get_conn(read_only=False)
        try:
            sql_clean = sql.strip().lower()
            result_obj = conn.execute(sql)
            
            # Se for SELECT, retorna dados. Se for UPDATE/DELETE, apenas confirmação.
            if sql_clean.startswith("select") or sql_clean.startswith("show") or sql_clean.startswith("describe"):
                df = result_obj.fetchdf()
                return {"status": "success", "data": df.to_dict(orient="records"), "rows_affected": 0}
            else:
                return {"status": "success", "data": None, "rows_affected": -1}
        except Exception as e:
            return {"status": "error", "error": str(e)}
        finally:
            conn.close()

    def export_to_csv(self, output_path: str, table_name: str = "raw_data"):
        """Exporta a tabela DuckDB para um arquivo CSV."""
        conn = self._get_conn(read_only=True)
        try:
            query = f"COPY (SELECT * FROM {table_name}) TO '{output_path}' (HEADER, DELIMITER ',')"
            conn.execute(query)
        finally:
            conn.close()

    def get_columns(self, table_name: str = "raw_data"):
        """Retorna a lista de colunas da tabela."""
        conn = self._get_conn(read_only=True)
        try:
            columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
            columns = [col[0] for col in columns_info]
            return columns
        finally:
            conn.close()
    
    def get_column_types(self, table_name: str = "raw_data"):
        """Retorna um dicionário {nome_coluna: tipo_dado} da tabela."""
        conn = self._get_conn(read_only=True)
        try:
            columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
            # columns_info é uma lista de tuplas: (column_name, column_type, null, key, default, extra)
            column_types = {col[0]: col[1] for col in columns_info}
            return column_types
        finally:
            conn.close()

    def rename_column(self, old_name: str, new_name: str, table_name: str = "raw_data"):
        """Renomeia uma coluna na tabela."""
        conn = self._get_conn(read_only=False)
        try:
            # DuckDB suporta ALTER TABLE RENAME COLUMN
            query = f"ALTER TABLE {table_name} RENAME COLUMN \"{old_name}\" TO \"{new_name}\""
            conn.execute(query)
        finally:
            conn.close()

    # --- FASE 2: MÉTODOS DE DIAGNÓSTICO E TRATAMENTO ---

    def diagnose_uppercase_issues(self, columns_to_check: set, table_name: str = "raw_data"):
        """Verifica quais colunas de string têm valores não-uppercase."""
        conn = self._get_conn(read_only=True)
        issues = []
        try:
            current_columns = set(self.get_columns(table_name))
            column_types = self.get_column_types(table_name)
            
            # Filtrar apenas colunas que existem E são do tipo string (VARCHAR, TEXT, etc.)
            valid_columns = [
                col for col in (columns_to_check & current_columns)
                if column_types.get(col, '').upper() in ('VARCHAR', 'TEXT', 'STRING')
            ]
            
            for col in valid_columns:
                query = f"SELECT COUNT(*) FROM {table_name} WHERE \"{col}\" IS NOT NULL AND \"{col}\" != '' AND \"{col}\" != UPPER(\"{col}\")"
                count = conn.execute(query).fetchone()[0]
                if count > 0:
                    issues.append(col)
            return issues
        finally:
            conn.close()

    def diagnose_null_strings(self, columns_to_check: set, table_name: str = "raw_data"):
        """Verifica quais colunas de string têm valores vazios (que devem ser NULL)."""
        conn = self._get_conn(read_only=True)
        issues = []
        try:
            current_columns = set(self.get_columns(table_name))
            column_types = self.get_column_types(table_name)
            
            # Filtrar apenas colunas que existem E são do tipo string
            valid_columns = [
                col for col in (columns_to_check & current_columns)
                if column_types.get(col, '').upper() in ('VARCHAR', 'TEXT', 'STRING')
            ]
            
            for col in valid_columns:
                # Considera erro apenas strings vazias (após TRIM)
                query = f"SELECT COUNT(*) FROM {table_name} WHERE TRIM(\"{col}\") = ''"
                count = conn.execute(query).fetchone()[0]
                if count > 0:
                    issues.append(col)
            return issues
        finally:
            conn.close()

    def diagnose_null_numerics(self, columns_to_check: set, table_name: str = "raw_data"):
        """Verifica quais colunas numéricas têm valores zero (que devem ser NULL)."""
        conn = self._get_conn(read_only=True)
        issues = []
        try:
            current_columns = set(self.get_columns(table_name))
            valid_columns = columns_to_check & current_columns
            
            for col in valid_columns:
                # Considera erro apenas valores iguais a zero
                query = f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE TRY_CAST(\"{col}\" AS DOUBLE) = 0
                """
                count = conn.execute(query).fetchone()[0]
                if count > 0:
                    issues.append(col)
            return issues
        finally:
            conn.close()

    # --- FASE 2.1: DIAGNÓSTICOS AVANÇADOS ---

    def diagnose_brand_issues(self, table_name: str = "raw_data"):
        """Diagnostica problemas em brand: tamanho, nulos, caracteres inválidos, apenas números."""
        conn = self._get_conn(read_only=True)
        try:
            current_columns = set(self.get_columns(table_name))
            if "brand" not in current_columns:
                return 0
            
            query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE
                    LENGTH(brand) < 2
                    OR brand IS NULL
                    OR brand NOT SIMILAR TO '[a-zA-Z0-9 .-]+'
                    OR brand SIMILAR TO '[0-9]+'
            """
            count = conn.execute(query).fetchone()[0]
            return count
        finally:
            conn.close()

    def diagnose_ncm_issues(self, table_name: str = "raw_data"):
        """Diagnostica problemas em ncm: tamanho incorreto, letras, hífen."""
        conn = self._get_conn(read_only=True)
        try:
            current_columns = set(self.get_columns(table_name))
            if "ncm" not in current_columns:
                return 0
            
            # Fazer CAST para VARCHAR para garantir compatibilidade com funções de string
            query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE
                    ncm IS NOT NULL
                    AND CAST(ncm AS VARCHAR) != ''
                    AND (
                        LENGTH(REPLACE(CAST(ncm AS VARCHAR), '.', '')) != 8
                        OR CAST(ncm AS VARCHAR) SIMILAR TO '.*[a-zA-Z].*'
                        OR CAST(ncm AS VARCHAR) LIKE '%-%'
                    )
            """
            count = conn.execute(query).fetchone()[0]
            return count
        finally:
            conn.close()

    def diagnose_barcode_issues(self, table_name: str = "raw_data"):
        """Diagnostica problemas em barcode: tamanho incorreto (deve ser 8, 12 ou 13), caracteres não-numéricos."""
        conn = self._get_conn(read_only=True)
        try:
            current_columns = set(self.get_columns(table_name))
            if "barcode" not in current_columns:
                return 0
            
            # Fazer CAST para VARCHAR para garantir compatibilidade com funções de string
            query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE
                    barcode IS NOT NULL
                    AND CAST(barcode AS VARCHAR) != ''
                    AND (
                        LENGTH(CAST(barcode AS VARCHAR)) NOT IN (8, 12, 13)
                        OR CAST(barcode AS VARCHAR) SIMILAR TO '.*[^0-9].*'
                    )
            """
            count = conn.execute(query).fetchone()[0]
            return count
        finally:
            conn.close()

    def diagnose_weight_issues(self, table_name: str = "raw_data"):
        """Diagnostica problemas em pesos: gross < net ou valores negativos."""
        conn = self._get_conn(read_only=True)
        try:
            current_columns = set(self.get_columns(table_name))
            has_gross = "gross_weight" in current_columns
            has_net = "net_weight" in current_columns
            
            if not (has_gross and has_net):
                return 0
            
            # Problemas reais:
            # 1. Peso bruto MENOR que líquido (gross < net)
            # 2. Valores negativos em qualquer um dos pesos
            # NOTA: Pesos iguais (incluindo ambos zero) NÃO são considerados erro
            query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE
                    (TRY_CAST(gross_weight AS DOUBLE) < TRY_CAST(net_weight AS DOUBLE))
                    OR (TRY_CAST(gross_weight AS DOUBLE) < 0)
                    OR (TRY_CAST(net_weight AS DOUBLE) < 0)
            """
            count = conn.execute(query).fetchone()[0]
            return count
        finally:
            conn.close()

    def diagnose_dimension_issues(self, table_name: str = "raw_data"):
        """Diagnostica problemas em dimensões: valores <= 0 ou extremos > 1000."""
        conn = self._get_conn(read_only=True)
        try:
            current_columns = set(self.get_columns(table_name))
            dims = {"width", "height", "depth"}
            existing_dims = dims & current_columns
            
            if not existing_dims:
                return 0
            
            # Construir condições dinamicamente para colunas existentes
            conditions = []
            for dim in existing_dims:
                conditions.append(f"TRY_CAST({dim} AS DOUBLE) < 0")
                conditions.append(f"TRY_CAST({dim} AS DOUBLE) > 1000")
            
            where_clause = " OR ".join(conditions)
            query = f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
            count = conn.execute(query).fetchone()[0]
            return count
        finally:
            conn.close()

    def diagnose_search_ref_issues(self, table_name: str = "raw_data"):
        """Diagnostica problemas em search_ref: tamanho < 3, qualquer espaço ou caractere especial."""
        conn = self._get_conn(read_only=True)
        try:
            current_columns = set(self.get_columns(table_name))
            if "search_ref" not in current_columns:
                return 0
            
            query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE
                    search_ref IS NOT NULL
                    AND search_ref != ''
                    AND (
                        LENGTH(search_ref) < 3
                        OR search_ref NOT SIMILAR TO '[a-zA-Z0-9]+'
                    )
            """
            count = conn.execute(query).fetchone()[0]
            return count
        finally:
            conn.close()

    def diagnose_manufacturer_ref_issues(self, table_name: str = "raw_data"):
        """Diagnostica problemas em search_ref: tamanho < 3, espaços, caracteres proibidos."""
        conn = self._get_conn(read_only=True)
        try:
            current_columns = set(self.get_columns(table_name))
            if "search_ref" not in current_columns:
                return 0
            
            query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE
                    search_ref IS NOT NULL
                    AND search_ref != ''
                    AND (
                        LENGTH(search_ref) < 3
                        OR search_ref LIKE '% %'
                        OR search_ref SIMILAR TO '.*[@#%&].*'
                    )
            """
            count = conn.execute(query).fetchone()[0]
            return count
        finally:
            conn.close()

    def fix_null_strings(self, columns_to_fix: set, table_name: str = "raw_data"):
        """Converte strings vazias para NULL em colunas de texto."""
        # Obter colunas válidas usando método separado
        current_columns = set(self.get_columns(table_name))
        column_types = self.get_column_types(table_name)
        
        # Filtrar apenas colunas que existem E são do tipo string
        valid_columns = [
            col for col in (columns_to_fix & current_columns)
            if column_types.get(col, '').upper() in ('VARCHAR', 'TEXT', 'STRING')
        ]
        
        conn = self._get_conn(read_only=False)
        try:
            total_affected = 0
            
            for col in valid_columns:
                # Contar quantas strings vazias existem
                count_query = f"SELECT COUNT(*) FROM {table_name} WHERE TRIM(\"{col}\") = ''"
                affected = conn.execute(count_query).fetchone()[0]
                total_affected += affected
                
                # Converter strings vazias para NULL
                query = f"""
                    UPDATE {table_name} 
                    SET \"{col}\" = NULL 
                    WHERE TRIM(\"{col}\") = ''
                """
                conn.execute(query)
            
            return {"columns": list(valid_columns), "rows_affected": total_affected}
        finally:
            conn.close()

    def apply_uppercase_fix(self, columns_to_fix: set, table_name: str = "raw_data"):
        """Converte valores para UPPERCASE em colunas de texto."""
        # Obter colunas válidas usando método separado
        current_columns = set(self.get_columns(table_name))
        column_types = self.get_column_types(table_name)
        
        # Filtrar apenas colunas que existem E são do tipo string
        valid_columns = [
            col for col in (columns_to_fix & current_columns)
            if column_types.get(col, '').upper() in ('VARCHAR', 'TEXT', 'STRING')
        ]
        
        conn = self._get_conn(read_only=False)
        try:
            total_affected = 0
            
            for col in valid_columns:
                # Contar quantas linhas serão afetadas
                count_query = f"SELECT COUNT(*) FROM {table_name} WHERE \"{col}\" IS NOT NULL AND \"{col}\" != '' AND \"{col}\" != UPPER(\"{col}\")"
                affected = conn.execute(count_query).fetchone()[0]
                total_affected += affected
                
                # Aplicar uppercase
                query = f"UPDATE {table_name} SET \"{col}\" = UPPER(\"{col}\") WHERE \"{col}\" IS NOT NULL AND \"{col}\" != ''"
                conn.execute(query)
            
            return {"columns": list(valid_columns), "rows_affected": total_affected}
        finally:
            conn.close()

    def fix_null_numerics(self, columns_to_fix: set, table_name: str = "raw_data"):
        """Converte valores zero para NULL em colunas numéricas."""
        # Obter colunas válidas usando método separado
        current_columns = set(self.get_columns(table_name))
        valid_columns = columns_to_fix & current_columns
        
        conn = self._get_conn(read_only=False)
        try:
            total_affected = 0
            
            for col in valid_columns:
                # Contar quantas linhas têm valor zero
                count_query = f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE TRY_CAST(\"{col}\" AS DOUBLE) = 0
                """
                affected = conn.execute(count_query).fetchone()[0]
                total_affected += affected
                
                # Converter zeros para NULL
                conn.execute(f"""
                    UPDATE {table_name} 
                    SET \"{col}\" = NULL 
                    WHERE TRY_CAST(\"{col}\" AS DOUBLE) = 0
                """)
            
            return {"columns": list(valid_columns), "rows_affected": total_affected}
        finally:
            conn.close()

    # --- FASE 2.2: TRATAMENTOS AUTOMATIZADOS (CORREÇÕES) ---

    def apply_barcode_fix(self, table_name: str = "raw_data"):
        """Aplica correção inteligente de barcode usando UDF Python no DuckDB."""
        current_columns = set(self.get_columns(table_name))
        if "barcode" not in current_columns:
            return {"columns": [], "rows_affected": 0}
        
        conn = self._get_conn(read_only=False)
        try:
            # Registrar a função Python no DuckDB
            conn.create_function("fix_ean_udf", _python_fix_barcode)
            
            # Contar quantas linhas serão afetadas (antes da correção)
            # Fazer CAST para garantir compatibilidade
            count_query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE barcode IS NOT NULL 
                AND CAST(barcode AS VARCHAR) != '' 
                AND CAST(barcode AS VARCHAR) != fix_ean_udf(CAST(barcode AS VARCHAR))
            """
            affected = conn.execute(count_query).fetchone()[0]
            
            # Executar a correção em massa
            conn.execute(f"UPDATE {table_name} SET barcode = fix_ean_udf(CAST(barcode AS VARCHAR)) WHERE barcode IS NOT NULL AND CAST(barcode AS VARCHAR) != ''")
            
            return {"columns": ["barcode"], "rows_affected": affected}
        finally:
            conn.close()

    def apply_ncm_fix(self, table_name: str = "raw_data"):
        """Sanitiza NCM removendo pontos, espaços e caracteres não-numéricos."""
        current_columns = set(self.get_columns(table_name))
        if "ncm" not in current_columns:
            return {"columns": [], "rows_affected": 0}
        
        conn = self._get_conn(read_only=False)
        try:
            # Contar linhas que serão afetadas (fazer CAST para garantir compatibilidade)
            count_query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE ncm IS NOT NULL 
                AND CAST(ncm AS VARCHAR) != ''
                AND CAST(ncm AS VARCHAR) != regexp_replace(CAST(ncm AS VARCHAR), '[^0-9]', '', 'g')
            """
            affected = conn.execute(count_query).fetchone()[0]
            
            # Remover tudo que não for número
            conn.execute(f"UPDATE {table_name} SET ncm = regexp_replace(CAST(ncm AS VARCHAR), '[^0-9]', '', 'g') WHERE ncm IS NOT NULL AND CAST(ncm AS VARCHAR) != ''")
            
            return {"columns": ["ncm"], "rows_affected": affected}
        finally:
            conn.close()

    def apply_codes_fix(self, table_name: str = "raw_data"):
        """Sanitiza search_ref: TRIM, UPPER, remove espaços e caracteres especiais."""
        current_columns = set(self.get_columns(table_name))
        
        if "search_ref" not in current_columns:
            return {"columns": [], "rows_affected": 0}
        
        conn = self._get_conn(read_only=False)
        try:
            # Contar linhas que serão afetadas
            count_query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE \"search_ref\" IS NOT NULL 
                AND \"search_ref\" != ''
                AND \"search_ref\" != regexp_replace(TRIM(UPPER(\"search_ref\")), '[^A-Z0-9]', '', 'g')
            """
            affected = conn.execute(count_query).fetchone()[0]
            
            # Aplicar: TRIM + UPPER + remover tudo que não for alfanumérico
            conn.execute(f"""
                UPDATE {table_name} 
                SET \"search_ref\" = regexp_replace(TRIM(UPPER(\"search_ref\")), '[^A-Z0-9]', '', 'g')
                WHERE \"search_ref\" IS NOT NULL AND \"search_ref\" != ''
            """)
            
            return {"columns": ["search_ref"], "rows_affected": affected}
        finally:
            conn.close()

    def apply_negative_weights_fix(self, table_name: str = "raw_data"):
        """Converte pesos negativos em valores absolutos."""
        current_columns = set(self.get_columns(table_name))
        weights = {"gross_weight", "net_weight"}
        existing_weights = weights & current_columns
        
        if not existing_weights:
            return {"columns": [], "rows_affected": 0}
        
        # Obter tipos das colunas
        conn_info = self._get_conn(read_only=True)
        try:
            columns_info = conn_info.execute(f"DESCRIBE {table_name}").fetchall()
            column_types = {col[0]: col[1] for col in columns_info}
        finally:
            conn_info.close()
        
        conn = self._get_conn(read_only=False)
        try:
            total_affected = 0
            
            for col in existing_weights:
                col_type = column_types.get(col, "VARCHAR")
                
                # Se for VARCHAR, converter para DOUBLE primeiro
                if "VARCHAR" in col_type.upper():
                    try:
                        # Limpar valores não-numéricos antes de converter
                        conn.execute(f"""
                            UPDATE {table_name} 
                            SET \"{col}\" = NULL 
                            WHERE LOWER(TRIM(\"{col}\")) IN ('nan', 'none', 'null', '')
                               OR TRIM(\"{col}\") = ''
                        """)
                        conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN \"{col}\" TYPE DOUBLE")
                    except:
                        # Se falhar, pular esta coluna
                        continue
                
                # Contar valores negativos
                count_query = f"SELECT COUNT(*) FROM {table_name} WHERE TRY_CAST(\"{col}\" AS DOUBLE) < 0"
                affected = conn.execute(count_query).fetchone()[0]
                total_affected += affected
                
                # Aplicar valor absoluto
                conn.execute(f"UPDATE {table_name} SET \"{col}\" = ABS(\"{col}\") WHERE \"{col}\" < 0")
            
            return {"columns": list(existing_weights), "rows_affected": total_affected}
        finally:
            conn.close()

    # --- ANÁLISE E REMOÇÃO DE DUPLICADAS ---

    def analyze_duplicates(self, table_name: str = "raw_data"):
        """Analisa peças duplicadas baseado em search_ref + brand."""
        current_columns = set(self.get_columns(table_name))
        if "search_ref" not in current_columns or "brand" not in current_columns:
            return {"total_duplicates": 0, "duplicate_groups": 0, "duplicates": []}
        
        conn = self._get_conn(read_only=True)
        try:
            # Encontrar grupos duplicados (search_ref + brand que aparecem mais de 1 vez)
            query = f"""
                SELECT search_ref, brand, COUNT(*) as count
                FROM {table_name}
                WHERE search_ref IS NOT NULL 
                AND search_ref != ''
                AND brand IS NOT NULL 
                AND brand != ''
                GROUP BY search_ref, brand
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """
            duplicate_groups_df = conn.execute(query).fetchdf()
            
            if len(duplicate_groups_df) == 0:
                return {"total_duplicates": 0, "duplicate_groups": 0, "duplicates": []}
            
            # Para cada grupo duplicado, buscar todas as linhas
            duplicates = []
            total_duplicates = 0
            
            for _, row in duplicate_groups_df.iterrows():
                search_ref = row['search_ref']
                brand = row['brand']
                count = row['count']
                
                # Buscar todas as linhas deste grupo
                rows_query = f"""
                    SELECT * FROM {table_name}
                    WHERE search_ref = '{search_ref}'
                    AND brand = '{brand}'
                """
                rows_df = conn.execute(rows_query).fetchdf()
                rows_data = rows_df.to_dict(orient="records")
                
                duplicates.append({
                    "search_ref": search_ref,
                    "brand": brand,
                    "count": int(count),
                    "rows": rows_data
                })
                
                total_duplicates += (count - 1)  # Conta apenas as duplicatas (primeira ocorrência não conta)
            
            return {
                "total_duplicates": int(total_duplicates),
                "duplicate_groups": len(duplicates),
                "duplicates": duplicates
            }
        finally:
            conn.close()

    def get_duplicates_diagnosis(self, columns: list = None, table_name: str = "raw_data", page: int = 1, page_size: int = 50):
        """
        Diagnostica duplicatas baseadas nas colunas especificadas.
        Retorna preview paginado das linhas que serão removidas.
        """
        if columns is None:
            columns = ["search_ref", "brand"]
        
        # Verificar se as colunas existem
        current_columns = set(self.get_columns(table_name))
        valid_columns = [col for col in columns if col in current_columns]
        
        if not valid_columns:
            return {"total_duplicates": 0, "preview": [], "columns_used": []}
        
        conn = self._get_conn(read_only=True)
        try:
            # Construir partition clause
            partition_cols = ", ".join(valid_columns)
            
            # Construir condição WHERE (não pode usar \' dentro de f-string)
            where_conditions = []
            for col in valid_columns:
                where_conditions.append(f'"{col}" IS NOT NULL AND "{col}" != \'\'')
            where_clause = ' AND '.join(where_conditions)
            
            # Calcular offset para paginação
            offset = (page - 1) * page_size
            
            # Query para identificar duplicatas (rn > 1 significa que não é a primeira ocorrência)
            query = f"""
                WITH ranked_data AS (
                    SELECT 
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY {partition_cols}
                            ORDER BY rowid
                        ) as rn
                    FROM {table_name}
                    WHERE {where_clause}
                )
                SELECT * FROM ranked_data
                WHERE rn > 1
                ORDER BY {partition_cols}, rn
                LIMIT {page_size} OFFSET {offset}
            """
            
            duplicates_df = conn.execute(query).fetchdf()
            
            # Remover coluna auxiliar 'rn' antes de retornar
            if 'rn' in duplicates_df.columns:
                duplicates_df = duplicates_df.drop(columns=['rn'])
            
            # Contar total de duplicatas (todas as linhas que não são primeira ocorrência)
            count_query = f"""
                WITH ranked_data AS (
                    SELECT 
                        ROW_NUMBER() OVER (
                            PARTITION BY {partition_cols}
                            ORDER BY rowid
                        ) as rn
                    FROM {table_name}
                    WHERE {where_clause}
                )
                SELECT COUNT(*) FROM ranked_data WHERE rn > 1
            """
            total_duplicates = conn.execute(count_query).fetchone()[0]
            
            return {
                "total_duplicates": int(total_duplicates),
                "preview": duplicates_df.to_dict(orient="records"),
                "columns_used": valid_columns,
                "page": page,
                "page_size": page_size,
                "total_pages": (int(total_duplicates) + page_size - 1) // page_size if total_duplicates > 0 else 0
            }
        finally:
            conn.close()

    def remove_duplicates(self, table_name: str = "raw_data"):
        """Remove duplicadas mantendo apenas a primeira ocorrência de cada search_ref + brand."""
        current_columns = set(self.get_columns(table_name))
        if "search_ref" not in current_columns or "brand" not in current_columns:
            return {"rows_affected": 0}
        
        conn = self._get_conn(read_only=False)
        try:
            # Contar duplicadas antes de remover usando ROW_NUMBER
            count_query = f"""
                WITH ranked_data AS (
                    SELECT ROW_NUMBER() OVER (
                        PARTITION BY search_ref, brand
                        ORDER BY rowid
                    ) as rn
                    FROM {table_name}
                    WHERE search_ref IS NOT NULL 
                    AND search_ref != ''
                    AND brand IS NOT NULL 
                    AND brand != ''
                )
                SELECT COUNT(*) FROM ranked_data WHERE rn > 1
            """
            duplicates_count = conn.execute(count_query).fetchone()[0]
            
            if duplicates_count == 0:
                return {"rows_affected": 0}
            
            # Estratégia: Criar tabela temporária com apenas as primeiras ocorrências
            # Usa ROW_NUMBER() OVER (PARTITION BY search_ref, brand ORDER BY rowid) para identificar a primeira
            conn.execute(f"""
                CREATE OR REPLACE TABLE {table_name}_temp AS
                SELECT * FROM (
                    SELECT *, ROW_NUMBER() OVER (
                        PARTITION BY search_ref, brand 
                        ORDER BY (SELECT NULL)
                    ) as rn
                    FROM {table_name}
                ) WHERE rn = 1
            """)
            
            # Remover coluna auxiliar rn
            conn.execute(f"ALTER TABLE {table_name}_temp DROP COLUMN rn")
            
            # Substituir tabela original pela temporária
            conn.execute(f"DROP TABLE {table_name}")
            conn.execute(f"ALTER TABLE {table_name}_temp RENAME TO {table_name}")
            
            return {"rows_affected": int(duplicates_count)}
        finally:
            conn.close()

    def get_statistics(self, table_name: str = "raw_data"):
        """Calcula estatísticas completas sobre os dados: resumo numérico, correlações e violações."""
        conn = self._get_conn(read_only=True)
        try:
            # Obter colunas disponíveis
            current_columns = set(self.get_columns(table_name))
            
            # Definir colunas numéricas de interesse
            numeric_cols = {"gross_weight", "net_weight", "width", "height", "depth"}
            existing_numeric = numeric_cols & current_columns
            
            if not existing_numeric:
                return {
                    "summary": [],
                    "violations": {"count_weight_error": 0, "count_negative": 0},
                    "correlation": None
                }
            
            # 1. SUMMARIZE: min, max, avg, stddev, quartis para todas as colunas numéricas
            summary_results = []
            for col in existing_numeric:
                # DuckDB SUMMARIZE retorna estatísticas automáticas
                summary_query = f"SUMMARIZE SELECT TRY_CAST(\"{col}\" AS DOUBLE) as value FROM {table_name} WHERE \"{col}\" IS NOT NULL"
                try:
                    summary_df = conn.execute(summary_query).fetchdf()
                    
                    # Construir estatísticas manualmente se SUMMARIZE não funcionar como esperado
                    stats_query = f"""
                        SELECT 
                            '{col}' as column_name,
                            MIN(TRY_CAST(\"{col}\" AS DOUBLE)) as min,
                            MAX(TRY_CAST(\"{col}\" AS DOUBLE)) as max,
                            AVG(TRY_CAST(\"{col}\" AS DOUBLE)) as avg,
                            STDDEV(TRY_CAST(\"{col}\" AS DOUBLE)) as stddev,
                            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY TRY_CAST(\"{col}\" AS DOUBLE)) as q25,
                            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY TRY_CAST(\"{col}\" AS DOUBLE)) as q50,
                            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY TRY_CAST(\"{col}\" AS DOUBLE)) as q75
                        FROM {table_name}
                        WHERE \"{col}\" IS NOT NULL
                    """
                    stats = conn.execute(stats_query).fetchone()
                    summary_results.append({
                        "column": stats[0],
                        "min": float(stats[1]) if stats[1] is not None else None,
                        "max": float(stats[2]) if stats[2] is not None else None,
                        "avg": float(stats[3]) if stats[3] is not None else None,
                        "stddev": float(stats[4]) if stats[4] is not None else None,
                        "q25": float(stats[5]) if stats[5] is not None else None,
                        "q50": float(stats[6]) if stats[6] is not None else None,
                        "q75": float(stats[7]) if stats[7] is not None else None,
                    })
                except Exception:
                    # Se falhar, pular esta coluna
                    continue
            
            # 2. CORRELAÇÃO entre gross_weight e net_weight
            correlation = None
            if "gross_weight" in existing_numeric and "net_weight" in existing_numeric:
                corr_query = f"""
                    SELECT CORR(
                        TRY_CAST(gross_weight AS DOUBLE),
                        TRY_CAST(net_weight AS DOUBLE)
                    ) as correlation
                    FROM {table_name}
                    WHERE gross_weight IS NOT NULL AND net_weight IS NOT NULL
                """
                corr_result = conn.execute(corr_query).fetchone()[0]
                correlation = float(corr_result) if corr_result is not None else None
            
            # 3. VIOLAÇÕES FÍSICAS
            violations = {"count_weight_error": 0, "count_negative": 0}
            
            # 3a. Contar onde net_weight > gross_weight
            if "gross_weight" in existing_numeric and "net_weight" in existing_numeric:
                weight_error_query = f"""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE TRY_CAST(net_weight AS DOUBLE) > TRY_CAST(gross_weight AS DOUBLE)
                """
                violations["count_weight_error"] = conn.execute(weight_error_query).fetchone()[0]
            
            # 3b. Contar valores negativos em qualquer coluna numérica
            negative_conditions = []
            for col in existing_numeric:
                negative_conditions.append(f"TRY_CAST(\"{col}\" AS DOUBLE) < 0")
            
            if negative_conditions:
                negative_query = f"""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE {' OR '.join(negative_conditions)}
                """
                violations["count_negative"] = conn.execute(negative_query).fetchone()[0]
            
            return {
                "summary": summary_results,
                "violations": violations,
                "correlation": correlation
            }
        finally:
            conn.close()

    # --- FASE 3: MAPEAMENTO DE MARCAS ---

    def analyze_brands(self, table_name: str = "raw_data"):
        """
        Analisa o impacto do mapeamento de marcas nos dados.
        
        Retorna métricas de diagnóstico:
        - total_rows: Total de linhas na tabela
        - mapped_count: Quantas linhas têm marcas que estão no mapeamento (serão corrigidas)
        - unknown_count: Quantas linhas têm marcas que não estão no mapeamento
        - top_corrections: As 5 principais marcas que serão alteradas
        - unknown_brands: Lista das marcas desconhecidas com suas contagens
        
        Returns:
            dict: Dicionário com métricas de diagnóstico
        """
        conn = self._get_conn(read_only=True)
        try:
            # Verificar se a coluna brand existe - usando a conexão existente
            columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
            current_columns = set([col[0] for col in columns_info])
            
            if "brand" not in current_columns:
                return {
                    "total_rows": 0,
                    "mapped_count": 0,
                    "unknown_count": 0,
                    "top_corrections": [],
                    "unknown_brands": []
                }
            
            # Obter o DataFrame de mapeamento do serviço
            mapping_service = get_brand_mapping_service()
            mapping_df = mapping_service.get_mapping_df()
            
            # Criar tabela temporária com o mapeamento
            # Primeiro, criar os valores para o INSERT
            values_list = []
            for _, row in mapping_df.iterrows():
                # Escapar aspas simples nas strings
                source_escaped = row['source'].replace("'", "''")
                target_escaped = row['target'].replace("'", "''")
                values_list.append(f"('{source_escaped}', '{target_escaped}')")
            values_str = ", ".join(values_list)
            
            # Criar tabela temporária
            conn.execute("DROP TABLE IF EXISTS brand_map")
            conn.execute("""
                CREATE TEMP TABLE brand_map (
                    source VARCHAR,
                    target VARCHAR
                )
            """)
            conn.execute(f"INSERT INTO brand_map VALUES {values_str}")
            
            # 1. Total de linhas
            total_query = f"SELECT COUNT(*) FROM {table_name}"
            total_rows = conn.execute(total_query).fetchone()[0]
            
            # 2. Linhas com marcas que estão no mapeamento (serão corrigidas)
            # Apenas contamos marcas que realmente serão alteradas (source != target)
            mapped_query = f"""
                SELECT COUNT(DISTINCT r.rowid) as mapped_count
                FROM {table_name} r
                INNER JOIN brand_map bm 
                    ON UPPER(TRIM(r.brand)) = bm.source
                WHERE r.brand IS NOT NULL 
                    AND r.brand != ''
                    AND bm.source != bm.target
            """
            mapped_count = conn.execute(mapped_query).fetchone()[0]
            
            # 3. Linhas com marcas que NÃO estão no mapeamento
            unknown_query = f"""
                SELECT COUNT(*) as unknown_count
                FROM {table_name} r
                WHERE r.brand IS NOT NULL 
                    AND r.brand != ''
                    AND UPPER(TRIM(r.brand)) NOT IN (SELECT source FROM brand_map)
            """
            unknown_count = conn.execute(unknown_query).fetchone()[0]
            
            # 4. Top 5 correções (marcas que serão mais alteradas)
            # Apenas mostramos marcas que realmente serão alteradas
            top_corrections_query = f"""
                SELECT 
                    r.brand as original_brand,
                    bm.target as corrected_brand,
                    COUNT(*) as occurrences
                FROM {table_name} r
                INNER JOIN brand_map bm 
                    ON UPPER(TRIM(r.brand)) = bm.source
                WHERE r.brand IS NOT NULL 
                    AND r.brand != ''
                    AND bm.source != bm.target
                GROUP BY r.brand, bm.target
                ORDER BY occurrences DESC
                LIMIT 5
            """
            top_corrections_df = conn.execute(top_corrections_query).fetchdf()
            top_corrections = top_corrections_df.to_dict(orient="records")
            
            # 5. Lista de marcas desconhecidas (top 20)
            unknown_brands_query = f"""
                SELECT 
                    UPPER(TRIM(r.brand)) as brand,
                    COUNT(*) as occurrences
                FROM {table_name} r
                WHERE r.brand IS NOT NULL 
                    AND r.brand != ''
                    AND UPPER(TRIM(r.brand)) NOT IN (SELECT source FROM brand_map)
                GROUP BY UPPER(TRIM(r.brand))
                ORDER BY occurrences DESC
                LIMIT 20
            """
            unknown_brands_df = conn.execute(unknown_brands_query).fetchdf()
            unknown_brands = unknown_brands_df.to_dict(orient="records")
            
            return {
                "total_rows": total_rows,
                "mapped_count": mapped_count,
                "unknown_count": unknown_count,
                "top_corrections": top_corrections,
                "unknown_brands": unknown_brands
            }
        finally:
            conn.close()

    def apply_brand_normalization(self, table_name: str = "raw_data"):
        """
        Aplica a normalização de marcas usando o mapeamento.
        
        Executa um UPDATE massivo que corrige os nomes de marcas
        de acordo com o mapeamento carregado.
        
        Returns:
            dict: Dicionário com número de linhas afetadas
        """
        conn = self._get_conn(read_only=False)
        try:
            # Verificar se a coluna brand existe - usando a conexão existente
            columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
            current_columns = set([col[0] for col in columns_info])
            
            if "brand" not in current_columns:
                return {
                    "rows_affected": 0,
                    "message": "Coluna 'brand' não encontrada na tabela"
                }
            
            # Obter o DataFrame de mapeamento do serviço
            mapping_service = get_brand_mapping_service()
            mapping_df = mapping_service.get_mapping_df()
            
            # Criar tabela temporária com o mapeamento
            # Primeiro, criar os valores para o INSERT
            values_list = []
            for _, row in mapping_df.iterrows():
                # Escapar aspas simples nas strings
                source_escaped = row['source'].replace("'", "''")
                target_escaped = row['target'].replace("'", "''")
                values_list.append(f"('{source_escaped}', '{target_escaped}')")
            values_str = ", ".join(values_list)
            
            # Criar tabela temporária
            conn.execute("DROP TABLE IF EXISTS brand_map")
            conn.execute("""
                CREATE TEMP TABLE brand_map (
                    source VARCHAR,
                    target VARCHAR
                )
            """)
            conn.execute(f"INSERT INTO brand_map VALUES {values_str}")
            
            # Contar quantas linhas serão afetadas
            # Apenas contamos marcas que realmente serão alteradas (source != target)
            count_query = f"""
                SELECT COUNT(*) 
                FROM {table_name}
                WHERE UPPER(TRIM(brand)) IN (
                    SELECT source FROM brand_map WHERE source != target
                )
            """
            rows_to_update = conn.execute(count_query).fetchone()[0]
            
            # Executar o UPDATE massivo
            # Apenas atualizamos marcas que realmente precisam ser alteradas
            update_query = f"""
                UPDATE {table_name}
                SET brand = (
                    SELECT bm.target 
                    FROM brand_map bm 
                    WHERE bm.source = UPPER(TRIM({table_name}.brand))
                        AND bm.source != bm.target
                )
                WHERE UPPER(TRIM(brand)) IN (
                    SELECT source FROM brand_map WHERE source != target
                )
            """
            
            conn.execute(update_query)
            
            return {
                "rows_affected": rows_to_update,
                "message": f"Normalização de marcas aplicada com sucesso"
            }
        finally:
            conn.close()
    # --- VALIDAÇÃO DE SIMILARIDADES ---

    def diagnose_similarities(self, table_name: str = "raw_data", page: int = 1, page_size: int = 20):
        """
        Diagnostica a coluna similarity e retorna preview paginado das linhas com problemas.
        
        Validações Nível 3:
        - Verifica se a coluna existe
        - Valida formato JSON (lista de dicionários)
        - Valida chaves obrigatórias (search_ref e brand)
        - Valida search_ref (sem espaços nem caracteres especiais)
        - Valida brand (deve estar em MAIÚSCULAS)
        - Verifica se search_ref existe no projeto
        - Verifica se brand está no mapeamento
        - Verifica se valores NULL devem ser []
        
        Returns:
            dict: Dicionário com diagnóstico e preview paginado
        """
        conn = self._get_conn(read_only=True)
        try:
            # Verificar se a coluna similarity existe
            columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
            current_columns = set([col[0] for col in columns_info])
            
            if "similarity" not in current_columns:
                return {
                    "column_exists": False,
                    "format_issues": 0,
                    "search_ref_issues": 0,
                    "brand_issues": 0,
                    "invalid_refs": 0,
                    "invalid_brands": 0,
                    "empty_list_issues": 0,
                    "total_issues": 0,
                    "preview": [],
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0
                }
            
            # Carregar mapeamento de marcas para validação
            mapping_service = get_brand_mapping_service()
            mapping_df = mapping_service.get_mapping_df()
            known_brands = set(mapping_df['target'].unique())
            
            # Obter todos os search_refs válidos do projeto
            valid_refs_query = f"SELECT DISTINCT search_ref FROM {table_name} WHERE search_ref IS NOT NULL"
            valid_refs_df = conn.execute(valid_refs_query).fetchdf()
            valid_refs = set(valid_refs_df['search_ref'].tolist())
            
            # Contadores de problemas
            format_issues = 0
            search_ref_issues = 0
            brand_issues = 0
            invalid_refs = 0
            invalid_brands = 0
            empty_list_issues = 0
            
            # Buscar todas as linhas para análise
            query = f"""
                SELECT 
                    ROW_NUMBER() OVER () as row_number,
                    search_ref,
                    brand,
                    similarity
                FROM {table_name}
            """
            df = conn.execute(query).fetchdf()
            
            # Lista para armazenar linhas com problemas
            problematic_rows = []
            
            for _, row in df.iterrows():
                issues = []
                similarity_value = row['similarity']
                
                # Verificar se é NULL (deveria ser [])
                if pd.isna(similarity_value) or similarity_value is None:
                    empty_list_issues += 1
                    issues.append("NULL ao invés de []")
                    problematic_rows.append({
                        "row_number": int(row['row_number']),
                        "search_ref": row['search_ref'],
                        "brand": row['brand'],
                        "similarity_value": None,
                        "issues": issues
                    })
                    continue
                
                # Tentar parsear JSON
                try:
                    if isinstance(similarity_value, str):
                        # Tentar corrigir aspas simples para aspas duplas
                        try:
                            similarities = json.loads(similarity_value)
                        except json.JSONDecodeError:
                            # Se falhar, tentar substituir aspas simples por duplas
                            try:
                                similarity_value_fixed = similarity_value.replace("'", '"')
                                similarities = json.loads(similarity_value_fixed)
                            except json.JSONDecodeError:
                                # Último recurso: usar ast.literal_eval para Python literals
                                import ast
                                similarities = ast.literal_eval(similarity_value)
                    else:
                        similarities = similarity_value
                    
                    # Verificar se é uma lista
                    if not isinstance(similarities, list):
                        format_issues += 1
                        issues.append("Não é uma lista")
                        problematic_rows.append({
                            "row_number": int(row['row_number']),
                            "search_ref": row['search_ref'],
                            "brand": row['brand'],
                            "similarity_value": similarity_value,
                            "issues": issues
                        })
                        continue
                    
                    # Se lista vazia, está OK
                    if len(similarities) == 0:
                        continue
                    
                    # Validar cada item da lista
                    for sim in similarities:
                        # Verificar se é um dicionário
                        if not isinstance(sim, dict):
                            format_issues += 1
                            issues.append("Item não é dicionário")
                            break
                        
                        # Verificar chaves obrigatórias
                        if 'search_ref' not in sim or 'brand' not in sim:
                            format_issues += 1
                            issues.append("Faltam chaves obrigatórias")
                            break
                        
                        # Validar search_ref (sem espaços nem caracteres especiais)
                        sim_ref = sim.get('search_ref', '')
                        if sim_ref:
                            if not re.match(r'^[A-Za-z0-9_]+$', str(sim_ref)):
                                search_ref_issues += 1
                                issues.append(f"search_ref inválido: {sim_ref}")
                        
                        # Validar brand (deve estar em MAIÚSCULAS)
                        sim_brand = sim.get('brand', '')
                        if sim_brand:
                            if sim_brand != sim_brand.upper():
                                brand_issues += 1
                                issues.append(f"brand em minúsculas: {sim_brand}")
                            
                            # Contar brand desconhecida apenas para estatísticas (não é erro)
                            if sim_brand.upper() not in known_brands:
                                invalid_brands += 1
                        
                        # Contar search_ref inexistente apenas para estatísticas (não é erro)
                        if sim_ref and sim_ref not in valid_refs:
                            invalid_refs += 1
                    
                    if issues:
                        problematic_rows.append({
                            "row_number": int(row['row_number']),
                            "search_ref": row['search_ref'],
                            "brand": row['brand'],
                            "similarity_value": similarities,
                            "issues": issues
                        })
                        
                except json.JSONDecodeError:
                    format_issues += 1
                    issues.append("JSON inválido")
                    problematic_rows.append({
                        "row_number": int(row['row_number']),
                        "search_ref": row['search_ref'],
                        "brand": row['brand'],
                        "similarity_value": similarity_value,
                        "issues": issues
                    })
                except Exception as e:
                    format_issues += 1
                    issues.append(f"Erro: {str(e)}")
                    problematic_rows.append({
                        "row_number": int(row['row_number']),
                        "search_ref": row['search_ref'],
                        "brand": row['brand'],
                        "similarity_value": similarity_value,
                        "issues": issues
                    })
            
            # Paginação
            total_issues = len(problematic_rows)
            total_pages = (total_issues + page_size - 1) // page_size if total_issues > 0 else 0
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            preview = problematic_rows[start_idx:end_idx]
            
            return {
                "column_exists": True,
                "format_issues": format_issues,
                "search_ref_issues": search_ref_issues,
                "brand_issues": brand_issues,
                "invalid_refs": invalid_refs,
                "invalid_brands": invalid_brands,
                "empty_list_issues": empty_list_issues,
                "total_issues": total_issues,
                "preview": preview,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        finally:
            conn.close()

    def fix_all_similarities(self, table_name: str = "raw_data"):
        """
        Aplica todas as correções na coluna similarity:
        - Converte NULL para []
        - Normaliza search_ref (remove espaços e caracteres especiais)
        - Converte brands para MAIÚSCULAS
        - Aplica mapeamento de marcas
        
        Returns:
            dict: Dicionário com número de linhas afetadas
        """
        conn = self._get_conn(read_only=False)
        try:
            # Verificar se a coluna similarity existe
            columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
            current_columns = set([col[0] for col in columns_info])
            
            if "similarity" not in current_columns:
                return {"rows_affected": 0}
            
            # Carregar mapeamento de marcas
            mapping_service = get_brand_mapping_service()
            mapping_df = mapping_service.get_mapping_df()
            
            # Criar dicionário de mapeamento
            brand_mapping = dict(zip(mapping_df['source'], mapping_df['target']))
            
            # Buscar todas as linhas
            query = f"SELECT * FROM {table_name}"
            df = conn.execute(query).fetchdf()
            
            rows_affected = 0
            
            # Processar cada linha
            for idx, row in df.iterrows():
                similarity_value = row['similarity']
                
                # Se NULL, converter para []
                if pd.isna(similarity_value) or similarity_value is None:
                    df.at[idx, 'similarity'] = '[]'
                    rows_affected += 1
                    continue
                
                try:
                    # Parsear JSON
                    if isinstance(similarity_value, str):
                        # Tentar corrigir aspas simples para aspas duplas
                        try:
                            similarities = json.loads(similarity_value)
                        except json.JSONDecodeError:
                            # Se falhar, tentar substituir aspas simples por duplas
                            try:
                                similarity_value_fixed = similarity_value.replace("'", '"')
                                similarities = json.loads(similarity_value_fixed)
                            except json.JSONDecodeError:
                                # Último recurso: usar ast.literal_eval para Python literals
                                import ast
                                similarities = ast.literal_eval(similarity_value)
                    else:
                        similarities = similarity_value
                    
                    if not isinstance(similarities, list):
                        df.at[idx, 'similarity'] = '[]'
                        rows_affected += 1
                        continue
                    
                    # Se lista vazia, não precisa processar
                    if len(similarities) == 0:
                        continue
                    
                    # Flag para rastrear se houve mudanças
                    has_changes = False
                    
                    # Processar cada similaridade
                    for sim in similarities:
                        if isinstance(sim, dict):
                            # Normalizar search_ref
                            if 'search_ref' in sim:
                                original_ref = sim['search_ref']
                                normalized_ref = re.sub(r'[^A-Za-z0-9_]', '', str(original_ref))
                                if normalized_ref != original_ref:
                                    sim['search_ref'] = normalized_ref
                                    has_changes = True
                            
                            # Converter brand para MAIÚSCULAS e aplicar mapeamento
                            if 'brand' in sim:
                                original_brand = sim['brand']
                                upper_brand = str(original_brand).upper()
                                
                                # Aplicar mapeamento
                                mapped_brand = brand_mapping.get(upper_brand, upper_brand)
                                
                                if mapped_brand != original_brand:
                                    sim['brand'] = mapped_brand
                                    has_changes = True
                    
                    # Salvar apenas se houve mudanças
                    if has_changes:
                        df.at[idx, 'similarity'] = json.dumps(similarities)
                        rows_affected += 1
                        
                except Exception as e:
                    # Em caso de erro de parsing, converter para []
                    print(f"Erro ao processar similarity na linha {idx}: {str(e)}")
                    df.at[idx, 'similarity'] = '[]'
                    rows_affected += 1
            
            # Substituir tabela com dados corrigidos
            if rows_affected > 0:
                conn.execute(f"DROP TABLE {table_name}")
                conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
            
            return {"rows_affected": rows_affected}
        finally:
            conn.close()

    def get_similarities_statistics(self, table_name: str = "raw_data"):
        """
        Retorna estatísticas detalhadas sobre as similaridades.
        
        Returns:
            dict: Dicionário com estatísticas completas
        """
        conn = self._get_conn(read_only=True)
        try:
            # Verificar se a coluna similarity existe
            columns_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
            current_columns = set([col[0] for col in columns_info])
            
            if "similarity" not in current_columns:
                return {
                    "total_rows": 0,
                    "rows_with_similarities": 0,
                    "percentage_with_similarities": 0.0,
                    "total_similarities": 0,
                    "avg_similarities_per_row": 0.0,
                    "top_search_refs": [],
                    "top_brands": [],
                    "distribution": [],
                    "invalid_search_refs": [],
                    "invalid_brands": []
                }
            
            # Carregar mapeamento de marcas para validação
            mapping_service = get_brand_mapping_service()
            mapping_df = mapping_service.get_mapping_df()
            known_brands = set(mapping_df['target'].unique())
            
            # Obter todos os search_refs válidos do projeto
            valid_refs_query = f"SELECT DISTINCT search_ref FROM {table_name} WHERE search_ref IS NOT NULL"
            valid_refs_df = conn.execute(valid_refs_query).fetchdf()
            valid_refs = set(valid_refs_df['search_ref'].tolist())
            
            # Buscar todas as linhas
            query = f"SELECT similarity FROM {table_name}"
            df = conn.execute(query).fetchdf()
            
            total_rows = len(df)
            rows_with_similarities = 0
            total_similarities = 0
            
            search_ref_counter = {}
            brand_counter = {}
            distribution_counter = {}
            invalid_refs_set = set()
            invalid_brands_set = set()
            
            for _, row in df.iterrows():
                similarity_value = row['similarity']
                
                # Pular NULL ou valores vazios
                if pd.isna(similarity_value) or similarity_value is None:
                    continue
                
                try:
                    # Parsear JSON
                    if isinstance(similarity_value, str):
                        # Tentar corrigir aspas simples para aspas duplas
                        try:
                            similarities = json.loads(similarity_value)
                        except json.JSONDecodeError:
                            # Se falhar, tentar substituir aspas simples por duplas
                            try:
                                similarity_value_fixed = similarity_value.replace("'", '"')
                                similarities = json.loads(similarity_value_fixed)
                            except json.JSONDecodeError:
                                # Último recurso: usar ast.literal_eval para Python literals
                                import ast
                                similarities = ast.literal_eval(similarity_value)
                    else:
                        similarities = similarity_value
                    
                    if not isinstance(similarities, list):
                        continue
                    
                    # Se lista vazia, pular
                    if len(similarities) == 0:
                        continue
                    
                    rows_with_similarities += 1
                    num_sims = len(similarities)
                    total_similarities += num_sims
                    
                    # Atualizar distribuição
                    distribution_counter[num_sims] = distribution_counter.get(num_sims, 0) + 1
                    
                    # Processar cada similaridade
                    for sim in similarities:
                        if isinstance(sim, dict):
                            # Contar search_ref
                            sim_ref = sim.get('search_ref')
                            if sim_ref:
                                search_ref_counter[sim_ref] = search_ref_counter.get(sim_ref, 0) + 1
                                
                                # Verificar se ref existe
                                if sim_ref not in valid_refs:
                                    invalid_refs_set.add(sim_ref)
                            
                            # Contar brand
                            sim_brand = sim.get('brand')
                            if sim_brand:
                                brand_counter[sim_brand] = brand_counter.get(sim_brand, 0) + 1
                                
                                # Verificar se brand existe no mapeamento
                                if sim_brand not in known_brands:
                                    invalid_brands_set.add(sim_brand)
                                    
                except Exception:
                    continue
            
            # Calcular percentual
            percentage = (rows_with_similarities / total_rows * 100) if total_rows > 0 else 0.0
            
            # Calcular média
            avg = (total_similarities / rows_with_similarities) if rows_with_similarities > 0 else 0.0
            
            # Top 10 search_refs
            top_refs = sorted(search_ref_counter.items(), key=lambda x: x[1], reverse=True)[:10]
            top_search_refs = [{"search_ref": ref, "count": count} for ref, count in top_refs]
            
            # Top 10 brands
            top_brands_list = sorted(brand_counter.items(), key=lambda x: x[1], reverse=True)[:10]
            top_brands = [{"brand": brand, "count": count} for brand, count in top_brands_list]
            
            # Distribuição
            distribution = sorted(
                [{"similarity_count": count, "row_count": rows} 
                 for count, rows in distribution_counter.items()],
                key=lambda x: x['similarity_count']
            )
            
            return {
                "total_rows": total_rows,
                "rows_with_similarities": rows_with_similarities,
                "percentage_with_similarities": round(percentage, 2),
                "total_similarities": total_similarities,
                "avg_similarities_per_row": round(avg, 2),
                "top_search_refs": top_search_refs,
                "top_brands": top_brands,
                "distribution": distribution,
                "invalid_search_refs": sorted(list(invalid_refs_set)),
                "invalid_brands": sorted(list(invalid_brands_set))
            }
        finally:
            conn.close()
