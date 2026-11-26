"""Dependências por critérios de serviços e análise sobre o retrato completo."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from avaliacao import AvaliacaoDependencia
from servico_risco import analisar_ativos
from .comum import (banco_para_gravar, confirmar, encontrar_ativo, exigir_cadastro,
                    falha, inteiro, ler_retrato)

bp=Blueprint('analise_web',__name__)

@bp.get('/dependencias')
def dependencias():
    try:
        ativos,_=ler_retrato()
        return render_template('dependencias.html',ativos=sorted(ativos,key=lambda a:a.id_ativo),por_id={a.id_ativo:a for a in ativos})
    except (ValueError,OSError,RuntimeError) as erro:
        return falha(erro)

@bp.route('/dependencias/nova',methods=['GET','POST'])
@bp.route('/dependencias/<int:origem>/<int:destino>/editar',methods=['GET','POST'])
def editar_dependencia(origem=None,destino=None):
    exigir_cadastro()
    campos=('origem','destino','total_servicos','servicos_fornecidos','duracao_falha_min','indisponibilidade_min','fonte_medicao')
    valores={k:request.form.get(k,'').strip() for k in campos}
    contexto={'valores':valores,'editar':origem is not None,'ativos':[],'revisao':request.form.get('revisao','')}
    try:
        if request.method=='POST':
            db=banco_para_gravar(contexto['revisao'])
            ativos=db.listar_todos()
        else:
            ativos,contexto['revisao']=ler_retrato()
        contexto['ativos']=sorted(ativos,key=lambda a:a.id_ativo)
        if origem is not None:
            ativo=encontrar_ativo(ativos,origem)
            if destino not in ativo.dependencias:
                abort(404,description='Dependência não encontrada.')
            if request.method=='GET':
                avaliacao=ativo.avaliacoes_dependencias.get(destino)
                valores.update(origem=str(origem),destino=str(destino))
                if avaliacao:
                    valores.update({k:str(v) if v is not None else '' for k,v in avaliacao.to_dict().items()})
        if request.method=='POST':
            if origem is None:
                origem=inteiro(valores['origem'],'Ativo dependente')
                destino=inteiro(valores['destino'],'Ativo fornecedor')
                ativo=encontrar_ativo(ativos,origem)
                if destino in ativo.dependencias:
                    raise ValueError('Dependência já cadastrada. Use editar.')
            tempos={}
            for campo in ('duracao_falha_min','indisponibilidade_min'):
                tempos[campo]=float(valores[campo].replace(',','.')) if valores[campo] else None
            avaliacao=AvaliacaoDependencia(
                inteiro(valores['total_servicos'],'Total de serviços'),
                inteiro(valores['servicos_fornecidos'],'Serviços fornecidos',0),
                **tempos,fonte_medicao=valores['fonte_medicao'] or None)
            db.definir_dependencia(origem,destino,avaliacao.peso,avaliacao=avaliacao)
            flash(f'Dependência salva. Peso calculado: {avaliacao.peso:.8g}.')
            return redirect(url_for('analise_web.dependencias'),code=303)
        return render_template('dependencia_form.html',**contexto)
    except (ValueError,OSError,RuntimeError) as erro:
        return falha(erro,'dependencia_form.html',**contexto)

@bp.route('/dependencias/<int:origem>/<int:destino>/remover',methods=['GET','POST'])
def remover_dependencia(origem,destino):
    exigir_cadastro()
    contexto={'titulo':'Remover dependência','texto_confirmacao':'Somente esta relação e seus critérios serão removidos. Os ativos serão preservados.','itens':[],
              'voltar':url_for('analise_web.dependencias'),'revisao':request.form.get('revisao','')}
    try:
        if request.method=='POST':
            db=banco_para_gravar(contexto['revisao'])
            confirmar()
            db.remover_dependencia(origem,destino)
            flash('Dependência removida.')
            return redirect(contexto['voltar'],code=303)
        ativos,contexto['revisao']=ler_retrato()
        ativo=encontrar_ativo(ativos,origem)
        fornecedor=encontrar_ativo(ativos,destino)
        if destino not in ativo.dependencias:
            abort(404)
        contexto['itens']=[f'{ativo.hostname} ({origem}) depende de {fornecedor.hostname} ({destino}).']
        return render_template('confirmar.html',**contexto)
    except (ValueError,OSError,RuntimeError) as erro:
        return falha(erro,'confirmar.html',**contexto)

@bp.get('/riscos')
def riscos():
    try:
        ativos,_=ler_retrato()
    except (ValueError,OSError,RuntimeError) as erro:
        return falha(erro)
    contexto={'ativos':sorted(ativos,key=lambda a:a.id_ativo),'analise':None,'individual':None,'aid':request.args.get('ativo_id',''),'erro_risco':None,'erro_consulta':None}
    try:
        analise=analisar_ativos(ativos)
        contexto['analise']=analise
    except Exception:
        current_app.logger.exception('Falha na consulta detalhada de risco')
        contexto['erro_risco']='Risco indisponível. Verifique a estabilidade das dependências e o ID consultado. Os ativos continuam disponíveis.'
    status=200
    if contexto['analise'] is not None and contexto['aid']:
        try:
            aid=inteiro(contexto['aid'],'ID do ativo')
            contexto['individual']=contexto['analise'].individual(aid)
            contexto['aid']=aid
        except ValueError as erro:
            contexto['erro_consulta']=str(erro)
            status=400
    contexto['sem_origem']=sum(not v.vetor_cvss and not v.fonte_severidade for a in ativos for v in a.vulnerabilidades)
    return render_template('riscos.html',**contexto),status
