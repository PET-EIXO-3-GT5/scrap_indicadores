from __future__ import annotations

from typing import Iterable

import pandas as pd

PICOS_CODE = "220800"
SINAN_DENGUE_SUMMARY_COLUMNS = [
    "CLASSI_FIN",
    "CRITERIO",
    "EVOLUCAO",
    "HOSPITALIZ",
    "CS_SEXO",
    "CS_RACA",
    "CS_GESTANT",
    "SOROTIPO",
]

def _empty_series(index: pd.Index, dtype: str = "string") -> pd.Series:
    return pd.Series(pd.NA, index=index, dtype=dtype)


def _text_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return _empty_series(df.index)
    return df[column].astype("string").str.strip()


def _normalize_municipality_code(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _municipality_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    return next((column for column in candidates if column in df.columns), None)


def filter_picos(
    df: pd.DataFrame,
    municipality_columns: Iterable[str],
    picos_code: str = PICOS_CODE,
) -> tuple[pd.DataFrame, str | None]:
    municipality_column = _municipality_column(df, municipality_columns)
    if municipality_column is None or df.empty:
        return df.iloc[0:0].copy(), municipality_column

    codes = df[municipality_column].map(_normalize_municipality_code)
    return df.loc[codes == picos_code].copy(), municipality_column


def calculate_sim_indicators(
    df: pd.DataFrame,
    picos_code: str = PICOS_CODE,
) -> dict[str, int]:
    df_picos, _ = filter_picos(df, ["CODMUNRES"], picos_code)
    idade = _text_column(df_picos, "IDADE")
    sexo = _text_column(df_picos, "SEXO")
    causa_basica = _text_column(df_picos, "CAUSABAS")
    obito_materno = _text_column(df_picos, "OBITOMAT")

    idade_anos = pd.to_numeric(idade.str[1:], errors="coerce")
    idade_fertil = idade.str.startswith("4", na=False) & idade_anos.between(10, 49)
    mulher = sexo == "2"
    materno = causa_basica.str.startswith("O", na=False) | obito_materno.isin(
        ["1", "2", "3", "4", "5"]
    )
    infantil = idade.str[0].isin(["0", "1", "2", "3"]).fillna(False)

    return {
        "obitos_total": int(len(df_picos)),
        "obitos_mulheres_idade_fertil": int((mulher & idade_fertil).sum()),
        "obitos_maternos": int(materno.sum()),
        "obitos_infantis": int(infantil.sum()),
    }


def calculate_sih_indicators(
    df: pd.DataFrame,
    picos_code: str = PICOS_CODE,
) -> dict[str, object]:
    df_picos, _ = filter_picos(df, ["MUNIC_RES"], picos_code)
    idade = pd.to_numeric(_text_column(df_picos, "IDADE"), errors="coerce")
    infantil = idade < 10

    principais_causas = {}
    if "DIAG_PRINC" in df_picos.columns:
        principais_causas = (
            df_picos.loc[infantil.fillna(False), "DIAG_PRINC"]
            .value_counts()
            .head(5)
            .to_dict()
        )

    return {
        "internacoes_total": int(len(df_picos)),
        "internacoes_infantis": int(infantil.sum()),
        "principais_causas_internacao_infantil": principais_causas,
    }


def calculate_sinan_indicators(
    df: pd.DataFrame,
    picos_code: str = PICOS_CODE,
) -> dict[str, object]:
    df_picos, municipality_column = filter_picos(df, ["ID_MN_RESI", "CO_MUN_RES"], picos_code)
    return {
        "casos_dengue_notificados": int(len(df_picos)),
        "coluna_municipio": municipality_column,
        "hospitalizacoes": _count_values(df_picos, "HOSPITALIZ", ["1"]),
        "obitos": _count_values(df_picos, "EVOLUCAO", ["2"]),
        "classificacao_final": value_counts_dict(df_picos, "CLASSI_FIN"),
        "criterio_confirmacao": value_counts_dict(df_picos, "CRITERIO"),
        "evolucao": value_counts_dict(df_picos, "EVOLUCAO"),
        "hospitalizacao": value_counts_dict(df_picos, "HOSPITALIZ"),
    }


def calculate_pni_indicators(
    df: pd.DataFrame,
    picos_code: str = PICOS_CODE,
) -> dict[str, object]:
    df_picos, municipality_column = filter_picos(df, ["CODMUNRES", "CO_MUNICIP", "MUNIC_RES", "MUNRES"], picos_code)
    return {
        "registros_vacinacao": int(len(df_picos)),
        "coluna_municipio": municipality_column,
    }


def calculate_sinasc_indicators(
    df: pd.DataFrame,
    picos_code: str = PICOS_CODE,
) -> dict[str, object]:
    df_picos, municipality_column = filter_picos(df, ["CODMUNRES", "CODMUNNASC"], picos_code)
    return {
        "nascidos_vivos": int(len(df_picos)),
        "coluna_municipio": municipality_column,
    }


def calculate_picos_indicators(
    df_sim: pd.DataFrame,
    df_sih: pd.DataFrame,
    df_sinan: pd.DataFrame,
    df_pni: pd.DataFrame,
    df_sinasc: pd.DataFrame | None = None,
    picos_code: str = PICOS_CODE,
) -> dict[str, dict[str, object]]:
    indicators = {
        "sim": calculate_sim_indicators(df_sim, picos_code),
        "sih": calculate_sih_indicators(df_sih, picos_code),
        "sinan": calculate_sinan_indicators(df_sinan, picos_code),
        "pni": calculate_pni_indicators(df_pni, picos_code),
    }

    if df_sinasc is not None:
        indicators["sinasc"] = calculate_sinasc_indicators(df_sinasc, picos_code)
        
        nascidos = indicators["sinasc"]["nascidos_vivos"]
        doses = indicators["pni"]["registros_vacinacao"]
        
        # Calculo basico de cobertura vacinal infantil aproximada
        indicador_cobertura = round((doses / nascidos) * 100, 2) if nascidos and nascidos > 0 else 0.0
        indicators["pni"]["cobertura_vacinal_estimada_porcentagem"] = indicador_cobertura

    return indicators


def _count_values(df: pd.DataFrame, column: str, values: Iterable[str]) -> int:
    if column not in df.columns:
        return 0
    allowed = {str(value) for value in values}
    data = df[column].astype("string").str.strip()
    return int(data.isin(allowed).sum())


def value_counts_dict(df: pd.DataFrame, column: str, top_n: int = 10) -> dict[str, int]:
    if column not in df.columns:
        return {}
    counts = df[column].astype("string").str.strip().fillna("<vazio>").value_counts().head(top_n)
    return {str(key): int(value) for key, value in counts.items()}


def summarize_available_indicators(
    df: pd.DataFrame,
    columns: Iterable[str],
    top_n: int = 10,
) -> dict[str, dict[str, int]]:
    return {
        column: value_counts_dict(df, column, top_n)
        for column in columns
        if column in df.columns
    }


def summarize_sinan_dengue_indicators(df: pd.DataFrame, top_n: int = 10) -> dict[str, dict[str, int]]:
    return summarize_available_indicators(df, SINAN_DENGUE_SUMMARY_COLUMNS, top_n=top_n)
