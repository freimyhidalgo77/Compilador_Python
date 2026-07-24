"""
CAPA SEMANTICA — FASE 3 (todas las validaciones semánticas)
──────────────────────────────────────────────────────────────
"""

from typing import List, Dict, Set, Tuple, Any
from Modelo import Token, TipoToken, TipoDato, Simbolo, ErrorCompilacion
from Simbolos import TablaSimbolos
from Constantes import PALABRAS_TIPO, OPERADORES_RELACIONALES


class AnalizadorSemantico:
    def __init__(self, tokens: List[Token], tabla_simbolos: TablaSimbolos):
        self.tokens = tokens
        self.tabla_simbolos = tabla_simbolos
        self.errores: List[ErrorCompilacion] = []
        self.pos = 0
        self._usos: Set[str] = set()
        self._declaraciones: Set[str] = set()

    def _err_sem(self, t: Token, mensaje: str):
        self.errores.append(ErrorCompilacion('SEMANTICO', t.linea, t.columna, mensaje))

    # ==================== PUNTO DE ENTRADA ====================
    def analizar(self):
        # 1. Validaciones semánticas en línea (recorriendo los tokens)
        self._analizar_semantica_en_linea()
        
        # 2. Validaciones globales
        self._recolectar_usos_y_declaraciones()
        self._verificar_variables_no_utilizadas()
        self._verificar_codigo_inalcanzable()

    # ==================== SEMÁNTICA EN LÍNEA ====================
    def _analizar_semantica_en_linea(self):
        """Recorre los tokens y aplica validaciones semánticas"""
        self.pos = 0
        while self.pos < len(self.tokens):
            t = self.tokens[self.pos]
            
            # Buscar declaraciones var
            if t.tipo == TipoToken.RESERVADA and t.valor == 'var':
                self._procesar_declaracion_var()
            
            # Buscar asignaciones
            elif t.tipo == TipoToken.IDENTIFICADOR:
                if self.pos + 1 < len(self.tokens):
                    siguiente = self.tokens[self.pos + 1]
                    if siguiente.tipo == TipoToken.ASIGNACION:
                        self._validar_asignacion(t)
            
            # Buscar condiciones if/while
            elif t.tipo == TipoToken.RESERVADA and t.valor in ('if', 'while'):
                self._validar_condicion(t)
            
            self.pos += 1

    def _procesar_declaracion_var(self):
        """Procesa declaraciones var y las registra en la tabla"""
        self.pos += 1  # Saltar 'var'
        
        while self.pos < len(self.tokens):
            t = self.tokens[self.pos]
            if t.tipo != TipoToken.IDENTIFICADOR:
                break
                
            # Recoger identificadores
            identificadores = []
            while self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.IDENTIFICADOR:
                identificadores.append(self.tokens[self.pos])
                self.pos += 1
                if self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.COMA:
                    self.pos += 1
                else:
                    break
            
            # Esperar ':'
            if self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.DOS_PUNTOS:
                self.pos += 1
            else:
                break
                
            # Obtener tipo
            if self.pos < len(self.tokens):
                tipo_tok = self.tokens[self.pos]
                tipo_dato = TipoDato.DESCONOCIDO
                if tipo_tok.tipo == TipoToken.RESERVADA and tipo_tok.valor in PALABRAS_TIPO:
                    tipo_dato = TipoDato[PALABRAS_TIPO[tipo_tok.valor]]
                    self.pos += 1
                    
                    # Registrar en tabla de símbolos
                    for id_tok in identificadores:
                        if id_tok is not None:
                            ok = self.tabla_simbolos.declarar(
                                Simbolo(id_tok.valor, tipo_dato, None, False, id_tok.linea)
                            )
                            if not ok:
                                self._err_sem(id_tok, f'"{id_tok.valor}" ya fue declarado en este ambito')
                            else:
                                self._declaraciones.add(id_tok.valor)
                
                # Buscar inicialización
                if self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.ASIGNACION:
                    self.pos += 1
                    tipo_expr, valor_expr = self._parsear_expresion()
                    if len(identificadores) == 1:
                        simb = self.tabla_simbolos.buscar(identificadores[0].valor)
                        if simb and simb.tipo != TipoDato.DESCONOCIDO and tipo_expr != TipoDato.DESCONOCIDO:
                            if simb.tipo != tipo_expr:
                                self._err_sem(identificadores[0], 
                                    f'no se puede asignar un valor de tipo {tipo_expr} a la '
                                    f'variable "{identificadores[0].valor}" declarada como {simb.tipo}')
                        if simb:
                            self.tabla_simbolos.actualizar(identificadores[0].valor, valor_expr)
                
                # Esperar ';'
                if self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.PUNTO_COMA:
                    self.pos += 1
                else:
                    break
            else:
                break

    def _validar_asignacion(self, id_tok: Token):
        """Valida asignación: variable declarada y tipos compatibles"""
        simb = self.tabla_simbolos.buscar(id_tok.valor)
        if simb is None:
            self._err_sem(id_tok, f'"{id_tok.valor}" no fue declarado')
            return
        
        if simb.es_constante:
            self._err_sem(id_tok, f'"{id_tok.valor}" es constante y no puede reasignarse')
            return
        
        # Saltar ':=' y analizar expresión
        self.pos += 2  # Saltar ID y :=
        tipo_expr, valor_expr = self._parsear_expresion()
        
        # Verificar compatibilidad de tipos
        if simb.tipo != TipoDato.DESCONOCIDO and tipo_expr != TipoDato.DESCONOCIDO:
            if simb.tipo != tipo_expr:
                self._err_sem(id_tok, 
                    f'no se puede asignar un valor de tipo {tipo_expr} a '
                    f'"{id_tok.valor}" declarada como {simb.tipo}')
        else:
            self.tabla_simbolos.actualizar(id_tok.valor, valor_expr)
        
        # Registrar uso
        self._usos.add(id_tok.valor)

    def _validar_condicion(self, t: Token):
        """Valida que la condición sea booleana"""
        self.pos += 1  # Saltar 'if' o 'while'
        tipo_cond, _ = self._parsear_expresion()
        if tipo_cond != TipoDato.BOOLEAN and tipo_cond != TipoDato.DESCONOCIDO:
            self._err_sem(t, f'la condicion de "{t.valor}" debe ser booleana, se recibio {tipo_cond}')

    # ==================== EXPRESIONES (igual que antes pero con validaciones) ====================
    def _parsear_expresion(self) -> Tuple[TipoDato, Any]:
        return self._parsear_or()

    def _parsear_or(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_and()
        while self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.RESERVADA and self.tokens[self.pos].valor == 'or':
            op_tok = self.tokens[self.pos]
            self.pos += 1
            tipo_der, val_der = self._parsear_and()
            if tipo_izq != TipoDato.BOOLEAN or tipo_der != TipoDato.BOOLEAN:
                self._err_sem(op_tok, f'"or" requiere operandos booleanos, se recibio {tipo_izq} y {tipo_der}')
            val_izq = (val_izq or val_der) if isinstance(val_izq, bool) and isinstance(val_der, bool) else None
            tipo_izq = TipoDato.BOOLEAN
        return tipo_izq, val_izq

    def _parsear_and(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_relacional()
        while self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.RESERVADA and self.tokens[self.pos].valor == 'and':
            op_tok = self.tokens[self.pos]
            self.pos += 1
            tipo_der, val_der = self._parsear_relacional()
            if tipo_izq != TipoDato.BOOLEAN or tipo_der != TipoDato.BOOLEAN:
                self._err_sem(op_tok, f'"and" requiere operandos booleanos, se recibio {tipo_izq} y {tipo_der}')
            val_izq = (val_izq and val_der) if isinstance(val_izq, bool) and isinstance(val_der, bool) else None
            tipo_izq = TipoDato.BOOLEAN
        return tipo_izq, val_izq

    def _parsear_relacional(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_suma()
        while self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.OPERADOR and self.tokens[self.pos].valor in OPERADORES_RELACIONALES:
            op = self.tokens[self.pos]
            self.pos += 1
            tipo_der, val_der = self._parsear_suma()
            if tipo_izq != tipo_der and tipo_izq != TipoDato.DESCONOCIDO and tipo_der != TipoDato.DESCONOCIDO:
                self._err_sem(op, f'operacion "{op.valor}" entre tipos incompatibles {tipo_izq} y {tipo_der}')
            val_izq = self._evaluar_relacional(op.valor, val_izq, val_der)
            tipo_izq = TipoDato.BOOLEAN
        return tipo_izq, val_izq

    def _parsear_suma(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_termino()
        while self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.OPERADOR and self.tokens[self.pos].valor in ('+', '-'):
            op = self.tokens[self.pos]
            self.pos += 1
            tipo_der, val_der = self._parsear_termino()
            es_concat = op.valor == '+' and (tipo_izq == TipoDato.STRING or tipo_der == TipoDato.STRING)
            if not es_concat and tipo_izq != tipo_der and tipo_izq != TipoDato.DESCONOCIDO and tipo_der != TipoDato.DESCONOCIDO:
                self._err_sem(op, f'operacion "{op.valor}" entre tipos incompatibles {tipo_izq} y {tipo_der}')
            val_izq = self._evaluar_binaria(op.valor, val_izq, val_der)
            if es_concat:
                tipo_izq = TipoDato.STRING
        return tipo_izq, val_izq

    def _parsear_termino(self) -> Tuple[TipoDato, Any]:
        tipo_izq, val_izq = self._parsear_unario()
        while (self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.OPERADOR and self.tokens[self.pos].valor in ('*', '/')) or \
              (self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.RESERVADA and self.tokens[self.pos].valor in ('div', 'mod')):
            op = self.tokens[self.pos]
            self.pos += 1
            tipo_der, val_der = self._parsear_unario()
            if tipo_izq != tipo_der and tipo_izq != TipoDato.DESCONOCIDO and tipo_der != TipoDato.DESCONOCIDO:
                self._err_sem(op, f'operacion "{op.valor}" entre tipos incompatibles {tipo_izq} y {tipo_der}')
            val_izq = self._evaluar_binaria(op.valor, val_izq, val_der)
        return tipo_izq, val_izq

    def _parsear_unario(self) -> Tuple[TipoDato, Any]:
        if self.pos >= len(self.tokens):
            return TipoDato.DESCONOCIDO, None
            
        t = self.tokens[self.pos]
        if t.tipo == TipoToken.OPERADOR and t.valor == '-':
            self.pos += 1
            tipo, valor = self._parsear_unario()
            if tipo not in (TipoDato.INTEGER, TipoDato.REAL, TipoDato.DESCONOCIDO):
                self._err_sem(t, f'el operador unario "-" requiere un tipo numerico, se recibio {tipo}')
            nuevo_valor = -valor if isinstance(valor, (int, float)) else None
            return tipo, nuevo_valor
        if t.tipo == TipoToken.RESERVADA and t.valor == 'not':
            self.pos += 1
            tipo, valor = self._parsear_unario()
            if tipo != TipoDato.BOOLEAN and tipo != TipoDato.DESCONOCIDO:
                self._err_sem(t, f'"not" requiere un operando booleano, se recibio {tipo}')
            nuevo_valor = (not valor) if isinstance(valor, bool) else None
            return TipoDato.BOOLEAN, nuevo_valor
        return self._parsear_primario()

    def _parsear_primario(self) -> Tuple[TipoDato, Any]:
        if self.pos >= len(self.tokens):
            return TipoDato.DESCONOCIDO, None
            
        t = self.tokens[self.pos]
        if t.tipo == TipoToken.ENTERO:
            self.pos += 1
            return TipoDato.INTEGER, int(t.valor)
        if t.tipo == TipoToken.REAL:
            self.pos += 1
            return TipoDato.REAL, float(t.valor)
        if t.tipo == TipoToken.CADENA:
            self.pos += 1
            return TipoDato.STRING, t.valor
        if t.tipo == TipoToken.RESERVADA and t.valor in ('true', 'false'):
            self.pos += 1
            return TipoDato.BOOLEAN, (t.valor == 'true')
        if t.tipo == TipoToken.IDENTIFICADOR:
            simb = self.tabla_simbolos.buscar(t.valor)
            if simb is None:
                self._err_sem(t, f'"{t.valor}" no fue declarado')
            self.pos += 1
            self._usos.add(t.valor)
            return (simb.tipo if simb else TipoDato.DESCONOCIDO), (simb.valor if simb else None)
        if t.tipo == TipoToken.PARENTESIS_A:
            self.pos += 1
            resultado = self._parsear_expresion()
            if self.pos < len(self.tokens) and self.tokens[self.pos].tipo == TipoToken.PARENTESIS_C:
                self.pos += 1
            return resultado
        return TipoDato.DESCONOCIDO, None

    # ==================== VALIDACIONES GLOBALES ====================
    def _recolectar_usos_y_declaraciones(self):
        # Ya se recolectan durante el análisis
        pass

    def _verificar_variables_no_utilizadas(self):
        for ambito in self.tabla_simbolos._pila_ambitos:
            for nombre, simbolo in ambito.items():
                if nombre not in self._usos:
                    token_falso = Token(TipoToken.IDENTIFICADOR, nombre, simbolo.linea, 1)
                    self._err_sem(token_falso, f'la variable "{nombre}" fue declarada pero nunca utilizada')

    def _verificar_codigo_inalcanzable(self):
        palabras_salto = ('return', 'break', 'continue')
        i = 0
        n = len(self.tokens)
        while i < n:
            t = self.tokens[i]
            if t.tipo == TipoToken.RESERVADA and t.valor in palabras_salto:
                j = i
                while j < n and self.tokens[j].tipo != TipoToken.PUNTO_COMA:
                    j += 1
                if j < n:
                    siguiente = self.tokens[j + 1] if j + 1 < n else None
                    if siguiente is not None and not (
                        siguiente.tipo == TipoToken.RESERVADA and siguiente.valor == 'end'
                    ) and siguiente.tipo != TipoToken.FIN_ARCHIVO:
                        self._err_sem(
                            siguiente,
                            f'codigo inalcanzable despues de "{t.valor}": "{siguiente.valor}" nunca se ejecutara'
                        )
                i = j
            i += 1

    # ==================== EVALUADORES ====================
    @staticmethod
    def _evaluar_binaria(op: str, izq: Any, der: Any) -> Any:
        if izq is None or der is None:
            return None
        try:
            if isinstance(izq, bool) or isinstance(der, bool):
                pass
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

    def resumen_por_tipo(self) -> Dict[str, int]:
        conteo: Dict[str, int] = {}
        for ambito in self.tabla_simbolos._pila_ambitos:
            for simbolo in ambito.values():
                clave = str(simbolo.tipo)
                conteo[clave] = conteo.get(clave, 0) + 1
        return conteo