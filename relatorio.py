"""Registros CSV comuns ao terminal e ao download, validados antes da escrita."""
import unicodedata

CAMPOS_CSV=['severidade','id_ativo','hostname','categoria','descricao']

def validar_celula_csv(valor):
    """Não deixa dados informados virarem fórmulas ao abrir uma planilha."""
    if isinstance(valor,str):
        normalizado=unicodedata.normalize('NFKC',valor).lstrip()
        if normalizado.startswith(('=','+','-','@')) or any(c in valor for c in ('\t','\r','\n')):
            raise ValueError('CSV recusado: campo contém fórmula ou controle de linha')
    return valor

def preparar_relatorio(ativos):
    linhas=[{'severidade':v.severidade,'id_ativo':a.id_ativo,'hostname':a.hostname,
             'categoria':v.categoria,'descricao':v.descricao} for a in ativos for v in a.vulnerabilidades]
    linhas.sort(key=lambda linha:(-linha['severidade'],linha['id_ativo']))
    return [{campo:validar_celula_csv(linha[campo]) for campo in CAMPOS_CSV} for linha in linhas]
