"""
CAPA SINTACTICA — FASE 2 (sintactico puro)
─────────────────────────────────────────────────────────────
"""

from typing import List, Optional, Tuple, Any
from Modelo import Token, TipoToken, TipoDato, Simbolo, ErrorCompilacion
from Constantes import PALABRAS_TIPO, OPERADORES_RELACIONALES
from Simbolos import TablaSimbolos


class AnalizadorSintactico:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errores: List[ErrorCompilacion] = []
        self.tabla_simbolos = TablaSimbolos()

    # ---- cursor sobre el flujo de tokens ----
    def _actual(self) -> Token:
        if self.pos >= len(self.tokens):
            return Token(TipoToken.FIN_ARCHIVO, "EOF", 0, 0)
        return self.tokens[self.pos]

    def _avanzar(self):
        if self.pos < len(self.tokens) - 1:
            self.pos += 1

    def _consumir(self, tipo: TipoToken, esperado: str = "") -> Optional[Token]:
        t = self._actual()
        if t.tipo == tipo:
            self._avanzar()
            return t
        msg = esperado or tipo.name
        self._err_sint(t, f'se esperaba {msg} pero se encontro "{t.valor}"')
        return None

    def _consumir_reservada(self, palabra: str) -> Optional[Token]:
        t = self._actual()
        if t.tipo == TipoToken.RESERVADA and t.valor == palabra:
            self._avanzar()
            return t
        self._err_sint(t, f'se esperaba "{palabra}" pero se encontro "{t.valor}"')
        return None

    def _es_reservada(self, palabra: str) -> bool:
        t = self._actual()
        return t.tipo == TipoToken.RESERVADA and t.valor == palabra

    def _err_sint(self, t: Token, mensaje: str):
        self.errores.append(ErrorCompilacion('SINTACTICO', t.linea, t.columna, mensaje))

    # ---- punto de entrada ----
    def analizar(self):
        self.tabla_simbolos.entrar_ambito()
        self._parsear_encabezado_program()
        
        while self.pos < len(self.tokens) and self._actual().tipo != TipoToken.FIN_ARCHIVO:
            self._parsear_declaracion()
            self._parsear_punto_final()

    # ==================== SENTENCIAS ====================
    def _parsear_declaracion(self):
        if self.pos >= len(self.tokens):
            return
            
        t = self._actual()
        
        if t.tipo == TipoToken.RESERVADA:
            if t.valor == 'var':
                self._parsear_var()
                return
            elif t.valor == 'if':
                self._parsear_if()
                return
            elif t.valor == 'while':
                self._parsear_while()
                return
            elif t.valor == 'for':
                self._parsear_for()
                return
            elif t.valor == 'function':
                self._parsear_function()
                return
            elif t.valor == 'return':
                self._parsear_return()
                return
            elif t.valor == 'break':
                self._parsear_salto('break')
                return
            elif t.valor == 'continue':
                self._parsear_salto('continue')
                return
            elif t.valor == 'begin':
                self._parsear_bloque()
                return
        
        if t.tipo == TipoToken.IDENTIFICADOR:
            if self.pos + 1 < len(self.tokens):
                siguiente = self.tokens[self.pos + 1]
                if siguiente.tipo == TipoToken.ASIGNACION:
                    self._parsear_asignacion()
                    return
                elif siguiente.tipo == TipoToken.PARENTESIS_A:
                    self._parsear_llamada_sentencia()
                    return
        
        self._err_sint(t, f'sentencia no reconocida: "{t.valor}"')
        self._avanzar()

    def _parsear_asignacion(self):
        """Parsing de asignación - SOLO SINTÁCTICO, sin verificación de tipos"""
        id_tok = self._consumir(TipoToken.IDENTIFICADOR, 'identificador')
        if id_tok is None:
            return
        
        self._consumir(TipoToken.ASIGNACION, '":="')
        self._parsear_expresion()
        self._consumir(TipoToken.PUNTO_COMA, '";"')

    def _parsear_encabezado_program(self):
        if self._es_reservada('program'):
            self._avanzar()
            self._consumir(TipoToken.IDENTIFICADOR, 'nombre de programa')
            self._consumir(TipoToken.PUNTO_COMA, '";"')
  
    def _parsear_punto_final(self):
        if self.pos < len(self.tokens) and self._actual().valor == '.':
            self._avanzar()

    def _parsear_var(self):
        self._consumir_reservada('var')
        self._parsear_grupo_var()
        while self._actual().tipo == TipoToken.IDENTIFICADOR:
            self._parsear_grupo_var()

    def _parsear_grupo_var(self):
        """Parsea grupo var - SOLO SINTÁCTICO, sin registro en tabla"""
        identificadores = [self._consumir(TipoToken.IDENTIFICADOR, 'identificador')]
        while self._actual().tipo == TipoToken.COMA:
            self._avanzar()
            identificadores.append(self._consumir(TipoToken.IDENTIFICADOR, 'identificador'))

        self._consumir(TipoToken.DOS_PUNTOS, '":"')
        tipo_tok = self._actual()
        if tipo_tok.tipo == TipoToken.RESERVADA and tipo_tok.valor in PALABRAS_TIPO:
            self._avanzar()
        else:
            self._err_sint(tipo_tok, f'tipo desconocido "{tipo_tok.valor}"')

        if len(identificadores) == 1 and self._actual().tipo == TipoToken.ASIGNACION:
            self._avanzar()
            self._parsear_expresion()

        self._consumir(TipoToken.PUNTO_COMA, '";"')

    def _parsear_if(self):
        self._consumir_reservada('if')
        self._parsear_expresion()
        self._consumir_reservada('then')
        self._parsear_sentencia_o_bloque()
        if self._es_reservada('else'):
            self._avanzar()
            self._parsear_sentencia_o_bloque()

    def _parsear_while(self):
        self._consumir_reservada('while')
        self._parsear_expresion()
        self._consumir_reservada('do')
        self._parsear_sentencia_o_bloque()

    def _parsear_for(self):
        self._consumir_reservada('for')
        id_tok = self._consumir(TipoToken.IDENTIFICADOR, 'identificador')
        self._consumir(TipoToken.ASIGNACION, '":="')
        self._parsear_expresion()
        self._consumir_reservada('to')
        self._parsear_expresion()
        self._consumir_reservada('do')
        self.tabla_simbolos.entrar_ambito()
        self._parsear_sentencia_o_bloque()
        self.tabla_simbolos.salir_ambito()

    def _parsear_function(self):
        self._consumir_reservada('function')
        nom_tok = self._consumir(TipoToken.IDENTIFICADOR, 'nombre de funcion')
        self._consumir(TipoToken.PARENTESIS_A, '"("')
        self.tabla_simbolos.entrar_ambito()
        while self._actual().tipo not in (TipoToken.PARENTESIS_C, TipoToken.FIN_ARCHIVO):
            p_tok = self._consumir(TipoToken.IDENTIFICADOR, 'parametro')
            self._consumir(TipoToken.DOS_PUNTOS, '":"')
            tipo_tok = self._actual()
            if tipo_tok.tipo == TipoToken.RESERVADA and tipo_tok.valor in PALABRAS_TIPO:
                self._avanzar()
            if self._actual().tipo == TipoToken.COMA:
                self._avanzar()
        self._consumir(TipoToken.PARENTESIS_C, '")"')
        if self._actual().tipo == TipoToken.DOS_PUNTOS:
            self._avanzar()
            self._avanzar()
        self._parsear_bloque(nuevo_ambito=False)
        self.tabla_simbolos.salir_ambito()

    def _parsear_return(self):
        self._consumir_reservada('return')
        if self._actual().tipo != TipoToken.PUNTO_COMA:
            self._parsear_expresion()
        self._consumir(TipoToken.PUNTO_COMA, '";"')

    def _parsear_salto(self, palabra: str):
        self._consumir_reservada(palabra)
        self._consumir(TipoToken.PUNTO_COMA, '";"')

    def _parsear_bloque(self, nuevo_ambito: bool = True):
        self._consumir_reservada('begin')
        if nuevo_ambito:
            self.tabla_simbolos.entrar_ambito()
        while not self._es_reservada('end') and self._actual().tipo != TipoToken.FIN_ARCHIVO:
            self._parsear_declaracion()
        self._consumir_reservada('end')
        if nuevo_ambito:
            self.tabla_simbolos.salir_ambito()

    def _parsear_sentencia_o_bloque(self):
        if self._es_reservada('begin'):
            self._parsear_bloque()
        else:
            self._parsear_declaracion()

    # ==================== EXPRESIONES ====================
    def _parsear_expresion(self) -> Tuple[TipoDato, Any]:
        return self._parsear_or()

    def _parsear_or(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_and()
        while self._es_reservada('or'):
            self._avanzar()
            tipo_der, val_der = self._parsear_and()
        return TipoDato.BOOLEAN, None

    def _parsear_and(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_relacional()
        while self._es_reservada('and'):
            self._avanzar()
            tipo_der, val_der = self._parsear_relacional()
        return TipoDato.BOOLEAN, None

    def _parsear_relacional(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_suma()
        while self._actual().tipo == TipoToken.OPERADOR and self._actual().valor in OPERADORES_RELACIONALES:
            self._avanzar()
            tipo_der, val_der = self._parsear_suma()
        return TipoDato.BOOLEAN, None

    def _parsear_suma(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_termino()
        while self._actual().tipo == TipoToken.OPERADOR and self._actual().valor in ('+', '-'):
            self._avanzar()
            tipo_der, val_der = self._parsear_termino()
        return tipo_izq, val_izq

    def _parsear_termino(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_unario()
        while (self._actual().tipo == TipoToken.OPERADOR and self._actual().valor in ('*', '/')) or \
              self._es_reservada('div') or self._es_reservada('mod'):
            self._avanzar()
            tipo_der, val_der = self._parsear_unario()
        return tipo_izq, val_izq

    def _parsear_unario(self) -> Tuple[TipoDato, Any]:
        t = self._actual()
        if t.tipo == TipoToken.OPERADOR and t.valor == '-':
            self._avanzar()
            tipo, valor = self._parsear_unario()
            return tipo, None
        if t.tipo == TipoToken.RESERVADA and t.valor == 'not':
            self._avanzar()
            tipo, valor = self._parsear_unario()
            return TipoDato.BOOLEAN, None
        return self._parsear_primario()

    def _parsear_llamada_sentencia(self):
        self._parsear_llamada()
        self._consumir(TipoToken.PUNTO_COMA, '";"')

    def _parsear_llamada(self) -> Tuple[TipoDato, Any]:
        self._consumir(TipoToken.IDENTIFICADOR, 'identificador')
        self._consumir(TipoToken.PARENTESIS_A, '"("')
        if self._actual().tipo != TipoToken.PARENTESIS_C:
            self._parsear_expresion()
            while self._actual().tipo == TipoToken.COMA:
                self._avanzar()
                self._parsear_expresion()
        self._consumir(TipoToken.PARENTESIS_C, '")"')
        return TipoDato.DESCONOCIDO, None

    def _parsear_primario(self) -> Tuple[TipoDato, Any]:
        t = self._actual()
        if t.tipo in (TipoToken.ENTERO, TipoToken.REAL, TipoToken.CADENA):
            self._avanzar()
            return TipoDato.DESCONOCIDO, None
        if t.tipo == TipoToken.RESERVADA and t.valor in ('true', 'false'):
            self._avanzar()
            return TipoDato.BOOLEAN, None
        if t.tipo == TipoToken.IDENTIFICADOR:
            self._avanzar()
            return TipoDato.DESCONOCIDO, None
        if t.tipo == TipoToken.PARENTESIS_A:
            self._avanzar()
            resultado = self._parsear_expresion()
            self._consumir(TipoToken.PARENTESIS_C, '")"')
            return resultado
        self._err_sint(t, f'factor inesperado "{t.valor}"')
        self._avanzar()
        return TipoDato.DESCONOCIDO, None