"""Leitura sem efeitos colaterais, tokens de formulário e erros da interface."""
import secrets

from flask import abort, current_app, render_template, request, session
from itsdangerous import BadSignature, URLSafeTimedSerializer

from banco_dados import BancoDeDados, InventarioIndisponivel


class ConflitoFormulario(RuntimeError):
    pass


def csrf_token():
    return session.setdefault('csrf_token', secrets.token_urlsafe(32))


def validar_csrf():
    token = request.form.get('csrf_token', '')
    esperado = session.get('csrf_token', '')
    if not token or not token.isascii() or not esperado or not secrets.compare_digest(token, esperado):
        abort(400, description='O formulário expirou ou é inválido. Reabra a tela e tente novamente.')


def exigir_cadastro():
    if not current_app.config['PERMITIR_CADASTRO']:
        abort(403, description='Esta instância está configurada somente para consulta.')


def ler_retrato():
    return BancoDeDados.consultar_retrato(current_app.config['INVENTARIO_ARQUIVO'])


def banco_para_gravar(revisao):
    exigir_cadastro()
    validar_csrf()
    db = BancoDeDados(current_app.config['INVENTARIO_ARQUIVO'], recuperar=False)
    if not revisao or revisao != db.revisao:
        raise ConflitoFormulario('A base mudou desde a abertura do formulário. Reabra a tela para revisar os dados.')
    return db


def encontrar_ativo(ativos, identificador):
    ativo = next((a for a in ativos if a.id_ativo == identificador), None)
    if ativo is None:
        abort(404, description='Ativo não encontrado.')
    return ativo


def inteiro(valor, rotulo, minimo=1):
    valor = str(valor).strip()
    if not valor.isascii() or not valor.isdecimal():
        raise ValueError(f'{rotulo}: informe um número inteiro válido.')
    numero = int(valor)
    if numero < minimo:
        raise ValueError(f'{rotulo}: o mínimo permitido é {minimo}.')
    return numero


def texto(valor, rotulo, limite=200):
    valor = str(valor).strip()
    if not valor or len(valor) > limite:
        raise ValueError(f'{rotulo}: informe de 1 a {limite} caracteres.')
    return valor


def confirmar():
    if request.form.get('confirmar') != 'sim':
        raise ValueError('Confirme a operação antes de prosseguir. Cancelar não altera a base.')


def assinar(dados, finalidade):
    serializador = URLSafeTimedSerializer(current_app.secret_key, salt=finalidade)
    return serializador.dumps({'sessao': csrf_token(), 'dados': dados})


def verificar(token, finalidade):
    try:
        dados = URLSafeTimedSerializer(current_app.secret_key, salt=finalidade).loads(token, max_age=900)
    except BadSignature as erro:
        raise ValueError('A prévia expirou ou foi alterada. Refaça a operação.') from erro
    if not isinstance(dados, dict) or dados.get('sessao') != session.get('csrf_token'):
        raise ValueError('Esta prévia não pertence à sessão atual.')
    return dados['dados']


def falha(erro, template='erro.html', **contexto):
    if isinstance(erro, InventarioIndisponivel):
        mensagem, status = 'Inventário indisponível. Verifique a base; nenhuma recuperação automática foi executada.', 503
    elif isinstance(erro, OSError):
        mensagem, status = 'Não foi possível acessar ou salvar os dados. Verifique as permissões e tente novamente.', 503
    elif isinstance(erro, RuntimeError):
        mensagem, status = str(erro), 409
    else:
        mensagem, status = str(erro), 400
    return render_template(template, erro=mensagem, **contexto), status
