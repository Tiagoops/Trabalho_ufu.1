"""Ativos e ocorrências de vulnerabilidades; severidade não é risco agregado."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional
from uuid import NAMESPACE_URL, uuid4, uuid5

from tipos import TipoAtivo
from avaliacao import AvaliacaoDependencia, calcular_cvss


def validar_numero(valor, campo: str, limite: float, *, exclusivo=False) -> float:
    """Aceita números JSON finitos; bool não é uma pontuação."""
    if type(valor) not in (int, float):
        raise ValueError(f"{campo} deve ser numérico e finito")
    try:
        numero = float(valor)
    except (OverflowError, ValueError) as erro:
        raise ValueError(f"{campo} deve ser numérico e finito") from erro
    if not math.isfinite(numero) or numero < 0 or (
        numero >= limite if exclusivo else numero > limite
    ):
        fechamento = ")" if exclusivo else "]"
        raise ValueError(f"{campo} deve estar em [0, {limite}{fechamento}")
    return numero


def _validar_textos(d: dict, campos) -> None:
    if not isinstance(d, dict):
        raise ValueError("o registro deve ser um objeto JSON")
    for campo in campos:
        if not isinstance(d[campo], str) or not d[campo].strip():
            raise ValueError(f"campo '{campo}' deve ser texto não vazio")


@dataclass
class Vulnerabilidade:
    """Uma ocorrência cadastrada em um ativo, identificada por ID estável."""
    descricao: str
    categoria: str
    severidade: float
    id_vulnerabilidade: str = field(default_factory=lambda: str(uuid4()))
    vetor_cvss: Optional[str] = None
    fonte_severidade: Optional[str] = None

    def __post_init__(self) -> None:
        self.severidade = validar_numero(self.severidade, "severidade", 10)
        if self.vetor_cvss is not None:
            nota, normalizado = calcular_cvss(self.vetor_cvss)
            if self.severidade != nota:
                raise ValueError("severidade não corresponde ao vetor CVSS")
            self.vetor_cvss = normalizado
        if self.fonte_severidade is not None:
            _validar_textos({"fonte": self.fonte_severidade}, ("fonte",))

    @classmethod
    def por_cvss(cls, descricao: str, categoria: str, vetor: str) -> Vulnerabilidade:
        nota, normalizado = calcular_cvss(vetor)
        return cls(descricao, categoria, nota, vetor_cvss=normalizado)

    def to_dict(self) -> dict:
        return {
            "descricao": self.descricao,
            "categoria": self.categoria,
            "severidade": validar_numero(self.severidade, "severidade", 10),
            "id_vulnerabilidade": self.id_vulnerabilidade,
            **({"vetor_cvss": self.vetor_cvss} if self.vetor_cvss is not None else {}),
            **({"fonte_severidade": self.fonte_severidade} if self.fonte_severidade is not None else {}),
        }

    @staticmethod
    def from_dict(d: dict, referencia: str = "") -> Vulnerabilidade:
        _validar_textos(d, ("descricao", "categoria"))
        if "status" in d:
            raise ValueError("registro antigo: prepare a migração antes de carregar")
        identificador = d.get("id_vulnerabilidade")
        if "id_vulnerabilidade" not in d:
            identificador = str(uuid5(NAMESPACE_URL, "ufu:ocorrencia:" + referencia))
        _validar_textos({"id": identificador}, ("id",))
        return Vulnerabilidade(d["descricao"], d["categoria"], d["severidade"], identificador,
                               d.get("vetor_cvss"), d.get("fonte_severidade"))

    def formatar(self, numero: Optional[int] = None) -> str:
        prefixo = f"  [{numero}] " if numero is not None else "  - "
        origem = self.vetor_cvss or self.fonte_severidade or "informada anteriormente; sem critérios registrados"
        return (f"{prefixo}[Severidade: {self.severidade:g}] {self.descricao} "
                f"(Categoria: {self.categoria} | ID: {self.id_vulnerabilidade} | Origem: {origem})")

    def __str__(self) -> str:
        return self.formatar()


@dataclass
class Ativo:
    id_ativo: int
    hostname: str
    responsavel: str
    setor: str
    tipo: TipoAtivo
    vulnerabilidades: List[Vulnerabilidade] = field(default_factory=list)
    dependencias: Dict[int, float] = field(default_factory=dict)
    campos_extras: dict = field(default_factory=dict, repr=False)
    avaliacoes_dependencias: Dict[int, AvaliacaoDependencia] = field(default_factory=dict)

    def to_dict(self) -> dict:
        for destino, peso in self.dependencias.items():
            if type(destino) is not int or destino < 1 or destino == self.id_ativo:
                raise ValueError("ID de dependência inválido ou autodependência")
            validar_numero(peso, "peso", 1, exclusivo=True)
        for destino, avaliacao in self.avaliacoes_dependencias.items():
            if type(destino) is not int or not isinstance(avaliacao, AvaliacaoDependencia):
                raise ValueError("avaliação de dependência inválida")
            if destino not in self.dependencias or self.dependencias[destino] != avaliacao.peso:
                raise ValueError("peso não corresponde aos critérios da dependência")
        if len({a.total_servicos for a in self.avaliacoes_dependencias.values()}) > 1:
            raise ValueError("o total de serviços deve ser igual nos vínculos avaliados do mesmo ativo")
        return {
            **deepcopy(self.campos_extras),
            "id_ativo": self.id_ativo,
            "hostname": self.hostname,
            "responsavel": self.responsavel,
            "setor": self.setor,
            "tipo": self.tipo.name,
            "vulnerabilidades": [v.to_dict() for v in self.vulnerabilidades],
            "dependencias": {str(k): v for k, v in self.dependencias.items()},
            **({"avaliacoes_dependencias": {str(k): v.to_dict() for k, v in self.avaliacoes_dependencias.items()}}
               if self.avaliacoes_dependencias else {}),
        }

    @staticmethod
    def from_dict(d: dict) -> Ativo:
        _validar_textos(d, ("hostname", "responsavel", "setor", "tipo"))
        if type(d["id_ativo"]) is not int or d["id_ativo"] < 1:
            raise ValueError("id_ativo deve ser um inteiro positivo")
        if not isinstance(d.get("vulnerabilidades", []), list):
            raise ValueError("vulnerabilidades deve ser uma lista")
        deps = d.get("dependencias", {})
        if not isinstance(deps, dict):
            raise ValueError("dependencias deve ser um objeto de IDs e pesos")
        dependencias = {}
        for chave, peso in deps.items():
            if not isinstance(chave, str) or not chave.isascii() or not chave.isdecimal():
                raise ValueError("destino da dependência deve ser um ID inteiro positivo")
            destino = int(chave)
            if destino < 1 or str(destino) != chave or destino == d["id_ativo"]:
                raise ValueError("ID de dependência inválido ou autodependência")
            dependencias[destino] = validar_numero(peso, "peso", 1, exclusivo=True)
        conhecidos = {"id_ativo", "hostname", "responsavel", "setor", "tipo",
                      "vulnerabilidades", "dependencias", "avaliacoes_dependencias"}
        criterios = d.get("avaliacoes_dependencias", {})
        if not isinstance(criterios, dict):
            raise ValueError("avaliações de dependências devem ser um objeto JSON")
        avaliacoes = {}
        for chave, valores in criterios.items():
            if chave not in deps or not isinstance(valores, dict):
                raise ValueError("avaliação sem dependência correspondente")
            try:
                avaliacao = AvaliacaoDependencia(**valores)
            except TypeError as erro:
                raise ValueError("estrutura de avaliação da dependência inválida") from erro
            if avaliacao.peso != dependencias[int(chave)]:
                raise ValueError("peso não corresponde aos critérios da dependência")
            avaliacoes[int(chave)] = avaliacao
        if len({a.total_servicos for a in avaliacoes.values()}) > 1:
            raise ValueError("o total de serviços deve ser igual nos vínculos avaliados do mesmo ativo")
        return Ativo(
            d["id_ativo"], d["hostname"], d["responsavel"], d["setor"], TipoAtivo[d["tipo"]],
            [Vulnerabilidade.from_dict(v, f"{d['id_ativo']}:{i}")
             for i, v in enumerate(d.get("vulnerabilidades", []))],
            dependencias, deepcopy({k: v for k, v in d.items() if k not in conhecidos}),
            avaliacoes,
        )

    def __str__(self) -> str:
        return "\n".join([
            f"ID: {self.id_ativo}", f"Hostname: {self.hostname}",
            f"Responsável: {self.responsavel}", f"Setor/Localização: {self.setor}",
            f"Tipo: {self.tipo.name} (código {self.tipo.value})",
            f"Qtd. de vulnerabilidades: {len(self.vulnerabilidades)}",
            f"Qtd. de dependências: {len(self.dependencias)}",
        ])
