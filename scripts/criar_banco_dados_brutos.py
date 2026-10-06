"""
PNITE — Carga dos dados brutos do SETE no Supabase (PostgreSQL).

Cria, caso não existam, as tabelas ``dado_bruto_{entidade}`` que replicam a
estrutura dos arquivos ``data/script_XX_*_consolidado.csv`` (precedidas da
coluna ``ano_carga``) e carrega os dados via COPY.

Tipos de coluna seguem o dicionário ``data/dicionario.docx``; quando o arquivo
estiver disponível, as descrições do dicionário viram COMMENT ON COLUMN.

Regras de carga:
- ``ano_carga`` recebe o valor de ``--ano-carga`` (padrão 2026) em todas as linhas;
- a carga é idempotente: antes de inserir, remove as linhas do mesmo ano_carga;
- valores que não podem ser convertidos ao tipo da coluna (ex.: data
  "20222-09-30", latitude "string") são gravados como NULL e listados no log;
- rotas: apenas uma amostra é enviada (``--limite-rotas`` linhas e no máximo
  ``--limite-mb-rotas`` MB), pois a coluna shape (GeoJSON) soma ~1,9 GB;
- antes de cada tabela, o tamanho estimado é comparado com ``--limite-mb-banco``;
  tabelas que ultrapassariam o limite são puladas (use ``--forcar`` para ignorar).

RLS: as tabelas ficam com Row Level Security ativo e apenas o papel
``authenticated`` pode ler (SELECT) pela API REST.

Uso:
    pip install "psycopg[binary]" python-dotenv python-docx
    python scripts/criar_banco_dados_brutos.py [--tabelas rotas alunos] [--somente-estrutura]
"""

import argparse
import csv
import os
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

import psycopg
from psycopg import sql
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
PASTA_TRANSP = RAIZ / "data" / "Transporte Escolar"
PASTA_DADOS = PASTA_TRANSP if PASTA_TRANSP.is_dir() else (RAIZ / "data")
DICIONARIO = PASTA_DADOS / "dicionario.docx"

csv.field_size_limit(2**31 - 1)

SN = "char(1)"  # variáveis binárias S/N
CIDADE = [("codigo_cidade", "integer"), ("nome_cidade", "text"), ("uf", "varchar(2)"), ("estado", "text")]

