"""
Sistema de Inventário de Segurança - Ativos de TI e Vulnerabilidades
Trabalho de Ciberseguranca - UFU (Sprints 1 e 2)

Execução: python main.py
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import tempfile
import os
import subprocess
import sys
from typing import List, Optional, Tuple

from configuracao import caminho_inventario
from tipos import TipoAtivo
from modelos import Ativo, Vulnerabilidade, validar_numero
from banco_dados import BancoDeDados
from avaliacao import AvaliacaoDependencia, calcular_cvss, METRICAS_CVSS4
from biblioteca import importar_ativos, preparar_importacao
from relatorio import CAMPOS_CSV, preparar_relatorio, validar_celula_csv as _validar_celula_csv
from catalogo_cvss import buscar_catalogo, carregar_catalogo, consultar_nvd


# ------------------------------------------------------------------
# Funções auxiliares de entrada de dados (Requisito 1: tratamento de erros)
# ------------------------------------------------------------------

def ler_inteiro(mensagem: str, minimo: Optional[int] = None) -> int:
    """Lê um inteiro do usuário, repetindo até obter uma entrada válida."""
    while True:
        valor = input(mensagem).strip()
        try:
            numero = int(valor)
        except ValueError:
            print("Entrada inválida. Digite um número inteiro.")
            continue
        if minimo is not None and numero < minimo:
            print(f"O valor deve ser maior ou igual a {minimo}.")
            continue
        return numero


def ler_real(mensagem: str, limite: float, *, exclusivo=False) -> float:
    """Aceita ponto ou vírgula decimal; valida antes de alterar o inventário."""
    while True:
        try:
            numero = float(input(mensagem).strip().replace(",", "."))
            return validar_numero(numero, "valor", limite, exclusivo=exclusivo)
        except ValueError as erro:
            print(f"Entrada inválida: {erro}")


def ler_texto(mensagem: str, permitir_vazio: bool = False) -> str:
    """Lê uma string não vazia (a menos que permitir_vazio=True)."""
    while True:
        valor = input(mensagem).strip()
        if valor or permitir_vazio:
            return valor
        print("Este campo não pode ficar vazio.")


def ler_sim_nao(mensagem: str) -> bool:
    while True:
        valor = input(mensagem).strip().lower()
        if valor in ("s", "sim"):
            return True
        if valor in ("n", "nao", "não"):
            return False
        print("Responda apenas com 's' ou 'n'.")


def ler_numero_da_lista(mensagem: str, total: int) -> int:
    """Lê um número entre 1 e 'total' (posição de um item numa lista exibida)."""
    while True:
        numero = ler_inteiro(mensagem, minimo=1)
        if numero <= total:
            return numero
        print(f"Escolha um número entre 1 e {total}.")


def escolher_enum(mensagem: str, enum_classe):
    """Exibe as opções de um Enum e retorna o valor escolhido pelo usuário."""
    opcoes = list(enum_classe)
    print(mensagem)
    for opcao in opcoes:
        print(f"  {opcao.value} - {opcao.name}")
    while True:
        escolha = ler_inteiro("Escolha o código da opção: ")
        for opcao in opcoes:
            if opcao.value == escolha:
                return opcao
        print("Código inválido. Tente novamente.")


# ------------------------------------------------------------------
# Requisito 3: Cadastro de ativo (Create)
# ------------------------------------------------------------------

def cadastrar_ativo(db: BancoDeDados) -> None:
    print("\n--- Cadastro de novo ativo de TI ---")
    while True:
        id_ativo = ler_inteiro("ID único do ativo (número inteiro): ", minimo=1)
        if db.existe_id(id_ativo):
            print("Já existe um ativo com esse ID. Escolha outro.")
            continue
        break

    # O hostname também precisa ser único, pois é usado como chave de busca.
    while True:
        hostname = ler_texto("Nome/Hostname do ativo: ")
        if db.existe_hostname(hostname):
            print("Já existe um ativo com esse hostname. Escolha outro.")
            continue
        break

    responsavel = ler_texto("Responsável: ")
    setor = ler_texto("Setor/Localização: ")
    tipo = escolher_enum("Tipo de ativo:", TipoAtivo)

    vulnerabilidades = []
    if ler_sim_nao("Deseja cadastrar vulnerabilidades iniciais já conhecidas? (s/n): "):
        vulnerabilidades = ler_multiplas_vulnerabilidades()

    ativo = Ativo.criar(id_ativo, hostname, responsavel, setor, tipo, vulnerabilidades)
    db.adicionar(ativo)
    print(f"\nAtivo '{hostname}' cadastrado com sucesso (ID {id_ativo}).")





def explicar_cvss() -> None:
    """Instruções acessíveis, sem supor que uma descrição prova a exploração."""
    print("\n--- COMO FUNCIONA O CVSS ---")
    print("CVSS é uma escala de severidade de 0 a 10 para uma falha específica.")
    print("Um vetor reúne códigos técnicos como AV (acesso), PR (privilégios) e impactos.")
    print("Exemplo CVSS 3.1, Log4Shell (referência):")
    print("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H")
    print("AV:N = pela rede; AC:L = baixa complexidade; PR:N = sem privilégios;")
    print("UI:N = sem interação. C:H/I:H/A:H = impactos altos.")
    print("Exemplo didático CVSS 4.0 (não associar sem análise técnica):")
    print("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N")
    print("\nPARA ENCONTRAR UM VETOR PUBLICADO:")
    print("1. Identifique o produto, versão e a CVE correspondente à falha.")
    print("2. Visite https://nvd.nist.gov/vuln/search e pesquise a CVE.")
    print("3. Abra o resultado, procure CVSS Metrics / Vector String (3.1 ou 4.0).")
    print("4. Copie o vetor BASE COMPLETO e confira a fonte e o contexto afetado.")
    print("5. Se não houver vetor Base publicado, utilize as perguntas técnicas.")
    print("A biblioteca é uma fotografia local e pode ficar desatualizada.")
    print("Uma CVE encontrada não prova que o seu equipamento está vulnerável.")
    print("Não confunda severidade da falha com risco propagado do inventário.\n")


def escolher_referencia_catalogo() -> dict | None:
    """Pesquisar CVEs validadas, escolher ou voltar sem gravar registros."""
    try:
        registros = carregar_catalogo()
    except (OSError, ValueError) as erro:
        print(f"Não foi possível ler o catálogo local: {erro}")
        return None
    print(f"\nBiblioteca local: {len(registros)} CVE(s) de referência; sem acesso online.")
    print("Busque por descrição, produto, versão, CVE ou código CWE. V = voltar.")
    while True:
        termo = input("Busca: ").strip()
        if termo.casefold() in ("v", "voltar", "0"):
            return None
        resultados = buscar_catalogo(termo, registros)
        if not resultados:
            print("Nenhuma correspondência. Tente outra busca ou V para voltar.")
            continue
        for indice, item in enumerate(resultados, 1):
            print(f"{indice} - {item['cve']} | {item['produto']} | CVSS {item['nota_base_publicada']:g}")
            print(f"    Versão do cenário de exemplo: {item.get('versao_ficticia_do_ativo', 'não informada')}")
        while True:
            escolha = input("Número para consultar/selecionar; V = voltar à busca: ").strip()
            if escolha.casefold() in ("v", "voltar", "0"):
                break
            if not escolha.isdecimal() or not 1 <= int(escolha) <= len(resultados):
                print("Escolha um número apresentado ou V.")
                continue
            item = resultados[int(escolha) - 1]
            print(f"\nCVE: {item['cve']} | Produto: {item['produto']}")
            if item.get("descricao"):
                print(f"Descrição de referência: {item['descricao']}")
            for cwe in item.get("cwes", []):
                print(f"{cwe['codigo']} | Classificação: {cwe['fonte']}")
            if item.get("consulta_descricao_cwe"):
                print(f"Consulta de descrição e CWE: {item['consulta_descricao_cwe']}")
            print(f"Vetor: {item['vetor_cvss']}")
            print(f"Severidade Base: {item['nota_base_publicada']:g}")
            print(f"Fonte: {item['fonte_primaria']}")
            print(f"Consulta de referência: {item.get('consulta', 'não informada')}")
            print("A versão do exemplo não garante aplicabilidade ao ativo atual.")
            confirma = ler_sim_nao("Confirmou que a CVE se aplica a este ativo? (s/n): ")
            if confirma:
                return {"vetor": item["vetor_cvss"], "cve": item["cve"],
                        "fonte_severidade": item["fonte_primaria"]}
            print("Nenhuma vulnerabilidade foi associada; escolha outra ou volte.")


def escolher_referencia_nvd() -> dict | None:
    cve = input("Identificador da CVE (V = voltar): ").strip()
    if cve.casefold() in ("v", "voltar", "0"):
        return None
    try:
        item = consultar_nvd(cve)
    except ValueError as erro:
        print(f"Consulta online: {erro}.")
        return None

    print(f"CVE: {item['cve']}")
    print(f"CWEs publicados: {', '.join(item['cwes']) or 'não informados'}")
    print(f"Fonte: {item['fonte_primaria']}")
    if item["vetor_cvss"] is None:
        print("A fonte ainda não oferece um vetor Base 3.1 ou 4.0 do NIST. Escolha outro modo de avaliação.")
        return None
    print(f"Severidade Base do NIST: {item['nota_base_publicada']:g}")
    print(f"Vetor: {item['vetor_cvss']}")
    if not ler_sim_nao("Conferiu na fonte que a CVE se aplica a este ativo? (s/n): "):
        return None
    return {"vetor": item["vetor_cvss"], "cve": item["cve"],
            "fonte_severidade": item["fonte_primaria"]}


def ler_avaliacao_cvss() -> dict | None:
    """Retorna vetor e eventual referência CVE, sem gravação parcial."""
    while True:
        print("\n--- AVALIAÇÃO DE VULNERABILIDADE ---")
        print("1 - Responder critérios técnicos CVSS 4.0")
        print("2 - Informar vetor Base CVSS 3.1/4.0 publicado")
        print("3 - Buscar CVE na biblioteca local de severidades")
        print("4 - Entender CVSS, exemplos e como localizar vetores")
        print("5 - Consultar uma CVE online no NVD (envia somente o identificador)")
        print("0 - Voltar ao cadastro anterior (sem gravar esta ocorrência)")
        modo = input("Escolha: ").strip()
        if modo in ("0", "v", "V"):
            return None
        if modo == "4":
            explicar_cvss()
            continue
        referencia = {}
        if modo in ("3", "5"):
            referencia = escolher_referencia_catalogo() if modo == "3" else escolher_referencia_nvd()
            if referencia is None:
                continue
            nota, normalizado = calcular_cvss(referencia["vetor"])
        elif modo == "1":
            print("\nResponda com base em evidências, não apenas no tipo do ativo.")
            print("N significa nenhum; se desconhecido, use V para voltar.")
            print("SC/SI/SA tratam de impacto em outros sistemas, não dos pesos da matriz A.")
            metricas = []
            voltar = False
            for codigo, rotulo, opcoes in METRICAS_CVSS4:
                print(f"\nCAMPO: {codigo} — {rotulo}")
                print("O QUE INFORMAR:")
                for letra, significado in opcoes.items():
                    print(f"  {letra} = {significado}")
                while True:
                    valor = input(codigo + " (V = voltar): ").strip().upper()
                    if valor == "V":
                        voltar = True
                        break
                    if valor in opcoes:
                        metricas.append(codigo + ":" + valor)
                        break
                    print("Código inválido. Escolha uma das características indicadas.")
                if voltar:
                    break
            if voltar:
                continue
            nota, normalizado = calcular_cvss("CVSS:4.0/" + "/".join(metricas))
        elif modo == "2":
            print("\nCole o vetor BASE COMPLETO, começando por CVSS:3.1/ ou CVSS:4.0/.")
            print("Exemplo: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H")
            print("Para achar o vetor: https://nvd.nist.gov/vuln/search → CVE → CVSS Metrics.")
            print("Digite V para voltar ao menu de avaliação sem perder o cadastro.")
            while True:
                vetor = input("Vetor técnico CVSS (V = voltar): ").strip()
                if vetor.casefold() in ("v", "voltar"):
                    break
                try:
                    nota, normalizado = calcular_cvss(vetor)
                    break
                except ValueError as erro:
                    print(f"{erro}. Utilize a ajuda da opção 4 se necessário.")
            if vetor.casefold() in ("v", "voltar"):
                continue
        else:
            print("Opção inválida. Escolha uma opção de 0 a 5.")
            continue
        print(f"\nVetor Base utilizado: {normalizado}")
        print(f"Severidade calculada: {nota:g} (não é o risco do ativo).")
        print("NA MATRIZ: v recebe a severidade; M vincula a ocorrência ao ativo.")
        print("b = M @ v (risco próprio); (I - A) @ x = b (risco efetivo).")
        return {"vetor": normalizado, "cve": referencia.get("cve"),
                "fonte_severidade": referencia.get("fonte_severidade")}


def ler_avaliacao_dependencia() -> AvaliacaoDependencia:
    print("\nCAMPO: A[i,j] — dependência do ativo i em relação ao fornecedor j")
    print("O QUE INFORMAR: total de serviços necessários a i e quantos deles j fornece.")
    print("O QUE CALCULAR: peso = fornecidos / total. Ex.: 2 de 5 serviços = 0,4.")
    print("Indisponibilidade observada = 100 × minutos indisponíveis / duração da falha;")
    print("essa medição é registrada separadamente e não substitui o peso de A.")
    total = ler_inteiro("Quantidade total de serviços necessários ao ativo dependente: ", minimo=1)
    fornecidos = ler_inteiro("Quantos desses serviços o outro ativo fornece: ", minimo=0)
    duracao = indisponibilidade = fonte = None
    if ler_sim_nao("Há medição de indisponibilidade durante uma falha? (s/n): "):
        duracao = ler_real("Duração observada da falha do fornecedor (minutos): ", float("inf"))
        indisponibilidade = ler_real("Tempo indisponível do ativo dependente nessa janela (minutos): ", float("inf"))
        fonte = ler_texto("Fonte da medição ou identificação do cenário fictício: ")
    return AvaliacaoDependencia(total, fornecidos, duracao, indisponibilidade, fonte)


def importar_biblioteca(db: BancoDeDados) -> None:
    caminho = ler_texto("Caminho da biblioteca JSON: ")
    ativos = preparar_importacao(db, caminho)
    print(f"Prévia validada: {len(ativos)} ativo(s), "
          f"{sum(len(a.vulnerabilidades) for a in ativos)} ocorrência(s).")
    for ativo in ativos:
        print(f"ID {ativo.id_ativo} | {ativo.hostname} | dependências: {ativo.dependencias}")
        for v in ativo.vulnerabilidades:
            print(v.formatar())
    if not ativos:
        return
    if ler_sim_nao("Confirmar a inclusão deste lote sem sobrescrever ativos existentes? (s/n): "):
        importar_ativos(db, ativos)
        print("Biblioteca importada com sucesso.")
    else:
        print("Importação cancelada; a base não foi alterada.")


def ler_multiplas_vulnerabilidades() -> List[Vulnerabilidade]:
    vulnerabilidades = []
    while True:
        descricao = ler_texto("  Descrição da vulnerabilidade: ")
        categoria = ler_texto(
            "  Categoria (ex.: senha fraca, software desatualizado, exposição de serviço): "
        )
        avaliacao = ler_avaliacao_cvss()
        if avaliacao is None:
            print("Cadastro de ocorrência cancelado; mantendo dados anteriores.")
            break
        vulnerabilidades.append(Vulnerabilidade.por_cvss(descricao, categoria, **avaliacao))
        if not ler_sim_nao("  Adicionar outra vulnerabilidade a este ativo? (s/n): "):
            break
    return vulnerabilidades


# ------------------------------------------------------------------
# Requisito 4: Consulta de ativo (Read)
# ------------------------------------------------------------------

def buscar_ativo_interativo(db: BancoDeDados) -> None:
    print("\n--- Consulta de ativo ---")
    print("1 - Buscar por ID")
    print("2 - Buscar por hostname (nome exato)")
    print("3 - Buscar por trecho do hostname")
    opcao = ler_inteiro("Escolha: ")

    if opcao == 1:
        id_ativo = ler_inteiro("ID do ativo: ")
        ativo = db.buscar_por_id(id_ativo)
        print("\n" + str(ativo) if ativo else "Ativo não encontrado.")
    elif opcao == 2:
        hostname = ler_texto("Hostname: ")
        ativo = db.buscar_por_hostname(hostname)
        print("\n" + str(ativo) if ativo else "Ativo não encontrado.")
    elif opcao == 3:
        trecho = ler_texto("Trecho do hostname: ")
        encontrados = sorted(
            db.buscar_por_trecho_hostname(trecho), key=lambda a: a.id_ativo
        )
        if not encontrados:
            print("Nenhum ativo encontrado com esse trecho no hostname.")
            return
        print(f"\n{len(encontrados)} ativo(s) encontrado(s):")
        for ativo in encontrados:
            print("\n" + str(ativo))
    else:
        print("Opção inválida.")


# ------------------------------------------------------------------
# Requisito 5: Atualização de ativo (Update)
# ------------------------------------------------------------------

def atualizar_ativo(db: BancoDeDados) -> None:
    print("\n--- Atualização de ativo ---")
    id_ativo = ler_inteiro("ID do ativo a atualizar: ")
    ativo = db.buscar_por_id(id_ativo)
    if not ativo:
        print("Ativo não encontrado.")
        return

    print("Pressione Enter sem digitar nada para manter o valor atual.")

    # Primeiro coleta todas as respostas; só no fim altera o ativo. Assim, se o
    # usuário cancelar no meio (Ctrl+C), nada fica alterado pela metade.
    while True:
        novo_hostname = ler_texto(f"Hostname [{ativo.hostname}]: ", permitir_vazio=True)
        if novo_hostname and db.existe_hostname(novo_hostname, ignorar_id=ativo.id_ativo):
            print("Já existe outro ativo com esse hostname. Escolha outro ou deixe em branco.")
            continue
        break

    novo_responsavel = ler_texto(f"Responsável [{ativo.responsavel}]: ", permitir_vazio=True)
    novo_setor = ler_texto(f"Setor/Localização [{ativo.setor}]: ", permitir_vazio=True)

    novo_tipo = None
    if ler_sim_nao("Deseja alterar o tipo de ativo? (s/n): "):
        novo_tipo = escolher_enum("Novo tipo de ativo:", TipoAtivo)

    db.atualizar_ativo(
        id_ativo, hostname=novo_hostname or ativo.hostname,
        responsavel=novo_responsavel or ativo.responsavel,
        setor=novo_setor or ativo.setor, tipo=novo_tipo or ativo.tipo,
    )
    print("\nAtivo atualizado com sucesso.")


# ------------------------------------------------------------------
# Requisito 6: Remoção de ativo (Delete)
# ------------------------------------------------------------------

def deletar_ativo(db: BancoDeDados) -> None:
    print("\n--- Remoção de ativo ---")
    id_ativo = ler_inteiro("ID do ativo a remover: ")
    ativo_existente = db.buscar_por_id(id_ativo)
    if not ativo_existente:
        print("Ativo não encontrado.")
        return

    if not ler_sim_nao(
        f"Confirma a remoção do ativo '{ativo_existente.hostname}' e de suas "
        f"{len(ativo_existente.vulnerabilidades)} vulnerabilidade(s), "
        "limpando também dependências de entrada e saída? (s/n): "
    ):
        print("Operação cancelada.")
        return

    ativo = db.remover(id_ativo)
    print(f"Ativo '{ativo.hostname}' e suas vulnerabilidades foram removidos.")


# ------------------------------------------------------------------
# Requisito 7: Cadastro de vulnerabilidade em ativo já existente
# ------------------------------------------------------------------

def cadastrar_vulnerabilidade(db: BancoDeDados) -> None:
    print("\n--- Cadastro de vulnerabilidade em ativo existente ---")
    id_ativo = ler_inteiro("ID do ativo: ")
    ativo = db.buscar_por_id(id_ativo)
    if not ativo:
        print("Ativo não encontrado.")
        return

    descricao = ler_texto("Descrição da vulnerabilidade: ")
    categoria = ler_texto("Categoria: ")
    avaliacao = ler_avaliacao_cvss()
    if avaliacao is None:
        print("Cadastro cancelado; a base não foi alterada.")
        return

    ativo.vulnerabilidades.append(Vulnerabilidade.por_cvss(descricao, categoria, **avaliacao))
    db.salvar()
    print("Vulnerabilidade cadastrada com sucesso.")


# ------------------------------------------------------------------
# Requisito 8: Visualização de vulnerabilidades de um ativo
# ------------------------------------------------------------------

def imprimir_vulnerabilidades(ativo: Ativo) -> None:
    """Mostra as vulnerabilidades numeradas (a partir de 1)."""
    for numero, vulnerabilidade in enumerate(ativo.vulnerabilidades, start=1):
        print(vulnerabilidade.formatar(numero))


def visualizar_vulnerabilidades(db: BancoDeDados) -> None:
    print("\n--- Visualização de vulnerabilidades ---")
    id_ativo = ler_inteiro("ID do ativo: ")
    ativo = db.buscar_por_id(id_ativo)
    if not ativo:
        print("Ativo não encontrado.")
        return

    print(f"\nAtivo: {ativo.hostname} (ID {ativo.id_ativo})")
    if not ativo.vulnerabilidades:
        print("Este ativo está sem vulnerabilidades registradas.")
        return

    imprimir_vulnerabilidades(ativo)


# ------------------------------------------------------------------
# Atualização e remoção de vulnerabilidades (acompanhamento do tratamento)
# ------------------------------------------------------------------

def selecionar_vulnerabilidade(db: BancoDeDados) -> Optional[Tuple[Ativo, int]]:
    """
    Pede o ID de um ativo, lista suas vulnerabilidades e pede qual delas
    o usuário quer manipular. Retorna (ativo, posição na lista) ou None.
    A posição devolvida já é o índice da lista (começa em 0).
    """
    id_ativo = ler_inteiro("ID do ativo: ")
    ativo = db.buscar_por_id(id_ativo)
    if not ativo:
        print("Ativo não encontrado.")
        return None

    print(f"\nAtivo: {ativo.hostname} (ID {ativo.id_ativo})")
    if not ativo.vulnerabilidades:
        print("Este ativo está sem vulnerabilidades registradas.")
        return None

    imprimir_vulnerabilidades(ativo)
    numero = ler_numero_da_lista("Número da vulnerabilidade: ", len(ativo.vulnerabilidades))
    return ativo, numero - 1


def atualizar_vulnerabilidade(db: BancoDeDados) -> None:
    print("\n--- Atualização de vulnerabilidade ---")
    selecao = selecionar_vulnerabilidade(db)
    if selecao is None:
        return
    ativo, indice = selecao
    vulnerabilidade = ativo.vulnerabilidades[indice]

    print("Pressione Enter sem digitar nada para manter o valor atual.")
    nova_descricao = ler_texto(f"Descrição [{vulnerabilidade.descricao}]: ", permitir_vazio=True)
    nova_categoria = ler_texto(f"Categoria [{vulnerabilidade.categoria}]: ", permitir_vazio=True)

    nova_avaliacao = None
    if ler_sim_nao(
        f"Alterar a severidade (atual: {vulnerabilidade.severidade:g})? (s/n): "
    ):
        avaliacao = ler_avaliacao_cvss()
        if avaliacao is None:
            print("Atualização cancelada; a base não foi alterada.")
            return
        nova_avaliacao = Vulnerabilidade.por_cvss(
            nova_descricao or vulnerabilidade.descricao,
            nova_categoria or vulnerabilidade.categoria, **avaliacao)

    # Só altera depois de coletar tudo (ver comentário em atualizar_ativo).
    if nova_descricao:
        vulnerabilidade.descricao = nova_descricao
    if nova_categoria:
        vulnerabilidade.categoria = nova_categoria
    if nova_avaliacao is not None:
        vulnerabilidade.severidade = nova_avaliacao.severidade
        vulnerabilidade.vetor_cvss = nova_avaliacao.vetor_cvss
        vulnerabilidade.fonte_severidade = nova_avaliacao.fonte_severidade
        vulnerabilidade.cve = nova_avaliacao.cve

    db.salvar()
    print("Vulnerabilidade atualizada com sucesso.")


def remover_vulnerabilidade(db: BancoDeDados) -> None:
    print("\n--- Remoção de vulnerabilidade ---")
    selecao = selecionar_vulnerabilidade(db)
    if selecao is None:
        return
    ativo, indice = selecao

    if not ler_sim_nao("Confirma a remoção desta vulnerabilidade? (s/n): "):
        print("Operação cancelada.")
        return

    ativo.vulnerabilidades.pop(indice)
    db.salvar()
    print("Vulnerabilidade removida com sucesso.")


# ------------------------------------------------------------------
# Extra: listagem geral (facilita a demonstração/apresentação)
# ------------------------------------------------------------------

def listar_ativos(db: BancoDeDados) -> None:
    print("\n--- Lista de todos os ativos cadastrados ---")
    # Ordenado por ID: a ordem "natural" do dict é a de inserção, que muda
    # conforme cadastros e remoções vão acontecendo e fica confusa de ler.
    ativos = sorted(db.listar_todos(), key=lambda ativo: ativo.id_ativo)
    if not ativos:
        print("Nenhum ativo cadastrado.")
        return
    for ativo in ativos:
        print(
            f"ID {ativo.id_ativo:<4} | {ativo.hostname:<20} | "
            f"{ativo.tipo.name:<20} | {len(ativo.vulnerabilidades)} vulnerabilidade(s)"
        )


# ------------------------------------------------------------------
# Extra: relatório de vulnerabilidades em CSV, ordenado por severidade
# ------------------------------------------------------------------

def exportar_relatorio_vulnerabilidades(db: BancoDeDados) -> None:
    print("\n--- Exportar relatório de vulnerabilidades (CSV) ---")
    linhas = preparar_relatorio(db.listar_todos())
    if not linhas:
        print("Não há vulnerabilidades cadastradas para exportar.")
        return

    nome_arquivo = ler_texto(
        "Nome do arquivo de saída [relatorio_vulnerabilidades.csv]: ",
        permitir_vazio=True,
    ) or "relatorio_vulnerabilidades.csv"

    campos = CAMPOS_CSV
    registros = linhas
    with open(nome_arquivo, "x", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(registros)
        arquivo.flush()
        os.fsync(arquivo.fileno())

    print(f"Relatório exportado para '{nome_arquivo}' ({len(linhas)} vulnerabilidade(s)).")


# ------------------------------------------------------------------
# Menu principal (Requisito 1)
# ------------------------------------------------------------------

def gerenciar_dependencias(db: BancoDeDados) -> None:
    print("\n1 - Cadastrar | 2 - Editar peso | 3 - Remover | 4 - Listar dependências")
    opcao = ler_inteiro("Escolha: ")
    if opcao == 4:
        for ativo in sorted(db.listar_todos(), key=lambda a: a.id_ativo):
            for destino, peso in sorted(ativo.dependencias.items()):
                print(f"{ativo.id_ativo} depende de {destino}; peso={peso:g}")
                avaliacao = ativo.avaliacoes_dependencias.get(destino)
                if avaliacao is not None:
                    print(f"  Serviços: {avaliacao.servicos_fornecidos}/{avaliacao.total_servicos}")
                    medida = avaliacao.indisponibilidade_percentual
                    print("  Indisponibilidade observada: " +
                          (f"{avaliacao.indisponibilidade_min:g} min / {avaliacao.duracao_falha_min:g} min = {medida:g}% ({avaliacao.fonte_medicao})"
                           if medida is not None else "não medida"))
                else:
                    print("  Peso importado ou anterior; critérios de serviços não registrados.")
        return
    if opcao not in (1, 2, 3):
        print("Opção inválida.")
        return
    origem = ler_inteiro("ID do ativo dependente: ", minimo=1)
    destino = ler_inteiro("ID do ativo do qual ele depende: ", minimo=1)
    if opcao == 3:
        db.remover_dependencia(origem, destino)
    else:
        ativo = db.buscar_por_id(origem)
        existe = ativo is not None and destino in ativo.dependencias
        if opcao == 1 and existe:
            raise ValueError("dependência já cadastrada; use editar peso")
        if opcao == 2 and not existe:
            raise ValueError("dependência inexistente")
        avaliacao = ler_avaliacao_dependencia()
        db.definir_dependencia(origem, destino, avaliacao.peso, avaliacao=avaliacao)
        print(f"Peso calculado: {avaliacao.peso:g}")
    print("Dependência gravada com sucesso.")


def consultar_risco(db: BancoDeDados) -> None:
    from servico_risco import analisar_inventario
    print("\n1 - Matrizes e vetores | 2 - Ranking de risco | 3 - Risco de um ativo")
    opcao = ler_inteiro("Escolha: ")
    if opcao not in (1, 2, 3):
        print("Opção inválida.")
        return
    analise = analisar_inventario(db)
    r = analise.resultado
    anteriores = sum(not v.vetor_cvss and not v.fonte_severidade
                     for a in db.listar_todos() for v in a.vulnerabilidades)
    if anteriores:
        print(f"Atenção: {anteriores} severidade(s) anteriores sem vetor/fonte. "
              "Foram preservadas; não foram recalculadas automaticamente.")
    print("Risco próprio = direto (b); risco efetivo = propagado (x).")
    print("Índice matemático de risco: pode ultrapassar 10; não é probabilidade, percentual ou CVSS.")
    print(f"rho(A)={r.raio_espectral:.8g}; condição={r.condicao:.8g}; "
          f"resíduo relativo={r.residuo_relativo:.3g}")
    if opcao == 1:
        print("Ordem dos ativos (linhas de M, linhas/colunas de A, b e x):", analise.ids_ativos)
        print("Ordem das ocorrências (colunas de M e vetor v):", analise.ids_vulnerabilidades)
        print("I é a matriz identidade: 1 na diagonal e 0 nas demais posições.")
        print("rho(A) deve ser menor que 1 para a propagação convergir; o sistema valida essa condição.")
        for nome, informar, calcular in (
            ("M", "cadastre as ocorrências de vulnerabilidade em cada ativo",
             "M[i,j] = 1 quando o ativo i tem a ocorrência j; caso contrário, 0"),
            ("v", "responda os critérios CVSS ou forneça um vetor Base publicado",
             "severidade de cada ocorrência, na mesma ordem das colunas de M"),
            ("A", "registre os serviços necessários e fornecidos na opção 11",
             "A[i,j] = serviços fornecidos por j / total necessário a i; 0 sem vínculo cadastrado"),
            ("b", "nenhuma nota adicional; usa M e v",
             "b = M @ v: soma das severidades de cada ativo, seu risco próprio/direto"),
            ("x", "nenhuma nota adicional; usa A e b",
             "resolver (I - A) @ x = b: risco efetivo, com propagação pelas dependências"),
        ):
            print(f"\nCAMPO: {nome}")
            print(f"O QUE INFORMAR: {informar}.")
            print(f"O QUE CALCULAR: {calcular}.")
            valor = getattr(r, nome)
            print(f"{nome} (forma {valor.shape}): {valor.tolist()}")
        print("\n@ representa multiplicação matricial; o sistema monta as matrizes e resolve a equação.")
        print("Cadastros antigos podem conter severidades/pesos numéricos sem os critérios de origem.")
    elif opcao == 2:
        for aid, direto, propagado in analise.ranking():
            print(f"Ativo {aid}: risco direto={direto:.8g}; propagado={propagado:.8g}")
        if not analise.ids_ativos:
            print("Nenhum ativo cadastrado.")
    else:
        aid = ler_inteiro("ID do ativo: ", minimo=1)
        direto, propagado = analise.individual(aid)
        print(f"Ativo {aid}: risco direto={direto:.8g}; propagado={propagado:.8g}")


def consultar_orientacoes(db: BancoDeDados) -> None:
    ativo = db.buscar_por_id(ler_inteiro("ID do ativo: "))
    if ativo is None:
        print("Ativo não encontrado.")
        return
    print(f"{ativo.hostname}: {type(ativo).__name__}")
    for orientacao in ativo.orientacoes_tratamento():
        print("- " + orientacao)


def exibir_menu() -> None:
    print("\n===== Inventário de Segurança - Ativos de TI =====")
    print("1 - Cadastrar novo ativo")
    print("2 - Consultar ativo (por ID ou hostname)")
    print("3 - Atualizar ativo")
    print("4 - Remover ativo")
    print("5 - Cadastrar vulnerabilidade em ativo existente")
    print("6 - Visualizar vulnerabilidades de um ativo")
    print("7 - Listar todos os ativos")
    print("8 - Atualizar vulnerabilidade")
    print("9 - Remover vulnerabilidade")
    print("10 - Exportar relatório de vulnerabilidades (CSV)")
    print("11 - Dependências: serviços e indisponibilidade")
    print("12 - Matrizes, riscos e ranking")
    print("13 - Importar biblioteca JSON de ativos")
    print("14 - Orientações por tipo de ativo (POO)")
    print("0 - Sair")


def executar_menu(db: BancoDeDados) -> None:
    acoes = {
        1: cadastrar_ativo,
        2: buscar_ativo_interativo,
        3: atualizar_ativo,
        4: deletar_ativo,
        5: cadastrar_vulnerabilidade,
        6: visualizar_vulnerabilidades,
        7: listar_ativos,
        8: atualizar_vulnerabilidade,
        9: remover_vulnerabilidade,
        10: exportar_relatorio_vulnerabilidades,
        11: gerenciar_dependencias,
        12: consultar_risco,
        13: importar_biblioteca,
        14: consultar_orientacoes,
    }

    print("Bem-vindo ao Sistema de Inventário de Segurança!")

    while True:
        # Leitura da opção do menu: Ctrl+C (KeyboardInterrupt) ou Ctrl+D
        # (EOFError) aqui significam "quero sair".
        try:
            exibir_menu()
            opcao = ler_inteiro("Escolha uma opção: ")
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando...")
            break

        if opcao == 0:
            print("Encerrando o programa. Até logo!")
            break

        acao = acoes.get(opcao)
        if acao is None:
            print("Opção inválida. Tente novamente.")
            continue

        try:
            acao(db)
        except KeyboardInterrupt:
            # Ctrl+C no meio de uma operação: cancela só a operação e volta ao
            # menu. Tudo o que já foi gravado continua na base.
            print("\nOperação cancelada. Voltando ao menu.")
        except EOFError:
            # A entrada foi encerrada (Ctrl+D ou fim de arquivo): não há como
            # continuar pedindo dados, então o programa termina normalmente.
            print("\nEntrada encerrada. Encerrando o programa...")
            break
        except Exception as erro:  # protege o loop principal de falhas inesperadas
            print(f"[Erro] Ocorreu um problema ao executar a operação: {erro}")


def main(*, demonstracao: bool = False) -> None:
    if not demonstracao:
        caminho = caminho_inventario()
        caminho.parent.mkdir(parents=True, exist_ok=True)
        print(f"Base em uso: {caminho}")
        executar_menu(BancoDeDados(caminho))
        return
    with tempfile.TemporaryDirectory(prefix="ufu_demo_") as pasta:
        db = BancoDeDados(Path(pasta) / "ativos_demo.json")
        biblioteca = Path(__file__).resolve().parent / "exemplos" / "ativos_teste.json"
        importar_ativos(db, preparar_importacao(db, biblioteca))
        print("DEMONSTRAÇÃO TEMPORÁRIA: ativos e falhas fictícios; referências CVE reais.")
        print("As alterações nesta demonstração são descartadas ao sair; a base real não é usada.")
        executar_menu(db)


_EM_DOCKER = Path("/.dockerenv").exists()


def _terminal_mesmo_backend() -> bool:
    """Com o frontend Docker ativo, mantém os escritores no mesmo SO."""
    compose = Path(__file__).resolve().parent / "docker/compose.yaml"
    if _EM_DOCKER or os.environ.get("INVENTARIO_ARQUIVO") or not compose.is_file():
        return False
    try:
        estado = subprocess.run(["docker", "compose", "-f", str(compose), "ps", "-q", "frontend"],
                                capture_output=True, text=True, timeout=5)
    except FileNotFoundError:
        return False
    except subprocess.TimeoutExpired as erro:
        raise RuntimeError("Não foi possível verificar o Docker; nenhuma base local foi aberta.") from erro
    if estado.returncode:
        raise RuntimeError("Não foi possível verificar o Docker. Para uso nativo, configure INVENTARIO_ARQUIVO explicitamente.")
    containers = estado.stdout.split()
    if not containers:
        return False
    if len(containers) != 1:
        raise RuntimeError("Há mais de um frontend Docker; selecione o ambiente antes de abrir o terminal.")
    print("Terminal conectado à mesma base da interface Docker.", flush=True)
    modo = "-it" if sys.stdin.isatty() and sys.stdout.isatty() else "-i"
    resultado = subprocess.run(["docker", "exec", modo, containers[0], "python", "-B", "main.py", "--terminal"])
    if resultado.returncode:
        raise RuntimeError("O terminal Docker não concluiu; nenhuma base local alternativa foi aberta.")
    return True


def _iniciar_terminal() -> int:
    try:
        if not _terminal_mesmo_backend():
            main()
        return 0
    except (OSError, RuntimeError) as erro:
        print(f"[Erro] {erro}")
        return 1


def escolher_interface() -> int:
    """Escolhe a interface antes de abrir ou modificar qualquer base."""
    print("\nComo deseja iniciar?")
    print("1 - Acessar interface gráfica (navegador)")
    print("2 - Continuar no terminal")
    while True:
        try:
            escolha = input("Escolha 1 ou 2: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nInicialização cancelada.")
            return 0
        if escolha == "1":
            from iniciar_web import main as abrir_previa
            return abrir_previa(abrir_navegador=True)
        if escolha == "2":
            return _iniciar_terminal()
        print("Opção inválida. Escolha 1 ou 2.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Abre ativos fictícios em base temporária.")
    parser.add_argument("--terminal", action="store_true", help="Abre diretamente o menu do terminal.")
    argumentos = parser.parse_args()
    if argumentos.demo:
        main(demonstracao=True)
    elif argumentos.terminal:
        raise SystemExit(_iniciar_terminal())
    else:
        raise SystemExit(escolher_interface())
