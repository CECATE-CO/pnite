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
        arquivos = sorted(glob.glob(os.path.join(data_dir, '*Consolida*.xlsx')))
    
    print(f"Encontrados {len(arquivos)} arquivos Excel para processar em '{data_dir}'.")
    tabelas = {}
    for caminho in arquivos:
        nome_base = os.path.basename(caminho)
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
    Alunos com Deficiência Atendidos pelo Transporte Escolar.
    Critério: def_caminhar, def_ouvir, def_enxergar, def_mental == 'S'
    Contagem única por aluno (se tiver múltiplas deficiências, conta apenas uma vez).
    Gera estatísticas por Cidade, Estado, Região e Brasil.
    """
    csv_path = os.path.join(data_dir, 'script_01_alunos_consolidado.csv')
    if not os.path.exists(csv_path):
        print(f"  [AVISO] Arquivo '{csv_path}' não encontrado para cálculo de PCD.")
        return None
        
    print(f"  [INFO] Processando alunos com deficiência em '{csv_path}'...")
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

def processar_rotas_prgm(data_dir='data'):
    """
    Processa script_03_rotas_consolidado.csv para calcular:
      1) PRGM: Percentual de Rotas Georreferenciadas e Distâncias da Malha (km)
      2) PRIO: Percentual de Rotas com Impedância Operacional (porteiras, mata-burros, colchetes, atoleiros, pontes)
      3) Tempo de Viagem: média e mediana do tempo operacional por rota
    Computa por Cidade, Estado, Região e Brasil.
    """
    csv_path = os.path.join(data_dir, 'script_03_rotas_consolidado.csv')
    if not os.path.exists(csv_path):
        print(f"  [AVISO] Arquivo '{csv_path}' não encontrado para cálculo de rotas.")
        return None

    print(f"  [INFO] Processando rotas, georreferenciamento, impedâncias e tempos em '{csv_path}'...")
    cols = ['codigo_cidade', 'uf', 'km', 'shape', 'da_porteira', 'da_mataburro', 'da_colchete', 'da_atoleiro', 'da_ponterustica', 'tempo']
    
    tot_br = 0
    geo_br = 0
    imped_br = 0
    km_tot_br = 0.0
    km_geo_br = 0.0
    tempos_br = []
    
    uf_rotas = {}
    mun_rotas = {}
    
    chunksize = 50000
    for chunk in pd.read_csv(csv_path, usecols=cols, chunksize=chunksize, dtype=str):
        has_shape = chunk['shape'].notna() & (chunk['shape'].str.strip() != '') & (chunk['shape'].str.upper() != 'NULL')
        km_vals = pd.to_numeric(chunk['km'].str.replace(',', '.'), errors='coerce').fillna(0.0)
        
        p = (chunk['da_porteira'].str.upper() == 'S')
        m = (chunk['da_mataburro'].str.upper() == 'S')
        c = (chunk['da_colchete'].str.upper() == 'S')
        a = (chunk['da_atoleiro'].str.upper() == 'S')
        pr = (chunk['da_ponterustica'].str.upper() == 'S')
        has_imped = p | m | c | a | pr
        
        t_num = pd.to_numeric(chunk['tempo'].str.replace(',', '.'), errors='coerce')
        t_valid = t_num[(t_num >= 1) & (t_num <= 360)]
        tempos_br.extend(t_valid.tolist()[:500])
        
        tot_br += len(chunk)
        geo_br += int(has_shape.sum())
        imped_br += int(has_imped.sum())
        km_tot_br += float(km_vals.sum())
        km_geo_br += float(km_vals[has_shape].sum())
        
        for uf, g in chunk.groupby('uf'):
            s = str(uf).lower().strip()
            if s not in uf_rotas:
                uf_rotas[s] = {'rotas': 0, 'geo': 0, 'imped': 0, 'km': 0.0, 'km_geo': 0.0, 'tempos': []}
            u = uf_rotas[s]
            u['rotas'] += len(g)
            u['geo'] += int(has_shape.loc[g.index].sum())
            u['imped'] += int(has_imped.loc[g.index].sum())
            u['km'] += float(km_vals.loc[g.index].sum())
            u['km_geo'] += float(km_vals.loc[g.index[has_shape.loc[g.index]]].sum())
            t_uf_valid = t_num.loc[g.index][(t_num.loc[g.index] >= 1) & (t_num.loc[g.index] <= 360)]
            if len(t_uf_valid) > 0:
                u['tempos'].extend(t_uf_valid.tolist()[:300])
            
        for cod, g in chunk.groupby('codigo_cidade'):
            cd = str(cod).strip()
            if cd not in mun_rotas:
                mun_rotas[cd] = {'rotas': 0, 'geo': 0, 'imped': 0, 'porteira': 0, 'mataburro': 0, 'colchete': 0, 'atoleiro': 0, 'ponte': 0, 'km': 0.0, 'km_geo': 0.0, 'tempos': []}
            mr = mun_rotas[cd]
            mr['rotas'] += len(g)
            mr['geo'] += int(has_shape.loc[g.index].sum())
            mr['imped'] += int(has_imped.loc[g.index].sum())
            mr['porteira'] += int(p.loc[g.index].sum())
            mr['mataburro'] += int(m.loc[g.index].sum())
            mr['colchete'] += int(c.loc[g.index].sum())
            mr['atoleiro'] += int(a.loc[g.index].sum())
            mr['ponte'] += int(pr.loc[g.index].sum())
            mr['km'] += float(km_vals.loc[g.index].sum())
            mr['km_geo'] += float(km_vals.loc[g.index[has_shape.loc[g.index]]].sum())
            t_mun_valid = t_num.loc[g.index][(t_num.loc[g.index] >= 1) & (t_num.loc[g.index] <= 360)]
            if len(t_mun_valid) > 0:
                mr['tempos'].extend(t_mun_valid.tolist())

    prgm_br = round((geo_br / tot_br) * 100, 2) if tot_br > 0 else 0.0
    prio_br = round((imped_br / tot_br) * 100, 2) if tot_br > 0 else 0.0
    med_tempo_br = round(float(np.median(tempos_br)), 1) if tempos_br else 60.0
    
    print(f"  [OK] Rotas Nacional: {tot_br:,} total | PRGM: {geo_br:,} ({prgm_br}%) | PRIO: {imped_br:,} ({prio_br}%) | Extensão: {km_tot_br:,.1f} km | Tempo mediano: {med_tempo_br} min.")
    
    # Formatar dados municipais
    mun_formatado = {}
    for c, d in mun_rotas.items():
        r = d['rotas']
        g = d['geo']
        imp = d['imped']
        k = round(d['km'], 1)
        kg = round(d['km_geo'], 1)
        prgm = round((g / r) * 100, 2) if r > 0 else 0.0
        prio = round((imp / r) * 100, 2) if r > 0 else 0.0
        km_med = round(k / r, 1) if r > 0 else 0.0
        t_arr = d['tempos']
        t_med = round(float(np.median(t_arr)), 1) if t_arr else None
        t_avg = round(float(np.mean(t_arr)), 1) if t_arr else None
        
        mun_formatado[c] = {
            'rotas': r,
            'geo': g,
            'PRGM': prgm,
            'imped': imp,
            'PRIO': prio,
            'porteira': d['porteira'],
            'mataburro': d['mataburro'],
            'colchete': d['colchete'],
            'atoleiro': d['atoleiro'],
            'ponte': d['ponte'],
            'km_total': k,
            'km_geo': kg,
            'km_medio': km_med,
            'tempo_mediano': t_med,
            'tempo_medio': t_avg,
            'has_geo': g > 0,
            'has_imped': imp > 0
        }
        
    return {
        'tot_br': tot_br,
        'geo_br': geo_br,
        'prgm_br': prgm_br,
        'imped_br': imped_br,
        'prio_br': prio_br,
        'km_tot_br': round(km_tot_br, 1),
        'km_geo_br': round(km_geo_br, 1),
        'tempo_med_br': med_tempo_br,
        'uf_rotas': uf_rotas,
        'municipios_rotas': mun_formatado
    }

def extrair_e_consolidar_tudo(data_dir='data', html_ref=None):
    """
    Executa a extração completa dos Excels e compõe a base RAW_DATA e DATA.
    """
    tabelas = carregar_planilhas(data_dir)
    detalhes_por_uf = extrair_metricas_por_uf(tabelas)
    dados_pcd = processar_alunos_pcd(data_dir)
    dados_rotas = processar_rotas_prgm(data_dir)

    # Obter dados de base de referência (para indicadores metodológicos de Censo, etc.)
    ref_raw = {}
    ref_data = {}
    
    arquivos_html = glob.glob('PNITE [V.*].html') + glob.glob('old/PNITE [V.*].html')
    if arquivos_html:
        html_alvo = arquivos_html[0]
        try:
            with open(html_alvo, 'r', encoding='utf-8', errors='replace') as f:
                conteudo = f.read()
            m_raw = re.search(r'const (?:_FALLBACK_RAW_DATA|RAW_DATA)\s*=\s*(\{.*?\});\n', conteudo)
            if m_raw:
                ref_raw = json.loads(m_raw.group(1))
            m_data = re.search(r'const (?:_FALLBACK_DATA|DATA)\s*=\s*(\{.*?\});\n', conteudo)
            if m_data:
                ref_data = json.loads(m_data.group(1))
            print(f"Base de inteligência de referência carregada de '{html_alvo}'.")
        except Exception as e:
            print(f"Aviso ao carregar referência do HTML: {e}")

    raw_data_unificada = {}
    todos_nos = list(UF_LABELS.keys()) + list(REGIOES.keys())
    for no in todos_nos:
        raw_data_unificada[no] = {}
        if no in ref_raw:
            raw_data_unificada[no].update(ref_raw[no])
            
    # Aplica os dados diretos dos Excels para as UFs e Nacional
    for uf, scripts in detalhes_por_uf.items():
        node = raw_data_unificada.setdefault(uf, {})
        
        if 'script_01_alunos' in scripts:
            s1 = scripts['script_01_alunos']
            if s1.get('total_alunos') is not None:
                node['al_cad'] = s1['total_alunos']
        
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

        if 'script_05_monitores' in scripts:
            s5 = scripts['script_05_monitores']
            if s5.get('total_monitores') is not None:
                node['tot_mon'] = s5['total_monitores']
            efetivo = s5.get('servidor_efetivo') or 0
            comiss = s5.get('servidor_comissionado') or 0
            if s5.get('servidor_efetivo') is not None or s5.get('servidor_comissionado') is not None:
                node['mon_cv'] = efetivo + comiss

        if 'script_06_motoristas' in scripts:
            s6 = scripts['script_06_motoristas']
            if s6.get('total_motoristas') is not None:
                node['tot_mot_info'] = s6['total_motoristas']
            efetivo = s6.get('servidor_efetivo') or 0
            comiss = s6.get('servidor_comissionado') or 0
            if s6.get('servidor_efetivo') is not None or s6.get('servidor_comissionado') is not None:
                node['mot_cv'] = efetivo + comiss

        if 'script_13_rota_atende_aluno' in scripts:
            s13 = scripts['script_13_rota_atende_aluno']
            if s13.get('total_alunos_distintos') is not None:
                node['al_transp'] = s13['total_alunos_distintos']

        if 'script_15_rota_passa_por_escolas' in scripts:
            s15 = scripts['script_15_rota_passa_por_escolas']
            if s15.get('total_escolas_distintas') is not None:
                node['esc_at'] = s15['total_escolas_distintas']

    # Injetar dados calculados de rotas (PRGM, PRIO/dif, km, tempos)
    if dados_rotas:
        raw_data_unificada['nacional']['tot_rotas'] = dados_rotas['tot_br']
        raw_data_unificada['nacional']['georref'] = dados_rotas['geo_br']
        raw_data_unificada['nacional']['dif'] = dados_rotas['imped_br']
        raw_data_unificada['nacional']['km_total'] = dados_rotas['km_tot_br']
        raw_data_unificada['nacional']['tempo_mediano'] = dados_rotas['tempo_med_br']
        
        for s, d_rot in dados_rotas['uf_rotas'].items():
            if s in raw_data_unificada:
                raw_data_unificada[s]['tot_rotas'] = d_rot['rotas']
                raw_data_unificada[s]['georref'] = d_rot['geo']
                raw_data_unificada[s]['dif'] = d_rot['imped']
                raw_data_unificada[s]['km_total'] = round(d_rot['km'], 1)
                
        for reg, ufs in REGIOES.items():
            reg_rot = sum(dados_rotas['uf_rotas'].get(u, {}).get('rotas', 0) for u in ufs)
            reg_geo = sum(dados_rotas['uf_rotas'].get(u, {}).get('geo', 0) for u in ufs)
            reg_imp = sum(dados_rotas['uf_rotas'].get(u, {}).get('imped', 0) for u in ufs)
            reg_km = sum(dados_rotas['uf_rotas'].get(u, {}).get('km', 0.0) for u in ufs)
            raw_data_unificada[reg]['tot_rotas'] = reg_rot
            raw_data_unificada[reg]['georref'] = reg_geo
            raw_data_unificada[reg]['dif'] = reg_imp
            raw_data_unificada[reg]['km_total'] = round(reg_km, 1)

    # Injetar dados de PCD
    if dados_pcd:
        raw_data_unificada['nacional']['al_pcd'] = dados_pcd['pcd_br']
        for s, pcd_val in dados_pcd['est_pcd'].items():
            if s in raw_data_unificada:
                raw_data_unificada[s]['al_pcd'] = pcd_val
        for reg, ufs in REGIOES.items():
            reg_pcd = sum(dados_pcd['est_pcd'].get(u, 0) for u in ufs)
            raw_data_unificada[reg]['al_pcd'] = reg_pcd

    # Recalcular DATA
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
        dif_val = r.get('dif')
        
        iuc = None
        if at and nvv and cap_m and (nvv * cap_m) > 0:
            iuc = round(at / (nvv * cap_m), 2)
            
        ate = round(at / ea, 2) if (at and ea and ea > 0) else None
        prio_val = pct(dif_val, tr)

        return {
            'label': label,
            'PRGM': pct(r.get('georref'), tr),
            'PRDAM': prio_val,
            'PRIO': prio_val,
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
            'PAD': pct(r.get('al_pcd'), r.get('al_cad')),
            'PARI': pct(r.get('al_dif'), at),
            'PAIH': pct(r.get('al_hidro_dif'), r.get('al_hidro')),
            'TVA': tva_val
        }

    data_calculada = {
        'nacional': calcular_indicadores(raw_data_unificada.get('nacional', {}), 'Brasil'),
        'regiao': {},
        'estado': {}
    }

    for reg, lbl in REGIOES.items():
        data_calculada['regiao'][reg] = calcular_indicadores(raw_data_unificada.get(reg, {}), REGIAO_LABELS[reg])

    for uf, lbl in UF_LABELS.items():
        if uf != 'nacional':
            data_calculada['estado'][uf] = calcular_indicadores(raw_data_unificada.get(uf, {}), lbl)

    # Monta a estrutura final do pacote consolidado
    pacote_consolidado = {
        'metadados': {
            'data_extracao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'origem': 'Planilhas Excel e CSVs oficiais da pasta data/',
            'total_planilhas_lidas': len(tabelas),
            'arquivos_processados': [t['arquivo'] for t in tabelas.values()]
        },
        'RAW_DATA': raw_data_unificada,
        'DATA': data_calculada,
        'detalhes_scripts': detalhes_por_uf,
        'municipios_rotas': dados_rotas['municipios_rotas'] if dados_rotas else {},
        'municipios_pcd': {c: {'pcd': dados_pcd['mun_pcd'].get(c, 0), 'total': dados_pcd['mun_tot'].get(c, 0), 'PAD': round(dados_pcd['mun_pcd'].get(c, 0) / dados_pcd['mun_tot'].get(c, 0) * 100, 2) if dados_pcd['mun_tot'].get(c, 0) > 0 else None} for c in dados_pcd['mun_pcd']} if dados_pcd else {}
    }

    json_path = os.path.join(data_dir, 'pnite_dados_consolidados.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(pacote_consolidado, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Arquivo JSON exportado com sucesso: '{json_path}' ({os.path.getsize(json_path)//1024} KB)")

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
