# Scripts e Utilitários da PNITE

Conjunto de scripts Python e Node.js para processamento, extração, agregação e integração dos dados do transporte escolar e capacitações da PNITE.

---

## Estrutura dos Scripts

- **`extrair_dados_excel.py`** *(na raiz)*:
  Script central de extração. Lê as planilhas consolidadas em `data/Transporte Escolar/`, calcula os 18 indicadores analíticos, gera os benchmarks nacionais e compõe os pacotes `pnite_dados_consolidados.json` e `pnite_dados_consolidados.js`.

- **`scripts/criar_banco_dados_brutos.py`**:
  Estrutura e carga dos dados brutos do SETE (`ano_carga` 2026) e do Censo Escolar (`ano_carga` 2025) no Supabase **via API** (HTTPS `/pg/query`, chave secreta do `.env`). Gera as migrações `0003_sete.sql`/`0004_censo.sql` (`--gerar-ddl`), carrega em lotes idempotentes com checkpoint (`--retomar`), aceita carga por UF (`--uf go`) e carrega as referências (`--tabelas municipios referencia`).

- **`scripts/supabase_migrar.py`**:
  Aplica as migrações SQL de `supabase/migrations/` (schemas, tabelas, views de análise e a view pública `indicadores`), registrando-as em `pnite_meta.migracoes`.

- **`scripts/validar_paridade.py`**:
  Compara a API (`/rest/v1/indicadores`, chave publishable) com o pacote compilado `pnite_dados_consolidados.json`, campo a campo, por escopo.

- **`scripts/supabase_api.py`**:
  Cliente mínimo da API do Supabase usado pelos scripts acima (lê `SUPABASE_URL` e `SUPABASE_SECRET_KEY` do `.env`).

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

---

## Base de Dados no Supabase

Camadas (definidas em `supabase/migrations/`):

| Schema | Conteúdo | Acesso pela API |
|---|---|---|
| `sete` | dados brutos do SETE (14 tabelas + `rota_shape` com o GeoJSON das rotas) | não exposto |
| `censo` | microdados do Censo Escolar (`matricula`) | não exposto |
| `ref` | UFs, municípios IBGE, pareamento de cargas, valores de referência legados | não exposto |
| `analise` | views de leitura limpa (`v_alunos`, `v_rotas`, ...) e agregações municipais | não exposto |
| `public` | `indicadores`: indicadores e contadores agregados por escopo | leitura (`anon`) |

Os dados brutos contêm dados pessoais (CPF, placa, coordenadas de alunos) e nunca são expostos; a chave publishable lê apenas `public.indicadores`.

Atualização completa (na raiz, com o `.env` preenchido a partir de `.env.example`):
```bash
pip install requests python-dotenv python-docx pandas openpyxl
python scripts/supabase_migrar.py
python scripts/criar_banco_dados_brutos.py --tabelas municipios referencia
python scripts/criar_banco_dados_brutos.py            # SETE + Censo (use --retomar se interromper)
python -c "import sys; sys.path.insert(0,'scripts'); from supabase_api import executar_sql; executar_sql('SELECT pnite_meta.atualizar_indicadores();')"
python scripts/validar_paridade.py
```

Consulta pela API:
```
GET {SUPABASE_URL}/rest/v1/indicadores?ano_carga=eq.2026&nivel=eq.estado&chave=eq.go
GET {SUPABASE_URL}/rest/v1/indicadores?ano_carga=eq.2026&nivel=eq.municipio&uf=eq.go&select=chave,label,indicadores
Cabeçalho: apikey: {SUPABASE_PUBLISHABLE_KEY}
```
