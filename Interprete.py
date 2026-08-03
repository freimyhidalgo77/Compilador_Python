"""
INTÉRPRETE - Ejecuta el programa y produce la salida (writeln, resultados de operaciones)
──────────────────────────────────────────────────────────────
Trabaja sobre la tabla de símbolos y los tokens ya validados
por las fases léxica/sintáctica/semántica.
"""

from Modelo import Token, TipoToken, TipoDato


class ErrorEjecucion(Exception):
    pass


class AnalizadorInterprete:
    def __init__(self, tokens, tabla_simbolos):
        self.tokens = [t for t in tokens if t.tipo != TipoToken.FIN_ARCHIVO]
        self.tabla_simbolos = tabla_simbolos
        self.pos = 0
        self.variables = {}  # nombre -> valor actual
        self.salida = []     # líneas que produce writeln
        self.errores = []

    # ---------- utilidades de recorrido ----------

    def _actual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _avanzar(self):
        tok = self._actual()
        self.pos += 1
        return tok

    def _coincide(self, valor=None, tipo=None):
        tok = self._actual()
        if tok is None:
            return False
        if valor is not None and tok.valor.lower() != valor.lower():
            return False
        if tipo is not None and tok.tipo != tipo:
            return False
        return True

    # ---------- punto de entrada ----------

    def ejecutar(self):
        """Busca el bloque begin...end principal y ejecuta cada sentencia."""
        try:
            self._saltar_hasta_begin_principal()
            self._ejecutar_bloque()
        except ErrorEjecucion as e:
            self.errores.append(str(e))
        except Exception as e:
            self.errores.append(f"Error inesperado en ejecución: {e}")
        return self.salida

    def _saltar_hasta_begin_principal(self):
        # Avanza hasta encontrar el 'begin' que abre el bloque principal
        # (asumiendo que las declaraciones 'var' ya fueron registradas
        # en la tabla de símbolos por el análisis sintáctico).
        while self._actual() is not None and not self._coincide('begin'):
            self._avanzar()
        if self._coincide('begin'):
            self._avanzar()  # consumir 'begin'
        else:
            raise ErrorEjecucion("No se encontró el bloque 'begin' principal para ejecutar")

    def _ejecutar_bloque(self):
        while self._actual() is not None and not self._coincide('end'):
            self._ejecutar_sentencia()
        if self._coincide('end'):
            self._avanzar()

    def _ejecutar_sentencia(self):
        tok = self._actual()
        if tok is None:
            return

        # writeln(...) o writeln 'texto';
        if tok.tipo == TipoToken.IDENTIFICADOR and tok.valor.lower() == 'writeln':
            self._ejecutar_writeln()
            return

        # asignación: identificador := expresion ;
        if tok.tipo == TipoToken.IDENTIFICADOR and self._siguiente_es(':='):
            self._ejecutar_asignacion()
            return

        # cualquier otra sentencia no soportada aún: se ignora avanzando
        # hasta el próximo punto y coma para no romper la ejecución
        while self._actual() is not None and not self._coincide(valor=';'):
            self._avanzar()
        if self._coincide(valor=';'):
            self._avanzar()

    def _siguiente_es(self, valor):
        sig = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
        return sig is not None and sig.valor == valor

    def _ejecutar_asignacion(self):
        nombre_tok = self._avanzar()          # identificador
        self._avanzar()                        # :=
        valor = self._evaluar_expresion_hasta(';')
        if self._coincide(valor=';'):
            self._avanzar()
        self.variables[nombre_tok.valor] = valor

    def _ejecutar_writeln(self):
        self._avanzar()  # 'writeln'
        partes_texto = []

        if self._coincide(valor='('):
            self._avanzar()
            while self._actual() is not None and not self._coincide(valor=')'):
                tok = self._actual()
                if tok.tipo == TipoToken.CADENA:
                    partes_texto.append(self._quitar_comillas(tok.valor))
                    self._avanzar()
                elif tok.tipo == TipoToken.IDENTIFICADOR:
                    valor = self.variables.get(tok.valor, '')
                    partes_texto.append(str(valor))
                    self._avanzar()
                elif tok.tipo in (TipoToken.ENTERO, TipoToken.REAL):
                    partes_texto.append(tok.valor)
                    self._avanzar()
                elif self._coincide(valor=','):
                    self._avanzar()
                else:
                    self._avanzar()
            if self._coincide(valor=')'):
                self._avanzar()
        if self._coincide(valor=';'):
            self._avanzar()

        self.salida.append(''.join(partes_texto))

    def _quitar_comillas(self, valor):
        if len(valor) >= 2 and valor[0] in ('"', "'") and valor[-1] == valor[0]:
            return valor[1:-1]
        return valor

    # ---------- evaluación de expresiones ----------

    def _evaluar_expresion_hasta(self, valor_final):
        """Evalúa una expresión aritmética simple (+, -, *, /) término a término
        hasta encontrar el token indicado (por ejemplo ';')."""
        resultado = self._evaluar_termino()
        while self._actual() is not None and self._actual().valor in ('+', '-'):
            op = self._avanzar().valor
            derecho = self._evaluar_termino()
            if op == '+':
                resultado = resultado + derecho
            else:
                resultado = resultado - derecho
        return resultado

    def _evaluar_termino(self):
        resultado = self._evaluar_factor()
        while self._actual() is not None and self._actual().valor in ('*', '/', 'div', 'mod'):
            op = self._avanzar().valor
            derecho = self._evaluar_factor()
            if op == '*':
                resultado = resultado * derecho
            elif op == '/':
                resultado = resultado / derecho
            elif op == 'div':
                resultado = int(resultado) // int(derecho)
            elif op == 'mod':
                resultado = int(resultado) % int(derecho)
        return resultado

    def _evaluar_factor(self):
        tok = self._actual()
        if tok is None:
            raise ErrorEjecucion("Expresión incompleta")

        if tok.valor == '(':
            self._avanzar()
            valor = self._evaluar_expresion_hasta(')')
            if self._coincide(valor=')'):
                self._avanzar()
            return valor

        if tok.tipo == TipoToken.ENTERO:
            self._avanzar()
            return int(tok.valor)

        if tok.tipo == TipoToken.REAL:
            self._avanzar()
            return float(tok.valor)

        if tok.tipo == TipoToken.CADENA:
            self._avanzar()
            return self._quitar_comillas(tok.valor)

        if tok.tipo == TipoToken.IDENTIFICADOR:
            self._avanzar()
            return self.variables.get(tok.valor, 0)

        raise ErrorEjecucion(f"Token inesperado en expresión: {tok.valor}")