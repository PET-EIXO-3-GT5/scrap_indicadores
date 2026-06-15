import os
import tempfile
import pytest
from scrap_indicadores.scraper_navegador import DatasusTabnetScraper

def test_clean_csv_file():
    scraper = DatasusTabnetScraper()
    
    # Create a temporary CSV file with typical Tabnet structure (headers and footers)
    raw_content = (
        "Mortalidade - Piauí\n"
        "Óbitos p/Residênc por Município\n"
        "Período:2024\n"
        "\"Município\";\"Óbitos_p/Residênc\"\n"
        "\"220005 ACAUA\";55\n"
        "\"220800 PICOS\";621\n"
        "\"Total\";676\n"
        "Fonte: MS/SVSA/CGIAE - Sistema de Informações sobre Mortalidade - SIM\n"
        "Notas:\n"
        "Dados preliminares.\n"
    )
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="latin1") as tmp:
        tmp.write(raw_content)
        tmp_path = tmp.name
        
    try:
        scraper._clean_csv_file(tmp_path)
        with open(tmp_path, "r", encoding="latin1") as f:
            cleaned_content = f.read()
            
        expected_content = (
            "\"Município\";\"Óbitos_p/Residênc\"\n"
            "\"220005 ACAUA\";55\n"
            "\"220800 PICOS\";621\n"
            "\"Total\";676\n"
        )
        
        assert cleaned_content == expected_content
    finally:
        os.remove(tmp_path)

def test_clean_csv_file_no_header():
    scraper = DatasusTabnetScraper()
    
    raw_content = "Some;random;content\nwithout;any;special;keyword\n"
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="latin1") as tmp:
        tmp.write(raw_content)
        tmp_path = tmp.name
        
    try:
        scraper._clean_csv_file(tmp_path)
        with open(tmp_path, "r", encoding="latin1") as f:
            cleaned_content = f.read()
        assert cleaned_content == raw_content
    finally:
        os.remove(tmp_path)

def test_parse_tabnet_csv():
    from scrap_indicadores.scraper_navegador import parse_tabnet_csv
    
    raw_content = (
        "Mortalidade - Piauí\n"
        "\"Município\";\"Óbitos\"\n"
        "\"220800 PICOS\";\"1.234,56\"\n"
        "\"Total\";\"1234,56\"\n"
        "Notas:\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="latin1") as tmp:
        tmp.write(raw_content)
        tmp_path = tmp.name
        
    try:
        df = parse_tabnet_csv(tmp_path)
        assert not df.empty
        assert "cod_ibge" in df.columns
        assert "municipio" in df.columns
        assert df["cod_ibge"].iloc[0] == "220800"
        assert df["municipio"].iloc[0] == "PICOS"
        assert df["Óbitos"].iloc[0] == 1234.56
    finally:
        os.remove(tmp_path)

def test_parse_tabnet_csv_no_header():
    from scrap_indicadores.scraper_navegador import parse_tabnet_csv
    
    raw_content = "Some;random;content\nwithout;any;special;keyword\n"
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="latin1") as tmp:
        tmp.write(raw_content)
        tmp_path = tmp.name
        
    try:
        with pytest.raises(ValueError, match="Linha de cabeçalho 'Município' não encontrada"):
            parse_tabnet_csv(tmp_path)
    finally:
        os.remove(tmp_path)



def test_real_get_options():
    import asyncio
    from scrap_indicadores.scraper_navegador import DatasusTabnetScraper

    async def run_test():
        scraper = DatasusTabnetScraper(headless=True)
        options = await scraper.get_options("http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/obt10pi.def")
        assert len(options) > 0
        
        keys = [k.lower() for k in options.keys()]
        assert "linha" in keys
        assert "coluna" in keys
    
    asyncio.run(run_test())

def test_real_download_csv(tmp_path):
    import asyncio
    import os
    from scrap_indicadores.scraper_navegador import DatasusTabnetScraper

    async def run_test():
        scraper = DatasusTabnetScraper(headless=True)
        out_path = os.path.join(tmp_path, "test_download.csv")
        
        downloaded = await scraper.download_csv(
            url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/obt10pi.def",
            output_path=out_path,
            linha="Município",
            coluna="--Não-Ativa--",
            incremento="Óbitos_p/Residênc",
            periodos="2024"
        )
        
        assert os.path.exists(downloaded)
        with open(downloaded, "r", encoding="latin1") as f:
            content = f.read()
        
        assert "Município" in content
        assert "220800" in content
    
    asyncio.run(run_test())
