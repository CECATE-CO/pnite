# Scripts e Utilitários da PNITE

Conjunto de scripts Python e Node.js para processamento, extração, agregação e integração dos dados do transporte escolar e capacitações da PNITE.

---

## Estrutura dos Scripts

- **`extrair_dados_excel.py`** *(na raiz)*:
  Script central de extração. Lê as planilhas consolidadas em `data/Transporte Escolar/`, calcula os 18 indicadores analíticos, gera os benchmarks nacionais e compõe os pacotes `pnite_dados_consolidados.json` e `pnite_dados_consolidados.js`.

- **`scripts/criar_banco_dados_brutos.py`**:
  Script de carga e estruturação dos dados brutos do SETE e Censo Escolar em banco de dados relacional PostgreSQL / Supabase, baseado nos metadados e dicionários do sistema.

- **`scripts/extrair_capacitacao.py`**:
  Extrai e consolida os dados das capacitações a partir de `data/Capacitação/` (convocações HTML, formulários de inscrição, listas de presença e avaliações de cada `XCTE`, além do legado `legado_cte_01a04_powerbi.json` das capacitações 1 a 4). Gera `data/Capacitação/pnite_capacitacao_dados.js` em tabelas normalizadas, sem dados pessoais, seguindo o esquema `data/Capacitação/schema_capacitacao.sql` (base da futura migração para SQL). Uso: `pip install openpyxl` e `python scripts/extrair_capacitacao.py`.

- **`scripts/pegar_dado_rota.py` / `scripts/pegar_dado_rota.js`**:
  Utilitários para amostragem e inspeção detalhada de traçados geométricos de rotas e coordenadas geográficas do SETE.

- **`scripts/agrega_ind.py`**:
  Rotina histórica de agregação municipal/estadual a partir das tabelas da Divisão Territorial Brasileira (DTB/IBGE) e dados operacionais de rotas, veículos e alunos.

---

## Como Executar a Atualização de Dados

Na raiz do repositório:
```bash
python extrair_dados_excel.py
```
Os arquivos consolidados em `data/Transporte Escolar/` serão atualizados automaticamente e lidos pelo `PNITE.html`.
