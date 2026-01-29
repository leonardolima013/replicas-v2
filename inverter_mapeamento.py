#!/usr/bin/env python3
"""
Script para inverter o mapeamento consolidado de marcas.

Estrutura do arquivo consolidado:
{
  "MARCA_PRINCIPAL": ["variacao1", "variacao2", ...]
}

Estrutura do arquivo invertido:
{
  "MARCA_PRINCIPAL": "MARCA_PRINCIPAL",  # auto-referência
  "variacao1": "MARCA_PRINCIPAL",
  "variacao2": "MARCA_PRINCIPAL",
  ...
}
"""

import json
from pathlib import Path


def inverter_mapeamento(arquivo_consolidado: str, arquivo_invertido: str) -> None:
    """
    Inverte o mapeamento consolidado e salva no arquivo invertido.
    
    Args:
        arquivo_consolidado: Caminho para o arquivo consolidado
        arquivo_invertido: Caminho para o arquivo invertido de saída
    """
    # Ler o arquivo consolidado
    print(f"Lendo arquivo consolidado: {arquivo_consolidado}")
    with open(arquivo_consolidado, 'r', encoding='utf-8') as f:
        mapeamento_consolidado = json.load(f)
    
    # Criar o mapeamento invertido
    mapeamento_invertido = {}
    
    print("Invertendo mapeamento...")
    for marca_principal, variacoes in mapeamento_consolidado.items():
        # Adicionar auto-referência da marca principal
        mapeamento_invertido[marca_principal] = marca_principal
        
        # Adicionar cada variação apontando para a marca principal
        for variacao in variacoes:
            if variacao in mapeamento_invertido and mapeamento_invertido[variacao] != marca_principal:
                print(f"⚠️  AVISO: '{variacao}' já existe no mapeamento invertido!")
                print(f"   Valor anterior: {mapeamento_invertido[variacao]}")
                print(f"   Novo valor: {marca_principal}")
            
            mapeamento_invertido[variacao] = marca_principal
    
    # Ordenar as chaves alfabeticamente
    mapeamento_invertido_ordenado = dict(sorted(mapeamento_invertido.items()))
    
    # Salvar o arquivo invertido
    print(f"Salvando arquivo invertido: {arquivo_invertido}")
    with open(arquivo_invertido, 'w', encoding='utf-8') as f:
        json.dump(mapeamento_invertido_ordenado, f, ensure_ascii=False, indent=2)
    
    # Estatísticas
    total_marcas_principais = len(mapeamento_consolidado)
    total_entradas_invertido = len(mapeamento_invertido_ordenado)
    total_variacoes = total_entradas_invertido - total_marcas_principais
    
    print("\n✅ Inversão concluída com sucesso!")
    print(f"📊 Estatísticas:")
    print(f"   - Marcas principais: {total_marcas_principais}")
    print(f"   - Variações: {total_variacoes}")
    print(f"   - Total de entradas no arquivo invertido: {total_entradas_invertido}")


def main():
    """Função principal."""
    # Caminhos dos arquivos
    base_dir = Path(__file__).parent
    arquivo_consolidado = base_dir / "mapeamento-final-consolidado.json"
    arquivo_invertido = base_dir / "mapeamento-marcas-invertido.json"
    
    # Verificar se o arquivo consolidado existe
    if not arquivo_consolidado.exists():
        print(f"❌ Erro: Arquivo consolidado não encontrado: {arquivo_consolidado}")
        return
    
    # Inverter o mapeamento
    inverter_mapeamento(str(arquivo_consolidado), str(arquivo_invertido))


if __name__ == "__main__":
    main()
