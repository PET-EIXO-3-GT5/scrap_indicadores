# Scraper de Dados do DataSUS (TabNet)

Este relatório apresenta o funcionamento e a arquitetura do scraper automatizado desenvolvido em Python e Playwright para baixar dados de saúde pública do DATASUS (TabNet), atendendo aos requisitos descritos no arquivo [bases.md](file:///home/mateus/Documentos/PET/scrap_indicadores/bases.md).

---

## 1. Como funciona o Scraper?

O TabNet do DATASUS funciona através de formulários dinâmicos (`deftohtm.exe` ou `dhdat.exe`) acoplados a um backend em CGI. Para obter e baixar uma tabela consolidada, o fluxo padrão consiste em preencher as variáveis do formulário (Linha, Coluna, Conteúdo, Períodos e Filtros), clicar em **"Mostra"** e fazer o download do arquivo CSV gerado.

O scraper desenvolvido em [scraper_navegador.py](file:///home/mateus/Documentos/PET/scrap_indicadores/scrap_indicadores/src/scrap_indicadores/scraper_navegador.py) automatiza todo esse fluxo com as seguintes características de robustez:
1. **Interação com Elementos Ocultos:** Os filtros regionais (como a Unidade da Federação no SIS-PNI) são frequentemente ocultos no DOM. O scraper utiliza injeção de JavaScript direto na página do navegador para manipular os seletores, contornando a validação de visibilidade do Playwright.
2. **Seleção Inteligente de Períodos:** O scraper realiza correspondência exata ou parcial para encontrar e selecionar períodos. Em bases mensais (como o SIHSUS), passar `"2024"` fará com que o scraper selecione automaticamente todos os 12 meses daquele ano de uma só vez.
3. **Tratamento de Novas Abas:** Ao clicar em "Mostra", o formulário do TabNet abre uma nova aba (`target="_blank"`). O scraper aguarda a abertura dessa aba e monitora o carregamento dos resultados nela.
4. **Parser de CSV Customizado:** O CSV exportado pelo TabNet é codificado em `latin1`, usa ponto-e-vírgula (`;`) como separador e possui cabeçalhos e rodapés com metadados (como notas de rodapé e totais). A função `parse_tabnet_csv` limpa esses metadados, separa o código IBGE e o nome do município (ex: `"220800 PICOS"` em `220800` e `PICOS`) e converte os números formatados (com pontos de milhar) para tipos numéricos do pandas.

---

## 2. Código do Scraper

O código completo do scraper está implementado em [scraper_navegador.py](file:///home/mateus/Documentos/PET/scrap_indicadores/scrap_indicadores/src/scrap_indicadores/scraper_navegador.py). A classe `DatasusTabnetScraper` pode ser importada e utilizada em qualquer script do projeto:

```python
from scrap_indicadores.scraper_navegador import DatasusTabnetScraper, parse_tabnet_csv

# Inicializa o scraper
scraper = DatasusTabnetScraper(headless=True)

# Faz o download dos dados de mortalidade do Piauí em 2024
csv_path = await scraper.download_csv(
    url="http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/obt10pi.def",
    output_path="./dados_scraped/sim_geral_2024.csv",
    linha="Município",
    coluna="--Não-Ativa--",
    incremento="Óbitos_p/Residênc",
    periodos="2024"
)

# Transforma em um DataFrame pandas limpo
df = parse_tabnet_csv(csv_path)
```

---

## 3. Mapeamento das Bases e Indicadores (bases.md)

Com base nas prioridades de indicadores listadas no [bases.md](file:///home/mateus/Documentos/PET/scrap_indicadores/bases.md), aqui está o mapeamento dos endpoints do TabNet, incluindo os parâmetros recomendados para a consulta:

### A. Principais causas de internação infantil (SIHSUS)
* **URL:** `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nrpi.def` (Morbidade Hospitalar - por local de residência - Piauí)
* **Linha:** `Município` (para extrair Picos e outros municípios) ou `Capítulo CID-10` / `Grupo CID-10` se desejar ver as doenças diretamente na tabela.
* **Coluna:** `Não ativa` ou `Ano/mês atendimento`.
* **Incremento:** `Internações`
* **Filtro Recomendado:** Faixa Etária (`SFaixa_Etária`) selecionando apenas idades infantis (ex: `< 1 ano`, `1 a 4 anos`, `5 a 9 anos`).

### B. Mortalidade materna e infantil (SIM)
* **URL de Óbitos Infantis:** `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/inf10pi.def`
  * **Linha:** `Município`
  * **Coluna:** `Não ativa`
  * **Incremento:** `Óbitos p/Residênc`
* **URL de Óbitos Maternos / Mulheres em Idade Fértil:** `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/mat10pi.def`
  * **Linha:** `Município`
  * **Coluna:** `Não ativa`
  * **Incremento:** `Óbitos p/Residênc` (ou `Óbitos maternos`)

### C. Principais agravos (SINAN)
O SINAN possui páginas individuais por doença/agravo. O link de Dengue foi validado com sucesso:
* **URL Dengue:** `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/denguebpi.def`
  * **Linha:** `Município de notificação`
  * **Coluna:** `Não ativa`
  * **Incremento:** `Casos_Prováveis`
* **Outros Agravos do SINAN (Exemplos):**
  * Animais Peçonhentos: `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/animaispi.def`
  * Violência Interpessoal: `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/violepi.def`
  * Tuberculose (desde 2001): `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/tubercpi.def`

### D. Nº de diabéticos e hipertensos do município (SISAB / HIPERDIA)
* **URL Histórica (Hiperdia):** `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?hiperdia/cnv/vadiapi.def` (Diabetes) e `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?hiperdia/cnv/vahippi.def` (Hipertensão).
* **Atenção:** O Hiperdia foi descontinuado e substituído pelo e-SUS APS (SISAB). O acesso aos dados diários e de acompanhamento ativo da Atenção Básica é feito de forma consolidada via relatórios públicos do SISAB. Recomenda-se utilizar o módulo do SISAB no PySUS (`pysus.online_data.SISAB`) que realiza as consultas programáticas diretamente à API do SISAB.

### E. Cobertura vacinal infantil (SIS-PNI)
* **URL de Doses Aplicadas:** `http://tabnet.datasus.gov.br/cgi/dhdat.exe?bd_pni/dpnibr.def`
  * **Linha:** `Município`
  * **Coluna:** `Não ativa`
  * **Incremento:** `Doses_aplicadas|QT_DOSE`
  * **Filtro:** `SUnidade da Federação` -> `Piauí` (para obter apenas os municípios do estado).
* **URL de Cobertura Vacinal:** `http://tabnet.datasus.gov.br/cgi/dhdat.exe?bd_pni/cpnibr.def`
  * **Linha:** `Município`
  * **Coluna:** `Não ativa`
  * **Filtro:** `SUnidade da Federação` -> `Piauí`

### F. Fila de espera para exames
Conforme descrito no [guia.md](file:///home/mateus/Documentos/PET/scrap_indicadores/guia.md), este dado **não está disponível** no TabNet ou no FTP do DATASUS por conter informações sigilosas de pacientes. Para obter este indicador, a alternativa é realizar scraping diretamente em portais de transparência locais de saúde do estado do Piauí ou do município de Picos.

---

## 4. Resultados do Teste de Download (Município de Picos - 220800)

O scraper foi executado com sucesso e os dados de 2024 para o município de Picos foram baixados e processados:

| Base de Dados | Indicador extraído | Ano de referência | Valor obtido para Picos (220800) | Arquivo local |
| :--- | :--- | :---: | :---: | :--- |
| **SIM** | Óbitos por residência | 2024 | **621** óbitos | `dados_scraped/sim_geral_2024.csv` |
| **SIHSUS** | Internações por residência | 2024 | **3877** internações | `dados_scraped/sih_geral_2024.csv` |
| **SINAN** | Casos prováveis de Dengue | 2024 | **78** casos notificados | `dados_scraped/sinan_dengue_2024.csv` |
| **SIS-PNI** | Doses aplicadas de vacinas | 2022 | **41964** doses aplicadas | `dados_scraped/pni_doses_2022.csv` |

> [!NOTE]
> O arquivo bruto consolidado do estado do Piauí contendo a tabela de todos os municípios fica salvo na pasta `dados_scraped/` para permitir análises comparativas e cálculos de médias regionais no pandas.
