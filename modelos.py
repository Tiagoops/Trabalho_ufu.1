"""
Classes de domínio: Ativo de TI e Vulnerabilidade.

Cada classe sabe se converter para dict (para gravação em arquivo de texto,
Requisito 3) e se reconstruir a partir de um dict (para leitura da base).
"""

from __future__ import annotations  # garante compatibilidade com Python 3.8+

from dataclasses import dataclass, field
from typing import List, Optional

from tipos import TipoAtivo, Severidade, StatusVulnerabilidade, rotulo_severidade, rotulo_status
from cores import colorir_severidade, colorir_status


def _validar_textos(d: dict, campos) -> None:
    if not isinstance(d, dict):
        raise ValueError("o registro deve ser um objeto JSON")
    for campo in campos:
        if not isinstance(d[campo], str) or not d[campo].strip():
            raise ValueError(f"campo '{campo}' deve ser texto não vazio")


@dataclass
class Vulnerabilidade:
    """
    Representa uma vulnerabilidade associada a um ativo de TI.
    Requisito 7: descrição, categoria, severidade e status de tratamento.
    """
    descricao: str
    categoria: str
    severidade: Severidade
    status: StatusVulnerabilidade

    def to_dict(self) -> dict:
        return {
            "descricao": self.descricao,
            "categoria": self.categoria,
            "severidade": self.severidade.name,
            "status": self.status.name,
        }

    @staticmethod
    def from_dict(d: dict) -> "Vulnerabilidade":
        _validar_textos(d, ("descricao", "categoria", "severidade", "status"))
        return Vulnerabilidade(
            descricao=d["descricao"],
            categoria=d["categoria"],
            severidade=Severidade[d["severidade"]],
            status=StatusVulnerabilidade[d["status"]],
        )

    def formatar(self, numero: Optional[int] = None) -> str:
        """
        Texto de exibição. Se 'numero' for informado, a linha começa com
        '[n]' (usado nas telas em que o usuário precisa escolher uma
        vulnerabilidade da lista); caso contrário, começa com um '-'.
        """
        prefixo = f"  [{numero}] " if numero is not None else "  - "
        severidade_txt = colorir_severidade(
            self.severidade.name, f"[{rotulo_severidade(self.severidade)}]"
        )
        status_txt = colorir_status(self.status.name, rotulo_status(self.status))
        return (
            f"{prefixo}{severidade_txt} {self.descricao} "
            f"(Categoria: {self.categoria} | Status: {status_txt})"
        )

    def __str__(self) -> str:
        return self.formatar()


@dataclass
class Ativo:
    """
    Representa um ativo de TI cadastrado no inventário.
    Requisito 3: identificador único (int), nome/hostname, responsável,
    setor/localização, tipo de ativo e lista de vulnerabilidades associadas.
    """
    id_ativo: int
    hostname: str
    responsavel: str
    setor: str
    tipo: TipoAtivo
    vulnerabilidades: List[Vulnerabilidade] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id_ativo": self.id_ativo,
            "hostname": self.hostname,
            "responsavel": self.responsavel,
            "setor": self.setor,
            "tipo": self.tipo.name,
            "vulnerabilidades": [v.to_dict() for v in self.vulnerabilidades],
        }

    @staticmethod
    def from_dict(d: dict) -> "Ativo":
        _validar_textos(d, ("hostname", "responsavel", "setor", "tipo"))
        if type(d["id_ativo"]) is not int or d["id_ativo"] < 1:
            raise ValueError("id_ativo deve ser um inteiro positivo")
        if not isinstance(d.get("vulnerabilidades", []), list):
            raise ValueError("vulnerabilidades deve ser uma lista")
        return Ativo(
            id_ativo=d["id_ativo"],
            hostname=d["hostname"],
            responsavel=d["responsavel"],
            setor=d["setor"],
            tipo=TipoAtivo[d["tipo"]],
            vulnerabilidades=[
                Vulnerabilidade.from_dict(v) for v in d.get("vulnerabilidades", [])
            ],
        )

    def __str__(self) -> str:
        linhas = [
            f"ID: {self.id_ativo}",
            f"Hostname: {self.hostname}",
            f"Responsável: {self.responsavel}",
            f"Setor/Localização: {self.setor}",
            f"Tipo: {self.tipo.name} (código {self.tipo.value})",
            f"Qtd. de vulnerabilidades: {len(self.vulnerabilidades)}",
        ]
        return "\n".join(linhas)