# Ordem das colunas = ordem do cabeçalho de cada CSV (validada na carga).
# A lista está em ordem crescente de volume para que, se o limite de espaço for
# atingido, as tabelas menores já estejam carregadas.
TABELAS = {
    "normas": {
        "arquivo": "script_09_normas_consolidado.csv",
        "descricao": "Normas municipais de transporte escolar cadastradas no SETE.",
        "colunas": [("id", "integer"), *CIDADE, ("numero_norma", "text"), ("titulo", "text"),
                    ("data_norma", "timestamp"), ("id_tipo", "smallint"), ("tipo_veiculo", "smallint"),
                    ("outro_tipo", "text")],
        "indices": [("codigo_cidade", "id")],
    },
    "fornecedores": {
        "arquivo": "script_10_fornecedores_consolidado.csv",
        "descricao": "Fornecedores (mecânica, combustível, seguro) cadastrados no SETE.",
        "colunas": [*CIDADE, ("id_fornecedor", "integer"), ("ramo_mecanica", SN), ("ramo_combustivel", SN),
                    ("ramo_seguro", SN), ("dt_criacao", "timestamp"), ("dt_alteracao", "timestamp")],
        "indices": [("codigo_cidade", "id_fornecedor")],
    },
    "monitores": {
        "arquivo": "script_05_monitores_consolidado.csv",
        "descricao": "Monitores do transporte escolar cadastrados no SETE.",
        "colunas": [*CIDADE, ("idade", "integer"), ("sexo", "smallint"), ("vinculo", "smallint"),
                    ("salario", "numeric"), ("turno_manha", SN), ("turno_tarde", SN), ("turno_noite", SN),
                    ("loc_latitude", "double precision"), ("loc_longitude", "double precision"),
                    ("dt_criacao", "timestamp"), ("dt_alteracao", "timestamp")],
        "indices": [("codigo_cidade",)],
    },
    "rota_possui_veiculo": {
        "arquivo": "script_16_rota_possui_veiculo_consolidado.csv",
        "descricao": "Vínculo rota × veículo (chave: codigo_cidade + id_rota / id_veiculo).",
        "colunas": [("id_rota", "integer"), ("id_veiculo", "integer"), *CIDADE],
        "indices": [("codigo_cidade", "id_rota"), ("codigo_cidade", "id_veiculo")],
    },
    "rota_dirigida_por_motorista": {
        "arquivo": "script_17_rota_dirigida_por_motorista_consolidado.csv",
        "descricao": "Vínculo rota × motorista (chave: codigo_cidade + id_rota / cpf_motorista).",
        "colunas": [("id_rota", "integer"), ("cpf_motorista", "text"), *CIDADE],
        "indices": [("codigo_cidade", "id_rota")],
    },
    "motoristas": {
        "arquivo": "script_06_motoristas_consolidado.csv",
        "descricao": "Motoristas do transporte escolar cadastrados no SETE.",
        "colunas": [*CIDADE, ("idade", "integer"), ("sexo", "smallint"), ("tem_cnh_a", SN), ("tem_cnh_b", SN),
                    ("tem_cnh_c", SN), ("tem_cnh_d", SN), ("tem_cnh_e", SN), ("turno_manha", SN),
                    ("turno_tarde", SN), ("turno_noite", SN), ("data_validade_cnh", "date"),
                    ("vinculo", "smallint"), ("salario", "numeric")],
        "indices": [("codigo_cidade",)],
    },
    "veiculos": {
        "arquivo": "script_04_veiculos_consolidado.csv",
        "descricao": "Frota (veículos) do transporte escolar cadastrada no SETE.",
        "colunas": [*CIDADE, ("id_veiculo", "integer"), ("placa", "text"), ("ano", "integer"), ("modo", "smallint"),
                    ("origem", "smallint"), ("km_inicial", "numeric"), ("capacidade", "bigint"),
                    ("km_atual", "numeric"), ("tipo", "smallint"), ("renavam", "text"), ("manutencao", SN),
                    ("marca", "smallint"), ("id_firebase", "text"), ("ipva", "numeric"), ("dpvat", "numeric"),
                    ("seguro_anual", "numeric"), ("consumo", "numeric"), ("tipo_combustivel", SN),
                    ("numero_de_pneus", "integer"), ("vida_util_do_pneu", "numeric"), ("preco", "numeric"),
                    ("potencia_do_motor", "numeric"), ("modelo", "smallint"), ("outro_tipo_text", "text"),
                    ("is_state", "text"), ("historico", "text"), ("ativo", "smallint"),
                    ("dt_criacao", "timestamp"), ("criado_id", "integer"), ("dt_alteracao", "timestamp"),
                    ("alterado_id", "integer")],
        "indices": [("codigo_cidade", "id_veiculo")],
    },
    "rota_passa_por_escolas": {
        "arquivo": "script_15_rota_passa_por_escolas_consolidado.csv",
        "descricao": "Vínculo rota × escola (chave: codigo_cidade + id_rota / id_escola).",
        "colunas": [("id_rota", "integer"), ("id_escola", "integer"), *CIDADE],
        "indices": [("codigo_cidade", "id_rota"), ("codigo_cidade", "id_escola")],
    },
    "ordem_servico": {
        "arquivo": "script_11_ordem_servico_consolidado.csv",
        "descricao": "Ordens de serviço (manutenção, combustível etc.) vinculadas a veículos e fornecedores.",
        "colunas": [*CIDADE, ("id_fornecedor", "integer"), ("id_veiculo", "integer"), ("termino", SN),
                    ("data", "timestamp"), ("tipo_servico", "smallint"), ("comentario", "text"),
                    ("id_ordem", "integer"), ("id_firebase", "text"), ("is_state", "text")],
        "indices": [("codigo_cidade", "id_ordem"), ("codigo_cidade", "id_veiculo")],
    },
    "escolas": {
        "arquivo": "script_02_escolas_consolidado.csv",
        "descricao": "Escolas atendidas pelo transporte escolar cadastradas no SETE.",
        "colunas": [*CIDADE, ("id_escola", "integer"), ("nome", "text"), ("mec_co_entidade", "bigint"),
                    ("mec_co_uf", "smallint"), ("mec_co_municipio", "integer"), ("mec_no_entidade", "text"),
                    ("mec_tp_dependencia", "smallint"), ("mec_tp_localizacao", "smallint"),
                    ("mec_in_regular", SN), ("mec_in_eja", SN), ("mec_in_profissionalizante", SN),
                    ("mec_in_especial_exclusiva", SN), ("loc_latitude", "double precision"),
                    ("loc_longitude", "double precision"), ("loc_cep", "text"), ("loc_endereco", "text"),
                    ("contato_responsavel", "text"), ("contato_telefone", "text"), ("contato_email", "text"),
                    ("horario_matutino", SN), ("horario_vespertino", SN), ("horario_noturno", SN),
                    ("ensino_superior", SN), ("ensino_medio", SN), ("ensino_fundamental", SN),
                    ("ensino_pre_escola", SN), ("mec_tp_localizacao_diferenciada", "smallint"),
                    ("codigo_escola_firebase", "text"), ("alterado_por", "text"), ("dt_criacao", "timestamp"),
                    ("criado_por", "text"), ("dt_alteracao", "timestamp"), ("horario_integral", SN),
                    ("informacoes_adicionais", "jsonb"), ("nome_unidade_anexa", "text"), ("tipo_unidade", "text")],
        "indices": [("codigo_cidade", "id_escola")],
    },
    "rotas": {
        "arquivo": "script_03_rotas_consolidado.csv",
        "descricao": "Rotas do transporte escolar cadastradas no SETE (carga parcial/amostral).",
        "colunas": [*CIDADE, ("id_rota", "integer"), ("nome", "text"), ("km", "numeric"), ("da_porteira", SN),
                    ("da_mataburro", SN), ("da_colchete", SN), ("da_atoleiro", SN), ("da_ponterustica", SN),
                    ("turno_matutino", SN), ("turno_vespertino", SN), ("turno_noturno", SN), ("shape", "text"),
                    ("tempo", "numeric"), ("tipo", "smallint"), ("ativo", "smallint")],
        "indices": [("codigo_cidade", "id_rota")],
        "amostra": True,
    },
    "rota_atende_aluno": {
        "arquivo": "script_13_rota_atende_aluno_consolidado.csv",
        "descricao": "Vínculo rota × aluno (chave: codigo_cidade + id_rota / id_aluno).",
        "colunas": [("id_rota", "integer"), ("id_aluno", "integer"), *CIDADE],
        "indices": [("codigo_cidade", "id_rota"), ("codigo_cidade", "id_aluno")],
    },
    "escola_tem_aluno": {
        "arquivo": "script_12_escola_tem_aluno_consolidado.csv",
        "descricao": "Vínculo escola × aluno (chave: codigo_cidade + id_escola / id_aluno).",
        "colunas": [("id_escola", "integer"), ("id_aluno", "integer"), *CIDADE],
        "indices": [("codigo_cidade", "id_escola"), ("codigo_cidade", "id_aluno")],
    },
    "alunos": {
        "arquivo": "script_01_alunos_consolidado.csv",
        "descricao": "Alunos usuários do transporte escolar cadastrados no SETE.",
        "colunas": [*CIDADE, ("id_aluno", "integer"), ("loc_latitude", "double precision"),
                    ("loc_longitude", "double precision"), ("da_porteira", SN), ("da_mataburro", SN),
                    ("da_colchete", SN), ("da_atoleiro", SN), ("da_ponterustica", SN), ("idade", "integer"),
                    ("sexo", "smallint"), ("cor", "smallint"), ("grau_responsavel", "smallint"),
                    ("def_caminhar", SN), ("def_ouvir", SN), ("def_enxergar", SN), ("def_mental", SN),
                    ("turno", "smallint"), ("nivel", "smallint"), ("dt_criacao", "timestamp"),
                    ("dt_alteracao", "timestamp")],
        "indices": [("codigo_cidade", "id_aluno")],
    },
}

