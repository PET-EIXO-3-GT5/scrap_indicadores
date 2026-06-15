# -*- coding: utf-8 -*-
import os
import pytest
import pandas as pd
from scrap_indicadores.scraper_navegador import parse_tabnet_csv
from scrap_indicadores.picos_indicators import calculate_picos_indicators

def test_02_verificar_dados(shared_data_dir):
    """
    Test 2: Lê os CSVs baixados no teste anterior e testa se todos 
    os valores exatos calculados para Picos (PI) batem com o esperado.
    """
    picos_code = "220800"
    dfs = {}
    bases = [
        "sim_geral", "sim_infantil", "sim_materno", "sim_fertil",
        "sih_geral", "sih_infantil_causas",
        "sinan_classificacao", "sinan_criterio", "sinan_evolucao", "sinan_hospitalizacao",
        "pni_doses"
    ]

    for base in bases:
        file_path = os.path.join(shared_data_dir, f"{base}.csv")
        if os.path.exists(file_path):
            try:
                dfs[base] = parse_tabnet_csv(file_path)
            except Exception as e:
                print(f"Erro ao parsear {base}: {e}")
                
    assert len(dfs) > 0, "Nenhuma base pôde ser lida para verificação."
    
    indicadores = calculate_picos_indicators(dfs, picos_code=picos_code)
    
    # 1. Validação SIM
    sim = indicadores.get("sim", [])
    assert len(sim) > 0, "SIM vazio"
    
    # Encontra as linhas totalizadoras anuais (2024 para geral, 2023 para materno)
    sim_2024 = next((item for item in sim if item["periodo"] == "2024"), {})
    sim_2023 = next((item for item in sim if item["periodo"] == "2023"), {})
    
    assert sim_2024.get("obitos_total") == 621
    assert sim_2024.get("obitos_mulheres_idade_fertil") == 135
    assert sim_2023.get("obitos_maternos") == 1
    assert sim_2024.get("obitos_infantis") == 14

    # 2. Validação SIH
    sih = indicadores.get("sih", [])
    assert len(sih) > 0, "SIH vazio"
    
    sih_2024 = next((item for item in sih if item["periodo"] == "2024"), {})
    
    assert sih_2024.get("internacoes_total") == 3798
    assert sih_2024.get("internacoes_infantis") == 457
    
    causas = sih_2024.get("principais_causas_internacao_infantil", {})
    assert causas.get("Cap 16") == 152
    assert causas.get("Cap 10") == 86
    assert causas.get("Cap 01") == 55

    # 3. Validação SINAN (Dengue)
    # O SINAN retorna dados mensais (sem linha totalizadora anual),
    # então agregamos todos os períodos para obter os totais.
    sinan = indicadores.get("sinan", [])
    assert len(sinan) > 0, "SINAN vazio"
    
    total_casos = sum(item.get("casos_dengue_notificados", 0) for item in sinan)
    total_hosp = sum(item.get("hospitalizacoes", 0) for item in sinan)
    total_obitos = sum(item.get("obitos", 0) for item in sinan)
    
    assert total_casos == 61
    assert total_hosp == 16
    assert total_obitos == 1

    # Agregar distribuições de todos os meses
    from collections import Counter
    class_total = Counter()
    criterio_total = Counter()
    evolucao_total = Counter()
    hospitalizacao_total = Counter()
    
    for item in sinan:
        for k, v in item.get("classificacao_final", {}).items():
            class_total[k] += v
        for k, v in item.get("criterio_confirmacao", {}).items():
            criterio_total[k] += v
        for k, v in item.get("evolucao", {}).items():
            evolucao_total[k] += v
        for k, v in item.get("hospitalizacao", {}).items():
            hospitalizacao_total[k] += v
            
    assert class_total.get("Dengue") == 56
    assert class_total.get("Dengue com sinais de alarme") == 5
    
    # Busca segura por chaves contendo caracteres problemáticos de encoding do CSV
    if criterio_total:
        laboratorial_keys = [k for k in criterio_total.keys() if "Laborat" in k]
        if laboratorial_keys:
            assert criterio_total[laboratorial_keys[0]] == 61
            
    assert evolucao_total.get("Cura") == 59
    assert any(v == 1 and "Ign" in k for k, v in evolucao_total.items())
    assert any(v == 1 and "bito por outra causa" in k for k, v in evolucao_total.items())
    
    assert any(v == 45 and "N" in k for k, v in hospitalizacao_total.items())
    assert hospitalizacao_total.get("Sim") == 16

    # 4. Validação PNI
    # O PNI retorna dados mensais (ex: "2022/Jan"), então somamos todos.
    pni = indicadores.get("pni", [])
    assert len(pni) > 0, "PNI vazio"
    
    pni_total = sum(item.get("registros_vacinacao", 0) for item in pni)
    assert pni_total == 41964
