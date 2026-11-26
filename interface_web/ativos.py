"""Busca, detalhes e manutenção de ativos pela mesma persistência da CLI."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from tipos import TipoAtivo
from .comum import (banco_para_gravar, confirmar, encontrar_ativo, exigir_cadastro,
                    falha, inteiro, ler_retrato, texto)

bp = Blueprint('ativos_web', __name__)


@bp.get('/ativos')
def listar():
    try:
        ativos, _ = ler_retrato()
        modo, termo = request.args.get('modo', 'trecho'), request.args.get('termo', '').strip()
        encontrados = ativos
        if termo:
            if modo == 'id':
                aid = inteiro(termo, 'ID')
                encontrados = [a for a in ativos if a.id_ativo == aid]
            elif modo == 'hostname':
                encontrados = [a for a in ativos if a.hostname.lower() == termo.lower()]
            elif modo == 'trecho':
                encontrados = [a for a in ativos if termo.lower() in a.hostname.lower()]
            else:
                raise ValueError('Selecione uma forma de busca válida.')
        return render_template('ativos.html', ativos=sorted(encontrados, key=lambda a:a.id_ativo),
                               total=len(ativos), modo=modo, termo=termo)
    except (ValueError, OSError, RuntimeError) as erro:
        return falha(erro)


@bp.get('/ativos/<int:aid>')
def detalhes(aid):
    try:
        ativos, _ = ler_retrato()
        ativo = encontrar_ativo(ativos, aid)
        return render_template('ativo_detalhes.html', ativo=ativo, por_id={a.id_ativo:a for a in ativos},
                               orientacoes=ativo.orientacoes_tratamento())
    except (ValueError, OSError, RuntimeError) as erro:
        return falha(erro)


@bp.route('/ativos/<int:aid>/editar', methods=['GET', 'POST'])
def editar(aid):
    exigir_cadastro()
    valores, revisao = {}, request.form.get('revisao', '')
    try:
        if request.method == 'POST':
            valores = {c:request.form.get(c, '').strip() for c in ('hostname','responsavel','setor','tipo')}
            db = banco_para_gravar(revisao)
            encontrar_ativo(db.listar_todos(), aid)
            try:
                tipo = TipoAtivo[valores['tipo']]
            except KeyError as causa:
                raise ValueError('Selecione um tipo de ativo válido.') from causa
            db.atualizar_ativo(aid, hostname=texto(valores['hostname'],'Hostname'),
                               responsavel=texto(valores['responsavel'],'Responsável'),
                               setor=texto(valores['setor'],'Setor'), tipo=tipo)
            flash('Ativo atualizado com sucesso.')
            return redirect(url_for('ativos_web.detalhes', aid=aid), code=303)
        ativos, revisao = ler_retrato()
        ativo = encontrar_ativo(ativos, aid)
        valores = {'id_ativo':aid, 'hostname':ativo.hostname, 'responsavel':ativo.responsavel,
                   'setor':ativo.setor, 'tipo':ativo.tipo.name}
        return render_template('cadastrar_ativo.html', valores=valores, tipos=TipoAtivo, editar=True,
                               acao_form=url_for('ativos_web.editar', aid=aid), revisao=revisao)
    except (ValueError, OSError, RuntimeError) as erro:
        valores['id_ativo'] = aid
        return falha(erro, 'cadastrar_ativo.html', valores=valores, tipos=TipoAtivo, editar=True,
                     acao_form=url_for('ativos_web.editar', aid=aid), revisao=revisao)


@bp.route('/ativos/<int:aid>/remover', methods=['GET','POST'])
def remover(aid):
    exigir_cadastro()
    contexto = {'titulo':'Remover ativo', 'texto_confirmacao':'O ativo, suas vulnerabilidades e seus vínculos serão removidos.',
                'revisao':request.form.get('revisao',''), 'voltar':url_for('ativos_web.detalhes',aid=aid)}
    try:
        if request.method == 'POST':
            db = banco_para_gravar(contexto['revisao'])
            encontrar_ativo(db.listar_todos(), aid)
            confirmar()
            db.remover(aid)
            flash('Ativo removido com sucesso; vínculos de entrada e saída foram limpos.')
            return redirect(url_for('ativos_web.listar'),code=303)
        ativos, contexto['revisao'] = ler_retrato()
        ativo = encontrar_ativo(ativos,aid)
        contexto['itens'] = [f'{ativo.id_ativo} · {ativo.hostname}',
                            f'{len(ativo.vulnerabilidades)} vulnerabilidade(s) associada(s)',
                            'Dependentes: ' + (', '.join(a.hostname for a in ativos if aid in a.dependencias) or 'nenhum')]
        return render_template('confirmar.html',**contexto)
    except (ValueError, OSError, RuntimeError) as erro:
        return falha(erro,'confirmar.html',**contexto)
