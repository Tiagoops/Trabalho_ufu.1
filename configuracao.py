"""Caminho compartilhado pelo terminal e pela interface; sem efeitos de escrita."""
import os
from hashlib import sha256
from pathlib import Path

RAIZ=Path(__file__).resolve().parent

def caminho_inventario():
    configurado=os.environ.get('INVENTARIO_ARQUIVO')
    return Path(configurado).expanduser().resolve() if configurado else RAIZ/'dados/inventario.json'


def identidade_base(caminho):
    """Identifica o caminho físico local, independentemente dos registros salvos."""
    normalizado = os.path.normcase(str(Path(caminho).resolve()))
    return sha256(normalizado.encode('utf-8')).hexdigest()
