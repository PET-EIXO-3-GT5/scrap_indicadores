import pandas as pd
from scrap_indicadores.picos_indicators import (
    calculate_sim_indicators, calculate_sih_indicators,
    calculate_sinan_indicators, calculate_pni_indicators, calculate_picos_indicators
)

def test_calculate_sim_indicators():
    df_geral = pd.DataFrame({"periodo": ["2024/Jan"], "geral_óbitos": [100]})
    df_infantil = pd.DataFrame({"periodo": ["2024/Jan"], "infantil_óbitos": [5]})
    df_materno = pd.DataFrame({"periodo": ["2024/Jan"], "materno_materno": [2]})
    df_fertil = pd.DataFrame({"periodo": ["2024/Jan"], "fertil_10 a 14 anos": [1], "fertil_15 a 19 anos": [2]})
    
    res = calculate_sim_indicators(df_geral, df_infantil, df_materno, df_fertil)
    assert len(res) == 1
    assert res[0]["obitos_total"] == 100
    assert res[0]["obitos_infantis"] == 5
    assert res[0]["obitos_maternos"] == 2
    assert res[0]["obitos_mulheres_idade_fertil"] == 3

def test_calculate_sih_indicators():
    df_geral = pd.DataFrame({"periodo": ["2024/Jan"], "geral_internações": [500]})
    df_infantil_causas = pd.DataFrame({
        "periodo": ["2024/Jan"],
        "causas_Total": [50],
        "causas_A00": [10],
        "causas_B00": [20]
    })
    
    res = calculate_sih_indicators(df_geral, df_infantil_causas)
    assert len(res) == 1
    assert res[0]["internacoes_total"] == 500
    assert res[0]["internacoes_infantis"] == 30
    assert res[0]["principais_causas_internacao_infantil"]["B00"] == 20
    assert res[0]["principais_causas_internacao_infantil"]["A00"] == 10

def test_calculate_sinan_indicators():
    df_class = pd.DataFrame({"periodo": ["2024/Jan"], "class_Total": [150], "class_Dengue": [100]})
    df_crit = pd.DataFrame({"periodo": ["2024/Jan"], "crit_Total": [150], "crit_Lab": [150]})
    df_evol = pd.DataFrame({"periodo": ["2024/Jan"], "evol_Cura": [140], "evol_Óbito por Dengue": [10]})
    df_hosp = pd.DataFrame({"periodo": ["2024/Jan"], "hosp_Sim": [20], "hosp_Não": [130]})
    
    res = calculate_sinan_indicators(df_class, df_crit, df_evol, df_hosp)
    assert len(res) == 1
    assert res[0]["casos_dengue_notificados"] == 100
    assert res[0]["obitos"] == 10
    assert res[0]["hospitalizacoes"] == 20
    assert res[0]["classificacao_final"]["Dengue"] == 100
    assert res[0]["criterio_confirmacao"]["Lab"] == 150

def test_calculate_pni_indicators():
    df_doses = pd.DataFrame({"periodo": ["2024/Jan"], "Doses_aplicadas": [1000]})
    res = calculate_pni_indicators(df_doses, ano="2024")
    assert len(res) == 1
    assert res[0]["registros_vacinacao"] == 1000

def test_calculate_picos_indicators():
    dfs = {
        "sim_geral": pd.DataFrame({"periodo": ["2024/Jan"], "Óbitos_p/Residênc": [10]}),
        "sih_geral": pd.DataFrame({"periodo": ["2024/Jan"], "Internações": [20]}),
    }
    res = calculate_picos_indicators(dfs)
    assert len(res["sim"]) == 1
    assert res["sim"][0]["obitos_total"] == 10
    assert len(res["sih"]) == 1
    assert res["sih"][0]["internacoes_total"] == 20
    assert len(res["sinan"]) == 0
    assert len(res["pni"]) == 0
