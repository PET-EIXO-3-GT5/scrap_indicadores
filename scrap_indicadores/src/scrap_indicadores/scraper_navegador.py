import asyncio
import os
import re
from typing import Dict, List, Optional, Union
from io import StringIO
import pandas as pd
from playwright.async_api import async_playwright

from scrap_indicadores.picos_indicators import calculate_picos_indicators

class DatasusTabnetScraper:
    """
    A robust web scraper for DATASUS TabNet tables utilizing Playwright.
    Enables automated form filling (even on hidden elements), query submission,
    new tab handling, and CSV download.
    """
    def __init__(self, headless: bool = True, timeout: int = 60000):
        self.headless = headless
        self.timeout = timeout

    async def get_options(self, url: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Visits a Tabnet page and returns all available options for all selectors.
        Useful for exploring fields and database parameters.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            try:
                print(f"Carregando opções da página: {url}")
                await page.goto(url, timeout=self.timeout)
                await page.wait_for_selector("select", state="attached", timeout=self.timeout)
                
                selects = await page.eval_on_selector_all("select", """
                    nodes => {
                        const result = {};
                        nodes.forEach(select => {
                            const name = select.name || select.id;
                            if (!name) return;
                            const options = Array.from(select.options).map(opt => ({
                                text: opt.textContent.trim(),
                                value: opt.value
                            }));
                            result[name] = options;
                        });
                        return result;
                    }
                """)
                return selects
            finally:
                await browser.close()

    async def _resolve_select_selector(self, page, name: str) -> str:
        """Finds the CSS selector for a select element based on its name or id."""
        # Try exact name
        if await page.locator(f"select[name='{name}']").count() > 0:
            return f"select[name='{name}']"
        # Try exact id
        if await page.locator(f"select[id='{name}']").count() > 0:
            return f"select[id='{name}']"
        # Try case-insensitive name
        names = await page.eval_on_selector_all("select", "nodes => nodes.map(n => n.name)")
        for n in names:
            if n and n.lower() == name.lower():
                return f"select[name='{n}']"
        # Try partial name/id
        count = await page.locator(f"select[name*='{name}']").count()
        if count > 0:
            name_attr = await page.locator(f"select[name*='{name}']").first.get_attribute("name")
            return f"select[name='{name_attr}']"
        count = await page.locator(f"select[id*='{name}']").count()
        if count > 0:
            id_attr = await page.locator(f"select[id*='{name}']").first.get_attribute("id")
            return f"select[id='{id_attr}']"
            
        raise ValueError(f"Não foi possível localizar o seletor correspondente a '{name}'.")

    async def _select_options_js(self, page, selector: str, queries: List[str]) -> List[str]:
        """
        Selects options directly in the DOM using JS evaluation.
        This bypasses Playwright's visibility/interactability checks,
        making it work perfectly on hidden filters.
        """
        queries_lower = [str(q).strip().lower() for q in queries]
        
        selected_values = await page.eval_on_selector(
            selector,
            """
            (selectEl, queries) => {
                const selected = [];
                // 1st pass: exact value or exact text match
                Array.from(selectEl.options).forEach(opt => {
                    const val = opt.value.trim().toLowerCase();
                    const text = opt.textContent.trim().toLowerCase();
                    
                    const isExactMatch = queries.some(q => val === q || text === q);
                    if (isExactMatch) {
                        opt.selected = true;
                        selected.push(opt.value);
                    }
                });
                
                // 2nd pass: if nothing matched, try partial matches
                if (selected.length === 0) {
                    Array.from(selectEl.options).forEach(opt => {
                        const val = opt.value.trim().toLowerCase();
                        const text = opt.textContent.trim().toLowerCase();
                        
                        const isPartialMatch = queries.some(q => text.includes(q) || val.includes(q));
                        if (isPartialMatch) {
                            opt.selected = true;
                            selected.push(opt.value);
                        }
                    });
                }
                
                // Dispatch change event to update page state
                if (selected.length > 0) {
                    selectEl.dispatchEvent(new Event('change', { bubbles: true }));
                }
                return selected;
            }
            """,
            queries_lower
        )
        return selected_values

    async def download_csv(
        self,
        url: str,
        output_path: str,
        linha: str = "Município",
        coluna: str = "--Não-Ativa--",
        incremento: Optional[str] = None,
        periodos: Optional[Union[str, List[str]]] = None,
        filtros: Optional[Dict[str, Union[str, List[str]]]] = None
    ) -> str:
        """
        Fills the Tabnet query form, submits it, handles the target="_blank" result tab,
        downloads the generated CSV file, and saves it.
        
        Args:
            url: The Datasus Tabnet/CGI page URL.
            output_path: Destination path for the CSV file.
            linha: Option text or value to select for rows (e.g. 'Município').
            coluna: Option text or value to select for columns (e.g. 'Não ativa').
            incremento: Option text or value to select for content/values.
            periodos: A string or list of strings representing periods to select (e.g. '2024').
            filtros: A dictionary mapping filter selector names/labels to their values.
            
        Returns:
            The absolute path of the downloaded CSV file.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                print(f"Acessando a página Tabnet: {url}")
                await page.goto(url, timeout=self.timeout)
                
                # Wait for form elements
                await page.wait_for_selector("select[name='Linha']", state="attached", timeout=self.timeout)
                
                # 1. Select Linha (Rows)
                print(f"Selecionando Linha: {linha}")
                linha_selector = await self._resolve_select_selector(page, "Linha")
                await self._select_options_js(page, linha_selector, [linha])
                
                # 2. Select Coluna (Columns)
                print(f"Selecionando Coluna: {coluna}")
                coluna_selector = await self._resolve_select_selector(page, "Coluna")
                await self._select_options_js(page, coluna_selector, [coluna])
                
                # 3. Select Incremento (Content)
                if incremento:
                    print(f"Selecionando Conteúdo (Incremento): {incremento}")
                    inc_selector = await self._resolve_select_selector(page, "Incremento")
                    await self._select_options_js(page, inc_selector, [incremento])
                else:
                    print("Utilizando o incremento padrão da página.")
                
                # 4. Select Períodos (can be named 'Arquivos' or 'PAno')
                period_select_name = "Arquivos" if await page.locator("select[name='Arquivos']").count() > 0 else "PAno"
                period_selector = await self._resolve_select_selector(page, period_select_name)
                
                if periodos:
                    period_queries = [periodos] if isinstance(periodos, str) else periodos
                    print(f"Selecionando Período(s) em '{period_select_name}': {period_queries}")
                    selected_periods = await self._select_options_js(page, period_selector, period_queries)
                    print(f"Períodos selecionados no formulário: {selected_periods}")
                else:
                    first_opt = await page.eval_on_selector(f"{period_selector} option", "node => node.value")
                    print(f"Nenhum período especificado. Selecionando o mais recente: {first_opt}")
                    await page.select_option(period_selector, value=first_opt)
                    
                # 5. Apply Filters
                if filtros:
                    for filter_name, filter_vals in filtros.items():
                        filter_vals_list = [filter_vals] if isinstance(filter_vals, str) else filter_vals
                        print(f"Aplicando filtro '{filter_name}': {filter_vals_list}")
                        filter_selector = await self._resolve_select_selector(page, filter_name)
                        selected_filters = await self._select_options_js(page, filter_selector, filter_vals_list)
                        print(f"Filtro '{filter_name}' selecionado com: {selected_filters}")
                        
                # 6. Click submit (Mostra) and wait for the new tab (popup)
                print("Enviando consulta (clicando no botão 'Mostra')...")
                submit_button = page.locator("input[type='submit'][value='Mostra'], input[value='Mostra'], button:has-text('Mostra')").first
                
                async with context.expect_page() as new_page_info:
                    await submit_button.click()
                    
                new_page = await new_page_info.value
                print("Nova aba detectada. Aguardando o processamento dos dados...")
                await new_page.wait_for_load_state("load", timeout=self.timeout)
                
                # Check for CGI crashes/errors in the page body
                body_content = await new_page.content()
                if "error" in body_content.lower() and "traceback" in body_content.lower():
                    raise RuntimeError("O servidor do DATASUS retornou um erro ao processar a consulta.")
                
                # 7. Locate the CSV download link
                print("Procurando o link para exportação de CSV...")
                links = await new_page.eval_on_selector_all("a", """
                    nodes => nodes.map(n => ({
                        text: n.textContent.trim(),
                        href: n.href
                    }))
                """)
                
                csv_link = None
                for link in links:
                    if ".csv" in link['href'].lower() or "copia como .csv" in link['text'].lower():
                        csv_link = link
                        break
                        
                if not csv_link:
                    raise FileNotFoundError("O link de download do arquivo CSV não foi encontrado nos resultados.")
                    
                print(f"Link CSV encontrado: {csv_link['text']} -> {csv_link['href']}")
                
                # 8. Download the CSV
                async with new_page.expect_download() as download_info:
                    filename = csv_link['href'].split('/')[-1]
                    await new_page.click(f"a[href*='{filename}']")
                download = await download_info.value
                
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                await download.save_as(output_path)
                print(f"Download concluído com sucesso e salvo em: {output_path}")
                self._clean_csv_file(output_path)
                return os.path.abspath(output_path)
                
            finally:
                await context.close()
                await browser.close()

    def _clean_csv_file(self, csv_path: str) -> None:
        """
        Cleans the downloaded Tabnet CSV by removing top metadata headers and bottom metadata footers,
        leaving only the data rows (including the header row and the total row).
        """
        try:
            with open(csv_path, "r", encoding="latin1") as f:
                lines = f.readlines()
                
            header_idx = -1
            total_idx = -1
            
            for idx, line in enumerate(lines):
                clean_line = line.strip().replace('"', '')
                # Matches headers containing 'municipio' / 'município' and a semicolon
                if header_idx == -1 and ("municipio" in clean_line.lower() or "município" in clean_line.lower()) and ";" in clean_line:
                    header_idx = idx
                elif clean_line.startswith("Total;") or clean_line.startswith("Total"):
                    total_idx = idx
                    break
                    
            if header_idx != -1:
                # Slice from header_idx to total_idx (inclusive of Total line if present)
                if total_idx != -1:
                    cleaned_lines = lines[header_idx:total_idx + 1]
                else:
                    cleaned_lines = lines[header_idx:]
                    
                with open(csv_path, "w", encoding="latin1") as f:
                    f.writelines(cleaned_lines)
                print(f"CSV limpo com sucesso: {csv_path}")
            else:
                print(f"Aviso: Cabeçalho do município não encontrado no CSV. Nenhuma alteração feita em: {csv_path}")
        except Exception as e:
            print(f"Erro ao limpar o arquivo CSV {csv_path}: {e}")



def parse_tabnet_csv(csv_path: str) -> pd.DataFrame:
    """
    Parses a downloaded Tabnet CSV into a clean pandas DataFrame.
    Identifies header and footer markers, splits municipality IBGE codes and names,
    and converts numerical columns.
    """
    with open(csv_path, "r", encoding="latin1") as f:
        lines = f.readlines()
        
    header_idx = -1
    total_idx = -1
    
    for idx, line in enumerate(lines):
        clean_line = line.strip().replace('"', '')
        # Matches headers containing 'municipio' / 'município' and a semicolon
        if header_idx == -1 and ("municipio" in clean_line.lower() or "município" in clean_line.lower()) and ";" in clean_line:
            header_idx = idx
        elif clean_line.startswith("Total;") or clean_line.startswith("Total"):
            total_idx = idx
            break
            
    if header_idx == -1:
        raise ValueError("Linha de cabeçalho 'Município' não encontrada no CSV do Tabnet.")
        
    # Slices the CSV rows
    data_lines = lines[header_idx:total_idx] if total_idx != -1 else lines[header_idx:]
    
    csv_data = "".join(data_lines)
    df = pd.read_csv(StringIO(csv_data), sep=";", encoding="latin1")
    
    # Clean the first column (Municípios)
    mun_col = df.columns[0]
    
    def split_mun(val):
        if pd.isna(val):
            return None, None
        val_str = str(val).strip()
        # Splits 6 digits code from name (e.g. "220800 PICOS")
        match = re.match(r"^(\d{6})\s+(.*)$", val_str)
        if match:
            return match.group(1), match.group(2)
        return None, val_str
        
    splits = df[mun_col].apply(split_mun)
    df["cod_ibge"] = [s[0] for s in splits]
    df["municipio"] = [s[1] for s in splits]
    
    # Reorganize column order
    cols = ["cod_ibge", "municipio"] + [c for c in df.columns if c not in ["cod_ibge", "municipio", mun_col]]
    df = df[cols]
    
    # Process numeric columns (clean thousands separators and decimal markers)
    for col in df.columns[2:]:
        cleaned_series = (
            df[col]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(cleaned_series, errors="coerce")
        
    return df



