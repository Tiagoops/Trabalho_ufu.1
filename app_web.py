"""Consulta local de ativos e riscos, sem operações de escrita."""
import os
from pathlib import Path

from flask import Flask, render_template

from banco_dados import BancoDeDados, InventarioIndisponivel
from servico_risco import analisar_ativos


EXEMPLO = Path(__file__).resolve().parent / "exemplos/inventario_web.json"


def create_app(caminho=None):
    """Usa o exemplo fictício por padrão; o caminho é definido no servidor."""
    app = Flask(__name__)
    app.config.update(
        INVENTARIO_ARQUIVO=str(caminho) if caminho is not None else os.environ.get(
            "INVENTARIO_ARQUIVO", str(EXEMPLO)),
        TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
    )

    @app.after_request
    def proteger_resposta(resposta):
        resposta.headers["Cache-Control"] = "no-store"
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        resposta.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src 'self' data:; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
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
            demonstracao=app.config["INVENTARIO_ARQUIVO"] == str(EXEMPLO),
            total_vulnerabilidades=sum(len(a.vulnerabilidades) for a in ativos or ()),
            total_dependencias=sum(len(a.dependencias) for a in ativos or ()),
        ), 503 if ativos is None else 200

    @app.template_filter("numero")
    def numero(valor):
        return f"{valor:.2f}".replace(".", ",")

    return app
