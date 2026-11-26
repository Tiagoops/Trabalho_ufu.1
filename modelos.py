"""Ativos e ocorrências de vulnerabilidades; severidade não é risco agregado."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, fields
import json
import math
from typing import Dict, List, Optional
from uuid import NAMESPACE_URL, uuid4, uuid5

from catalogo_cvss import CVE_RE
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
    cve: Optional[str] = None

    def __post_init__(self) -> None:
        self.severidade = validar_numero(self.severidade, "severidade", 10)
        if self.vetor_cvss is not None:
            nota, normalizado = calcular_cvss(self.vetor_cvss)
            if self.severidade != nota:
                raise ValueError("severidade não corresponde ao vetor CVSS")
            self.vetor_cvss = normalizado
        if self.fonte_severidade is not None:
            _validar_textos({"fonte": self.fonte_severidade}, ("fonte",))
        self._validar_referencia_cve()

    def _validar_referencia_cve(self) -> None:
        if self.cve is not None:
            if not isinstance(self.cve, str) or not CVE_RE.fullmatch(self.cve):
                raise ValueError("CVE inválida: use CVE-AAAA-NNNN ou mais dígitos")
            if self.fonte_severidade != f"https://nvd.nist.gov/vuln/detail/{self.cve}":
                raise ValueError("a fonte NVD deve corresponder à CVE registrada")

    @classmethod
    def por_cvss(cls, descricao: str, categoria: str, vetor: str, *,
                 cve: Optional[str] = None, fonte_severidade: Optional[str] = None) -> Vulnerabilidade:
        nota, normalizado = calcular_cvss(vetor)
        return cls(descricao, categoria, nota, vetor_cvss=normalizado,
                   cve=cve, fonte_severidade=fonte_severidade)

    def to_dict(self) -> dict:
        self._validar_referencia_cve()
        return {
            "descricao": self.descricao,
            "categoria": self.categoria,
            "severidade": validar_numero(self.severidade, "severidade", 10),
            "id_vulnerabilidade": self.id_vulnerabilidade,
            **({"vetor_cvss": self.vetor_cvss} if self.vetor_cvss is not None else {}),
            **({"fonte_severidade": self.fonte_severidade} if self.fonte_severidade is not None else {}),
            **({"cve": self.cve} if self.cve is not None else {}),
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
                               d.get("vetor_cvss"), d.get("fonte_severidade"), d.get("cve"))

    def formatar(self, numero: Optional[int] = None) -> str:
        prefixo = f"  [{numero}] " if numero is not None else "  - "
        origem = " | ".join(v for v in (self.vetor_cvss, self.fonte_severidade) if v)
        origem = origem or "informada anteriormente; sem critérios registrados"
        referencia = f" | CVE: {self.cve}" if self.cve is not None else ""
        return (f"{prefixo}[Severidade: {self.severidade:g}] {self.descricao} "
                f"(Categoria: {self.categoria} | ID: {self.id_vulnerabilidade}{referencia} | Origem: {origem})")

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

    def __eq__(self, outro):
        if not isinstance(outro, Ativo):
            return NotImplemented
        return all(getattr(self, campo.name) == getattr(outro, campo.name)
                   for campo in fields(Ativo))

    def __post_init__(self) -> None:
        if type(self) is not Ativo:
            self._validar_tipo_concreto()

    def _validar_tipo_concreto(self) -> None:
        if not isinstance(self.tipo, TipoAtivo):
            raise ValueError("tipo deve ser uma categoria TipoAtivo")
        if type(self) is not Ativo and CLASSES_POR_TIPO[self.tipo] is not type(self):
            raise ValueError("tipo do cadastro incompatível com a classe do ativo")

    @staticmethod
    def criar(id_ativo: int, hostname: str, responsavel: str, setor: str, tipo: TipoAtivo,
              vulnerabilidades=None, dependencias=None, campos_extras=None,
              avaliacoes_dependencias=None) -> Ativo:
        """Seleciona um dos oito tipos concretos sem mudar os campos do cadastro."""
        if not isinstance(tipo, TipoAtivo):
            raise ValueError("tipo deve ser uma categoria TipoAtivo")
        return CLASSES_POR_TIPO[tipo](
            id_ativo, hostname, responsavel, setor, tipo,
            [] if vulnerabilidades is None else vulnerabilidades,
            {} if dependencias is None else dependencias,
            {} if campos_extras is None else campos_extras,
            {} if avaliacoes_dependencias is None else avaliacoes_dependencias,
        )

    def orientacoes_tratamento(self) -> tuple[str, ...]:
        """Consulta de preparação e verificação; não executa correções."""
        return ("Revisar as ocorrências cadastradas e verificar as correções.",)

    def to_dict(self) -> dict:
        self._validar_tipo_concreto()
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
        try:
            json.dumps(d, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (ValueError, TypeError, OverflowError, RecursionError) as erro:
            raise ValueError("O documento deve conter JSON válido, números finitos e texto UTF-8 válido.") from erro
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
        return Ativo.criar(
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
class EstacaoTrabalho(Ativo):
    def orientacoes_tratamento(self) -> tuple[str, ...]:
        return super().orientacoes_tratamento() + (
            "Proteger arquivos do usuário e testar login e aplicativos após a correção.",)


class Notebook(EstacaoTrabalho):
    def orientacoes_tratamento(self) -> tuple[str, ...]:
        return super().orientacoes_tratamento() + (
            "Garantir energia e conexão estáveis; conferir acesso remoto e dados em mobilidade.",)


class Servidor(Ativo):
    def orientacoes_tratamento(self) -> tuple[str, ...]:
        return super().orientacoes_tratamento() + (
            "Planejar janela dos serviços e conferir cópia recuperável antes da correção.",
            f"Verificar serviços, clientes e as {len(self.dependencias)} dependência(s) cadastrada(s).",)


class Roteador(Ativo):
    def orientacoes_tratamento(self) -> tuple[str, ...]:
        return super().orientacoes_tratamento() + (
            "Exportar configuração antes da correção; depois validar rotas e conectividade.",)


class ImpressoraRede(Ativo):
    def orientacoes_tratamento(self) -> tuple[str, ...]:
        return super().orientacoes_tratamento() + (
            "Proteger configuração e credenciais; testar fila e impressão pela rede.",)


class Software(Ativo):
    def orientacoes_tratamento(self) -> tuple[str, ...]:
        return super().orientacoes_tratamento() + (
            "Confirmar produto e versão, preparar retorno e executar testes funcionais.",)


class AplicacaoWeb(Software):
    def orientacoes_tratamento(self) -> tuple[str, ...]:
        return super().orientacoes_tratamento() + (
            "Validar autenticação, rotas e integrações da aplicação web.",)


class SistemaBancoDados(Software):
    def orientacoes_tratamento(self) -> tuple[str, ...]:
        return ("Conferir backup e restauração em ambiente separado antes da atualização.",) + (
            super().orientacoes_tratamento()) + (
            "Validar integridade, permissões e consultas das aplicações dependentes.",)


CLASSES_POR_TIPO = {
    TipoAtivo.NOTEBOOK: Notebook,
    TipoAtivo.SERVIDOR: Servidor,
    TipoAtivo.ROTEADOR: Roteador,
    TipoAtivo.SOFTWARE_LICENCIADO: Software,
    TipoAtivo.APLICACAO_WEB: AplicacaoWeb,
    TipoAtivo.BANCO_DE_DADOS: SistemaBancoDados,
    TipoAtivo.IMPRESSORA_REDE: ImpressoraRede,
    TipoAtivo.ESTACAO_TRABALHO: EstacaoTrabalho,
}
