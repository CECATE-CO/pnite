# Scripts e Utilitários da PNITE

Conjunto de scripts Python e Node.js para processamento, extração, agregação e integração dos dados do transporte escolar e capacitações da PNITE.

---

## Estrutura dos Scripts

- **`extrair_dados_excel.py`** *(na raiz)*:
  Script central de extração. Lê as planilhas consolidadas em `data/Transporte Escolar/`, calcula os 18 indicadores analíticos, gera os benchmarks nacionais e compõe os pacotes `pnite_dados_consolidados.json` e `pnite_dados_consolidados.js`.

- **`scripts/criar_banco_dados_brutos.py`**:
  Script de carga e estruturação dos dados brutos do SETE e Censo Escolar em banco de dados relacional PostgreSQL / Supabase, baseado nos metadados e dicionários do sistema.

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
