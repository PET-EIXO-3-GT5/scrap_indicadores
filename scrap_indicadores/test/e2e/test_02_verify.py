import os
import pytest
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
    sim = indicadores.get("sim", {})
    assert sim.get("obitos_total") == 621
    assert sim.get("obitos_mulheres_idade_fertil") == 135
    assert sim.get("obitos_maternos") == 0
    assert sim.get("obitos_infantis") == 14

    # 2. Validação SIH
    sih = indicadores.get("sih", {})
    assert sih.get("internacoes_total") == 3877
    assert sih.get("internacoes_infantis") == 3877
    
    causas_infantis = sih.get("principais_causas_internacao_infantil", {})
    assert causas_infantis.get("Cap 15") == 693
    assert causas_infantis.get("Cap 10") == 555
    assert causas_infantis.get("Cap 19") == 544
    assert causas_infantis.get("Cap 11") == 516
    assert causas_infantis.get("Cap 01") == 447

    # 3. Validação SINAN (Dengue)
    sinan = indicadores.get("sinan", {})
    assert sinan.get("casos_dengue_notificados") == 78
    assert sinan.get("hospitalizacoes") == 18
    assert sinan.get("obitos") == 0
    
    classificacao = sinan.get("classificacao_final", {})
    assert classificacao.get("Dengue") == 72
    assert classificacao.get("Dengue com sinais de alarme") == 5
    assert classificacao.get("Dengue grave") == 1
    
    # Busca segura por chaves contendo caracteres problemáticos de encoding do CSV
    criterio = sinan.get("criterio_confirmacao", {})
    if criterio:
        # Pega a chave que parece com Laboratorial e valida que o valor é 78
        laboratorial_keys = [k for k in criterio.keys() if "Laborat" in k]
        if laboratorial_keys:
            assert criterio[laboratorial_keys[0]] == 78
            
    evolucao = sinan.get("evolucao", {})
    assert evolucao.get("Cura") == 76
    # Validando ignorado e óbito por outras causas
    assert any(v == 1 and "Ign" in k for k, v in evolucao.items())
    assert any(v == 1 and "bito por outra causa" in k for k, v in evolucao.items())
    
    hospitalizacao = sinan.get("hospitalizacao", {})
    assert any(v == 60 and "N" in k for k, v in hospitalizacao.items())
    assert hospitalizacao.get("Sim") == 18

    # 4. Validação PNI
    pni = indicadores.get("pni", {})
    assert pni.get("registros_vacinacao") == 41964
