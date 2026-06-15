# 1. O que o código atual faz?
Atualmente, o seu código atua como um extrator e processador automático de dados de saúde pública focado no município de Picos - PI. Ele consome os dados abertos do DataSUS através da biblioteca PySUS.

Aqui está o passo a passo do que as diferentes partes do seu código fazem:

- Extração (extract_picos.py): Ele se conecta aos servidores do DataSUS e tenta baixar os arquivos mais recentes (geralmente em formato Parquet) para quatro sistemas de informação específicos referentes ao estado do Piauí (PI) ou ao Brasil inteiro (no caso da Dengue):
    - SIM: Sistema de Informações sobre Mortalidade.
    - SIH: Sistema de Informações Hospitalares.
    - SINAN: Sistema de Informação de Agravos de Notificação (atualmente filtrando apenas para "Dengue").
    - PNI: Programa Nacional de Imunizações.

- Filtragem e Cálculo (picos_indicators.py): Depois que os arquivos brutos do estado são baixados, este script atua como um "funil".
    - Ele varre todas as linhas e mantém apenas aquelas cujo município de residência (CODMUNRES, MUNIC_RES, etc.) seja igual ao código IBGE de Picos (220800).
    - Em seguida, ele calcula os indicadores: quantas mortes ocorreram, quantas dessas mortes foram maternas ou de crianças, quantas internações ocorreram, a contagem dos CIDs (doenças) que mais internaram crianças menores de 10 anos, e faz um resumo dos casos de Dengue.
- Exploração (validacao_picos.ipynb): Este é um ambiente de testes. Ele tenta ver se os arquivos estão disponíveis entre 2020 e 2025 (mostrando uma tabela de disponibilidade), testa o download para 2024 e imprime os indicadores calculados e algumas linhas de exemplo (amostras) do DataFrame.


# 2. Como conseguir os indicadores listados no bases.md?
O seu arquivo bases.md define excelentes prioridades. Vamos analisar o status de cada um e o que falta para você consegui-los:

## A. Principais causas de internação infantil (SIHSUS)
✅ Status: Já implementado (parcialmente). O seu código atual (calculate_sih_indicators) já isola pacientes com menos de 10 anos e lista as principais causas usando a coluna DIAG_PRINC.

- O que falta melhorar: O código atual retorna CIDs (ex: J189, P599). Para virar um indicador compreensível, você precisará usar uma tabela de conversão do CID-10 para mapear J189 para "Pneumonia não especificada", por exemplo. O PySUS possui utilitários para decodificar CIDs ou você pode baixar um arquivo CSV/JSON com os códigos e cruzar com o pandas (pd.merge).

## B. Mortalidade materna e infantil (SIM)
✅ Status: Já implementado. A função calculate_sim_indicators já está mapeando óbitos de mulheres em idade fértil, filtrando causas que começam com "O" (Causas maternas segundo CID-10) ou flags de óbito materno (OBITOMAT), e identificando óbitos de menores de 4 anos de idade (IDADE começando com 0 a 3).

- O que falta melhorar: A mortalidade infantil, formalmente, foca em crianças menores de 1 ano. Você pode ajustar o código para ser mais estrito na coluna de IDADE do SIM (que usa um formato onde o primeiro dígito indica se são minutos, horas, dias, meses ou anos).
## C. Principais agravos (SINAN)
⚠️ Status: Incompleto. Atualmente seu código baixa apenas dados do grupo "Dengue" (group="DENG"). O SINAN relata muitos agravos (Zika, Chikungunya, Tuberculose, Hanseníase, Sífilis, etc.).

- Como conseguir: Você precisará alterar o seu script de extração (extract_picos.py) para iterar não apenas pela Dengue, mas por uma lista de grupos do SINAN. Para obter os principais agravos do município, o ideal é consultar as bases de Animais Peçonhentos, Violência Interpessoal, Tuberculose, e compilar a contagem de casos notificados de cada um para gerar um ranking.
## D. Nº de diabéticos e hipertensos do município
❌ Status: Não implementado. O SIM e o SIH só mostram diabetes e hipertensão se a pessoa for internada ou falecer por isso. Para o acompanhamento populacional diário, você precisa da base da Atenção Básica, gerida pelo SISAB / e-SUS.

- Como conseguir: O PySUS tem um módulo específico para o SISAB. Você pode obter os relatórios de "Cadastro Individual" ou de "Condições de Saúde". O código seria algo assim (para testar em um notebook):
python

```bash
from pysus.online_data import SISAB

# É possível buscar relatórios consolidados do SISAB por município informando
# os códigos das linhas, colunas e os agravos desejados.
df_sisab = SISAB.get_reports(
    linha="Municipio", 
    coluna="Condicao_avaliada",
    # Parâmetros adicionais dependerão da documentação da API do SISAB do próprio PySUS
)
```
## E. Cobertura vacinal infantil (SIS-PNI)
⚠️ Status: Difícil direto no FTP bruto. No seu notebook, a coleta do PNI está retornando "sem arquivos". O FTP do Datasus mudou a organização do PNI algumas vezes. Além disso, ter as vacinas aplicadas não é igual à cobertura vacinal. Cobertura é igual a (Doses Aplicadas / População Alvo) * 100.

- Como conseguir as Doses: Explore o PySUS/FTP baixando pelo Tabnet diretamente, ou tente investigar pelo módulo pysus.online_data.PNI. Pode ser necessário procurar grupos específicos de PNI como DP (Doses Aplicadas).
- Como conseguir a Cobertura: Você precisará integrar outra base: o SINASC (Sistema de Nascidos Vivos). Cruzando a quantidade de crianças que nasceram (SINASC) com as vacinas aplicadas, você obtém a porcentagem real da cobertura vacinal infantil do município de Picos.

## F. Fila de espera para exames
❌ Status: Fora do escopo do Tabnet/FTP Padrão. Isso não fica disponível no SINAN, SIH ou SIM. As filas de regulação ficam em sistemas como o SISREG (Sistema Nacional de Regulação) ou plataformas específicas de regulação do Governo do Estado do Piauí.

- Como conseguir: Os dados granulares do SISREG não são abertos de forma fácil no FTP do Datasus por questões de sigilo dos pacientes. Para automatizar isso, sua equipe terá que pesquisar se o Governo do Piauí (Sesapi) ou a prefeitura de Picos possui um Portal de Transparência da Fila de Regulação e fazer técnicas de Web Scraping tradicional (usando BeautifulSoup ou Selenium em Python) em cima desse portal específico, ou obter os dados via portal de dados abertos estaduais.

# Resumo do Próximo Passo Sugerido
Recomendo que você foque agora em integrar o SINASC (Nascidos Vivos) no projeto. Ao fazer o download do SINASC, você conseguirá:

1. Fechar o cálculo exato da mortalidade infantil (Mortes de crianças menores de 1 ano do SIM / Número de nascidos vivos do SINASC).
2. Ter a base populacional (População alvo) que vai ser obrigatória quando você for lidar com a cobertura vacinal.
