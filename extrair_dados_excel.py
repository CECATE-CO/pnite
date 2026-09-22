"""
Script de Extração e Consolidação de Dados das Planilhas Excel da PNITE
PNITE — Plataforma Nacional de Inteligência em Transporte Escolar

Este script realiza a leitura automatizada de todas as planilhas Excel consolidadas
armazenadas na pasta 'data/' (com o prefixo 'consolidado XX - script_XX_*.xlsx'),
consolida os indicadores estaduais, regionais e nacionais, e exporta os resultados
para:
  1) data/pnite_dados_consolidados.json (para consumo via APIs ou fetch)
  2) data/pnite_dados_consolidados.js   (objeto window.PNITE_EXCEL_DATA para acesso direto)
"""

import os
import sys
import glob
import json
import re
import unicodedata
import pandas as pd
import numpy as np
from datetime import datetime

# Assegura suporte a utf-8 no console Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


# Mapeamento de nomes de estado para sigla (UF)
UF_SIGLA_MAP = {
    'acre': 'ac', 'alagoas': 'al', 'amapa': 'ap', 'amazonas': 'am', 'bahia': 'ba',
    'ceara': 'ce', 'distrito federal': 'df', 'espirito santo': 'es', 'goias': 'go',
    'maranhao': 'ma', 'mato grosso': 'mt', 'mato grosso do sul': 'ms', 'minas gerais': 'mg',
    'para': 'pa', 'paraiba': 'pb', 'parana': 'pr', 'pernambuco': 'pe', 'piaui': 'pi',
    'rio de janeiro': 'rj', 'rio grande do norte': 'rn', 'rio grande do sul': 'rs',
    'rondonia': 'ro', 'roraima': 'rr', 'santa catarina': 'sc', 'sao paulo': 'sp',
    'sergipe': 'se', 'tocantins': 'to', 'brasil': 'nacional', 'total': 'nacional',
    'total geral': 'nacional'
}

UF_LABELS = {
    'ac': 'Acre', 'al': 'Alagoas', 'ap': 'Amapá', 'am': 'Amazonas', 'ba': 'Bahia',
    'ce': 'Ceará', 'df': 'Distrito Federal', 'es': 'Espírito Santo', 'go': 'Goiás',
    'ma': 'Maranhão', 'mt': 'Mato Grosso', 'ms': 'Mato Grosso do Sul', 'mg': 'Minas Gerais',
    'pa': 'Pará', 'pb': 'Paraíba', 'pr': 'Paraná', 'pe': 'Pernambuco', 'pi': 'Piauí',
    'rj': 'Rio de Janeiro', 'rn': 'Rio Grande do Norte', 'rs': 'Rio Grande do Sul',
    'ro': 'Rondônia', 'rr': 'Roraima', 'sc': 'Santa Catarina', 'sp': 'São Paulo',
    'se': 'Sergipe', 'to': 'Tocantins', 'nacional': 'Brasil'
}

REGIOES = {
    'norte': ['ac', 'ap', 'am', 'pa', 'ro', 'rr', 'to'],
    'nordeste': ['al', 'ba', 'ce', 'ma', 'pb', 'pe', 'pi', 'rn', 'se'],
    'sudeste': ['es', 'mg', 'rj', 'sp'],
    'sul': ['pr', 'rs', 'sc'],
    'centro-oeste': ['df', 'go', 'mt', 'ms']
}

REGIAO_LABELS = {
    'norte': 'Norte',
    'nordeste': 'Nordeste',
    'sudeste': 'Sudeste',
    'sul': 'Sul',
    'centro-oeste': 'Centro-Oeste'
}

def normalizar_texto(texto):
    """Remove acentuação e converte para minúsculas para correspondência segura."""
    if not isinstance(texto, str):
        return ''
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = u"".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.strip().lower()

