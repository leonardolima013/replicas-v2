REQUIRED_COLUMNS = {"search_ref", "manufacturer_ref", "name", "brand"}

OPTIONAL_COLUMNS = {
    "barcode", "ncm", "application", "net_weight", "gross_weight",
    "born_at", "deprecated_at", "catalog_id", "height", "width",
    "depth", "url_thumb", "notes", "file_high", "file_low",
    "file_medium", "file_water_mark", "position"
}

# Agrupamentos para tratamento automatizado
STRING_CHECK_COLUMNS = {"search_ref", "application", "notes", "ncm", "name", "brand"}
NUMERIC_CHECK_COLUMNS = {"gross_weight", "net_weight", "width", "depth", "height", "ipi"}

# Colunas alvo para cada tipo de validação
BRAND_COLS = {"brand"}
NCM_COLS = {"ncm"}
BARCODE_COLS = {"barcode"}
WEIGHT_COLS = {"gross_weight", "net_weight"} # Validação cruzada
DIMENSION_COLS = {"width", "height", "depth"}
CODE_REF_COLS = {"search_ref", "manufacturer_ref"}