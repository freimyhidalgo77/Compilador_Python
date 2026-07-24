"""
CAPA LEXICA — FASE 1: ANALISIS LEXICO
──────────────────────────────────────────────────────────────
"""

from typing import List
from Modelo import Token, TipoToken, ErrorCompilacion
from Constantes import PALABRAS_RESERVADAS, OPERADORES_DOS_CARACTERES


class AnalizadorLexico:
    def __init__(self, fuente: str):
        self.fuente = fuente
        self.pos = 0
        self.linea = 1
        self.columna = 1
        self.tokens: List[Token] = []
        self.errores: List[ErrorCompilacion] = []

    # ---- utilidades internas ----
    def _avanzar(self):
        if self.pos < len(self.fuente) and self.fuente[self.pos] == '\n':
            self.linea += 1
            self.columna = 1
        else:
            self.columna += 1
        self.pos += 1

    def _agregar(self, tipo: TipoToken, valor: str, lin: int, col: int):
        self.tokens.append(Token(tipo, valor, lin, col))

    def _error(self, lin: int, col: int, mensaje: str):
        self.errores.append(ErrorCompilacion('LEXICO', lin, col, mensaje))

    # ---- punto de entrada ----
    def analizar(self) -> List[Token]:
        n = len(self.fuente)
        while self.pos < n:
            self._saltar_espacios()
            if self.pos >= n:
                break
            c = self.fuente[self.pos]
            lin, col = self.linea, self.columna

            if c == '\n':
                self._avanzar()
            elif c == '{':
                self._leer_comentario(lin, col)
            elif c in '"\'':
                self._leer_cadena(c, lin, col)
            elif self.pos + 1 < n and self.fuente[self.pos:self.pos + 2] in OPERADORES_DOS_CARACTERES:
                op = self.fuente[self.pos:self.pos + 2]
                tipo = TipoToken.ASIGNACION if op == ':=' else TipoToken.OPERADOR
                self._agregar(tipo, op, lin, col)
                self._avanzar(); self._avanzar()
            elif c in '+-*/=<>':
                self._agregar(TipoToken.OPERADOR, c, lin, col)
                self._avanzar()
            elif c in '();:,':
                tipo = {
                    '(': TipoToken.PARENTESIS_A,
                    ')': TipoToken.PARENTESIS_C,
                    ';': TipoToken.PUNTO_COMA,
                    ':': TipoToken.DOS_PUNTOS,
                    ',': TipoToken.COMA,
                }[c]
                self._agregar(tipo, c, lin, col)
                self._avanzar()
            elif c.isdigit():
                self._leer_numero(lin, col)
            elif c.isalpha() or c == '_':
                self._leer_identificador(lin, col)
            else:
                self._error(lin, col, f'caracter invalido "{c}"')
                self._agregar(TipoToken.DESCONOCIDO, c, lin, col)
                self._avanzar()

        self.tokens.append(Token(TipoToken.FIN_ARCHIVO, 'EOF', self.linea, self.columna))
        return self.tokens

    # ---- reconocedores ----
    def _saltar_espacios(self):
        while self.pos < len(self.fuente) and self.fuente[self.pos] in ' \t\r':
            self._avanzar()

    def _leer_comentario(self, lin: int, col: int):
        self._avanzar()  # consume '{'
        while self.pos < len(self.fuente) and self.fuente[self.pos] != '}':
            self._avanzar()
        if self.pos >= len(self.fuente):
            self._error(lin, col, 'comentario sin cerrar (falta "}")')
        else:
            self._avanzar()  # consume '}'

    def _leer_cadena(self, comilla: str, lin: int, col: int):
        self._avanzar()  # consume comilla de apertura
        inicio = self.pos
        cerrada = False
        while self.pos < len(self.fuente) and self.fuente[self.pos] != '\n':
            if self.fuente[self.pos] == comilla:
                cerrada = True
                break
            self._avanzar()
        valor = self.fuente[inicio:self.pos]
        if cerrada:
            self._avanzar()  # consume comilla de cierre
        else:
            self._error(lin, col, 'cadena de texto sin cerrar')
        self._agregar(TipoToken.CADENA, valor, lin, col)

    def _leer_numero(self, lin: int, col: int):
        inicio = self.pos
        while self.pos < len(self.fuente) and self.fuente[self.pos].isdigit():
            self._avanzar()
        if self.pos < len(self.fuente) and self.fuente[self.pos] == '.' and \
                self.pos + 1 < len(self.fuente) and self.fuente[self.pos + 1].isdigit():
            self._avanzar()
            while self.pos < len(self.fuente) and self.fuente[self.pos].isdigit():
                self._avanzar()
            self._agregar(TipoToken.REAL, self.fuente[inicio:self.pos], lin, col)
        elif self.pos < len(self.fuente) and self.fuente[self.pos] == '.':
            # ej. "5." sin dígitos después del punto: error explícito, no se ignora en silencio
            self._error(lin, col, f'numero decimal mal formado "{self.fuente[inicio:self.pos + 1]}"')
            self._avanzar()
            self._agregar(TipoToken.REAL, self.fuente[inicio:self.pos], lin, col)
        else:
            self._agregar(TipoToken.ENTERO, self.fuente[inicio:self.pos], lin, col)

    def _leer_identificador(self, lin: int, col: int):
        inicio = self.pos
        while self.pos < len(self.fuente) and (self.fuente[self.pos].isalnum() or self.fuente[self.pos] == '_'):
            self._avanzar()
        lexema = self.fuente[inicio:self.pos]
        tipo = TipoToken.RESERVADA if lexema.lower() in PALABRAS_RESERVADAS else TipoToken.IDENTIFICADOR
        # Se guarda la palabra reservada en minúscula para comparar fácil en el parser,
        # pero el identificador conserva su forma original.
        valor = lexema.lower() if tipo == TipoToken.RESERVADA else lexema
        self._agregar(tipo, valor, lin, col)