def carregar_planilhas(data_dir='data'):
    """Lê todas as planilhas consolidadas na pasta especificada."""
    padrao = os.path.join(data_dir, 'consolidado *.xlsx')
    arquivos = sorted(glob.glob(padrao))
    if not arquivos:
        # Tenta também caso ainda haja nomes legados
        arquivos = sorted(glob.glob(os.path.join(data_dir, '*Consolida*.xlsx')))
    
    print(f"Encontrados {len(arquivos)} arquivos Excel para processar em '{data_dir}'.")
    tabelas = {}
    for caminho in arquivos:
        nome_base = os.path.basename(caminho)
        # Extrai o identificador do script, ex.: script_01_alunos
        partes = nome_base.split(' - ')
        chave = partes[1].replace('.xlsx', '').strip() if len(partes) > 1 else nome_base.replace('.xlsx', '')
        try:
            df = pd.read_excel(caminho)
            tabelas[chave] = {
                'arquivo': nome_base,
                'df': df
            }
            print(f"  [OK] {nome_base} ({len(df)} registros)")
        except Exception as e:
            print(f"  [ERRO] Falha ao ler {nome_base}: {e}")
            
    return tabelas

def extrair_metricas_por_uf(tabelas):
    """Extrai e calcula as variáveis por UF a partir das tabelas carregadas."""
    dados_uf = {uf: {} for uf in list(UF_LABELS.keys())}
    detalhes_scripts = {uf: {} for uf in list(UF_LABELS.keys())}

    for chave, tab in tabelas.items():
        df = tab['df']
        if 'estado' not in df.columns:
            continue
        
        for _, row in df.iterrows():
            est_norm = normalizar_texto(str(row['estado']))
            uf = UF_SIGLA_MAP.get(est_norm)
            if not uf or uf not in dados_uf:
                continue
            
            # Salva o registro detalhado por script
            detalhe = {}
            for col in df.columns:
                if col != 'estado':
                    val = row[col]
                    if pd.isna(val):
                        detalhe[col] = None
                    elif isinstance(val, (int, float, bool)):
                        detalhe[col] = int(val) if isinstance(val, float) and val.is_integer() else round(val, 2)
                    else:
                        detalhe[col] = str(val)
            detalhes_scripts[uf][chave] = detalhe

    return detalhes_scripts


def processar_alunos_pcd(data_dir='data'):
    """
    Processa script_01_alunos_consolidado.csv para calcular o indicador PAD:
    Alunos com Defici?ncia Atendidos pelo Transporte Escolar.
    Crit?rio: def_caminhar, def_ouvir, def_enxergar, def_mental == 'S'
    Contagem ?nica por aluno (se tiver m?ltiplas defici?ncias, conta apenas uma vez).
    Gera estat?sticas por Cidade, Estado, Regi?o e Brasil.
    """
    csv_path = os.path.join(data_dir, 'script_01_alunos_consolidado.csv')
    if not os.path.exists(csv_path):
        print(f"  [AVISO] Arquivo '{csv_path}' n?o encontrado para c?lculo de PCD.")
        return None
        
    print(f"  [INFO] Processando alunos com defici?ncia em '{csv_path}'...")
    cols = ['codigo_cidade', 'uf', 'def_caminhar', 'def_ouvir', 'def_enxergar', 'def_mental']
    
    total_br = 0
    pcd_br = 0
    est_tot = {}
    est_pcd = {}
    mun_tot = {}
    mun_pcd = {}
    
    chunksize = 500000
    for chunk in pd.read_csv(csv_path, usecols=cols, chunksize=chunksize, dtype=str):
        has_def = (chunk['def_caminhar'].str.upper() == 'S') | \
                  (chunk['def_ouvir'].str.upper() == 'S') | \
                  (chunk['def_enxergar'].str.upper() == 'S') | \
                  (chunk['def_mental'].str.upper() == 'S')
        
        total_br += len(chunk)
        pcd_br += int(has_def.sum())
        
        for uf, g in chunk.groupby('uf'):
            s = str(uf).lower().strip()
            est_tot[s] = est_tot.get(s, 0) + len(g)
            est_pcd[s] = est_pcd.get(s, 0) + int(has_def.loc[g.index].sum())
            
        for cod, g in chunk.groupby('codigo_cidade'):
            c = str(cod).strip()
            mun_tot[c] = mun_tot.get(c, 0) + len(g)
            mun_pcd[c] = mun_pcd.get(c, 0) + int(has_def.loc[g.index].sum())
            
    pct_br = round((pcd_br / total_br) * 100, 2) if total_br > 0 else 0.0
    print(f"  [OK] PCD Nacional: {pcd_br:,} de {total_br:,} alunos ({pct_br}%).")
    
    return {
        'total_br': total_br,
        'pcd_br': pcd_br,
        'pad_br': pct_br,
        'est_tot': est_tot,
        'est_pcd': est_pcd,
        'mun_tot': mun_tot,
        'mun_pcd': mun_pcd
    }