# Seções do dicionário (docx) -> tabela
SECOES_DICIONARIO = {"Escolas": "escolas", "Alunos": "alunos", "Rotas": "rotas",
                     "Veículos": "veiculos", "Motoristas": "motoristas", "Monitores": "monitores"}

# Fator empírico (tamanho no PostgreSQL ÷ tamanho do CSV), incluindo índices.
# Medido na carga de 2026: ~1,2 (escolas) a ~2,5 (tabelas de vínculo); usa-se o pior caso.
FATOR_TAMANHO = 2.5

RE_INT = re.compile(r"^-?\d+(\.0+)?$")
RE_NUM = re.compile(r"^-?(\d+(\.\d*)?|\.\d+)$")
LIMITES_INT = {"smallint": 2**15, "integer": 2**31, "bigint": 2**63}


def conversor(tipo):
    """Retorna função valor_csv -> valor_banco (None = NULL; ValueError = valor inválido)."""
    if tipo in LIMITES_INT:
        limite = LIMITES_INT[tipo]

        def f(v):
            if not RE_INT.match(v):
                raise ValueError
            n = int(v.split(".")[0])
            if not -limite <= n < limite:
                raise ValueError
            return n
        return f
    if tipo in ("numeric", "double precision"):
        def f(v):
            if RE_NUM.match(v) or v.lower() == "nan":
                return v
            raise ValueError
        return f
    if tipo == "timestamp":
        def f(v):
            return datetime.fromisoformat(v)  # ValueError para anos > 9999, mês/dia inválidos etc.
        return f
    if tipo == "date":
        def f(v):
            return date.fromisoformat(v)
        return f
    if tipo == SN or tipo.startswith("varchar"):
        tamanho = 1 if tipo == SN else int(tipo[8:-1])

        def f(v):
            if len(v) > tamanho:
                raise ValueError
            return v
        return f
    return lambda v: v  # text / jsonb (jsonb validado pelo próprio PostgreSQL)


