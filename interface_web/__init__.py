"""Registra as telas do inventário e a saída da sessão de navegação."""
from flask import redirect, render_template, request, session, url_for

from .comum import csrf_token, validar_csrf
from .ativos import bp as ativos
from .analise import bp as analise
from .transferencias import bp as transferencias
from .vulnerabilidades import bp as vulnerabilidades


def registrar_rotas(app):
    app.register_blueprint(ativos)
    app.register_blueprint(analise)
    app.register_blueprint(transferencias)
    app.register_blueprint(vulnerabilidades)
    app.jinja_env.globals['csrf_token'] = csrf_token
    app.jinja_env.filters['preciso'] = lambda valor: format(float(valor), '.8g')

    @app.before_request
    def verificar_sessao():
        livres = {'static','metadados','sessao_encerrada','entrar_web','sair_web'}
        if session.get('encerrada') and request.endpoint not in livres:
            return redirect(url_for('sessao_encerrada'), code=303 if request.method == 'POST' else 302)

    @app.post('/sair')
    def sair_web():
        validar_csrf()
        session.clear()
        session['encerrada'] = True
        return redirect(url_for('sessao_encerrada'),code=303)

    @app.get('/sessao-encerrada')
    def sessao_encerrada():
        return render_template('sessao_encerrada.html')

    @app.post('/entrar')
    def entrar_web():
        validar_csrf()
        session.clear()
        return redirect(url_for('inventario'),code=303)