def extrair_e_consolidar_tudo(data_dir='data', html_ref=None):
    """
    Executa a extração completa dos Excels e compõe a base RAW_DATA e DATA.
    Se html_ref for fornecido, complementa com os campos de censo e recalcula os indicadores.
    """
    tabelas = carregar_planilhas(data_dir)
    dados_pcd = processar_alunos_pcd(data_dir)
    detalhes_por_uf = extrair_metricas_por_uf(tabelas)

    # Obter dados de base de referência (para indicadores do Censo/Metodológicos já consolidados)
    ref_raw = {}
    ref_data = {}
    
    # Procura arquivo HTML de referência na raiz ou em old/
    arquivos_html = glob.glob('PNITE [V.*].html') + glob.glob('old/PNITE [V.*].html')
    if arquivos_html:
        html_alvo = arquivos_html[0]
        try:
            with open(html_alvo, 'r', encoding='utf-8', errors='replace') as f:
                conteudo = f.read()
            m_raw = re.search(r'const RAW_DATA\s*=\s*(\{.*?\});\n', conteudo)
            if m_raw:
                ref_raw = json.loads(m_raw.group(1))
            m_data = re.search(r'const DATA\s*=\s*(\{.*?\});\n', conteudo)
            if m_data:
                ref_data = json.loads(m_data.group(1))
            print(f"Base de inteligência de referência carregada de '{html_alvo}'.")
        except Exception as e:
            print(f"Aviso ao carregar referência do HTML: {e}")

    # Mescla as variáveis dos Excels atualizados sobre a base
    raw_data_unificada = {}
    
    # Prepara todos os nós: nacional + 27 UFs + 5 regiões
    todos_nos = list(UF_LABELS.keys()) + list(REGIOES.keys())
    for no in todos_nos:
        raw_data_unificada[no] = {}
        if no in ref_raw:
            raw_data_unificada[no].update(ref_raw[no])
            
    # Aplica os dados diretos dos Excels para as UFs e Nacional
    for uf, scripts in detalhes_por_uf.items():
        node = raw_data_unificada.setdefault(uf, {})
        
        # script_01_alunos
        if 'script_01_alunos' in scripts:
            s1 = scripts['script_01_alunos']
            if s1.get('total_alunos') is not None:
                node['al_cad'] = s1['total_alunos']
        
        # script_03_rotas
        if 'script_03_rotas' in scripts:
            s3 = scripts['script_03_rotas']
            if s3.get('total_rotas') is not None:
                node['tot_rotas'] = s3['total_rotas']
            if s3.get('com_georreferenciamento') is not None:
                node['georref'] = s3['com_georreferenciamento']
            if s3.get('rodoviaria') is not None:
                node['t1'] = s3['rodoviaria']
            if s3.get('aquaviaria') is not None:
                node['t2'] = s3['aquaviaria']
            if s3.get('mista') is not None:
                node['t3'] = s3['mista']
                
        # script_04_veiculos
        if 'script_04_veiculos' in scripts:
            s4 = scripts['script_04_veiculos']
            if s4.get('total_veiculos') is not None:
                node['tot_veic'] = s4['total_veiculos']
            if s4.get('proprio') is not None:
                node['vp'] = s4['proprio']
            if s4.get('terceirizado') is not None:
                node['vt'] = s4['terceirizado']
            if s4.get('caminho_da_escola_total') is not None:
                node['ce_veic'] = s4['caminho_da_escola_total']

        # script_05_monitores
        if 'script_05_monitores' in scripts:
            s5 = scripts['script_05_monitores']
            if s5.get('total_monitores') is not None:
                node['tot_mon'] = s5['total_monitores']
            efetivo = s5.get('servidor_efetivo') or 0
            comiss = s5.get('servidor_comissionado') or 0
            if s5.get('servidor_efetivo') is not None or s5.get('servidor_comissionado') is not None:
                node['mon_cv'] = efetivo + comiss

        # script_06_motoristas
        if 'script_06_motoristas' in scripts:
            s6 = scripts['script_06_motoristas']
            if s6.get('total_motoristas') is not None:
                node['tot_mot_info'] = s6['total_motoristas']
            efetivo = s6.get('servidor_efetivo') or 0
            comiss = s6.get('servidor_comissionado') or 0
            if s6.get('servidor_efetivo') is not None or s6.get('servidor_comissionado') is not None:
                node['mot_cv'] = efetivo + comiss

        # script_13_rota_atende_aluno
        if 'script_13_rota_atende_aluno' in scripts:
            s13 = scripts['script_13_rota_atende_aluno']
            if s13.get('total_alunos_distintos') is not None:
                node['al_transp'] = s13['total_alunos_distintos']

        # script_15_rota_passa_por_escolas
        if 'script_15_rota_passa_por_escolas' in scripts:
            s15 = scripts['script_15_rota_passa_por_escolas']
            if s15.get('total_escolas_distintas') is not None:
                node['esc_at'] = s15['total_escolas_distintas']

    # Recalcular agregados das Macrorregiões a partir dos estados
    campos_soma = [
        'tot_rotas', 'georref', 'dif', 't1', 't2', 't3', 'tot_veic', 'vp', 'vt',
        'n_veic_validos', 'tot_mon', 'mon_cv', 'tot_mot_info', 'mot_cv',
        'al_cad', 'al_transp', 'esc_at', 'al_adeq', 'al_transp_teti',
        'cs_mat', 'cs_transp', 'cs_test', 'cs_tmun', 'cs_esc_ativas', 'cs_esc_transp',
        'sete_esc', 'ce_veic', 'veic_adeq_idade', 'tot_veic_ano', 'al_pcd',
        'al_dif', 'al_hidro', 'al_hidro_dif'
    ]

    for reg, ufs in REGIOES.items():
        reg_node = raw_data_unificada.setdefault(reg, {})
        for campo in campos_soma:
            valores = [raw_data_unificada[u].get(campo) for u in ufs if raw_data_unificada[u].get(campo) is not None]
            if valores:
                reg_node[campo] = sum(valores)

    # Calcular DATA a partir de RAW_DATA
    def calcular_indicadores(r, label):
        def pct(a, b):
            return round((a / b) * 100, 2) if b and b > 0 and a is not None else None
        
        tr = r.get('tot_rotas')
        tv = r.get('tot_veic')
        nvv = r.get('n_veic_validos')
        cap_m = r.get('cap_media')
        at = r.get('al_transp')
        ea = r.get('esc_at')
        tm = r.get('tot_mon')
        tmi = r.get('tot_mot_info')
        tva_val = r.get('tva')
        
        iuc = None
        if at and nvv and cap_m and (nvv * cap_m) > 0:
            iuc = round(at / (nvv * cap_m), 2)
            
        ate = round(at / ea, 2) if (at and ea and ea > 0) else None

        return {
            'label': label,
            'PRGM': pct(r.get('georref'), tr),
            'PRDAM': pct(r.get('dif'), tr),
            'PRRM': pct(r.get('t1'), tr),
            'PRHM': pct(r.get('t2'), tr),
            'PRMM': pct(r.get('t3'), tr),
            'PVP': pct(r.get('vp'), tv),
            'PVT': pct(r.get('vt'), tv),
            'PVPCE': pct(r.get('ce_veic'), tv),
            'PECS': pct(r.get('sete_esc'), r.get('cs_esc_transp')),
            'IUC': iuc,
            'MON_CVE': pct(r.get('mon_cv'), tm),
            'MOT_CVE': pct(r.get('mot_cv'), tmi),
            'PRPM': None,
            'ATE': ate,
            'TETI': pct(r.get('al_adeq'), r.get('al_transp_teti') or at),
            'IPE': None,
            'TEDC': pct(at, r.get('al_cad')),
            'PATM': pct(r.get('cs_tmun'), r.get('cs_transp')),
            'PATE': pct(r.get('cs_test'), r.get('cs_transp')),
            'IPTE': round(r.get('cs_test') / r.get('cs_transp'), 3) if (r.get('cs_test') and r.get('cs_transp')) else None,
            'MEDATE': r.get('medate_val'),
            'ICA': None,
            'IMFP': r.get('imfp'),
            'IMFT': r.get('imft'),
            'MIFCE': r.get('mifce'),
            'PAFI': pct(r.get('veic_adeq_idade'), r.get('tot_veic_ano')) or r.get('pafi'),
            'PAD': pct(r.get('al_pcd'), at),
            'PARI': pct(r.get('al_dif'), at),
            'PAIH': pct(r.get('al_hidro_dif'), r.get('al_hidro')),
            'TVA': tva_val
        }

    data_calculada = {
        'nacional': calcular_indicadores(raw_data_unificada.get('nacional', {}), 'Brasil'),
        'regiao': {},
        'estado': {}
    }

    for reg, lbl in REGIAO_LABELS.items():
        data_calculada['regiao'][reg] = calcular_indicadores(raw_data_unificada.get(reg, {}), lbl)

    for uf, lbl in UF_LABELS.items():
        if uf != 'nacional':
            data_calculada['estado'][uf] = calcular_indicadores(raw_data_unificada.get(uf, {}), lbl)


    # Injetar dados calculados de PCD (script_01_alunos_consolidado.csv)
    if dados_pcd:
        raw_data_unificada['nacional']['al_pcd'] = dados_pcd['pcd_br']
        for s, pcd_val in dados_pcd['est_pcd'].items():
            if s in raw_data_unificada:
                raw_data_unificada[s]['al_pcd'] = pcd_val
                
        # Atualizar PAD nos estados e nacional
        data_calculada['nacional']['PAD'] = dados_pcd['pad_br']
        for s, pcd_val in dados_pcd['est_pcd'].items():
            tot_s = dados_pcd['est_tot'].get(s, 0)
            if s in data_calculada['estado']:
                data_calculada['estado'][s]['PAD'] = round((pcd_val / tot_s) * 100, 2) if tot_s > 0 else 0.0
                
        # Atualizar PAD nas macrorregi?es
        for reg, ufs in REGIOES.items():
            reg_pcd = sum(dados_pcd['est_pcd'].get(u, 0) for u in ufs)
            reg_tot = sum(dados_pcd['est_tot'].get(u, 0) for u in ufs)
            raw_data_unificada[reg]['al_pcd'] = reg_pcd
            if reg in data_calculada['regiao']:
                data_calculada['regiao'][reg]['PAD'] = round((reg_pcd / reg_tot) * 100, 2) if reg_tot > 0 else 0.0

    # Monta a estrutura final do pacote consolidado
    pacote_consolidado = {
        'metadados': {
            'data_extracao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'origem': 'Planilhas Excel da pasta data/',
            'total_planilhas_lidas': len(tabelas),
            'arquivos_processados': [t['arquivo'] for t in tabelas.values()]
        },
        'RAW_DATA': raw_data_unificada,
        'DATA': data_calculada,
        'detalhes_scripts': detalhes_por_uf,
        'municipios_pcd': {c: {'pcd': dados_pcd['mun_pcd'].get(c, 0), 'total': dados_pcd['mun_tot'].get(c, 0), 'PAD': round(dados_pcd['mun_pcd'].get(c, 0) / dados_pcd['mun_tot'].get(c, 0) * 100, 2) if dados_pcd['mun_tot'].get(c, 0) > 0 else None} for c in dados_pcd['mun_pcd']} if dados_pcd else {}
    }

    # Salva em formato JSON
    json_path = os.path.join(data_dir, 'pnite_dados_consolidados.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(pacote_consolidado, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Arquivo JSON exportado com sucesso: '{json_path}' ({os.path.getsize(json_path)//1024} KB)")

    # Salva em formato JS para inclusão direta
    js_path = os.path.join(data_dir, 'pnite_dados_consolidados.js')
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write("/**\n * Dados Consolidados da PNITE extraídos das planilhas Excel em data/\n")
        f.write(f" * Gerado automaticamente em: {pacote_consolidado['metadados']['data_extracao']}\n */\n")
        f.write("window.PNITE_EXCEL_DATA = ")
        json.dump(pacote_consolidado, f, ensure_ascii=False, separators=(',', ':'))
        f.write(";\n")
    print(f"  [OK] Arquivo JS exportado com sucesso: '{js_path}' ({os.path.getsize(js_path)//1024} KB)")

    return pacote_consolidado

if __name__ == '__main__':
    print("=" * 60)
    print("PNITE — Processamento e Extração de Dados das Planilhas Excel")
    print("=" * 60)
    resultado = extrair_e_consolidar_tudo()
    print("\nExtração finalizada com total sucesso!")
