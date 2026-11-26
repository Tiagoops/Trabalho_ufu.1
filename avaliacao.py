"""Severidades CVSS e participação de serviços; não infere falhas de um nome."""
from dataclasses import asdict, dataclass
import math

from cvss import CVSS3, CVSS4
from cvss.exceptions import CVSSError


def calcular_cvss(vetor: str) -> tuple[float, str]:
    """Calcula somente métricas Base CVSS 3.1 ou 4.0, sem notas inventadas."""
    if not isinstance(vetor, str):
        raise ValueError("informe um vetor CVSS 3.1 ou 4.0")
    vetor = vetor.strip()
    if vetor.startswith("CVSS:4.0/"):
        classe, permitidas = CVSS4, {"AV", "AC", "AT", "PR", "UI", "VC", "VI", "VA", "SC", "SI", "SA"}
    elif vetor.startswith("CVSS:3.1/"):
        classe, permitidas = CVSS3, {"AV", "AC", "PR", "UI", "S", "C", "I", "A"}
    else:
        raise ValueError("use um vetor Base CVSS:3.1/... ou CVSS:4.0/...")
    metricas = [parte.split(":", 1)[0] for parte in vetor.split("/")[1:]]
    if set(metricas) != permitidas or len(metricas) != len(permitidas):
        raise ValueError("informe todas as métricas Base, sem extras nem duplicatas")
    try:
        calculadora = classe(vetor)
        return float(calculadora.scores()[0]), calculadora.clean_vector()
    except CVSSError as erro:
        raise ValueError(f"vetor CVSS inválido: {erro}") from erro


@dataclass(frozen=True)
class AvaliacaoDependencia:
    """Aij = serviços fornecidos por j / serviços necessários a i.

    Os serviços têm igual importância neste critério. A indisponibilidade é
    uma observação separada, não um multiplicador nem previsão de falhas.
    """
    total_servicos: int
    servicos_fornecidos: int
    duracao_falha_min: float | None = None
    indisponibilidade_min: float | None = None
    fonte_medicao: str | None = None

    def __post_init__(self) -> None:
        if type(self.total_servicos) is not int or self.total_servicos <= 0:
            raise ValueError("total de serviços deve ser inteiro positivo")
        if (type(self.servicos_fornecidos) is not int
                or not 0 <= self.servicos_fornecidos <= self.total_servicos):
            raise ValueError("serviços fornecidos devem ser um inteiro entre zero e o total")
        if self.servicos_fornecidos == self.total_servicos:
            raise ValueError("dependência integral (100%): Aij=1 não é permitido pelo modelo; não será reduzido artificialmente")
        valores = (self.duracao_falha_min, self.indisponibilidade_min)
        if all(v is None for v in valores):
            if self.fonte_medicao is not None:
                raise ValueError("fonte de medição exige os tempos observados")
            return
        try:
            validos = all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in valores)
        except OverflowError:
            validos = False
        if not validos or self.duracao_falha_min <= 0:
            raise ValueError("informe tempos finitos: duração da falha > 0 e indisponibilidade >= 0")
        if self.indisponibilidade_min > self.duracao_falha_min:
            raise ValueError("indisponibilidade deve estar dentro da janela da falha")
        if not isinstance(self.fonte_medicao, str) or not self.fonte_medicao.strip():
            raise ValueError("identifique a fonte da medição ou o cenário fictício")

    @property
    def peso(self) -> float:
        return self.servicos_fornecidos / self.total_servicos

    @property
    def indisponibilidade_percentual(self) -> float | None:
        if self.duracao_falha_min is None:
            return None
        return 100 * (self.indisponibilidade_min / self.duracao_falha_min)

    def to_dict(self) -> dict:
        return asdict(self)


METRICAS_CVSS4 = (
    ("AV", "Vetor de ataque: por onde a falha pode ser explorada", {
        "N": "rede remota", "A": "rede adjacente (ex.: mesma rede local)",
        "L": "acesso local ao ambiente", "P": "contato físico com o equipamento"}),
    ("AC", "Complexidade: necessidade de contornar proteções contra o ataque", {
        "L": "baixa, sem contornar essas proteções", "H": "alta, exige contorná-las"}),
    ("AT", "Pré-condições: condições específicas de execução ou implantação", {
        "N": "nenhuma condição especial", "P": "depende dessas condições"}),
    ("PR", "Privilégios: permissões que o atacante precisa ter antes do ataque", {
        "N": "nenhuma", "L": "permissões básicas", "H": "permissões elevadas/administrativas"}),
    ("UI", "Interação: participação de outra pessoa para explorar a falha", {
        "N": "dispensa interação", "P": "passiva, interação limitada/involuntária",
        "A": "ativa, ação específica consciente ou quebra de proteção"}),
    ("VC", "Confidencialidade do sistema vulnerável: exposição de informações", {
        "N": "sem exposição", "L": "exposição limitada", "H": "exposição total ou de dados críticos"}),
    ("VI", "Integridade do sistema vulnerável: alteração indevida de dados", {
        "N": "sem alteração", "L": "alteração limitada", "H": "alteração total ou com efeito grave"}),
    ("VA", "Disponibilidade do sistema vulnerável: interrupção do funcionamento", {
        "N": "sem interrupção", "L": "redução/interrupção parcial", "H": "interrupção total ou grave"}),
    ("SC", "Confidencialidade de outros sistemas: exposição fora do sistema vulnerável", {
        "N": "sem exposição", "L": "exposição limitada", "H": "exposição total ou de dados críticos"}),
    ("SI", "Integridade de outros sistemas: alteração fora do sistema vulnerável", {
        "N": "sem alteração", "L": "alteração limitada", "H": "alteração total ou com efeito grave"}),
    ("SA", "Disponibilidade de outros sistemas: interrupção fora do sistema vulnerável", {
        "N": "sem interrupção", "L": "redução/interrupção parcial", "H": "interrupção total ou grave"}),
)
