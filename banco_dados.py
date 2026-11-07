"""Persistência JSON com índices e restauração do último estado salvo.

Uma única instância deve escrever na base por vez. Não há coordenação entre
processos concorrentes nem garantia de durabilidade contra queda de energia.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from modelos import Ativo

CAMINHO_ARQUIVO_PADRAO = str(Path(__file__).resolve().parent / "ativos_db.txt")


class BancoDeDados:
    def __init__(self, caminho: str = CAMINHO_ARQUIVO_PADRAO):
        self.caminho = os.fspath(caminho)
        self.ativos_por_id: Dict[int, Ativo] = {}
        self.ativos_por_hostname: Dict[str, Ativo] = {}
        self._gravacao_bloqueada = False
        self._estado_salvo = []
        self._carregar()
        self._estado_salvo = self._capturar_estado()

    def _carregar(self) -> None:
        try:
            with open(self.caminho, "rb") as arquivo:
                original = arquivo.read()
        except FileNotFoundError:
            return
        except OSError as erro:
            self._gravacao_bloqueada = True
            print(
                f"[Aviso] Não foi possível acessar a base ({erro}). "
                "Gravações bloqueadas; verifique o caminho e as permissões."
            )
            return
        try:
            conteudo = original.decode("utf-8").strip()
            if not conteudo:
                return
            dados = json.loads(conteudo)
            if not isinstance(dados, list):
                raise ValueError("a raiz da base deve ser uma lista")
            ativos = [Ativo.from_dict(item) for item in dados]
            self._validar_unicidade(ativos)
        except (ValueError, KeyError, TypeError, AttributeError) as erro:
            self._isolar_base_ilegivel(erro, original)
            return
        for ativo in ativos:
            self._indexar(ativo)

    @staticmethod
    def _validar_unicidade(ativos: List[Ativo]) -> None:
        ids = set()
        hostnames = set()
        for ativo in ativos:
            Ativo.from_dict(ativo.to_dict())
            if ativo.id_ativo in ids:
                raise ValueError(f"ID {ativo.id_ativo} repetido")
            chave = ativo.hostname.lower()
            if chave in hostnames:
                raise ValueError(f"hostname '{ativo.hostname}' repetido")
            ids.add(ativo.id_ativo)
            hostnames.add(chave)

    def _isolar_base_ilegivel(self, erro: Exception, original: bytes) -> None:
        """Copia os bytes originais para um backup exclusivo antes de liberar escrita."""
        destino = None
        caminho = Path(self.caminho)
        carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            fd, destino = tempfile.mkstemp(
                prefix=f"{caminho.name}.{carimbo}.", suffix=".bak", dir=str(caminho.parent)
            )
            with os.fdopen(fd, "wb") as arquivo:
                arquivo.write(original)
                arquivo.flush()
                os.fsync(arquivo.fileno())
        except OSError as erro_arquivo:
            self._gravacao_bloqueada = True
            self._limpar_temporario(destino)
            print(
                f"[Aviso] Base inválida ({erro}); backup falhou ({erro_arquivo}). "
                "Gravações bloqueadas para preservar o original."
            )
            return
        print(
            f"[Aviso] Base inválida ({erro}). Backup preservado em '{destino}'. "
            "Iniciando com base vazia; o original só será substituído ao salvar."
        )

    def _capturar_estado(self):
        """Guarda valores e referências para restaurar inclusive aliases externos."""
        return [
            (
                ativo,
                (ativo.id_ativo, ativo.hostname, ativo.responsavel, ativo.setor, ativo.tipo),
                ativo.vulnerabilidades,
                [(v, (v.descricao, v.categoria, v.severidade, v.status))
                 for v in ativo.vulnerabilidades],
            )
            for ativo in self.ativos_por_id.values()
        ]

    def _restaurar_estado(self) -> None:
        self.ativos_por_id.clear()
        self.ativos_por_hostname.clear()
        for ativo, campos, lista, vulnerabilidades in self._estado_salvo:
            (ativo.id_ativo, ativo.hostname, ativo.responsavel, ativo.setor, ativo.tipo) = campos
            for vulnerabilidade, valores in vulnerabilidades:
                (vulnerabilidade.descricao, vulnerabilidade.categoria,
                 vulnerabilidade.severidade, vulnerabilidade.status) = valores
            lista[:] = [v for v, _ in vulnerabilidades]
            ativo.vulnerabilidades = lista
            self._indexar(ativo)

    @staticmethod
    def _limpar_temporario(caminho) -> None:
        if caminho is None:
            return
        try:
            os.unlink(caminho)
        except FileNotFoundError:
            pass
        except OSError as erro:
            print(f"[Aviso] Não foi possível remover o temporário '{caminho}': {erro}")

    def salvar(self) -> None:
        temporario = None
        confirmado = False
        try:
            if self._gravacao_bloqueada:
                raise RuntimeError("gravação bloqueada: a base não pôde ser lida ou protegida")
            ativos = list(self.ativos_por_id.values())
            self._validar_unicidade(ativos)
            dados = [ativo.to_dict() for ativo in ativos]
            estado = self._capturar_estado()
            por_id = {ativo.id_ativo: ativo for ativo in ativos}
            por_hostname = {ativo.hostname.lower(): ativo for ativo in ativos}
            caminho = Path(self.caminho)
            fd, temporario = tempfile.mkstemp(
                prefix=caminho.name + ".", suffix=".tmp", dir=str(caminho.parent)
            )
            with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
                json.dump(dados, arquivo, ensure_ascii=False, indent=2)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, self.caminho)
            confirmado = True
            self._estado_salvo = estado
            self.ativos_por_id.clear()
            self.ativos_por_id.update(por_id)
            self.ativos_por_hostname.clear()
            self.ativos_por_hostname.update(por_hostname)
        except BaseException:
            if not confirmado:
                self._restaurar_estado()
            raise
        finally:
            self._limpar_temporario(temporario)

    def _indexar(self, ativo: Ativo) -> None:
        self.ativos_por_id[ativo.id_ativo] = ativo
        self.ativos_por_hostname[ativo.hostname.lower()] = ativo

    def existe_id(self, id_ativo: int) -> bool:
        return id_ativo in self.ativos_por_id

    def existe_hostname(self, hostname: str, ignorar_id: Optional[int] = None) -> bool:
        ativo = self.ativos_por_hostname.get(hostname.lower())
        return ativo is not None and ativo.id_ativo != ignorar_id

    def adicionar(self, ativo: Ativo) -> None:
        Ativo.from_dict(ativo.to_dict())
        if self.existe_id(ativo.id_ativo):
            raise ValueError(f"já existe um ativo com o ID {ativo.id_ativo}")
        if self.existe_hostname(ativo.hostname):
            raise ValueError(f"já existe um ativo com o hostname '{ativo.hostname}'")
        self._indexar(ativo)
        self.salvar()

    def buscar_por_id(self, id_ativo: int) -> Optional[Ativo]:
        return self.ativos_por_id.get(id_ativo)

    def buscar_por_hostname(self, hostname: str) -> Optional[Ativo]:
        return self.ativos_por_hostname.get(hostname.lower())

    def buscar_por_trecho_hostname(self, trecho: str) -> List[Ativo]:
        return [ativo for ativo in self.ativos_por_id.values()
                if trecho.lower() in ativo.hostname.lower()]

    def remover(self, id_ativo: int) -> Optional[Ativo]:
        ativo = self.ativos_por_id.pop(id_ativo, None)
        if ativo is not None:
            self.ativos_por_hostname.pop(ativo.hostname.lower(), None)
            self.salvar()
        return ativo

    def listar_todos(self) -> List[Ativo]:
        return list(self.ativos_por_id.values())

    def reindexar_apos_edicao(self, ativo: Ativo, hostname_antigo: str) -> None:
        # salvar() valida duplicidades antes de confirmar os novos índices.
        if not any(item is ativo for item in self.ativos_por_id.values()):
            raise ValueError("ativo não pertence a esta base")
        self.salvar()
