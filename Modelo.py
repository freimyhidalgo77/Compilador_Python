"""
CAPA DE MODELO
──────────────────────────────────────────────────────────────
Estructuras de datos compartidas por todas las capas (lexica, sintactica y semantica) del compilador.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


# ==================== TOKENS ====================

class TipoToken(Enum):
    RESERVADA = auto()        # palabra clave del lenguaje (if, while, var, ...)
    IDENTIFICADOR = auto()
    ENTERO = auto()
    REAL = auto()
    CADENA = auto()
    ASIGNACION = auto()       # :=
    OPERADOR = auto()         # + - * / = <> < > <= >=
    PARENTESIS_A = auto()
    PARENTESIS_C = auto()
    PUNTO_COMA = auto()
    DOS_PUNTOS = auto()
    COMA = auto()
    FIN_ARCHIVO = auto()
    DESCONOCIDO = auto()


@dataclass
class Token:
    tipo: TipoToken
    valor: str
    linea: int
    columna: int = 1

    def __repr__(self) -> str:
        return f'[{self.tipo.name} | "{self.valor}" | linea {self.linea}, columna {self.columna}]'


# ==================== TIPOS Y SIMBOLOS ====================

class TipoDato(Enum):
    INTEGER = auto()
    REAL = auto()
    STRING = auto()
    BOOLEAN = auto()
    DESCONOCIDO = auto()

    def __str__(self) -> str:
        return self.name.lower()


@dataclass
class Simbolo:
    nombre: str
    tipo: TipoDato
    valor: Optional[Any] = None
    es_constante: bool = False
    linea: int = 0


# ==================== ERRORES ====================

@dataclass
class ErrorCompilacion:
    """Error unificado de cualquier fase (léxica, sintáctica o semántica),
    equivalente a los strings 'ERROR LEXICO [...]' / 'ERROR SINTACTICO [...]'
    / 'ERROR SEMANTICO [...]' que arma el compilador de Kotlin."""
    fase: str          # "LEXICO" | "SINTACTICO" | "SEMANTICO"
    linea: int
    columna: int
    mensaje: str

    def __str__(self) -> str:
        return f"ERROR {self.fase} [linea {self.linea}, columna {self.columna}]: {self.mensaje}"