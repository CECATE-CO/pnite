# BACKLOG DE INDICADORES REMOVIDOS — PNITE
**Plataforma Nacional de Inteligência em Transporte Escolar**  
*Registro oficial de descontinuação e catálogo de restauração de indicadores*

---

## 1. Identificação da Remoção
- **Data:** 14/09/2026
- **Versão de Origem:** `v.1.0.0`
- **Versão pós-remoção:** `v.1.1.0`
- **Indicadores Removidos:**
  1. **PVT** — Veículos Terceirizados (Tipo: Descritivo - D)
  2. **TEDC** — Taxa de Eficácia da Demanda Cadastrada (Tipo: Finalístico - FNL)

---

## 2. Indicador 1: PVT — Veículos Terceirizados

### 2.1. Ficha Metodológica
- **Sigla:** `PVT`
- **Nome:** Veículos Terceirizados
- **Categoria / Tipo:** Descritivo (`D`)
- **Unidade de Medida:** `%`
- **Fonte de Dados:** SETE/PDDE (`script_04_veiculos.csv`)
- **Valor Nacional de Referência:** `49.32%`
- **Fórmula Matemática:**
  $$\text{PVT} = \left(\frac{\text{Veículos Terceirizados}}{\text{Total de Veículos}}\right) \times 100$$
- **Objetivo:**
  > Medir a participação de veículos terceirizados na frota do transporte escolar, indicando o arranjo operacional adotado pelo ente federado.
- **Regra Técnica Operacional:**
  - Origem dos dados: campo `origem = 2` na tabela de veículos do SETE (`script_04_veiculos.csv`).
  - Total de veículos: contagem total de registros de veículos ativos.
  - Nota de ressalva metodológica original: *Suposição não confirmada nos manuais oficiais do SETE de que o código `origem = 2` equivale estritamente a veículo terceirizado*.

### 2.2. Snippets de Código para Restauração

#### A. Inclusão no catálogo geral (`ALL_INDICATORS`)
Localização original: Array `ALL_INDICATORS` (~linha 523 do arquivo principal):
```javascript
{
  sigla: 'PVT',
  nome: 'Veículos Terceirizados',
  tipo: 'D',
  formula: '(Veículos terceirizados ÷ Total de veículos) × 100',
  fonte: 'SETE/PDDE',
  status: 'ok',
  valNac: 49.32,
  unit: '%',
  obj: 'Medir a participação de veículos terceirizados na frota, indicando o arranjo operacional adotado.'
},
```

#### B. Inclusão no grupo de indicadores da Dashboard (`INDICATORS.D`)
Localização original: Objeto `INDICATORS.D` (~linha 545):
```javascript
{ sigla: 'PVT', nome: 'Veículos Terceirizados', unit: '%', key: 'PVT' },
```

#### C. Inclusão no dropdown de cálculo manual (`calcSelect`)
Localização original: Elemento `<select id="calcSelect">` (~linha 425):
```html
<option value="PVT">PVT — Veículos Terceirizados</option>
```

#### D. Inclusão nas definições da calculadora (`CALC_DEFS`)
Localização original: Objeto `CALC_DEFS` (~linha 577):
```javascript
PVT: {
  fields: ['Veículos terceirizados', 'Total de veículos'],
  formula: '(A ÷ B) × 100',
  fn: v => (v[0] / v[1] * 100).toFixed(1) + '%'
},
```

#### E. Inclusão na Memória de Cálculo
Localização original: Seção de veículos da função de memória de cálculo (~linha 925):
```javascript
html += card(
  'PVT',
  'Veículos Terceirizados',
  'D',
  [['Veículos origem 2', fmt(r.vt)], ['Total de veículos', fmt(r.tot_veic)]],
  `(${fmt(r.vt)} ÷ ${fmt(r.tot_veic)}) × 100`,
  calcVal(r.vt, r.tot_veic, true),
  'Campo origem = 2',
  'Suposição não confirmada: origem 2 = terceirizado',
  null
);
```

#### F. Inclusão na tabela de microdados SETE (`SETE_COLS_IND`)
Localização original: Array `SETE_COLS_IND` (~linha 1057):
```javascript
{ k: 'PVT', l: 'PVT %⚠' },
```

#### G. Inclusão no grid de métricas de frota (`renderFrotaGrid`)
Localização original: Array de métricas de frota (~linha 708):
```javascript
{ k: 'PVT', n: 'Veículos Terceirizados', c: 'fb2' }
```

---

## 3. Indicador 2: TEDC — Taxa de Eficácia da Demanda Cadastrada

### 3.1. Ficha Metodológica
- **Sigla:** `TEDC`
- **Nome:** Taxa de Eficácia da Demanda Cadastrada
- **Categoria / Tipo:** Finalístico (`FNL`)
- **Unidade de Medida:** `%`
- **Fonte de Dados:** SETE/PDDE (`script_13_rota_atende_aluno.csv` cruzado com `script_01_alunos.csv`)
- **Valor Nacional de Referência:** `30.96%`
- **Fórmula Matemática:**
  $$\text{TEDC} = \left(\frac{\text{Alunos Transportados em Rotas Ativas}}{\text{Total de Alunos Cadastrados no SETE}}\right) \times 100$$
- **Objetivo:**
  > Medir a cobertura efetiva do atendimento do transporte escolar, relacionando os alunos efetivamente alocados em rotas ativas ao total de alunos cadastrados no sistema SETE.