def nome_tabela(entidade):
    return f"dado_bruto_{entidade}"


def conectar():
    load_dotenv(RAIZ / ".env")
    obrigatorias = ["DATABASE_HOST", "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD"]
    faltando = [v for v in obrigatorias if not os.getenv(v)]
    if faltando:
        sys.exit(f"Variáveis ausentes no .env: {', '.join(faltando)}")
    conn = psycopg.connect(
        host=os.environ["DATABASE_HOST"], dbname=os.environ["DATABASE_NAME"],
        user=os.environ["DATABASE_USER"], password=os.environ["DATABASE_PASSWORD"],
        port=int(os.getenv("DATABASE_PORT", "5432")), sslmode="require",
    )
    conn.execute("SET statement_timeout = 0")  # COPY de tabelas grandes excede o padrão de 2 min
    conn.commit()
    return conn


def criar_tabela(conn, entidade, cfg, ano_carga):
    tabela = sql.Identifier(nome_tabela(entidade))
    colunas = [sql.SQL("ano_carga smallint NOT NULL DEFAULT {}").format(sql.Literal(ano_carga))]
    colunas += [sql.SQL("{} {}").format(sql.Identifier(c), sql.SQL(t)) for c, t in cfg["colunas"]]
    with conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE TABLE IF NOT EXISTS public.{} ({})").format(tabela, sql.SQL(", ").join(colunas)))
        cur.execute(sql.SQL("COMMENT ON TABLE public.{} IS {}").format(tabela, sql.Literal(
            f"Dado bruto do SETE — {cfg['descricao']} Fonte: data/{cfg['arquivo']}.")))
        cur.execute(sql.SQL("COMMENT ON COLUMN public.{}.ano_carga IS {}").format(
            tabela, sql.Literal("Ano de referência da carga do dado.")))
        for i, cols in enumerate(cfg["indices"]):
            cur.execute(sql.SQL("CREATE INDEX IF NOT EXISTS {} ON public.{} (ano_carga, {})").format(
                sql.Identifier(f"idx_{nome_tabela(entidade)}_{i}"), tabela,
                sql.SQL(", ").join(map(sql.Identifier, cols))))
        if any(c == "shape" for c, _ in cfg["colunas"]):
            cur.execute(sql.SQL("ALTER TABLE public.{} ALTER COLUMN shape SET COMPRESSION lz4").format(tabela))
        # Acesso via API REST: somente usuários autenticados, somente leitura.
        cur.execute(sql.SQL("ALTER TABLE public.{} ENABLE ROW LEVEL SECURITY").format(tabela))
        cur.execute(sql.SQL("REVOKE ALL ON public.{} FROM anon, authenticated").format(tabela))
        cur.execute(sql.SQL("GRANT SELECT ON public.{} TO authenticated").format(tabela))
        cur.execute(sql.SQL("DROP POLICY IF EXISTS leitura_autenticada ON public.{}").format(tabela))
        cur.execute(sql.SQL("CREATE POLICY leitura_autenticada ON public.{} FOR SELECT TO authenticated USING (true)")
                    .format(tabela))
    conn.commit()


