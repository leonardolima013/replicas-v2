import duckdb
import os
import pandas as pd
import re

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
            valid_columns = columns_to_check & current_columns
            
            for col in valid_columns:
                query = f"SELECT COUNT(*) FROM {table_name} WHERE \"{col}\" IS NOT NULL AND \"{col}\" != '' AND \"{col}\" != UPPER(\"{col}\")"
                count = conn.execute(query).fetchone()[0]
                if count > 0:
                    issues.append(col)
            return issues
        finally:
            conn.close()

    def diagnose_null_strings(self, columns_to_check: set, table_name: str = "raw_data"):
        """Verifica quais colunas de string têm valores nulos ou 'nan'."""
        conn = self._get_conn(read_only=True)
        issues = []
        try:
            current_columns = set(self.get_columns(table_name))
            valid_columns = columns_to_check & current_columns
            
            for col in valid_columns:
                query = f"SELECT COUNT(*) FROM {table_name} WHERE \"{col}\" IS NULL OR LOWER(\"{col}\") = 'nan' OR \"{col}\" = ''"
                count = conn.execute(query).fetchone()[0]
                if count > 0:
                    issues.append(col)
            return issues
        finally:
            conn.close()

    def diagnose_null_numerics(self, columns_to_check: set, table_name: str = "raw_data"):
        """Verifica quais colunas numéricas têm valores nulos."""
        conn = self._get_conn(read_only=True)
        issues = []
        try:
            current_columns = set(self.get_columns(table_name))
            valid_columns = columns_to_check & current_columns
            
            for col in valid_columns:
                query = f"SELECT COUNT(*) FROM {table_name} WHERE \"{col}\" IS NULL OR LOWER(\"{col}\") = 'nan' OR \"{col}\" = ''"
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
            
            query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE
                    ncm IS NOT NULL
                    AND ncm != ''
                    AND (
                        LENGTH(REPLACE(ncm, '.', '')) != 8
                        OR ncm SIMILAR TO '.*[a-zA-Z].*'
                        OR ncm LIKE '%-%'
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
            
            query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE
                    barcode IS NOT NULL
                    AND barcode != ''
                    AND (
                        LENGTH(barcode) NOT IN (8, 12, 13)
                        OR barcode SIMILAR TO '.*[^0-9].*'
                    )
            """
            count = conn.execute(query).fetchone()[0]
            return count
        finally:
            conn.close()

    def diagnose_weight_issues(self, table_name: str = "raw_data"):
        """Diagnostica problemas em pesos: gross < net, negativos, zerados."""
        conn = self._get_conn(read_only=True)
        try:
            current_columns = set(self.get_columns(table_name))
            has_gross = "gross_weight" in current_columns
            has_net = "net_weight" in current_columns
            
            if not (has_gross and has_net):
                return 0
            
            # Tentar converter para DOUBLE, se falhar usar como VARCHAR
            query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE
                    (TRY_CAST(gross_weight AS DOUBLE) < TRY_CAST(net_weight AS DOUBLE))
                    OR (TRY_CAST(gross_weight AS DOUBLE) < 0)
                    OR (TRY_CAST(net_weight AS DOUBLE) < 0)
                    OR (TRY_CAST(gross_weight AS DOUBLE) = 0 AND TRY_CAST(net_weight AS DOUBLE) = 0)
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
                conditions.append(f"TRY_CAST({dim} AS DOUBLE) <= 0")
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
        """Diagnostica problemas em manufacturer_ref: tamanho < 3, espaços, caracteres proibidos."""
        conn = self._get_conn(read_only=True)
        try:
            current_columns = set(self.get_columns(table_name))
            if "manufacturer_ref" not in current_columns:
                return 0
            
            query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE
                    manufacturer_ref IS NOT NULL
                    AND manufacturer_ref != ''
                    AND (
                        LENGTH(manufacturer_ref) < 3
                        OR manufacturer_ref LIKE '% %'
                        OR manufacturer_ref SIMILAR TO '.*[@#%&].*'
                    )
            """
            count = conn.execute(query).fetchone()[0]
            return count
        finally:
            conn.close()

    def fix_null_strings(self, columns_to_fix: set, table_name: str = "raw_data"):
        """Substitui NULL e 'nan' por string vazia em colunas de texto."""
        # Obter colunas válidas usando método separado
        current_columns = set(self.get_columns(table_name))
        valid_columns = columns_to_fix & current_columns
        
        conn = self._get_conn(read_only=False)
        try:
            total_affected = 0
            
            for col in valid_columns:
                # Primeiro, atualizar NULLs e 'nan'
                query = f"UPDATE {table_name} SET \"{col}\" = '' WHERE \"{col}\" IS NULL OR LOWER(\"{col}\") = 'nan'"
                result = conn.execute(query)
                # DuckDB não retorna rows_affected diretamente, então contamos antes
                count_query = f"SELECT COUNT(*) FROM {table_name} WHERE \"{col}\" = ''"
                total_affected += conn.execute(count_query).fetchone()[0]
            
            return {"columns": list(valid_columns), "rows_affected": total_affected}
        finally:
            conn.close()

    def apply_uppercase_fix(self, columns_to_fix: set, table_name: str = "raw_data"):
        """Converte valores para UPPERCASE em colunas de texto."""
        # Obter colunas válidas usando método separado
        current_columns = set(self.get_columns(table_name))
        valid_columns = columns_to_fix & current_columns
        
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
        """Substitui NULL por 0 em colunas numéricas, com conversão de tipo se necessário."""
        # Obter colunas válidas e tipos usando método separado
        current_columns = set(self.get_columns(table_name))
        valid_columns = columns_to_fix & current_columns
        
        # Obter informações de tipo das colunas em uma conexão separada
        conn_info = self._get_conn(read_only=True)
        try:
            columns_info = conn_info.execute(f"DESCRIBE {table_name}").fetchall()
            column_types = {col[0]: col[1] for col in columns_info}
        finally:
            conn_info.close()
        
        # Agora fazer as modificações
        conn = self._get_conn(read_only=False)
        try:
            total_affected = 0
            
            for col in valid_columns:
                # Contar quantas linhas têm NULL ou 'nan'
                count_query = f"SELECT COUNT(*) FROM {table_name} WHERE \"{col}\" IS NULL OR LOWER(\"{col}\") = 'nan' OR \"{col}\" = ''"
                affected = conn.execute(count_query).fetchone()[0]
                total_affected += affected
                
                col_type = column_types.get(col, "VARCHAR")
                
                # Se a coluna for VARCHAR (importada com ALL_VARCHAR=TRUE), precisamos converter
                if "VARCHAR" in col_type.upper():
                    # Primeiro, substituir 'nan' e vazios por NULL
                    conn.execute(f"UPDATE {table_name} SET \"{col}\" = NULL WHERE LOWER(\"{col}\") = 'nan' OR \"{col}\" = ''")
                    
                    # Depois, tentar converter para DOUBLE e substituir NULL por 0
                    try:
                        conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN \"{col}\" TYPE DOUBLE")
                        conn.execute(f"UPDATE {table_name} SET \"{col}\" = 0 WHERE \"{col}\" IS NULL")
                    except:
                        # Se falhar a conversão, apenas substituir por '0' como string
                        conn.execute(f"UPDATE {table_name} SET \"{col}\" = '0' WHERE \"{col}\" IS NULL")
                else:
                    # Se já for numérico, apenas substituir NULL por 0
                    conn.execute(f"UPDATE {table_name} SET \"{col}\" = 0 WHERE \"{col}\" IS NULL")
            
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
            count_query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE barcode IS NOT NULL 
                AND barcode != '' 
                AND barcode != fix_ean_udf(barcode)
            """
            affected = conn.execute(count_query).fetchone()[0]
            
            # Executar a correção em massa
            conn.execute(f"UPDATE {table_name} SET barcode = fix_ean_udf(barcode) WHERE barcode IS NOT NULL AND barcode != ''")
            
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
            # Contar linhas que serão afetadas
            count_query = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE ncm IS NOT NULL 
                AND ncm != ''
                AND ncm != regexp_replace(ncm, '[^0-9]', '', 'g')
            """
            affected = conn.execute(count_query).fetchone()[0]
            
            # Remover tudo que não for número
            conn.execute(f"UPDATE {table_name} SET ncm = regexp_replace(ncm, '[^0-9]', '', 'g') WHERE ncm IS NOT NULL AND ncm != ''")
            
            return {"columns": ["ncm"], "rows_affected": affected}
        finally:
            conn.close()

    def apply_codes_fix(self, table_name: str = "raw_data"):
        """Sanitiza search_ref e manufacturer_ref: TRIM, UPPER, remove espaços e caracteres especiais."""
        current_columns = set(self.get_columns(table_name))
        codes = {"search_ref", "manufacturer_ref"}
        existing_codes = codes & current_columns
        
        if not existing_codes:
            return {"columns": [], "rows_affected": 0}
        
        conn = self._get_conn(read_only=False)
        try:
            total_affected = 0
            
            for col in existing_codes:
                # Contar linhas que serão afetadas
                count_query = f"""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE \"{col}\" IS NOT NULL 
                    AND \"{col}\" != ''
                    AND \"{col}\" != regexp_replace(TRIM(UPPER(\"{col}\")), '[^A-Z0-9]', '', 'g')
                """
                affected = conn.execute(count_query).fetchone()[0]
                total_affected += affected
                
                # Aplicar: TRIM + UPPER + remover tudo que não for alfanumérico
                conn.execute(f"""
                    UPDATE {table_name} 
                    SET \"{col}\" = regexp_replace(TRIM(UPPER(\"{col}\")), '[^A-Z0-9]', '', 'g')
                    WHERE \"{col}\" IS NOT NULL AND \"{col}\" != ''
                """)
            
            return {"columns": list(existing_codes), "rows_affected": total_affected}
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
                        conn.execute(f"UPDATE {table_name} SET \"{col}\" = NULL WHERE LOWER(\"{col}\") = 'nan' OR \"{col}\" = ''")
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

    def remove_duplicates(self, table_name: str = "raw_data"):
        """Remove duplicadas mantendo apenas a primeira ocorrência de cada search_ref + brand."""
        current_columns = set(self.get_columns(table_name))
        if "search_ref" not in current_columns or "brand" not in current_columns:
            return {"rows_affected": 0}
        
        conn = self._get_conn(read_only=False)
        try:
            # Contar duplicadas antes de remover
            count_query = f"""
                SELECT COUNT(*) - COUNT(DISTINCT search_ref, brand) as duplicates
                FROM {table_name}
                WHERE search_ref IS NOT NULL 
                AND search_ref != ''
                AND brand IS NOT NULL 
                AND brand != ''
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