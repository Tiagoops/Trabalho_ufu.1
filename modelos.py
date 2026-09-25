"""
Classes de domínio: Ativo de TI e Vulnerabilidade.

Cada classe sabe se converter para dict (para gravação em arquivo de texto,
Requisito 3) e se reconstruir a partir de um dict (para leitura da base).
"""

from __future__ import annotations  # garante compatibilidade com Python 3.8+

from dataclasses import dataclass, field
from typing import List

from tipos import TipoAtivo, Severidade, StatusVulnerabilidade, rotulo_severidade, rotulo_status


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
        return Vulnerabilidade(
            descricao=d["descricao"],
            categoria=d["categoria"],
            severidade=Severidade[d["severidade"]],
            status=StatusVulnerabilidade[d["status"]],
        )

    def __str__(self) -> str:
        return (
            f"  - [{rotulo_severidade(self.severidade)}] {self.descricao} "
            f"(Categoria: {self.categoria} | Status: {rotulo_status(self.status)})"
        )


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