def ler_dicionario():
    """Lê data/dicionario.docx -> {tabela: {coluna: descrição}}. Retorna {} se indisponível."""
    try:
        import docx
        from docx.oxml.ns import qn
    except ImportError:
        print("  [aviso] python-docx não instalado; comentários do dicionário não aplicados.")
        return {}
    if not DICIONARIO.exists():
        return {}
    doc = docx.Document(DICIONARIO)
    resultado, secao, idx_tabela = {}, None, 0
    for el in doc.element.body.iterchildren():
        if el.tag == qn("w:p"):
            texto = "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()
            if texto in SECOES_DICIONARIO:
                secao = SECOES_DICIONARIO[texto]
        elif el.tag == qn("w:tbl"):
            tabela_doc = doc.tables[idx_tabela]
            idx_tabela += 1
            if secao:
                for linha in tabela_doc.rows[1:]:
                    celulas = [c.text.strip() for c in linha.cells]
                    if len(celulas) >= 3 and celulas[0]:
                        resultado.setdefault(secao, {})[celulas[0]] = " ".join(celulas[2].split())
    return resultado


def aplicar_comentarios(conn, dicionario):
    with conn.cursor() as cur:
        for entidade, descricoes in dicionario.items():
            colunas = {c for c, _ in TABELAS[entidade]["colunas"]}
            for coluna, texto in descricoes.items():
                if coluna in colunas:
                    cur.execute(sql.SQL("COMMENT ON COLUMN public.{}.{} IS {}").format(
                        sql.Identifier(nome_tabela(entidade)), sql.Identifier(coluna), sql.Literal(texto)))
    conn.commit()


def tamanho_banco_mb(conn):
    return conn.execute("SELECT pg_database_size(current_database())").fetchone()[0] / 2**20


