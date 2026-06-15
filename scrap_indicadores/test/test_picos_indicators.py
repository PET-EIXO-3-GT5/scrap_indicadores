import pandas as pd
from scrap_indicadores.picos_indicators import (
    _empty_series, _text_column, _normalize_municipality_code, _municipality_column,
    filter_picos, calculate_sim_indicators, calculate_sih_indicators, calculate_sinan_indicators,
    calculate_pni_indicators, calculate_picos_indicators, _count_values, value_counts_dict,
    summarize_available_indicators, summarize_sinan_dengue_indicators
)

def test_empty_series():
    idx = pd.Index([1, 2, 3])
    s = _empty_series(idx)
    assert len(s) == 3
    assert s.isna().all()
    
def test_text_column():
    df = pd.DataFrame({"A": [1, 2, None], "B": [" x ", "y", "z"]})
    s = _text_column(df, "B")
    assert s[0] == "x"
    assert s[2] == "z"
    s2 = _text_column(df, "C")
    assert s2.isna().all()

def test_normalize_municipality_code():
    assert _normalize_municipality_code(pd.NA) is None
    assert _normalize_municipality_code("123.0") == "123"
    assert _normalize_municipality_code(" 123 ") == "123"

def test_municipality_column():
    df = pd.DataFrame({"CODMUNRES": [1]})
    assert _municipality_column(df, ["A", "CODMUNRES"]) == "CODMUNRES"
    assert _municipality_column(df, ["A", "B"]) is None

def test_filter_picos():
    df = pd.DataFrame({"CODMUNRES": ["220800", "111111", "220800.0", pd.NA], "VAL": [1, 2, 3, 4]})
    df_filtered, col = filter_picos(df, ["CODMUNRES"])
    assert col == "CODMUNRES"
    assert len(df_filtered) == 2
    assert df_filtered["VAL"].tolist() == [1, 3]

def test_filter_picos_empty():
    df = pd.DataFrame({"A": [1, 2]})
    df_filtered, col = filter_picos(df, ["CODMUNRES"])
    assert col is None
    assert df_filtered.empty

def test_calculate_sim_indicators():
    df = pd.DataFrame({
        "CODMUNRES": ["220800", "220800", "220800", "220800"],
        "IDADE": ["425", "450", "012", "115"],
        "SEXO": ["2", "1", "2", "2"],
        "CAUSABAS": ["O10", "A10", "B10", "C10"],
        "OBITOMAT": ["1", None, None, "5"]
    })
    res = calculate_sim_indicators(df)
    assert res["obitos_total"] == 4
    assert res["obitos_mulheres_idade_fertil"] == 1
    assert res["obitos_maternos"] == 2
    assert res["obitos_infantis"] == 2

def test_calculate_sih_indicators():
    df = pd.DataFrame({
        "MUNIC_RES": ["220800", "220800", "220800"],
        "IDADE": ["5", "15", "8"],
        "DIAG_PRINC": ["A00", "B00", "A00"]
    })
    res = calculate_sih_indicators(df)
    assert res["internacoes_total"] == 3
    assert res["internacoes_infantis"] == 2
    assert res["principais_causas_internacao_infantil"]["A00"] == 2

def test_calculate_sinan_indicators():
    df = pd.DataFrame({
        "ID_MN_RESI": ["220800", "220800"],
        "HOSPITALIZ": ["1", "2"],
        "EVOLUCAO": ["1", "2"],
        "CLASSI_FIN": ["10", "10"],
        "CRITERIO": ["1", "2"]
    })
    res = calculate_sinan_indicators(df)
    assert res["casos_dengue_notificados"] == 2
    assert res["hospitalizacoes"] == 1
    assert res["obitos"] == 1
    assert res["classificacao_final"]["10"] == 2

def test_calculate_pni_indicators():
    df = pd.DataFrame({
        "CODMUNRES": ["220800", "220800", "111111"]
    })
    res = calculate_pni_indicators(df)
    assert res["registros_vacinacao"] == 2

def test_calculate_picos_indicators():
    df_empty = pd.DataFrame()
    res = calculate_picos_indicators(df_empty, df_empty, df_empty, df_empty)
    assert "sim" in res
    assert "sih" in res
    assert "sinan" in res
    assert "pni" in res

def test_count_values():
    df = pd.DataFrame({"A": ["1", "2", " 1 ", pd.NA]})
    assert _count_values(df, "A", ["1"]) == 2
    assert _count_values(df, "B", ["1"]) == 0

def test_value_counts_dict():
    df = pd.DataFrame({"A": ["X", "X", "Y", pd.NA]})
    res = value_counts_dict(df, "A")
    assert res["X"] == 2
    assert res["Y"] == 1
    assert res["<vazio>"] == 1
    assert value_counts_dict(df, "B") == {}

def test_summarize_available_indicators():
    df = pd.DataFrame({"A": ["X"], "B": ["Y"]})
    res = summarize_available_indicators(df, ["A", "C"])
    assert "A" in res
    assert "C" not in res

def test_summarize_sinan_dengue_indicators():
    df = pd.DataFrame({"CLASSI_FIN": ["1", "1"], "IGNORE_ME": ["2", "2"]})
    res = summarize_sinan_dengue_indicators(df)
    assert "CLASSI_FIN" in res
    assert "IGNORE_ME" not in res
