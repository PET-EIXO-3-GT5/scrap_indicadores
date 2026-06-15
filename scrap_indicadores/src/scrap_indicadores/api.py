import os
import sys
import json
import asyncio
from typing import Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from scrap_indicadores.scraper_navegador import DatasusTabnetScraper, parse_tabnet_csv
from scrap_indicadores.picos_indicators import calculate_picos_indicators

app = FastAPI(title="Datasus Scraper API", version="1.0.0")

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache_datasus")

async def fetch_sequential(scraper, tasks, shared_data_dir):
    for name, kwargs in tasks:
        for attempt in range(3):
            try:
                kwargs['output_path'] = os.path.join(shared_data_dir, f"{name}.csv")
                await scraper.download_csv(**kwargs)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"Falha ao baixar {name}: {e}")
                    raise
                await asyncio.sleep(2)

async def rodar_scraper_datasus(ano: str = "2024") -> Dict[str, Any]:
    os.makedirs(CACHE_DIR, exist_ok=True)
    scraper = DatasusTabnetScraper(headless=True)
    
    # Filtros padrão para Picos-PI
    picos_filter = "220800 PICOS"
    
    group_sim = [
        ("sim_geral", dict(url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/obt10pi.def", linha="Ano/mês do óbito", coluna="--Não-Ativa--", incremento="Óbitos_p/Residênc", periodos=ano, filtros={"SMunicípio": picos_filter})),
        ("sim_infantil", dict(url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/inf10pi.def", linha="Ano/mês do óbito", coluna="--Não-Ativa--", incremento="Óbitos_p/Residênc", periodos=ano, filtros={"SMunicípio": picos_filter})),
        ("sim_materno", dict(url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/mat10pi.def", linha="Ano/mês do óbito", coluna="--Não-Ativa--", incremento="Óbitos_maternos", periodos=ano, filtros={"SMunicípio": picos_filter})),
        ("sim_fertil", dict(url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/obt10pi.def", linha="Ano/mês do óbito", coluna="Faixa Etária", incremento="Óbitos_p/Residênc", periodos=ano, filtros={"SMunicípio": picos_filter, "Sexo": "Feminino"}))
    ]

    group_sih = [
        ("sih_geral", dict(url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nrpi.def", linha="Ano/mês processamento", coluna="--Não-Ativa--", incremento="Internações", periodos=ano, filtros={"SMunicípio": picos_filter})),
        ("sih_infantil_causas", dict(url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nrpi.def", linha="Ano/mês processamento", coluna="Capítulo CID-10", incremento="Internações", periodos=ano, filtros={"SMunicípio": picos_filter, "SFaixa_Etária_1": ["Menor 1 ano", "1 a 4 anos", "5 a 9 anos"]}))
    ]

    group_sinan = [
        ("sinan_classificacao", dict(url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebpi.def", linha="Mês notificação", coluna="Class. Final", incremento="Casos_Prováveis", periodos=ano, filtros={"SMunicípio_de_notificação": picos_filter})),
        ("sinan_criterio", dict(url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebpi.def", linha="Mês notificação", coluna="Criterio conf.", incremento="Casos_Prováveis", periodos=ano, filtros={"SMunicípio_de_notificação": picos_filter})),
        ("sinan_evolucao", dict(url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebpi.def", linha="Mês notificação", coluna="Evolução", incremento="Casos_Prováveis", periodos=ano, filtros={"SMunicípio_de_notificação": picos_filter})),
        ("sinan_hospitalizacao", dict(url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebpi.def", linha="Mês notificação", coluna="Ocorreu hospitalização", incremento="Casos_Prováveis", periodos=ano, filtros={"SMunicípio_de_notificação": picos_filter}))
    ]

    group_pni = [
        ("pni_doses", dict(url="http://tabnet.datasus.gov.br/cgi/dhdat.exe?bd_pni/dpnibr.def", linha="Ano/mês", coluna="--Não-Ativa--", incremento="Doses_aplicadas|QT_DOSE", periodos=ano, filtros={"SMunicípio": picos_filter, "SUnidade da Federação": "Piauí"}))
    ]

    print(f"Iniciando a extração da Série Histórica no DATASUS TabNet via API (Ano: {ano})...")
    await asyncio.gather(
        fetch_sequential(scraper, group_sim, CACHE_DIR),
        fetch_sequential(scraper, group_sih, CACHE_DIR),
        fetch_sequential(scraper, group_sinan, CACHE_DIR),
        fetch_sequential(scraper, group_pni, CACHE_DIR)
    )

    print("Extração concluída, parseando CSVs...")
    bases = [
        "sim_geral", "sim_infantil", "sim_materno", "sim_fertil",
        "sih_geral", "sih_infantil_causas",
        "sinan_classificacao", "sinan_criterio", "sinan_evolucao", "sinan_hospitalizacao",
        "pni_doses"
    ]
    
    dfs = {}
    for base in bases:
        file_path = os.path.join(CACHE_DIR, f"{base}.csv")
        if os.path.exists(file_path):
            try:
                dfs[base] = parse_tabnet_csv(file_path)
            except Exception as e:
                print(f"Erro ao parsear {base}: {e}")
                
    if not dfs:
        raise Exception("Nenhum arquivo CSV baixado com sucesso.")

    print("Agrupando a série temporal de Picos (PI)...")
    picos_code = "220800"
    indicadores = calculate_picos_indicators(dfs, picos_code=picos_code, ano=ano)
    
    json_output = os.path.join(CACHE_DIR, f"indicadores_cache_{ano}.json")
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(indicadores, f, indent=4, ensure_ascii=False)
        
    return indicadores

@app.get("/api/indicadores")
async def get_indicadores(ano: str = "2024", force_refresh: bool = False):
    """
    Retorna os indicadores históricos calculados de Picos.
    """
    json_output = os.path.join(CACHE_DIR, f"indicadores_cache_{ano}.json")
    if not force_refresh and os.path.exists(json_output):
        try:
            with open(json_output, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Falha ao ler cache: {e}")
            
    # Roda o scraper
    dados = await rodar_scraper_datasus(ano=ano)
    return dados
