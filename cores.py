"""
Cores ANSI para deixar a saída do terminal mais fácil de ler.

Não usa nenhuma biblioteca externa (nada de colorama): só os códigos de
escape ANSI, suportados pela imensa maioria dos terminais modernos (Linux,
macOS, Windows Terminal / PowerShell atual). As cores são desligadas
automaticamente quando:
  - a saída não é um terminal (por exemplo, ao redirecionar para um
    arquivo com "python main.py > saida.txt"), ou
  - a variável de ambiente NO_COLOR está definida (convenção usada por
    várias ferramentas de linha de comando para pedir saída sem cor).
"""

from __future__ import annotations

import os
import sys

if os.name == "nt":
    # Truque conhecido para habilitar códigos ANSI no cmd.exe do Windows 10+.
    # Não tem efeito (e não faz mal) em terminais que já suportam ANSI.
    os.system("")

_ATIVADO = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

_RESET = "\033[0m"
_CODIGOS = {
    "verde": "32",
    "amarelo": "33",
    "vermelho": "31",
    "vermelho_forte": "1;31",
    "ciano": "36",
}

def colorir(texto: str, cor: str) -> str:
    """Envolve 'texto' com o código ANSI de 'cor', se as cores estiverem ativas."""
    codigo = _CODIGOS.get(cor)
    if not _ATIVADO or not codigo:
        return texto
    return f"\033[{codigo}m{texto}{_RESET}"
