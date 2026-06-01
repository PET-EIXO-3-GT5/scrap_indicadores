import asyncio
import pandas as pd
import pyarrow.dataset as ds
from pysus.api.client import PySUS

from scrap_indicadores.picos_indicators import (
    PICOS_CODE,
    calculate_picos_indicators,
    summarize_sinan_dengue_indicators,
)

async def fetch_dataset(pysus, dataset, state=None, year=None, group=None, filter_fn=None):
    try:
        print(
            f"Buscando {dataset} (Grupo: {group}, Estado: {state}, Ano: {year})...")
        files = await pysus.query(dataset=dataset, state=state, year=year, group=group)
        if filter_fn:
            files = [f for f in files if filter_fn(f)]

        paths = []
        for f in files:
            try:
                f_local = await pysus.download(f)
                paths.append(f_local.path)
            except Exception as e:
                print(f"Erro ao baixar arquivo {f.path}: {e}")

        if not paths:
            print(f"Nenhum arquivo encontrado/baixado para {dataset}")
            return pd.DataFrame()
        return pysus.read_parquet(paths).df()
    except Exception as e:
        print(f"Erro na consulta do dataset {dataset}: {e}")
        return pd.DataFrame()


async def fetch_sinan_dengue_picos(pysus, year, picos_code=PICOS_CODE):
    """SINAN Dengue is national in PySUS; filter Picos while reading Parquet."""
    files = await pysus.query(dataset="sinan", group="DENG", year=year)
    files = [f for f in files if f.path.name.startswith("DENG")]

    paths = []
    for f in files:
        try:
            f_local = await pysus.download(f)
            paths.append(f_local.path)
        except Exception as e:
            print(f"Erro ao baixar arquivo {f.path}: {e}")

    if not paths:
        print(
            f"Nenhum arquivo nacional de Dengue encontrado para SINAN {year}")
        return pd.DataFrame()

    frames = []
    for path in paths:
        dataset = ds.dataset(path, format="parquet")
        table = dataset.to_table(filter=ds.field(
            "ID_MN_RESI") == str(picos_code))
        frames.append(table.to_pandas())
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

async def main():
    async with PySUS() as pysus:
        df_sim = await fetch_dataset(pysus, "sim", state="PI", year=2024)
        df_sih = await fetch_dataset(pysus, "sih", state="PI", year=2024, filter_fn=lambda f: f.path.name.startswith('RD'))
        df_sinan = await fetch_sinan_dengue_picos(pysus, year=2024)
        df_pni = await fetch_dataset(pysus, "pni", group="DP", state="PI", year=2024)
        df_sinasc = await fetch_dataset(pysus, "sinasc", state="PI", year=2024)

    indicators = calculate_picos_indicators(
        df_sim, df_sih, df_sinan, df_pni, df_sinasc)
    sinan_summary = summarize_sinan_dengue_indicators(df_sinan)

    print(f"RESULTADOS PARA PICOS - PI ({PICOS_CODE}) - 2024")
    print(indicators)
    if sinan_summary:
        print("Resumos adicionais SINAN Dengue:")
        print(pd.Series(sinan_summary))

if __name__ == "__main__":
    asyncio.run(main())
