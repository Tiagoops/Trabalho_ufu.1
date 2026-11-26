"""Inicia o cadastro demonstrativo sem sobrescrever uma base existente."""
import os
import json
import subprocess
from hashlib import sha256
from pathlib import Path, PurePosixPath
from http.client import HTTPConnection, HTTPException
from threading import Thread
import webbrowser

from app_web import EXEMPLO, create_app
from configuracao import caminho_inventario, identidade_base


def preparar_base(caminho):
    """Inicialização explícita; requisições HTTP nunca criam a base."""
    caminho = Path(caminho).resolve()
    if caminho == EXEMPLO:
        raise ValueError("o exemplo versionado não pode ser a base de gravação")
    original = b'[]\n'
    caminho.parent.mkdir(parents=True, exist_ok=True)
    try:
        with caminho.open("xb") as arquivo:
            arquivo.write(original)
            arquivo.flush()
            os.fsync(arquivo.fileno())
    except FileExistsError:
        pass


URL_PREVIA = "http://127.0.0.1:8000/"


def _identidades_docker(caminho, porta):
    """Reconhece o mesmo arquivo através de uma montagem, sem presumir /dados."""
    identidades = set()
    try:
        lista = subprocess.run(['docker', 'ps', '-q'],
                               capture_output=True, text=True, timeout=2)
        containers = lista.stdout.split()
        if lista.returncode or not containers:
            return identidades
        formato = '{"NetworkSettings":{"Ports":{{json .NetworkSettings.Ports}}},"Mounts":{{json .Mounts}}}'
        inspecao = subprocess.run(['docker', 'inspect', '--format', formato, *containers],
                                  capture_output=True, text=True, timeout=2)
        if inspecao.returncode:
            return identidades
        for linha in inspecao.stdout.splitlines():
            container = json.loads(linha)
            publicadas = container.get('NetworkSettings', {}).get('Ports', {}).get('8000/tcp') or []
            if not any(p.get('HostIp') == '127.0.0.1' and p.get('HostPort') == str(porta) for p in publicadas):
                continue
            for montagem in container.get('Mounts', []):
                if montagem.get('Type') != 'bind':
                    continue
                try:
                    relativo = caminho.resolve().relative_to(Path(montagem['Source']).resolve())
                except ValueError:
                    continue
                interno = str(PurePosixPath(montagem['Destination'], *relativo.parts))
                identidades.add(sha256(interno.encode('utf-8')).hexdigest())
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError, AttributeError):
        return set()
    return identidades


def _estado_previa(porta=8000):
    conexao = HTTPConnection("127.0.0.1", porta, timeout=1)
    try:
        conexao.request("GET", "/metadados")
        resposta = conexao.getresponse()
        try:
            if resposta.status not in (200, 503) or resposta.getheader("X-Inventario-App") != "inventario-ti":
                return "ocupada"
            corpo = resposta.read(4097)
            if len(corpo) > 4096:
                return "ocupada"
            dados = json.loads(corpo)
            if (not isinstance(dados, dict) or dados.get('aplicacao') != 'inventario-ti'
                    or type(dados.get('protocolo')) is not int or dados['protocolo'] != 1
                    or not isinstance(dados.get('base_id'), str)):
                return "ocupada"
            caminho = caminho_inventario()
            if dados['base_id'] == identidade_base(caminho):
                return "inventario"
            return "inventario" if dados['base_id'] in _identidades_docker(caminho, porta) else "diferente"
        finally:
            resposta.close()
    except ConnectionRefusedError:
        return "livre"
    except (OSError, HTTPException, ValueError, TypeError):
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


def main(*, abrir_navegador=False) -> int:
    from waitress import create_server

    estado = _estado_previa()
    if estado == "inventario":
        print(f"A prévia já está em execução: {URL_PREVIA}", flush=True)
        if abrir_navegador:
            _abrir_no_navegador()
        return 0
    if estado == "diferente":
        print("A interface na porta 8000 usa outra base. Ela não será reutilizada.")
        print("Encerre essa instância ou use a base correspondente antes de abrir a interface.")
        return 1
    if estado == "ocupada":
        print("Não foi possível validar a instância na porta 8000. Encerre o serviço antigo ou indisponível.")
        print("Encerre o outro serviço ou escolha continuar no terminal.")
        return 1
    padrao = caminho_inventario()
    if "INVENTARIO_ARQUIVO" not in os.environ:
        os.environ["INVENTARIO_ARQUIVO"] = str(padrao)
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
        return 0
    except KeyboardInterrupt:
        print("\nPrévia encerrada.")
        return 0
    except OSError as erro:
        print(f"Não foi possível iniciar a prévia: {erro}")
        return 1
    finally:
        if servidor is not None:
            servidor.close()
            servidor.task_dispatcher.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
