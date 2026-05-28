import pandas as pd

from scrap_indicadores.picos_indicators import (
    calculate_picos_indicators,
    calculate_pni_indicators,
    calculate_sih_indicators,
    calculate_sim_indicators,
    calculate_sinan_indicators,
    filter_picos,
)


def test_filter_picos_keeps_only_picos_and_accepts_numeric_codes():
    df = pd.DataFrame(
        {
            "CODMUNRES": ["220800", "221100", 220800, 220800.0, None],
            "valor": [1, 2, 3, 4, 5],
        }
    )

    filtered, municipality_column = filter_picos(df, ["CODMUNRES"])

    assert municipality_column == "CODMUNRES"
    assert filtered["valor"].tolist() == [1, 3, 4]


def test_sim_indicators_count_only_picos_records():
    df = pd.DataFrame(
        {
            "CODMUNRES": ["220800", "220800", "220800", "220800", "221100", "220800"],
            "IDADE": ["420", "405", "300", "499", "430", None],
            "SEXO": ["2", "2", "1", "2", "2", "2"],
            "CAUSABAS": ["A10", "O95", "B20", None, "O10", "C10"],
            "OBITOMAT": ["0", "0", "2", "0", "1", None],
        }
    )

    result = calculate_sim_indicators(df)

    assert result == {
        "obitos_total": 5,
        "obitos_mulheres_idade_fertil": 1,
        "obitos_maternos": 2,
        "obitos_infantis": 1,
    }


def test_sim_indicators_handle_empty_and_missing_columns():
    result = calculate_sim_indicators(pd.DataFrame())

    assert result == {
        "obitos_total": 0,
        "obitos_mulheres_idade_fertil": 0,
        "obitos_maternos": 0,
        "obitos_infantis": 0,
    }


def test_sih_indicators_count_children_and_top_causes():
    df = pd.DataFrame(
        {
            "MUNIC_RES": ["220800", "220800", "220800", "221100", "220800"],
            "IDADE": ["9", "10", "bad", "3", None],
            "DIAG_PRINC": ["A90", "B20", "C10", "A90", "D50"],
        }
    )

    result = calculate_sih_indicators(df)

    assert result["internacoes_total"] == 4
    assert result["internacoes_infantis"] == 1
    assert result["principais_causas_internacao_infantil"] == {"A90": 1}


def test_sinan_indicators_use_available_municipality_columns():
    result_primary = calculate_sinan_indicators(
        pd.DataFrame({"ID_MN_RESI": ["220800", "221100", "220800"]})
    )
    result_fallback = calculate_sinan_indicators(
        pd.DataFrame({"CO_MUN_RES": ["221100", "220800"]})
    )

    assert result_primary == {
        "casos_dengue_notificados": 2,
        "coluna_municipio": "ID_MN_RESI",
        "hospitalizacoes": 0,
        "obitos": 0,
        "classificacao_final": {},
        "criterio_confirmacao": {},
        "evolucao": {},
        "hospitalizacao": {},
    }
    assert result_fallback == {
        "casos_dengue_notificados": 1,
        "coluna_municipio": "CO_MUN_RES",
        "hospitalizacoes": 0,
        "obitos": 0,
        "classificacao_final": {},
        "criterio_confirmacao": {},
        "evolucao": {},
        "hospitalizacao": {},
    }


def test_pni_indicators_use_available_municipality_columns():
    result_primary = calculate_pni_indicators(
        pd.DataFrame({"CODMUNRES": ["220800", "221100", "220800"]})
    )
    result_fallback = calculate_pni_indicators(
        pd.DataFrame({"CO_MUNICIP": ["221100", "220800"]})
    )

    assert result_primary == {
        "registros_vacinacao": 2,
        "coluna_municipio": "CODMUNRES",
    }
    assert result_fallback == {
        "registros_vacinacao": 1,
        "coluna_municipio": "CO_MUNICIP",
    }


def test_calculate_picos_indicators_groups_all_datasets():
    result = calculate_picos_indicators(
        df_sim=pd.DataFrame({"CODMUNRES": ["220800"], "IDADE": ["430"], "SEXO": ["2"]}),
        df_sih=pd.DataFrame({"MUNIC_RES": ["220800"], "IDADE": ["8"]}),
        df_sinan=pd.DataFrame({"ID_MN_RESI": ["220800"]}),
        df_pni=pd.DataFrame({"CODMUNRES": ["220800"]}),
    )

    assert result["sim"]["obitos_total"] == 1
    assert result["sih"]["internacoes_total"] == 1
    assert result["sinan"]["casos_dengue_notificados"] == 1
    assert result["pni"]["registros_vacinacao"] == 1