- **Regra Técnica Operacional:**
  - Numerador: alunos distintos vinculados a rotas ativas (`al_transp`).
  - Denominador: total de alunos cadastrados no SETE (`al_cad`).
  - Nota metodológica original: *Indicador da cadeia de alunos calculado no grão municipal (município, id_aluno). Não reagrega diretamente para os valores estaduais simples devido à colisão de chaves locais de id_aluno*.

### 3.2. Snippets de Código para Restauração

#### A. Inclusão no catálogo geral (`ALL_INDICATORS`)
Localização original: Array `ALL_INDICATORS` (~linha 532):
```javascript
{
  sigla: 'TEDC',
  nome: 'Taxa de Eficácia da Demanda Cadastrada',
  tipo: 'FNL',
  formula: '(Alunos em rotas ativas ÷ Total cadastrados) × 100',
  fonte: 'SETE/PDDE',
  status: 'ok',
  valNac: 30.96,
  unit: '%',
  obj: 'Medir a cobertura efetiva do atendimento, relacionando alunos atendidos em rotas ativas aos alunos cadastrados no SETE.'
},
```

#### B. Inclusão no grupo de indicadores da Dashboard (`INDICATORS.FNL`)
Localização original: Objeto `INDICATORS.FNL` (~linha 558):
```javascript
{ sigla: 'TEDC', nome: 'Eficácia Demanda Cadastrada', unit: '%', key: 'TEDC' },
```

#### C. Inclusão na Memória de Cálculo
Localização original: Seção de alunos/finalísticos da memória de cálculo (~linha 980):
```javascript
const tedc_val = r.al_transp && r.al_cad ? (r.al_transp / r.al_cad * 100).toFixed(2) + '%' : null;
html += card(
  'TEDC',
  'Taxa de Eficácia da Demanda Cadastrada',
  'FNL',
  [['Alunos em rotas ativas', fmt(r.al_transp)], ['Alunos cadastrados', fmt(r.al_cad)]],
  `(${fmt(r.al_transp)} ÷ ${fmt(r.al_cad)}) × 100`,
  tedc_val,
  'script_13 (alunos em rotas) ÷ script_01 (alunos cadastrados)',
  null,
  null
);
```

#### D. Inclusão na tabela de microdados SETE (`SETE_COLS_IND`)
Localização original: Array `SETE_COLS_IND` (~linha 1059):
```javascript
{ k: 'TEDC', l: 'TEDC %' },
```

#### E. Vínculo como substituto do ICA (`MISSING_TABLE`)
Caso seja desejável reconectar o indicador `ICA` ao `TEDC`:
```javascript
{
  sigla: 'ICA',
  nome: 'Continuidade do Acesso',
  info: 'Requer registro diário de execução de rotas',
  subst: 'TEDC',
  ganho: 'Substitui a medida de continuidade pela cobertura do aluno efetivamente atendido, com base apenas em demanda cadastrada e atendimento realizado.'
}
```

---

## 4. Dados Históricos Registrados (Valores por Unidade Geográfica)

| Âmbito | PVT (%) | TEDC (%) |
| :--- | :---: | :---: |
| **Brasil (Nacional)** | 49.32 | 30.96 |
| **Norte** | 44.99 | — |
| **Nordeste** | 47.07 | — |
| **Sudeste** | 55.14 | — |
| **Sul** | 45.58 | — |
| **Centro-Oeste** | 23.62 | — |
| Acre (AC) | 18.80 | — |
| Alagoas (AL) | 37.71 | — |
| Amazonas (AM) | 57.81 | — |
| Amapá (AP) | 57.89 | — |
| Bahia (BA) | 64.03 | — |
| Ceará (CE) | 47.97 | — |
| Distrito Federal (DF) | 0.72 | — |
| Espírito Santo (ES) | 69.99 | — |
| Goiás (GO) | 48.82 | — |
| Maranhão (MA) | 66.17 | — |
| Minas Gerais (MG) | 51.98 | — |
| Mato Grosso do Sul (MS) | 31.06 | — |
| Mato Grosso (MT) | 13.87 | — |
| Pará (PA) | 50.56 | — |
| Paraíba (PB) | 27.72 | — |
| Pernambuco (PE) | 52.79 | — |
| Piauí (PI) | 55.71 | — |
| Paraná (PR) | 53.21 | — |
| Rio de Janeiro (RJ) | 45.33 | — |
| Rio Grande do Norte (RN) | 40.42 | — |
| Rondônia (RO) | 38.89 | — |
| Roraima (RR) | 36.51 | — |
| Rio Grande do Sul (RS) | 49.06 | — |
| Santa Catarina (SC) | 34.48 | — |
| Sergipe (SE) | 31.12 | — |
| São Paulo (SP) | 53.27 | — |
| Tocantins (TO) | 54.48 | — |

---

## 5. Instruções para Restauração Rápida
Para restaurar qualquer um dos dois indicadores (ou ambos):
1. Copie o snippet correspondente da Seção 2.2 ou 3.2.
2. Localize no arquivo principal `PNITE [V.1.2.0].html` (anteriormente `ESTRUTURA HTML [TE V140926].html`) o array/objeto indicado.
3. Cole a respectiva entrada no array/objeto mantendo a sintaxe JavaScript / HTML.
4. Incremente a versão do sistema em conformidade com o padrão SemVer (`v.X.Y.Z`).
5. Execute o teste de carregamento e interface no console do navegador.
