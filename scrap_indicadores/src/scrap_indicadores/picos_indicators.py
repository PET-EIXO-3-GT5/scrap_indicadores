from __future__ import annotations
import pandas as pd
from typing import Dict, Any, List

def standardize_periodo(p: str) -> str:
    """Padroniza o nome do período para ajudar no agrupamento."""
    p = str(p).strip()
    # Converte "Janeiro" para "Jan" etc se necessário, mas vamos deixar original por enquanto
    # Só removemos "Total" ou afins
    return p

def merge_dfs_by_periodo(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Faz um merge outer de todos os DataFrames usando a coluna 'periodo'."""
    merged = None
    for name, df in dfs.items():
        if df.empty or "periodo" not in df.columns:
            continue
        # Remove a linha de "Total" se houver
        df = df[~df["periodo"].astype(str).str.contains("Total", case=False, na=False)].copy()
        
        # Prefixo nas colunas para evitar colisão, exceto em periodo
        rename_map = {c: f"{name}_{c}" for c in df.columns if c != "periodo"}
        df_renamed = df.rename(columns=rename_map)
        
        if merged is None:
            merged = df_renamed
        else:
            merged = pd.merge(merged, df_renamed, on="periodo", how="outer")
            
    if merged is None:
        return pd.DataFrame(columns=["periodo"])
        
    merged = merged.fillna(0)
    return merged

def calculate_sim_indicators(
    df_geral: pd.DataFrame,
    df_infantil: pd.DataFrame,
    df_materno: pd.DataFrame,
    df_fertil: pd.DataFrame,
    ano: str = None
) -> List[Dict[str, Any]]:
    
    dfs = {
        "geral": df_geral,
        "infantil": df_infantil,
        "materno": df_materno,
        "fertil": df_fertil
    }
    
    merged = merge_dfs_by_periodo(dfs)
    if ano:
        merged = merged[merged["periodo"].astype(str).str.contains(ano, na=False)]
    
    def find_col(df, prefix, keyword):
        for col in df.columns:
            if col.startswith(prefix) and keyword.lower() in col.lower():
                return col
        return None

    results = []
    for _, row in merged.iterrows():
        periodo = row["periodo"]
        
        # Total
        col_geral = find_col(merged, "geral_", "óbitos")
        total = int(row[col_geral]) if col_geral else 0
        
        # Infantil
        col_inf = find_col(merged, "infantil_", "óbitos")
        infantil = int(row[col_inf]) if col_inf else 0
        
        # Materno
        col_mat = find_col(merged, "materno_", "materno")
        materno = int(row[col_mat]) if col_mat else 0
        
        # Fertil
        fertil_total = 0
        for col in merged.columns:
            if col.startswith("fertil_") and any(x in col for x in ["10", "15", "20", "30", "40"]):
                fertil_total += int(row[col])
                
        results.append({
            "periodo": periodo,
            "obitos_total": total,
            "obitos_mulheres_idade_fertil": fertil_total,
            "obitos_maternos": materno,
            "obitos_infantis": infantil
        })
        
    return results

def calculate_sih_indicators(
    df_geral: pd.DataFrame,
    df_infantil_causas: pd.DataFrame,
    ano: str = None
) -> List[Dict[str, Any]]:
    
    dfs = {
        "geral": df_geral,
        "causas": df_infantil_causas
    }
    
    merged = merge_dfs_by_periodo(dfs)
    if ano:
        merged = merged[merged["periodo"].astype(str).str.contains(ano, na=False)]
    
    results = []
    for _, row in merged.iterrows():
        periodo = row["periodo"]
        
        # Total
        col_geral = [c for c in merged.columns if c.startswith("geral_") and "internações" in c.lower()]
        total = int(row[col_geral[0]]) if col_geral else 0
        
        # Causas infantis
        causas = {}
        infantil = 0
        for col in merged.columns:
            if col.startswith("causas_") and "Total" not in col:
                causa_nome = col.replace("causas_", "")
                val = int(row[col])
                if val > 0:
                    causas[causa_nome] = val
                    infantil += val
                    
        # Ordenar as top 5 causas
        causas_ordenadas = dict(sorted(causas.items(), key=lambda item: item[1], reverse=True)[:5])
        
        results.append({
            "periodo": periodo,
            "internacoes_total": total,
            "internacoes_infantis": infantil,
            "principais_causas_internacao_infantil": causas_ordenadas
        })
        
    return results

def calculate_sinan_indicators(
    df_classificacao: pd.DataFrame,
    df_criterio: pd.DataFrame,
    df_evolucao: pd.DataFrame,
    df_hosp: pd.DataFrame
) -> List[Dict[str, Any]]:
    
    dfs = {
        "class": df_classificacao,
        "crit": df_criterio,
        "evol": df_evolucao,
        "hosp": df_hosp
    }
    
    merged = merge_dfs_by_periodo(dfs)
    
    results = []
    for _, row in merged.iterrows():
        periodo = row["periodo"]
        
        # Distribuições
        dist_class = {}
        dist_crit = {}
        dist_evol = {}
        dist_hosp = {}
        
        casos = 0
        obitos = 0
        hospitalizacoes = 0
        
        for col in merged.columns:
            if col == "periodo" or "Total" in col:
                continue
            
            try:
                val = int(float(row[col]))
            except (ValueError, TypeError):
                continue
                
            if val == 0:
                continue
                
            if col.startswith("class_"):
                nome = col.replace("class_", "")
                dist_class[nome] = val
                casos += val  # Soma das classificações é o total de casos
            elif col.startswith("crit_"):
                dist_crit[col.replace("crit_", "")] = val
            elif col.startswith("evol_"):
                nome = col.replace("evol_", "")
                dist_evol[nome] = val
                if "óbito" in nome.lower() or "obito" in nome.lower():
                    obitos += val
            elif col.startswith("hosp_"):
                nome = col.replace("hosp_", "")
                dist_hosp[nome] = val
                if "sim" in nome.lower():
                    hospitalizacoes += val

        results.append({
            "periodo": periodo,
            "casos_dengue_notificados": casos,
            "hospitalizacoes": hospitalizacoes,
            "obitos": obitos,
            "classificacao_final": dist_class,
            "criterio_confirmacao": dist_crit,
            "evolucao": dist_evol,
            "hospitalizacao": dist_hosp
        })
        
    return results

def calculate_pni_indicators(
    df_doses: pd.DataFrame,
    ano: str = None
) -> List[Dict[str, Any]]:
    
    if df_doses.empty or "periodo" not in df_doses.columns:
        return []
        
    df = df_doses[~df_doses["periodo"].astype(str).str.contains("Total", case=False, na=False)].copy()
    
    if ano:
        df = df[df["periodo"].astype(str).str.contains(ano, na=False)].copy()
    
    col_dose = [c for c in df.columns if c != "periodo"]
    col_dose = col_dose[0] if col_dose else None
    
    results = []
    for _, row in df.iterrows():
        periodo = row["periodo"]
        val = int(row[col_dose]) if col_dose and pd.notna(row[col_dose]) else 0
        results.append({
            "periodo": periodo,
            "registros_vacinacao": val
        })
        
    return results

def calculate_picos_indicators(
    dfs: dict[str, pd.DataFrame],
    picos_code: str = "220800",
    ano: str = None,
) -> dict[str, List[Dict[str, Any]]]:
    # picos_code is unused since data is already pre-filtered by the scraper
    return {
        "sim": calculate_sim_indicators(
            dfs.get("sim_geral", pd.DataFrame()),
            dfs.get("sim_infantil", pd.DataFrame()),
            dfs.get("sim_materno", pd.DataFrame()),
            dfs.get("sim_fertil", pd.DataFrame()),
            ano=ano
        ),
        "sih": calculate_sih_indicators(
            dfs.get("sih_geral", pd.DataFrame()),
            dfs.get("sih_infantil_causas", pd.DataFrame()),
            ano=ano
        ),
        "sinan": calculate_sinan_indicators(
            dfs.get("sinan_classificacao", pd.DataFrame()),
            dfs.get("sinan_criterio", pd.DataFrame()),
            dfs.get("sinan_evolucao", pd.DataFrame()),
            dfs.get("sinan_hospitalizacao", pd.DataFrame())
        ),
        "pni": calculate_pni_indicators(
            dfs.get("pni_doses", pd.DataFrame()),
            ano=ano
        ),
    }
