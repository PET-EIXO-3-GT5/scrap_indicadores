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
        # Clean the file
        scraper._clean_csv_file(tmp_path)
        
        # Read the file back
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
