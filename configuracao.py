"""Caminho compartilhado pelo terminal e pela interface; sem efeitos de escrita."""
import os
from pathlib import Path

RAIZ=Path(__file__).resolve().parent

def caminho_inventario():
    configurado=os.environ.get('INVENTARIO_ARQUIVO')
    return Path(configurado).expanduser().resolve() if configurado else RAIZ/'dados/inventario.json'
