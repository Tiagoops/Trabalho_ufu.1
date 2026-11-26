"""Avaliações CVSS, referências e rascunhos com confirmação antes da gravação."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from avaliacao import METRICAS_CVSS4
from catalogo_cvss import buscar_catalogo, carregar_catalogo, consultar_nvd
from modelos import Ativo, Vulnerabilidade
from .comum import (ConflitoFormulario, assinar, banco_para_gravar, confirmar, encontrar_ativo,
                    exigir_cadastro, falha, inteiro, ler_retrato, texto, validar_csrf, verificar)

bp = Blueprint('vulnerabilidades_web', __name__)


def encontrar_ocorrencia(ativo, vid):
    v = next((v for v in ativo.vulnerabilidades if v.id_vulnerabilidade == vid), None)
    if v is None:
        abort(404, description='Vulnerabilidade não encontrada neste ativo.')
    return v


def mostrar_rascunho(dados, erro=None):
    return render_template('rascunho_ativo.html', ativo=Ativo.from_dict(dados['ativo']),
                           rascunho=assinar(dados,'rascunho-ativo'), erro=erro)


@bp.get('/vulnerabilidades')
def listar():
    try:
        ativos, _ = ler_retrato()
        return render_template('vulnerabilidades.html', ativos=sorted(ativos,key=lambda a:a.id_ativo))
    except (ValueError, OSError, RuntimeError) as erro:
        return falha(erro)


@bp.get('/vulnerabilidades/nova')
def selecionar_ativo():
    exigir_cadastro()
    try:
        aid=inteiro(request.args.get('ativo_id',''),'Ativo')
        return redirect(url_for('vulnerabilidades_web.nova',aid=aid))
    except ValueError as erro:
        return falha(erro)


@bp.get('/ajuda/cvss')
def ajuda():
    return render_template('ajuda_cvss.html', metricas=METRICAS_CVSS4)


def avaliar(valores, anterior):
    descricao=texto(valores.get('descricao',''),'Descrição',4000)
    categoria=texto(valores.get('categoria',''),'Categoria')
    modo=valores.get('modo')
    referencia=None
    if modo=='manter' and anterior is not None:
        v=Vulnerabilidade.from_dict({**anterior.to_dict(),'descricao':descricao,'categoria':categoria})
        return v, referencia
    if modo=='questionario':
        partes=[]
        for codigo,rotulo,opcoes in METRICAS_CVSS4:
            valor=valores.get('cvss_'+codigo,'')
            if valor not in opcoes:
                raise ValueError(f'{codigo}: selecione uma característica técnica válida. Não presuma uma resposta desconhecida.')
            partes.append(codigo+':'+valor)
        vetor='CVSS:4.0/'+'/'.join(partes)
    elif modo=='vetor':
        vetor=texto(valores.get('vetor',''),'Vetor CVSS',2048)
    elif modo=='catalogo':
        selecionada=valores.get('cve','').strip().upper()
        referencia=next((item for item in carregar_catalogo() if item['cve']==selecionada),None)
        if referencia is None:
            raise ValueError('Selecione uma CVE válida do catálogo local.')
        vetor=referencia['vetor_cvss']
    elif modo=='nvd':
        referencia=consultar_nvd(valores.get('cve','').strip().upper())
        vetor=referencia['vetor_cvss']
        if vetor is None:
            raise ValueError('O NVD ainda não oferece vetor Base 3.1 ou 4.0 do NIST para essa CVE. Use outro modo de avaliação.')
    else:
        raise ValueError('Selecione um modo de avaliação válido.')
    v=Vulnerabilidade.por_cvss(descricao,categoria,vetor,
        cve=referencia['cve'] if referencia else None,
        fonte_severidade=referencia['fonte_primaria'] if referencia else None)
    if anterior is not None:
        v.id_vulnerabilidade=anterior.id_vulnerabilidade
    return v, referencia


def fluxo(ativo, revisao, anterior=None, db=None, rascunho=None):
    campos=('descricao','categoria','modo','vetor','cve','busca_catalogo')+tuple('cvss_'+c for c,_,_ in METRICAS_CVSS4)
    valores={c:request.form.get(c,'').strip() for c in campos}
    if request.method=='GET':
        valores.update(descricao=anterior.descricao if anterior else '',
                       categoria=anterior.categoria if anterior else '',
                       modo='manter' if anterior else 'vetor',vetor=anterior.vetor_cvss or '' if anterior else '')
    modo=valores.get('modo') or ('manter' if anterior else 'vetor')
    valores['modo']=modo
    contexto={'ativo':ativo,'anterior':anterior,'revisao':revisao,'valores':valores,
              'metricas':METRICAS_CVSS4,'referencias':[], 'acao_form':request.path,
              'rascunho':assinar(rascunho,'rascunho-ativo') if rascunho else None}
    previa=None
    try:
        acao=request.form.get('acao')
        if request.method=='POST' and acao=='salvar_vulnerabilidade':
            previa=verificar(request.form.get('avaliacao',''),'avaliacao-vulnerabilidade')
            if (previa['ativo_id']!=ativo.id_ativo or previa['ocorrencia_id']!=(anterior.id_vulnerabilidade if anterior else None)
                    or previa['revisao']!=revisao):
                raise ConflitoFormulario('A avaliação não corresponde ao ativo, à ocorrência ou à versão atual da base.')
            if previa['exigir_aplicabilidade'] and request.form.get('aplicavel')!='sim':
                raise ValueError('Confirme na fonte que a CVE se aplica ao ativo antes de associá-la.')
            v=Vulnerabilidade.from_dict(previa['vulnerabilidade'])
            if rascunho is not None:
                ativo.vulnerabilidades.append(v)
                rascunho['ativo']=ativo.to_dict()
                return mostrar_rascunho(rascunho)
            if anterior is None:
                ativo.vulnerabilidades.append(v)
            else:
                for campo in ('descricao','categoria','severidade','vetor_cvss','fonte_severidade','cve'):
                    setattr(anterior,campo,getattr(v,campo))
            db.salvar()
            flash('Vulnerabilidade salva com sucesso.')
            return redirect(url_for('ativos_web.detalhes',aid=ativo.id_ativo),code=303)
        if modo=='catalogo':
            catalogo=carregar_catalogo()
            termo=valores.get('busca_catalogo','')
            contexto['referencias']=buscar_catalogo(termo,catalogo) if termo else catalogo
        if request.method=='POST' and acao=='avaliar':
            v, referencia=avaliar(valores,anterior)
            previa={'ativo_id':ativo.id_ativo,'ocorrencia_id':anterior.id_vulnerabilidade if anterior else None,
                    'revisao':revisao,'vulnerabilidade':v.to_dict(),'referencia':referencia,
                    'exigir_aplicabilidade':referencia is not None}
            return render_template('avaliacao_previa.html',previa=previa,
                                   avaliacao=assinar(previa,'avaliacao-vulnerabilidade'),**contexto)
        return render_template('vulnerabilidade_form.html',**contexto)
    except (ValueError, OSError, RuntimeError) as erro:
        if previa is not None:
            return falha(erro,'avaliacao_previa.html',previa=previa,
                         avaliacao=request.form.get('avaliacao',''),**contexto)
        return falha(erro,'vulnerabilidade_form.html',**contexto)


def tela_ocorrencia(aid, vid=None):
    exigir_cadastro()
    try:
        db=None
        if request.method=='POST':
            db=banco_para_gravar(request.form.get('revisao',''))
            ativos,revisao=db.listar_todos(),db.revisao
        else:
            ativos,revisao=ler_retrato()
        ativo=encontrar_ativo(ativos,aid)
        anterior=encontrar_ocorrencia(ativo,vid) if vid is not None else None
        return fluxo(ativo,revisao,anterior,db)
    except (ValueError, OSError, RuntimeError) as erro:
        return falha(erro)


@bp.route('/ativos/<int:aid>/vulnerabilidades/nova',methods=['GET','POST'])
def nova(aid):
    return tela_ocorrencia(aid)


@bp.route('/ativos/<int:aid>/vulnerabilidades/<path:vid>/editar',methods=['GET','POST'])
def editar(aid,vid):
    return tela_ocorrencia(aid,vid)


@bp.route('/ativos/<int:aid>/vulnerabilidades/<path:vid>/remover',methods=['GET','POST'])
def remover(aid,vid):
    exigir_cadastro()
    contexto={'titulo':'Remover vulnerabilidade','texto_confirmacao':'Esta ocorrência será removida do ativo.',
              'revisao':request.form.get('revisao',''),'voltar':url_for('ativos_web.detalhes',aid=aid)}
    try:
        if request.method=='POST':
            db=banco_para_gravar(contexto['revisao'])
            ativo=encontrar_ativo(db.listar_todos(),aid)
            v=encontrar_ocorrencia(ativo,vid)
            confirmar()
            ativo.vulnerabilidades.remove(v)
            db.salvar()
            flash('Vulnerabilidade removida com sucesso.')
            return redirect(contexto['voltar'],code=303)
        ativos,contexto['revisao']=ler_retrato()
        v=encontrar_ocorrencia(encontrar_ativo(ativos,aid),vid)
        contexto['itens']=[v.descricao,f'ID {v.id_vulnerabilidade} · severidade {v.severidade:g}']
        return render_template('confirmar.html',**contexto)
    except (ValueError, OSError, RuntimeError) as erro:
        return falha(erro,'confirmar.html',**contexto)


@bp.post('/ativos/rascunho')
def rascunho():
    exigir_cadastro()
    validar_csrf()
    try:
        dados=verificar(request.form.get('rascunho',''),'rascunho-ativo')
        db=banco_para_gravar(dados['revisao'])
        ativo=Ativo.from_dict(dados['ativo'])
        acao=request.form.get('acao')
        if acao=='salvar_ativo':
            db.adicionar(ativo)
            flash('Ativo e vulnerabilidades iniciais cadastrados com sucesso.')
            return redirect(url_for('ativos_web.detalhes',aid=ativo.id_ativo),code=303)
        if acao=='excluir_rascunho':
            indice=inteiro(request.form.get('indice',''),'Ocorrência',minimo=0)
            if indice>=len(ativo.vulnerabilidades):
                raise ValueError('Ocorrência inexistente no rascunho.')
            ativo.vulnerabilidades.pop(indice)
            dados['ativo']=ativo.to_dict()
            return mostrar_rascunho(dados)
        return fluxo(ativo,dados['revisao'],rascunho=dados)
    except (ValueError, OSError, RuntimeError) as erro:
        return falha(erro)
