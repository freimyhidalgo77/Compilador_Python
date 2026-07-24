"""
Constantes léxicas del lenguaje Pascal-like
"""

PALABRAS_RESERVADAS = {
    'var', 'begin', 'end', 'if', 'then', 'else', 'while', 'do', 'for', 'to',
    'integer', 'real', 'string', 'boolean', 'function', 'return', 'break',
    'continue', 'true', 'false', 'program', 'array', 'and', 'or', 'not',
    'div', 'mod'
}

# Palabras que representan un tipo de dato dentro de una declaración 'var'
PALABRAS_TIPO = {
    'integer': 'INTEGER', 'real': 'REAL', 'string': 'STRING', 'boolean': 'BOOLEAN', 'program': 'PROGRAM'
}

OPERADORES_DOS_CARACTERES = {':=', '<>', '<=', '>='}
OPERADORES_RELACIONALES = {'=', '<>', '<', '>', '<=', '>='}
OPERADORES_ADITIVOS = {'+', '-'}
OPERADORES_MULTIPLICATIVOS = {'*', '/'}
