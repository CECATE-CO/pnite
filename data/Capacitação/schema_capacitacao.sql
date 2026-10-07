-- ============================================================================
-- PNITE — Esquema relacional das Capacitações do Transporte Escolar
-- ----------------------------------------------------------------------------
-- Referência para a futura migração ao banco SQL (PostgreSQL/Supabase).
-- As tabelas e colunas são as mesmas de data/Capacitação/pnite_capacitacao_dados.js
-- (gerado por scripts/extrair_capacitacao.py), de modo que cada bloco
-- {colunas, linhas} do arquivo JS pode ser carregado diretamente com INSERT/COPY.
-- Não há dados pessoais: presença e inscrição são agregadas por município.
-- ============================================================================

-- Municípios envolvidos (convidados, participantes, polos e avaliações)
CREATE TABLE municipios (
    cod_ibge    char(7) PRIMARY KEY,
    nome        text        NOT NULL,
    uf          char(2)     NOT NULL,
    lat         numeric(8,4),            -- centróide da malha municipal
    lon         numeric(8,4)
);

-- Uma linha por capacitação (XCTE)
CREATE TABLE capacitacoes (
    numero          smallint PRIMARY KEY,           -- X do arquivo XCTE
    polo            text        NOT NULL,           -- município sede do evento
    polo_cod_ibge   char(7)     NOT NULL REFERENCES municipios (cod_ibge),
    uf              char(2)     NOT NULL,
    data_inicio     date        NOT NULL,
    data_fim        date        NOT NULL,
    local           text,                           -- texto da convocação
    fonte           text        NOT NULL            -- 'arquivos_brutos' | 'legado_power_bi'
);

-- Fato município × capacitação: convite, inscrições e presença
CREATE TABLE municipio_capacitacao (
    capacitacao         smallint NOT NULL REFERENCES capacitacoes (numero),
    cod_ibge            char(7)  NOT NULL REFERENCES municipios (cod_ibge),
    convidado           smallint NOT NULL CHECK (convidado IN (0, 1)),
    inscritos_total     integer,          -- NULL quando não há formulário (capacitações 1 a 4)
    inscritos_gestores  integer,
    inscritos_cacs      integer,
    inscritos_outros    integer,
    presentes_total     integer  NOT NULL,
    presentes_gestores  integer  NOT NULL,
    presentes_cacs      integer  NOT NULL,
    presentes_outros    integer  NOT NULL,
    distancia_polo_km   numeric(7,1),     -- linha reta entre centróides
    PRIMARY KEY (capacitacao, cod_ibge)
);

-- ---------------------------------------------------------------------------
-- Avaliação das capacitações 1 a 5 (Ótimo/Bom/Regular/Ruim e Sim/Em parte/Não)
-- ---------------------------------------------------------------------------
CREATE TABLE aval15_perguntas (
    id_pergunta smallint PRIMARY KEY,
    bloco       text NOT NULL,   -- Aspectos Gerais | Módulos | SETE | EAD | Divulgação | Sugestões | Comentários
    subgrupo    text NOT NULL,
    pergunta    text NOT NULL
);

CREATE TABLE aval15_respondentes (
    id_resposta text PRIMARY KEY,
    capacitacao smallint NOT NULL REFERENCES capacitacoes (numero),
    publico     text     NOT NULL   -- Gestores | CACS | Outros
);

CREATE TABLE aval15_respostas (
    id_resposta text     NOT NULL REFERENCES aval15_respondentes (id_resposta),
    id_pergunta smallint NOT NULL REFERENCES aval15_perguntas (id_pergunta),
    resposta    text     NOT NULL   -- categoria fechada ou texto livre
);

-- ---------------------------------------------------------------------------
-- Avaliação das capacitações 6 a 16 (notas de 1 a 5)
-- ---------------------------------------------------------------------------
CREATE TABLE aval616_perguntas (
    ordem    smallint PRIMARY KEY,
    pergunta text NOT NULL
);

CREATE TABLE aval616_respondentes (
    id_resposta         text PRIMARY KEY,
    capacitacao         smallint NOT NULL REFERENCES capacitacoes (numero),
    cod_ibge            char(7)  REFERENCES municipios (cod_ibge),
    municipio           text,
    cargo               text     NOT NULL,   -- Gestores | CACS | Outros
    instituicao         text,
    aspectos_positivos  text,
    aspectos_melhorar   text,
    temas_futuros       text,
    comentarios         text
);

CREATE TABLE aval616_notas (
    id_resposta text     NOT NULL REFERENCES aval616_respondentes (id_resposta),
    ordem       smallint NOT NULL REFERENCES aval616_perguntas (ordem),
    nota        smallint NOT NULL CHECK (nota BETWEEN 1 AND 5),
    PRIMARY KEY (id_resposta, ordem)
);

CREATE TABLE aval616_canais (
    id_resposta text NOT NULL REFERENCES aval616_respondentes (id_resposta),
    canal       text NOT NULL
);
