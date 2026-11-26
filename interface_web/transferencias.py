"""Importação confirmada e download sem gravar relatórios no servidor."""
import csv
import io
import json
from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for
from banco_dados import BancoDeDados
from biblioteca import importar_ativos, preparar_importacao_dados
from modelos import Ativo
from relatorio import CAMPOS_CSV, preparar_relatorio
from .comum import (assinar,banco_para_gravar,confirmar,exigir_cadastro,falha,ler_retrato,validar_csrf,verificar)

bp=Blueprint('transferencias_web',__name__)

@bp.get('/relatorio.csv')
def exportar():
    try:
        ativos,_=ler_retrato()
        linhas=preparar_relatorio(ativos)
        if not linhas:
            return render_template('exportacao_vazia.html')
        saida=io.StringIO(newline='')
        escritor=csv.DictWriter(saida,fieldnames=CAMPOS_CSV)
        escritor.writeheader()
        escritor.writerows(linhas)
        return Response(saida.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename="relatorio_vulnerabilidades.csv"'})
    except (ValueError,OSError,RuntimeError) as erro:
        return falha(erro)

@bp.route('/importar',methods=['GET','POST'])
def importar():
    exigir_cadastro()
    contexto={'lote':None,'previa':None}
    try:
        if request.method=='GET':
            ler_retrato()
            return render_template('importar.html',**contexto)
        validar_csrf()
        if request.form.get('acao')=='confirmar':
            dados=verificar(request.form.get('previa',''),'importacao')
            contexto.update(lote=[Ativo.from_dict(a) for a in dados['ativos']],previa=request.form.get('previa'))
            db=banco_para_gravar(dados['revisao'])
            confirmar()
            importar_ativos(db,contexto['lote'])
            flash(f"Importação concluída: {len(contexto['lote'])} ativo(s) adicionado(s).")
            return redirect(url_for('ativos_web.listar'),code=303)
        arquivo=request.files.get('arquivo')
        if arquivo is None:
            raise ValueError('Selecione uma biblioteca JSON.')
        conteudo=arquivo.read(1024*1024+1)
        if len(conteudo)>1024*1024:
            raise ValueError('A biblioteca excede o limite de 1 MiB. Divida o lote em arquivos menores.')
        try:
            dados=json.loads(conteudo.decode('utf-8-sig'))
        except (UnicodeError,ValueError,RecursionError) as erro:
            raise ValueError('Envie uma lista JSON válida, em UTF-8.') from erro
        db=BancoDeDados(current_app.config['INVENTARIO_ARQUIVO'],recuperar=False)
        lote=preparar_importacao_dados(db,dados)
        contexto.update(lote=lote,previa=assinar({'ativos':[a.to_dict() for a in lote],'revisao':db.revisao},'importacao'))
        return render_template('importar.html',**contexto)
    except (ValueError,KeyError,TypeError,OSError,RuntimeError) as erro:
        return falha(erro,'importar.html',**contexto)
