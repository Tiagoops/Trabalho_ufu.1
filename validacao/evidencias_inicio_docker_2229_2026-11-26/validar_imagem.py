"""Smoke test do CMD real da imagem, sem entrada e com base fictícia isolada."""
import hashlib
import http.cookiejar
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler
from uuid import uuid4

pasta = Path(__file__).resolve().parent
imagem = sys.argv[1]
nome = "ufu-inicio-smoke-" + uuid4().hex[:10]

def docker(*args, entrada=None):
    return subprocess.check_output(["docker", *args], input=entrada, encoding="utf-8", timeout=35).strip()

def inspecionar():
    return json.loads(docker("inspect", nome))[0]

with tempfile.TemporaryDirectory(prefix="base-ficticia-", dir=pasta) as temporaria:
    dados = Path(temporaria).resolve()
    assert dados.is_relative_to(pasta.resolve())
    base = dados / "inventario.json"
    base.write_bytes(b"[]\n")
    criou = False
    try:
        docker("run", "-d", "--name", nome, "--read-only", "--user", "65534:65534",
               "-p", "127.0.0.1::2229", "--mount", f"type=bind,source={dados},target=/dados", imagem)
        criou = True
        info = inspecionar()
        publicado = info["NetworkSettings"]["Ports"].get("2229/tcp")
        assert publicado and publicado[0]["HostIp"] == "127.0.0.1"
        url = "http://127.0.0.1:" + publicado[0]["HostPort"]
        cliente = build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))

        def aguardar():
            for _ in range(40):
                try:
                    with cliente.open(url + "/metadados", timeout=2) as r:
                        metadados = json.load(r)
                    assert metadados["inventario_disponivel"] is True
                    return metadados
                except (URLError, ConnectionError):
                    estado = inspecionar()["State"]
                    assert estado["Running"], "CMD encerrou: " + docker("logs", nome)
                    time.sleep(.25)
            raise AssertionError("servidor não ficou pronto: " + docker("logs", nome))

        aguardar()
        assert info["Config"]["Cmd"] == ["python", "-B", "iniciar_web.py"]
        assert info["Config"]["OpenStdin"] is False
        assert base.read_bytes() == b"[]\n"
        with cliente.open(url + "/ativos/novo") as r:
            token = re.search(r'name="csrf_token" value="([^"]+)"', r.read().decode()).group(1)
        with cliente.open(url + "/ativos/novo", urlencode({"csrf_token":token, "id_ativo":"9907",
                "hostname":"demo-inicio-9907", "responsavel":"Pessoa fictícia", "setor":"Laboratório fictício",
                "tipo":"NOTEBOOK", "website":""}).encode()) as r:
            assert "cadastrado com sucesso" in r.read().decode()
        gravado = base.read_bytes()
        assert json.loads(gravado)[0]["id_ativo"] == 9907
        saida_cli = docker("exec", "-i", nome, "python", "-B", "main.py", "--terminal", entrada="0\n")
        assert "Base em uso: /dados/inventario.json" in saida_cli
        assert "Como deseja iniciar?" not in saida_cli
        assert base.read_bytes() == gravado
        docker("restart", "--time", "1", nome)
        apos_reinicio = inspecionar()
        porta_apos = apos_reinicio["NetworkSettings"]["Ports"]["2229/tcp"][0]["HostPort"]
        url = "http://127.0.0.1:" + porta_apos
        aguardar()
        assert base.read_bytes() == gravado
        assert "Inicialização cancelada" not in docker("logs", nome)
        resultado = {"imagem":imagem, "id":info["Image"], "cmd":info["Config"]["Cmd"],
            "stdin_fechado":True, "porta_interna":2229, "porta_externa_ficticia":int(publicado[0]["HostPort"]),
            "porta_ficticia_apos_reinicio":int(porta_apos),
            "http_metadados":200, "cadastro_ficticio":9907, "cli_explicita":True,
            "persistencia_apos_reiniciar":True, "sha256_base_ficticia":hashlib.sha256(gravado).hexdigest()}
        (pasta / "smoke_aprovado.json").write_text(json.dumps(resultado,indent=2),encoding="utf-8")
        print(json.dumps(resultado))
    finally:
        if criou:
            docker("rm", "-f", nome)
