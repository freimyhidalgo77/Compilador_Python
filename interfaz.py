"""
CAPA SINTACTICA — FASE 2 (sintactico) + FASE 3 (semantico embebido)
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
            # Crear un token EOF si no hay más tokens
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

    def _err_sem(self, t: Token, mensaje: str):
        self.errores.append(ErrorCompilacion('SEMANTICO', t.linea, t.columna, mensaje))

    # ---- punto de entrada ----
    def analizar(self):
        self.tabla_simbolos.entrar_ambito()
        self._parsear_encabezado_program()  # <--- CAMBIO: ahora es opcional
        
        # Verificar que hay tokens antes de procesar
        while self.pos < len(self.tokens) and self._actual().tipo != TipoToken.FIN_ARCHIVO:
            self._parsear_declaracion()
            self._parsear_punto_final()  # <--- CAMBIO: ahora maneja EOF

    # ==================== SENTENCIAS ====================
    def _parsear_declaracion(self):
        """Punto de entrada para cualquier declaración/sentencia"""
        if self.pos >= len(self.tokens):
            return
            
        t = self._actual()
        
        # Palabras reservadas que inician una sentencia específica
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
        
        # Si es un identificador, puede ser asignación o llamada a función
        if t.tipo == TipoToken.IDENTIFICADOR:
            # Verificar el siguiente token para decidir
            if self.pos + 1 < len(self.tokens):
                siguiente = self.tokens[self.pos + 1]
                if siguiente.tipo == TipoToken.ASIGNACION:
                    self._parsear_asignacion()
                    return
                elif siguiente.tipo == TipoToken.PARENTESIS_A:
                    self._parsear_llamada_sentencia()
                    return
        
        # Si no se reconoce ningún patrón, error
        self._err_sint(t, f'sentencia no reconocida: "{t.valor}"')
        self._avanzar()  # Avanzar para evitar bucle infinito

    def _parsear_asignacion(self):
        """Parsing de asignación: identificador := expresion ;"""
        id_tok = self._consumir(TipoToken.IDENTIFICADOR, 'identificador')
        if id_tok is None:
            return
        
        # Verificar que la variable existe
        simb = self.tabla_simbolos.buscar(id_tok.valor)
        if simb is None:
            self._err_sem(id_tok, f'"{id_tok.valor}" no fue declarado')
        elif simb.es_constante:
            self._err_sem(id_tok, f'"{id_tok.valor}" es constante y no puede reasignarse')
        
        # Consumir el operador de asignación
        self._consumir(TipoToken.ASIGNACION, '":="')
        
        # Parsear la expresión
        tipo_expr, valor_expr = self._parsear_expresion()
        
        # Verificar compatibilidad de tipos
        if simb is not None and not simb.es_constante:
            if simb.tipo != TipoDato.DESCONOCIDO and tipo_expr != TipoDato.DESCONOCIDO:
                if simb.tipo != tipo_expr:
                    self._err_sem(id_tok, f'no se puede asignar un valor de tipo {tipo_expr} a '
                                           f'"{id_tok.valor}" declarada como {simb.tipo}')
            else:
                self.tabla_simbolos.actualizar(id_tok.valor, valor_expr)
        
        # Consumir el punto y coma
        self._consumir(TipoToken.PUNTO_COMA, '";"')

    def _parsear_encabezado_program(self):
        """Encabezado opcional 'program nombre;'"""
        # <--- CAMBIO: ahora es opcional
        if self._es_reservada('program'):
            self._avanzar()
            self._consumir(TipoToken.IDENTIFICADOR, 'nombre de programa')
            self._consumir(TipoToken.PUNTO_COMA, '";"')
        # Si no hay 'program', simplemente continuar sin errores
  
    def _parsear_punto_final(self):
        """Punto final opcional '.' al final del programa"""
        # <--- CAMBIO: verificar que hay tokens
        if self.pos < len(self.tokens) and self._actual().valor == '.':
            self._avanzar()

    def _parsear_var(self):
      self._consumir_reservada('var')
      self._parsear_grupo_var()
    # Permite múltiples grupos bajo el mismo 'var':
    #   var
    #       x, y: integer;
    #       resultado: integer;
      while self._actual().tipo == TipoToken.IDENTIFICADOR:
         self._parsear_grupo_var()

    def _parsear_grupo_var(self):
        """Parsea un solo grupo: 'id (, id)* : tipo [:= expr] ;'"""
        identificadores = [self._consumir(TipoToken.IDENTIFICADOR, 'identificador')]
        while self._actual().tipo == TipoToken.COMA:
            self._avanzar()
            identificadores.append(self._consumir(TipoToken.IDENTIFICADOR, 'identificador'))

        self._consumir(TipoToken.DOS_PUNTOS, '":"')
        tipo_tok = self._actual()
        tipo_dato = TipoDato.DESCONOCIDO
        if tipo_tok.tipo == TipoToken.RESERVADA and tipo_tok.valor in PALABRAS_TIPO:
            tipo_dato = TipoDato[PALABRAS_TIPO[tipo_tok.valor]]
            self._avanzar()
        else:
            self._err_sint(tipo_tok, f'tipo desconocido "{tipo_tok.valor}"')

        valor_final = None
        if len(identificadores) == 1 and self._actual().tipo == TipoToken.ASIGNACION:
            self._avanzar()
            tipo_expr, valor_expr = self._parsear_expresion()
            valor_final = valor_expr
            if tipo_dato != TipoDato.DESCONOCIDO and tipo_expr != TipoDato.DESCONOCIDO and tipo_dato != tipo_expr:
                self._err_sem(identificadores[0], f'no se puede asignar un valor de tipo {tipo_expr} a la '
                                                   f'variable "{identificadores[0].valor}" declarada como {tipo_dato}')
                valor_final = None

        # --- estas dos partes deben estar SIEMPRE, sin importar si hubo ":=" o no ---
        for id_tok in identificadores:
            if id_tok is not None:
                ok = self.tabla_simbolos.declarar(Simbolo(id_tok.valor, tipo_dato, valor_final, False, id_tok.linea))
                if not ok:
                    self._err_sem(id_tok, f'"{id_tok.valor}" ya fue declarado en este ambito')

        self._consumir(TipoToken.PUNTO_COMA, '";"')

    def _parsear_if(self):
        self._consumir_reservada('if')
        cond_tok = self._actual()
        tipo_cond, _ = self._parsear_expresion()
        if tipo_cond != TipoDato.BOOLEAN and tipo_cond != TipoDato.DESCONOCIDO:
            self._err_sem(cond_tok, f'la condicion de "if" debe ser booleana, se recibio {tipo_cond}')
        self._consumir_reservada('then')
        self._parsear_sentencia_o_bloque()
        if self._es_reservada('else'):
            self._avanzar()
            self._parsear_sentencia_o_bloque()

    def _parsear_while(self):
        self._consumir_reservada('while')
        cond_tok = self._actual()
        tipo_cond, _ = self._parsear_expresion()
        if tipo_cond != TipoDato.BOOLEAN and tipo_cond != TipoDato.DESCONOCIDO:
            self._err_sem(cond_tok, f'la condicion de "while" debe ser booleana, se recibio {tipo_cond}')
        self._consumir_reservada('do')
        self._parsear_sentencia_o_bloque()

    def _parsear_for(self):
        self._consumir_reservada('for')
        id_tok = self._consumir(TipoToken.IDENTIFICADOR, 'identificador')
        simb = self.tabla_simbolos.buscar(id_tok.valor) if id_tok else None
        if id_tok is not None and simb is None:
            self._err_sem(id_tok, f'"{id_tok.valor}" no fue declarado')
        self._consumir(TipoToken.ASIGNACION, '":="')
        tipo_ini, _ = self._parsear_expresion()
        self._consumir_reservada('to')
        tipo_fin, _ = self._parsear_expresion()
        for tipo, tok in ((tipo_ini, id_tok), (tipo_fin, id_tok)):
            if tok is not None and tipo not in (TipoDato.INTEGER, TipoDato.DESCONOCIDO):
                self._err_sem(tok, f'los limites de "for" deben ser integer, se recibio {tipo}')
        self._consumir_reservada('do')
        self.tabla_simbolos.entrar_ambito()
        self._parsear_sentencia_o_bloque()
        self.tabla_simbolos.salir_ambito()

    def _parsear_function(self):
        self._consumir_reservada('function')
        nom_tok = self._consumir(TipoToken.IDENTIFICADOR, 'nombre de funcion')
        if nom_tok is not None:
            self.tabla_simbolos.declarar(Simbolo(nom_tok.valor, TipoDato.DESCONOCIDO, None, False, nom_tok.linea))
        self._consumir(TipoToken.PARENTESIS_A, '"("')
        self.tabla_simbolos.entrar_ambito()
        while self._actual().tipo not in (TipoToken.PARENTESIS_C, TipoToken.FIN_ARCHIVO):
            # Parámetros simplificados: "nombre : tipo" separados por comas.
            p_tok = self._consumir(TipoToken.IDENTIFICADOR, 'parametro')
            self._consumir(TipoToken.DOS_PUNTOS, '":"')
            tipo_tok = self._actual()
            tipo_param = TipoDato.DESCONOCIDO
            if tipo_tok.tipo == TipoToken.RESERVADA and tipo_tok.valor in PALABRAS_TIPO:
                tipo_param = TipoDato[PALABRAS_TIPO[tipo_tok.valor]]
                self._avanzar()
            if p_tok is not None:
                self.tabla_simbolos.declarar(Simbolo(p_tok.valor, tipo_param, None, False, p_tok.linea))
            if self._actual().tipo == TipoToken.COMA:
                self._avanzar()
        self._consumir(TipoToken.PARENTESIS_C, '")"')
        if self._actual().tipo == TipoToken.DOS_PUNTOS:
            self._avanzar()
            self._avanzar()  # tipo de retorno (no se valida contra los "return" internos)
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
        """'then' / 'do' / 'else' pueden ir seguidos de un bloque begin..end
        o de una única sentencia suelta."""
        if self._es_reservada('begin'):
            self._parsear_bloque()
        else:
            self._parsear_declaracion()

    # ==================== EXPRESIONES ====================
    # expresion   := or_expr
    # or_expr     := and_expr ( "or"  and_expr )*
    # and_expr    := relacional ( "and" relacional )*
    # relacional  := suma ( ("="|"<>"|"<"|">"|"<="|">=") suma )*
    # suma        := termino ( ("+"|"-") termino )*
    # termino     := unario ( ("*"|"/"|"div"|"mod") unario )*
    # unario      := ("-" | "not") unario | primario
    # primario    := ENTERO | REAL | CADENA | "true" | "false" | ID
    #              | "(" expresion ")"

    def _parsear_expresion(self) -> Tuple[TipoDato, Any]:
        return self._parsear_or()

    def _parsear_or(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_and()
        while self._es_reservada('or'):
            op_tok = self._actual(); self._avanzar()
            tipo_der, val_der = self._parsear_and()
            if tipo_izq != TipoDato.BOOLEAN or tipo_der != TipoDato.BOOLEAN:
                self._err_sem(op_tok, f'"or" requiere operandos booleanos, se recibio {tipo_izq} y {tipo_der}')
            val_izq = (val_izq or val_der) if isinstance(val_izq, bool) and isinstance(val_der, bool) else None
            tipo_izq = TipoDato.BOOLEAN
        return tipo_izq, val_izq

    def _parsear_and(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_relacional()
        while self._es_reservada('and'):
            op_tok = self._actual(); self._avanzar()
            tipo_der, val_der = self._parsear_relacional()
            if tipo_izq != TipoDato.BOOLEAN or tipo_der != TipoDato.BOOLEAN:
                self._err_sem(op_tok, f'"and" requiere operandos booleanos, se recibio {tipo_izq} y {tipo_der}')
            val_izq = (val_izq and val_der) if isinstance(val_izq, bool) and isinstance(val_der, bool) else None
            tipo_izq = TipoDato.BOOLEAN
        return tipo_izq, val_izq

    def _parsear_relacional(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_suma()
        while self._actual().tipo == TipoToken.OPERADOR and self._actual().valor in OPERADORES_RELACIONALES:
            op = self._actual(); self._avanzar()
            tipo_der, val_der = self._parsear_suma()
            if tipo_izq != tipo_der and tipo_izq != TipoDato.DESCONOCIDO and tipo_der != TipoDato.DESCONOCIDO:
                self._err_sem(op, f'operacion "{op.valor}" entre tipos incompatibles {tipo_izq} y {tipo_der}')
            val_izq = self._evaluar_relacional(op.valor, val_izq, val_der)
            tipo_izq = TipoDato.BOOLEAN
        return tipo_izq, val_izq

    def _parsear_suma(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_termino()
        while self._actual().tipo == TipoToken.OPERADOR and self._actual().valor in ('+', '-'):
            op = self._actual(); self._avanzar()
            tipo_der, val_der = self._parsear_termino()
            # Concatenación: "+" con al menos un lado STRING mezcla libremente con otros tipos.
            es_concat = op.valor == '+' and (tipo_izq == TipoDato.STRING or tipo_der == TipoDato.STRING)
            if not es_concat and tipo_izq != tipo_der and tipo_izq != TipoDato.DESCONOCIDO and tipo_der != TipoDato.DESCONOCIDO:
                self._err_sem(op, f'operacion "{op.valor}" entre tipos incompatibles {tipo_izq} y {tipo_der}')
            val_izq = self._evaluar_binaria(op.valor, val_izq, val_der)
            if es_concat:
                tipo_izq = TipoDato.STRING
        return tipo_izq, val_izq

    def _parsear_termino(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_unario()
        while (self._actual().tipo == TipoToken.OPERADOR and self._actual().valor in ('*', '/')) or \
              self._es_reservada('div') or self._es_reservada('mod'):
            op = self._actual(); self._avanzar()
            tipo_der, val_der = self._parsear_unario()
            if tipo_izq != tipo_der and tipo_izq != TipoDato.DESCONOCIDO and tipo_der != TipoDato.DESCONOCIDO:
                self._err_sem(op, f'operacion "{op.valor}" entre tipos incompatibles {tipo_izq} y {tipo_der}')
            val_izq = self._evaluar_binaria(op.valor, val_izq, val_der)
        return tipo_izq, val_izq

    def _parsear_unario(self) -> Tuple[TipoDato, Any]:
        t = self._actual()
        if t.tipo == TipoToken.OPERADOR and t.valor == '-':
            self._avanzar()
            tipo, valor = self._parsear_unario()
            if tipo not in (TipoDato.INTEGER, TipoDato.REAL, TipoDato.DESCONOCIDO):
                self._err_sem(t, f'el operador unario "-" requiere un tipo numerico, se recibio {tipo}')
            nuevo_valor = -valor if isinstance(valor, (int, float)) else None
            return tipo, nuevo_valor
        if t.tipo == TipoToken.RESERVADA and t.valor == 'not':
            self._avanzar()
            tipo, valor = self._parsear_unario()
            if tipo != TipoDato.BOOLEAN and tipo != TipoDato.DESCONOCIDO:
                self._err_sem(t, f'"not" requiere un operando booleano, se recibio {tipo}')
            nuevo_valor = (not valor) if isinstance(valor, bool) else None
            return TipoDato.BOOLEAN, nuevo_valor
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
        if t.tipo == TipoToken.ENTERO:
            self._avanzar(); return TipoDato.INTEGER, int(t.valor)
        if t.tipo == TipoToken.REAL:
            self._avanzar(); return TipoDato.REAL, float(t.valor)
        if t.tipo == TipoToken.CADENA:
            self._avanzar(); return TipoDato.STRING, t.valor
        if t.tipo == TipoToken.RESERVADA and t.valor in ('true', 'false'):
            self._avanzar(); return TipoDato.BOOLEAN, (t.valor == 'true')
        if t.tipo == TipoToken.IDENTIFICADOR:
            simb = self.tabla_simbolos.buscar(t.valor)
            if simb is None:
                self._err_sem(t, f'"{t.valor}" no fue declarado')
            self._avanzar()
            return (simb.tipo if simb else TipoDato.DESCONOCIDO), (simb.valor if simb else None)
        if t.tipo == TipoToken.PARENTESIS_A:
            self._avanzar()
            resultado = self._parsear_expresion()
            self._consumir(TipoToken.PARENTESIS_C, '")"')
            return resultado
        self._err_sint(t, f'factor inesperado "{t.valor}"')
        self._avanzar()
        return TipoDato.DESCONOCIDO, None

    # ---- mini-evaluador constante ----
    @staticmethod
    def _evaluar_binaria(op: str, izq: Any, der: Any) -> Any:
        if izq is None or der is None:
            return None
        try:
            if isinstance(izq, bool) or isinstance(der, bool):
                pass  # bool no participa en aritmética
            elif isinstance(izq, (int, float)) and isinstance(der, (int, float)) and type(izq) == type(der):
                if op == '+': return izq + der
                if op == '-': return izq - der
                if op == '*': return izq * der
                if op == '/': return (izq / der) if der != 0 else None
                if op == 'div': return (izq // der) if der != 0 else None
                if op == 'mod': return (izq % der) if der != 0 else None
            if op == '+' and (isinstance(izq, str) or isinstance(der, str)):
                return f'{izq}{der}'
        except (TypeError, ZeroDivisionError):
            return None
        return None

    @staticmethod
    def _evaluar_relacional(op: str, izq: Any, der: Any) -> Any:
        if izq is None or der is None:
            return None
        if type(izq) != type(der):
            return None
        try:
            if op == '=': return izq == der
            if op == '<>': return izq != der
            if op in ('<', '>', '<=', '>=') and isinstance(izq, (int, float)) and not isinstance(izq, bool):
                if op == '<': return izq < der
                if op == '>': return izq > der
                if op == '<=': return izq <= der
                if op == '>=': return izq >= der
        except TypeError:
            return None
        return None
