# PNITE — Plataforma Nacional de Inteligência em Transporte Escolar

A **PNITE** é uma plataforma analítica desenvolvida para visualização, monitoramento, exploração e interpretação de informações estratégicas sobre o transporte escolar público brasileiro.

A ferramenta consolida dados operacionais do Sistema Eletrônico de Gestão do Transporte Escolar (**SETE**), do **Censo Escolar** (MEC/Inep) e das ações de formação do Centro Colaborador de Apoio ao Transporte Escolar (**CECATE/UFG**).

---

## 🏛️ Realização e Parcerias

- **MEC** — Ministério da Educação
- **FNDE** — Fundo Nacional de Desenvolvimento da Educação
- **UFG** — Universidade Federal de Goiás
- **CECATE** — Centro Colaborador de Apoio ao Transporte Escolar

---

## 🚀 Como Executar

A PNITE é uma aplicação web de alta performance projetada para execução direta no navegador (arquitetura *client-side* prioritária), sem necessidade de servidor back-end obrigatório:

1. Clone o repositório ou faça o download dos arquivos:
   ```bash
   git clone https://github.com/mathmorato/pnite.git
   ```
2. Abra o arquivo principal no navegador:
   - Dê um duplo-clique em `PNITE.html`, ou
   - Inicie um servidor local se preferir:
     ```bash
     npx serve .
     # ou
     python -m http.server 8000
     ```

---

## 📂 Organização do Repositório

O repositório adota uma estrutura limpa e modular:

```
pnite/
├── PNITE.html                 # Aplicação web principal (versão mais recente)
├── README.md                  # Documentação geral do repositório
├── AGENTS.md                  # Diretrizes e regras técnicas de manutenção e versionamento
├── GEMINI.md                  # Referência de regras do agente
├── LICENSE                    # Licença do projeto
│
├── assets/                    # Recursos visuais e logomarcas
│   ├── README.md              # Guia de identidade e especificações de uso
│   ├── logos/                 # Logomarcas oficiais (PNG e SVG vetorial)
│   │   ├── logo_pnite_color.png
│   │   ├── logo_pnite_white.png
│   │   ├── logo_pnite_original.png
│   │   ├── logo_ufg.jpg
│   │   └── logo_cecate.svg
│   └── img/                   # Ilustrações e fotografias de frotas
│       └── escolar_sao_goncalo.png
│
├── data/                      # Bases de dados estruturadas por frente analítica
│   ├── Transporte Escolar/    # Planilhas e consolidados do SETE e Censo Escolar
│   │   ├── pnite_dados_consolidados.js
│   │   ├── pnite_dados_consolidados.json
│   │   ├── malhas_mg.json
│   │   ├── sete_mun.json
│   │   └── *.xlsx / *.csv consolidados
│   ├── Capacitação/           # Dados e formulários das oficinas regionais (5CTE a 16CTE)
│   │   ├── pnite_capacitacao_dados.js
│   │   └── *CTE - Avaliação, Formulário e Lista de Presença.xlsx
│   └── Gestão/                # Diretório reservado para indicadores de governança e regulação
│
├── supabase/migrations/       # Estrutura SQL do banco (schemas, tabelas, views, API)
│
├── scripts/                   # Utilitários de agregação e banco de dados
│   ├── README.md              # Descrição das rotinas de suporte
│   ├── criar_banco_dados_brutos.py
│   ├── pegar_dado_rota.js
│   ├── pegar_dado_rota.py
│   └── agrega_ind.py
│
├── dic/                       # Dicionários de dados originais de extração
│   ├── Dicionário utilizado Marcos extração SETE.docx
│   └── Dicionário utilizado Marcos extração SETE.pdf
│
├── old/                       # Histórico rigoroso de versões arquivadas (v.1.0.0 até atual)
│   └── PNITE [V.*].html
│
└── extrair_dados_excel.py     # Script central de processamento das planilhas em data/
```

---

## 📊 Frentes Analíticas da Plataforma

1. **Indicadores do Transporte Escolar:**
   - Diagnóstico nacional, regional e estadual por 18 indicadores analíticos (PRGM, PRIO, PRRM, PVP, PVT, IUC, ATE, MEDATE, PCSC, PARI, etc.).
   - Mapa coroplético do Brasil interativo por UF com faixas metodológicas.
   - Detalhamento por rotas, alunos, escolas, frotas, motoristas e monitores.
   - Memória de cálculo detalhada com fórmulas e fontes.

2. **Indicadores da Capacitação (Centro-Oeste):**
   - Monitoramento das ações presenciais nos estados de GO, MT, MS e DF.
   - Filtros por polo de formação, UF, perfil de participação e ano (2024–2025).
   - Estatísticas de engajamento de Conselheiros CACS-Fundeb e Gestores Municipais/Estaduais.
   - Mapa georreferenciado dos municípios participantes.

3. **Gestão e Regulação:**
   - Módulo preparado para integração de normas, compras públicas, custos operacionais e fornecedores.

---

## 🔄 Atualização dos Dados

Para recalcular os indicadores a partir de planilhas adicionadas ou atualizadas em `data/Transporte Escolar/`:

```bash
python extrair_dados_excel.py
```

O script recalcula os totais nacionais, agregações regionais/estaduais e atualiza os arquivos:
- `data/Transporte Escolar/pnite_dados_consolidados.json`
- `data/Transporte Escolar/pnite_dados_consolidados.js`

Ao abrir o `PNITE.html`, os dados atualizados são refletidos imediatamente.

### Base de dados no Supabase (em migração)

Os dados brutos do SETE e do Censo Escolar estão sendo migrados para o Supabase, com os indicadores calculados no banco e servidos por escopo via API (`/rest/v1/indicadores`). Estrutura, carga e validação estão descritas em [`scripts/README.md`](scripts/README.md#base-de-dados-no-supabase). As credenciais ficam no `.env` (modelo em `.env.example`), que nunca deve ser versionado nem servido pelo navegador.

---

## 🏷️ Versionamento

A plataforma segue um versionamento sequencial $Z \rightarrow Y \rightarrow X$ estrito (`v.X.Y.Z`). Toda evolução é arquivada em `old/PNITE [V.X.Y.Z].html` antes de cada incremento, garantindo rastreabilidade histórica e segurança operacional.
