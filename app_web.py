"""Consulta e cadastro local de ativos, com gravação somente após envio válido."""
import os
import secrets
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from banco_dados import BancoDeDados, InventarioIndisponivel
from servico_risco import analisar_ativos
from modelos import Ativo
from tipos import TipoAtivo


EXEMPLO = Path(__file__).resolve().parent / "exemplos/inventario_web.json"


def create_app(caminho=None, *, permitir_cadastro=None):
    """Usa o exemplo fictício por padrão; o caminho é definido no servidor."""
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.config.update(
        INVENTARIO_ARQUIVO=str(caminho) if caminho is not None else os.environ.get(
            "INVENTARIO_ARQUIVO", str(EXEMPLO)),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_HTTPONLY=True,
        TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
    )

    habilitado = (os.environ.get("INVENTARIO_CADASTRO") == "1"
                  if permitir_cadastro is None else permitir_cadastro)
    app.config["PERMITIR_CADASTRO"] = bool(
        habilitado and Path(app.config["INVENTARIO_ARQUIVO"]).resolve() != EXEMPLO)

    @app.context_processor
    def contexto_cadastro():
        return {"permitir_cadastro": app.config["PERMITIR_CADASTRO"]}

    @app.after_request
    def proteger_resposta(resposta):
        resposta.headers["X-Inventario-App"] = "inventario-ti"
        resposta.headers["Cache-Control"] = "no-store"
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        resposta.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src 'self' data:; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        return resposta

    @app.get("/")
    def inventario():
        ativos = None
        riscos = {}
        risco_indisponivel = False
        try:
            ativos = BancoDeDados.consultar_ativos(app.config["INVENTARIO_ARQUIVO"])
        except InventarioIndisponivel:
            pass
        if ativos:
            try:
                analise = analisar_ativos(ativos)
                riscos = {aid: (proprio, efetivo) for aid, proprio, efetivo in analise.ranking()}
            except Exception:
                # A falha do cálculo não pode ocultar o inventário já validado.
                app.logger.exception("Falha ao calcular o risco do inventário")
                risco_indisponivel = True
        return render_template(
            "inventario.html", ativos=ativos, riscos=riscos,
            risco_indisponivel=risco_indisponivel,
            demonstracao=(app.config["INVENTARIO_ARQUIVO"] == str(EXEMPLO)
                          or os.environ.get("INVENTARIO_DEMONSTRACAO") == "1"),
            total_vulnerabilidades=sum(len(a.vulnerabilidades) for a in ativos or ()),
            total_dependencias=sum(len(a.dependencias) for a in ativos or ()),
        ), 503 if ativos is None else 200

    @app.route("/ativos/novo", methods=["GET", "POST"])
    def cadastrar_ativo():
        if not app.config["PERMITIR_CADASTRO"]:
            abort(403)
        session.setdefault("csrf_token", secrets.token_urlsafe(32))
        valores = {campo: request.form.get(campo, "").strip()
                   for campo in ("id_ativo", "hostname", "responsavel", "setor", "tipo")}
        erro = None
        status = 200
        try:
            if request.method == "POST":
                token = request.form.get("csrf_token", "")
                if (not token or not token.isascii()
                        or not secrets.compare_digest(token, session["csrf_token"])):
                    raise ValueError("O formulário expirou ou é inválido. Atualize a página e tente novamente.")
                if (not valores["id_ativo"].isascii() or not valores["id_ativo"].isdecimal()
                        or int(valores["id_ativo"]) < 1):
                    raise ValueError("Informe um ID inteiro positivo.")
                for campo, rotulo in (("hostname", "Hostname"), ("responsavel", "Responsável"),
                                      ("setor", "Setor / localização")):
                    if not valores[campo] or len(valores[campo]) > 200:
                        raise ValueError(f"{rotulo}: informe de 1 a 200 caracteres.")
                try:
                    tipo = TipoAtivo[valores["tipo"]]
                except KeyError as causa:
                    raise ValueError("Selecione um tipo de ativo válido.") from causa
                ativo = Ativo.criar(int(valores["id_ativo"]), valores["hostname"],
                                    valores["responsavel"], valores["setor"], tipo)
                # A abertura estrita impede backup ou recuperação durante o cadastro web.
                db = BancoDeDados(app.config["INVENTARIO_ARQUIVO"], recuperar=False)
                if request.form.get('incluir_vulnerabilidades') == 'sim':
                    db._validar_unicidade(db.listar_todos() + [ativo])
                    from interface_web.vulnerabilidades import mostrar_rascunho
                    return mostrar_rascunho({'ativo':ativo.to_dict(), 'revisao':db.revisao})
                db.adicionar(ativo)
                flash(f"Ativo '{ativo.hostname}' cadastrado com sucesso.")
                return redirect(url_for("inventario"), code=303)
            BancoDeDados.consultar_ativos(app.config["INVENTARIO_ARQUIVO"])
        except InventarioIndisponivel:
            erro, status = "Inventário indisponível. O cadastro não foi salvo; verifique a base.", 503
        except ValueError as causa:
            erro, status = str(causa), 400
        except RuntimeError:
            erro, status = "A base está em uso ou mudou em outra instância. Atualize a página e tente novamente.", 409
        except OSError:
            erro, status = "Não foi possível salvar o ativo. Verifique as permissões e tente novamente.", 503
        return render_template("cadastrar_ativo.html", valores=valores, tipos=TipoAtivo,
                               erro=erro, indisponivel=status == 503), status

    @app.template_filter("numero")
    def numero(valor):
        return f"{valor:.2f}".replace(".", ",")

    from interface_web import registrar_rotas
    registrar_rotas(app)
    return app