def carregar_tabela(conn, entidade, cfg, args):
    caminho = PASTA_DADOS / cfg["arquivo"]
    nomes = [c for c, _ in cfg["colunas"]]
    conversores = [conversor(t) for _, t in cfg["colunas"]]
    amostra = cfg.get("amostra", False)
    limite_linhas = args.limite_rotas if amostra else None
    limite_bytes = args.limite_mb_rotas * 2**20 if amostra else None

    tabela = sql.Identifier(nome_tabela(entidade))
    copy_sql = sql.SQL("COPY public.{} ({}) FROM STDIN").format(
        tabela, sql.SQL(", ").join(map(sql.Identifier, ["ano_carga", *nomes])))

    linhas, bytes_lidos, invalidos = 0, 0, []
    inicio = time.time()
    with open(caminho, encoding="utf-8-sig", newline="") as fh, conn.cursor() as cur:
        leitor = csv.reader(fh)
        cabecalho = next(leitor)
        if cabecalho != nomes:
            raise RuntimeError(f"Cabeçalho de {cfg['arquivo']} difere da estrutura esperada:\n"
                               f"  CSV:      {cabecalho}\n  esperado: {nomes}")
        cur.execute(sql.SQL("DELETE FROM public.{} WHERE ano_carga = %s").format(tabela), (args.ano_carga,))
        with cur.copy(copy_sql) as copia:
            for registro in leitor:
                tamanho = sum(len(v) for v in registro)
                if limite_bytes and linhas and bytes_lidos + tamanho > limite_bytes:
                    continue  # amostra: pula rotas que estourariam o limite de MB
                valores = [args.ano_carga]
                for nome, conv, v in zip(nomes, conversores, registro):
                    if v == "":
                        valores.append(None)
                        continue
                    try:
                        valores.append(conv(v))
                    except ValueError:
                        valores.append(None)
                        invalidos.append((linhas + 2, nome, v[:60]))
                copia.write_row(valores)
                linhas += 1
                bytes_lidos += tamanho
                if limite_linhas and linhas >= limite_linhas:
                    break
                if linhas % 500_000 == 0:
                    print(f"    ... {linhas:,} linhas", flush=True)
    conn.commit()
    with conn.cursor() as cur:
        cur.execute(sql.SQL("ANALYZE public.{}").format(tabela))
    conn.commit()

    print(f"  {nome_tabela(entidade)}: {linhas:,} linhas em {time.time() - inicio:.0f}s"
          + (f" (amostra, {bytes_lidos / 2**20:.1f} MB de dados)" if amostra else ""))
    for linha, coluna, valor in invalidos[:20]:
        print(f"    [NULL] linha {linha}, {coluna} = {valor!r} (valor inválido para o tipo)")
    if len(invalidos) > 20:
        print(f"    ... e mais {len(invalidos) - 20} valores inválidos convertidos em NULL")
    return linhas


def main():
    p = argparse.ArgumentParser(description="Cria e carrega as tabelas dado_bruto_* no Supabase.")
    p.add_argument("--tabelas", nargs="*", choices=list(TABELAS), help="entidades a processar (padrão: todas)")
    p.add_argument("--ano-carga", type=int, default=2026)
    p.add_argument("--limite-rotas", type=int, default=2000, help="nº máximo de rotas enviadas (amostra)")
    p.add_argument("--limite-mb-rotas", type=float, default=50, help="volume máximo (MB de CSV) de rotas enviadas")
    p.add_argument("--limite-mb-banco", type=float, default=float(os.getenv("SUPABASE_LIMITE_MB", 480)),
                   help="tamanho máximo do banco; tabelas que o excederiam são puladas")
    p.add_argument("--forcar", action="store_true", help="ignora o limite de tamanho do banco")
    p.add_argument("--somente-estrutura", action="store_true", help="apenas cria as tabelas, sem carga")
    args = p.parse_args()

    entidades = args.tabelas or list(TABELAS)
    conn = conectar()
    print(f"Conectado. Tamanho atual do banco: {tamanho_banco_mb(conn):.0f} MB")

    print("Criando tabelas (se não existirem)...")
    for entidade in entidades:
        criar_tabela(conn, entidade, TABELAS[entidade], args.ano_carga)
    aplicar_comentarios(conn, {k: v for k, v in ler_dicionario().items() if k in entidades})
    conn.execute("NOTIFY pgrst, 'reload schema'")  # atualiza o cache de esquema da API REST
    conn.commit()
    if args.somente_estrutura:
        return

    puladas = []
    for entidade in entidades:
        cfg = TABELAS[entidade]
        mb_csv = (PASTA_DADOS / cfg["arquivo"]).stat().st_size / 2**20
        if cfg.get("amostra"):
            mb_csv = min(mb_csv, args.limite_mb_rotas)
        atual = tamanho_banco_mb(conn)
        estimado = atual + mb_csv * FATOR_TAMANHO
        if not args.forcar and estimado > args.limite_mb_banco:
            print(f"  [PULADA] {nome_tabela(entidade)}: estimativa {estimado:.0f} MB > limite "
                  f"{args.limite_mb_banco:.0f} MB (atual {atual:.0f} MB)")
            puladas.append(entidade)
            continue
        carregar_tabela(conn, entidade, cfg, args)

    print(f"Concluído. Tamanho final do banco: {tamanho_banco_mb(conn):.0f} MB")
    if puladas:
        print("Tabelas criadas mas não carregadas (limite de espaço): " + ", ".join(puladas))
    conn.close()


if __name__ == "__main__":
    main()
