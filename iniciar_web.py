"""Inicia o cadastro demonstrativo sem sobrescrever uma base existente."""
import os
from pathlib import Path

from app_web import EXEMPLO, create_app


def preparar_base(caminho):
    """Inicialização explícita; requisições HTTP nunca criam a base."""
    caminho = Path(caminho).resolve()
    if caminho == EXEMPLO:
        raise ValueError("o exemplo versionado não pode ser a base de gravação")
    original = EXEMPLO.read_bytes()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    try:
        with caminho.open("xb") as arquivo:
            arquivo.write(original)
            arquivo.flush()
            os.fsync(arquivo.fileno())
    except FileExistsError:
        pass


def main():
    from waitress import serve

    padrao = Path(__file__).resolve().parent / "dados_web/inventario.json"
    if "INVENTARIO_ARQUIVO" not in os.environ:
        os.environ["INVENTARIO_ARQUIVO"] = str(padrao)
        os.environ["INVENTARIO_DEMONSTRACAO"] = "1"
    preparar_base(os.environ["INVENTARIO_ARQUIVO"])
    os.environ["INVENTARIO_CADASTRO"] = "1"
    serve(create_app(), host=os.environ.get("INVENTARIO_HOST", "127.0.0.1"), port=8000)


if __name__ == "__main__":
    main()
