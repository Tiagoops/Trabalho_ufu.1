"""Inicia o cadastro demonstrativo sem sobrescrever uma base existente."""
import os
from pathlib import Path
from http.client import HTTPConnection, HTTPException
from threading import Thread
import webbrowser

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


URL_PREVIA = "http://127.0.0.1:8000/"


def _estado_previa(porta=8000):
    conexao = HTTPConnection("127.0.0.1", porta, timeout=1)
    try:
        conexao.request("GET", "/")
        resposta = conexao.getresponse()
        try:
            return "inventario" if resposta.getheader("X-Inventario-App") == "inventario-ti" else "ocupada"
        finally:
            resposta.close()
    except ConnectionRefusedError:
        return "livre"
    except (OSError, HTTPException):
        return "ocupada"
    finally:
        conexao.close()


def _abrir_no_navegador():
    if Path("/.dockerenv").exists():
        print(f"No Docker, abra {URL_PREVIA} no navegador do computador.", flush=True)
        return
    try:
        if webbrowser.open(URL_PREVIA, new=2):
            return
    except (OSError, webbrowser.Error):
        pass
    print(f"Abra manualmente no navegador: {URL_PREVIA}", flush=True)


def main(*, abrir_navegador=False):
    from waitress import create_server

    estado = _estado_previa()
    if estado == "inventario":
        print(f"A prévia já está em execução: {URL_PREVIA}", flush=True)
        if abrir_navegador:
            _abrir_no_navegador()
        return
    if estado == "ocupada":
        print("Não foi possível iniciar a prévia: a porta 8000 está ocupada ou indisponível.")
        print("Encerre o outro serviço ou escolha continuar no terminal.")
        return
    padrao = Path(__file__).resolve().parent / "dados_web/inventario.json"
    if "INVENTARIO_ARQUIVO" not in os.environ:
        os.environ["INVENTARIO_ARQUIVO"] = str(padrao)
        os.environ["INVENTARIO_DEMONSTRACAO"] = "1"
    os.environ["INVENTARIO_CADASTRO"] = "1"
    servidor = None
    try:
        # A porta é reservada antes da cópia inicial e da abertura do navegador.
        servidor = create_server(create_app(), host=os.environ.get("INVENTARIO_HOST", "127.0.0.1"), port=8000)
        preparar_base(os.environ["INVENTARIO_ARQUIVO"])
        print(f"Prévia web: {URL_PREVIA}", flush=True)
        print("Mantenha este terminal aberto. Ctrl+C encerra esta prévia.", flush=True)
        if abrir_navegador:
            Thread(target=_abrir_no_navegador, daemon=True).start()
        servidor.run()
    except KeyboardInterrupt:
        print("\nPrévia encerrada.")
    except OSError as erro:
        print(f"Não foi possível iniciar a prévia: {erro}")
    finally:
        if servidor is not None:
            servidor.close()
            servidor.task_dispatcher.shutdown()


if __name__ == "__main__":
    main()
