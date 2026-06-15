import pandas as pd
from scrap_indicadores.picos_indicators import (
    get_picos_value, calculate_sim_indicators, calculate_sih_indicators,
    calculate_sinan_indicators, calculate_pni_indicators, calculate_picos_indicators
)

def test_get_picos_value():
    df = pd.DataFrame({
        "cod_ibge": ["220800", "111111"],
        "VAL": [10.5, 20.0]
    })
    val = get_picos_value(df, "VAL", "220800")
    assert val == 10.5
    
    val2 = get_picos_value(df, "INEXISTENTE", "220800")
    assert val2 == 0.0

def test_calculate_sim_indicators():
    df_geral = pd.DataFrame({"cod_ibge": ["220800"], "Óbitos_p/Residênc": [100]})
    df_infantil = pd.DataFrame({"cod_ibge": ["220800"], "Óbitos_p/Residênc": [5]})
    df_materno = pd.DataFrame({"cod_ibge": ["220800"], "Óbitos_p/Residênc": [2]})
    df_fertil = pd.DataFrame({"cod_ibge": ["220800"], "10 a 14 anos": [1], "15 a 19 anos": [2], "IGNORE": [99]})
    
    res = calculate_sim_indicators(df_geral, df_infantil, df_materno, df_fertil, "220800")
    assert res["obitos_total"] == 100
    assert res["obitos_infantis"] == 5
    assert res["obitos_maternos"] == 2
    assert res["obitos_mulheres_idade_fertil"] == 3

def test_calculate_sih_indicators():
    df_geral = pd.DataFrame({"cod_ibge": ["220800"], "Internações": [500]})
    df_infantil_causas = pd.DataFrame({
        "cod_ibge": ["220800"],
        "Total": [50],
        "A00": [10],
        "B00": [20],
        "C00": [5]
    })
    
    res = calculate_sih_indicators(df_geral, df_infantil_causas, "220800")
    assert res["internacoes_total"] == 500
    assert res["internacoes_infantis"] == 50
    assert res["principais_causas_internacao_infantil"]["B00"] == 20
    assert res["principais_causas_internacao_infantil"]["A00"] == 10

def test_calculate_sinan_indicators():
    df_class = pd.DataFrame({"cod_ibge": ["220800"], "Total": [150], "Dengue": [100], "Outro": [50]})
    df_crit = pd.DataFrame({"cod_ibge": ["220800"], "Total": [150], "Lab": [150]})
    df_evol = pd.DataFrame({"cod_ibge": ["220800"], "Cura": [140], "Óbito por Dengue": [10]})
    df_hosp = pd.DataFrame({"cod_ibge": ["220800"], "Sim": [20], "Não": [130]})
    
    res = calculate_sinan_indicators(df_class, df_crit, df_evol, df_hosp, "220800")
    assert res["casos_dengue_notificados"] == 150
    assert res["obitos"] == 10
    assert res["hospitalizacoes"] == 20
    assert res["classificacao_final"]["Dengue"] == 100
    assert res["criterio_confirmacao"]["Lab"] == 150

def test_calculate_pni_indicators():
    df_doses = pd.DataFrame({"cod_ibge": ["220800"], "Doses_aplicadas": [1000]})
    res = calculate_pni_indicators(df_doses, "220800")
    assert res["registros_vacinacao"] == 1000

def test_calculate_picos_indicators():
    dfs = {
        "sim_geral": pd.DataFrame({"cod_ibge": ["220800"], "Óbitos_p/Residênc": [10]}),
        "sih_geral": pd.DataFrame({"cod_ibge": ["220800"], "Internações": [20]}),
    }
    res = calculate_picos_indicators(dfs, "220800")
    assert res["sim"]["obitos_total"] == 10
    assert res["sih"]["internacoes_total"] == 20
    assert res["sinan"]["casos_dengue_notificados"] == 0
    assert res["pni"]["registros_vacinacao"] == 0
