from __future__ import annotations
import pandas as pd

PICOS_CODE = "220800"

def get_picos_value(df: pd.DataFrame, metric_column: str, picos_code: str = PICOS_CODE) -> float:
    if df.empty or "cod_ibge" not in df.columns:
        return 0.0
    df_picos = df[df["cod_ibge"] == picos_code]
    if df_picos.empty or metric_column not in df_picos.columns:
        return 0.0
    val = df_picos[metric_column].iloc[0]
    return float(val) if pd.notna(val) else 0.0

def calculate_sim_indicators(
    df_geral: pd.DataFrame,
    df_infantil: pd.DataFrame,
    df_materno: pd.DataFrame,
    df_fertil: pd.DataFrame,
    picos_code: str = PICOS_CODE,
) -> dict[str, int]:
    
    obitos_fertil = 0
    if not df_fertil.empty and "cod_ibge" in df_fertil.columns:
        df_picos_fertil = df_fertil[df_fertil["cod_ibge"] == picos_code]
        if not df_picos_fertil.empty:
            for col in df_fertil.columns:
                if any(x in col for x in ["10", "15", "20", "30", "40"]):
                    val = df_picos_fertil[col].iloc[0]
                    obitos_fertil += int(val) if pd.notna(val) else 0

    return {
        "obitos_total": int(get_picos_value(df_geral, "Óbitos_p/Residênc", picos_code)),
        "obitos_mulheres_idade_fertil": int(obitos_fertil),
        "obitos_maternos": int(get_picos_value(df_materno, "Óbitos_p/Residênc", picos_code)),
        "obitos_infantis": int(get_picos_value(df_infantil, "Óbitos_p/Residênc", picos_code)),
    }

def calculate_sih_indicators(
    df_geral: pd.DataFrame,
    df_infantil_causas: pd.DataFrame,
    picos_code: str = PICOS_CODE,
) -> dict[str, object]:
    
    internacoes_infantis = 0
    principais_causas = {}
    if not df_infantil_causas.empty and "cod_ibge" in df_infantil_causas.columns:
        df_picos_causas = df_infantil_causas[df_infantil_causas["cod_ibge"] == picos_code]
        if not df_picos_causas.empty:
            row = df_picos_causas.iloc[0].drop(labels=["cod_ibge", "municipio"], errors="ignore")
            if "Total" in row.index:
                val = row["Total"]
                internacoes_infantis = int(val) if pd.notna(val) else 0
                row = row.drop(labels=["Total"])
            
            row = pd.to_numeric(row, errors="coerce").fillna(0)
            row = row[row > 0].sort_values(ascending=False).head(5)
            principais_causas = {str(k): int(v) for k, v in row.items()}

    return {
        "internacoes_total": int(get_picos_value(df_geral, "Internações", picos_code)),
        "internacoes_infantis": internacoes_infantis,
        "principais_causas_internacao_infantil": principais_causas,
    }

def calculate_sinan_indicators(
    df_classificacao: pd.DataFrame,
    df_criterio: pd.DataFrame,
    df_evolucao: pd.DataFrame,
    df_hosp: pd.DataFrame,
    picos_code: str = PICOS_CODE,
) -> dict[str, object]:
    
    def extract_distribution(df, picos_code):
        if df.empty or "cod_ibge" not in df.columns:
            return {}
        df_picos = df[df["cod_ibge"] == picos_code]
        if df_picos.empty:
            return {}
        row = df_picos.iloc[0].drop(labels=["cod_ibge", "municipio", "Total"], errors="ignore")
        row = pd.to_numeric(row, errors="coerce").fillna(0)
        row = row[row > 0].sort_values(ascending=False)
        return {str(k): int(v) for k, v in row.items()}

    dist_class = extract_distribution(df_classificacao, picos_code)
    
    casos = 0
    if not df_classificacao.empty and "cod_ibge" in df_classificacao.columns:
        df_picos_class = df_classificacao[df_classificacao["cod_ibge"] == picos_code]
        if not df_picos_class.empty and "Total" in df_picos_class.columns:
            val = df_picos_class["Total"].iloc[0]
            casos = int(val) if pd.notna(val) else 0

    obitos = 0
    dist_evol = extract_distribution(df_evolucao, picos_code)
    for k, v in dist_evol.items():
        if "óbito pelo agravo" in k.lower() or "óbito por dengue" in k.lower() or "obito" in k.lower():
            obitos += int(v)
            
    hosp = 0
    dist_hosp = extract_distribution(df_hosp, picos_code)
    for k, v in dist_hosp.items():
        if "sim" in k.lower():
            hosp += int(v)

    return {
        "casos_dengue_notificados": casos,
        "hospitalizacoes": hosp,
        "obitos": obitos,
        "classificacao_final": dist_class,
        "criterio_confirmacao": extract_distribution(df_criterio, picos_code),
        "evolucao": dist_evol,
        "hospitalizacao": dist_hosp,
    }

def calculate_pni_indicators(
    df_doses: pd.DataFrame,
    picos_code: str = PICOS_CODE,
) -> dict[str, object]:
    return {
        "registros_vacinacao": int(get_picos_value(df_doses, "Doses_aplicadas", picos_code)),
    }

def calculate_picos_indicators(
    dfs: dict[str, pd.DataFrame],
    picos_code: str = PICOS_CODE,
) -> dict[str, dict[str, object]]:
    return {
        "sim": calculate_sim_indicators(
            dfs.get("sim_geral", pd.DataFrame()),
            dfs.get("sim_infantil", pd.DataFrame()),
            dfs.get("sim_materno", pd.DataFrame()),
            dfs.get("sim_fertil", pd.DataFrame()),
            picos_code
        ),
        "sih": calculate_sih_indicators(
            dfs.get("sih_geral", pd.DataFrame()),
            dfs.get("sih_infantil_causas", pd.DataFrame()),
            picos_code
        ),
        "sinan": calculate_sinan_indicators(
            dfs.get("sinan_classificacao", pd.DataFrame()),
            dfs.get("sinan_criterio", pd.DataFrame()),
            dfs.get("sinan_evolucao", pd.DataFrame()),
            dfs.get("sinan_hospitalizacao", pd.DataFrame()),
            picos_code
        ),
        "pni": calculate_pni_indicators(
            dfs.get("pni_doses", pd.DataFrame()),
            picos_code
        ),
    }
