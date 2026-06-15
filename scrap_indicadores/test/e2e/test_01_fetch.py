import os
import pytest
from scrap_indicadores.scraper_navegador import DatasusTabnetScraper

@pytest.mark.asyncio
async def test_01_fetch_dados(shared_data_dir):
    """
    Test 1: Foca apenas na raspagem assíncrona dos dados e salvamento em CSV.
    Salva os dados no diretório compartilhado da sessão.
    """
    scraper = DatasusTabnetScraper(headless=True)
    
    import asyncio

    async def fetch_sequential(tasks):
        # Executa as chamadas de um mesmo grupo de forma sequencial
        # para não embaralhar a sessão do servidor Tabnet (CGI).
        for name, kwargs in tasks:
            for attempt in range(3):
                try:
                    await scraper.download_csv(**kwargs)
                    break
                except Exception as e:
                    if attempt == 2:
                        pytest.fail(f"Falha ao baixar {name}: {e}")
                    await asyncio.sleep(2)

    group_sim = [
        ("sim_geral", dict(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/obt10pi.def",
            output_path=os.path.join(shared_data_dir, "sim_geral.csv"),
            linha="Município", coluna="--Não-Ativa--", incremento="Óbitos_p/Residênc", periodos="2024"
        )),
        ("sim_infantil", dict(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/inf10pi.def",
            output_path=os.path.join(shared_data_dir, "sim_infantil.csv"),
            linha="Município", coluna="--Não-Ativa--", incremento="Óbitos_p/Residênc", periodos="2024"
        )),
        ("sim_materno", dict(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/mat10pi.def",
            output_path=os.path.join(shared_data_dir, "sim_materno.csv"),
            linha="Município", coluna="--Não-Ativa--", incremento="Óbitos_p/Residênc", periodos="2024"
        )),
        ("sim_fertil", dict(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/obt10pi.def",
            output_path=os.path.join(shared_data_dir, "sim_fertil.csv"),
            linha="Município", coluna="Faixa Etária", incremento="Óbitos_p/Residênc", periodos="2024",
            filtros={"Sexo": "Feminino"}
        ))
    ]

    group_sih = [
        ("sih_geral", dict(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nrpi.def",
            output_path=os.path.join(shared_data_dir, "sih_geral.csv"),
            linha="Município", coluna="--Não-Ativa--", incremento="Internações", periodos="2024"
        )),
        ("sih_infantil_causas", dict(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nrpi.def",
            output_path=os.path.join(shared_data_dir, "sih_infantil_causas.csv"),
            linha="Município", coluna="Capítulo CID-10", incremento="Internações", periodos="2024",
            filtros={"SFaixa_Etária_1": ["Menor 1 ano", "1 a 4 anos", "5 a 9 anos"]}
        ))
    ]

    group_sinan = [
        ("sinan_classificacao", dict(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebpi.def",
            output_path=os.path.join(shared_data_dir, "sinan_classificacao.csv"),
            linha="Município de notificação", coluna="Class. Final", incremento="Casos_Prováveis", periodos="2024"
        )),
        ("sinan_criterio", dict(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebpi.def",
            output_path=os.path.join(shared_data_dir, "sinan_criterio.csv"),
            linha="Município de notificação", coluna="Criterio conf.", incremento="Casos_Prováveis", periodos="2024"
        )),
        ("sinan_evolucao", dict(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebpi.def",
            output_path=os.path.join(shared_data_dir, "sinan_evolucao.csv"),
            linha="Município de notificação", coluna="Evolução", incremento="Casos_Prováveis", periodos="2024"
        )),
        ("sinan_hospitalizacao", dict(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebpi.def",
            output_path=os.path.join(shared_data_dir, "sinan_hospitalizacao.csv"),
            linha="Município de notificação", coluna="Ocorreu hospitalização", incremento="Casos_Prováveis", periodos="2024"
        ))
    ]

    group_pni = [
        ("pni_doses", dict(
            url="http://tabnet.datasus.gov.br/cgi/dhdat.exe?bd_pni/dpnibr.def",
            output_path=os.path.join(shared_data_dir, "pni_doses.csv"),
            linha="Município", coluna="--Não-Ativa--", incremento="Doses_aplicadas|QT_DOSE", periodos="2022",
            filtros={"SUnidade da Federação": "Piauí"}
        ))
    ]

    # Executa os grupos de bases (sistemas diferentes) em paralelo,
    # garantindo que o mesmo sistema (CGI) não sofra com requisições simultâneas conflitantes.
    await asyncio.gather(
        fetch_sequential(group_sim),
        fetch_sequential(group_sih),
        fetch_sequential(group_sinan),
        fetch_sequential(group_pni)
    )
    arquivos_baixados = os.listdir(shared_data_dir)
    assert len(arquivos_baixados) > 0, "Nenhum arquivo CSV foi salvo durante a raspagem."
