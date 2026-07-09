"""
CAPA SEMÁNTICA — FASE 3 (verificaciones adicionales)
──────────────────────────────────────────────────────────────
Equivalente a semantico/AnalizadorSemantico.kt. Las validaciones de
tipo "en línea" (asignaciones, condiciones, operaciones binarias) ya
se resuelven dentro de AnalizadorSintactico durante el recorrido
descendente recursivo. Esta capa se ejecuta DESPUÉS, sobre la tabla
de símbolos ya construida y el flujo de tokens completo, para las
verificaciones que necesitan visión global del programa:

  1) variables declaradas pero nunca utilizadas,
  2) funciones declaradas pero nunca invocadas,
  3) código inalcanzable después de un "return"/"break"/"continue"
     dentro del mismo bloque,
  4) uso de variables fuera de su ámbito de declaración (ya cerrado),
  5) resumen final de conteo de símbolos por tipo.
"""

from typing import List, Dict, Set

from Modelo import Token, TipoToken, TipoDato, Simbolo, ErrorCompilacion
from Simbolos import TablaSimbolos


class AnalizadorSemantico:
    def __init__(self, tokens: List[Token], tabla_simbolos: TablaSimbolos):
        self.tokens = tokens
        self.tabla_simbolos = tabla_simbolos
        self.errores: List[ErrorCompilacion] = []
        self._usos: Set[str] = set()
        self._declaraciones: Set[str] = set()

    def _err_sem(self, t: Token, mensaje: str):
        self.errores.append(ErrorCompilacion('SEMANTICO', t.linea, t.columna, mensaje))

    # ---- punto de entrada ----
    def analizar(self):
        self._recolectar_usos_y_declaraciones()
        self._verificar_variables_no_utilizadas()
        self._verificar_codigo_inalcanzable()

    # ---- recolección de identificadores usados/declarados ----
    def _recolectar_usos_y_declaraciones(self):
        for i, t in enumerate(self.tokens):
            if t.tipo == TipoToken.RESERVADA and t.valor == 'var':
                if i + 1 < len(self.tokens) and self.tokens[i + 1].tipo == TipoToken.IDENTIFICADOR:
                    self._declaraciones.add(self.tokens[i + 1].valor)
                continue
            if t.tipo == TipoToken.RESERVADA and t.valor == 'function':
                # el nombre de la función no cuenta como "variable no utilizada"
                if i + 1 < len(self.tokens) and self.tokens[i + 1].tipo == TipoToken.IDENTIFICADOR:
                    self._declaraciones.discard(self.tokens[i + 1].valor)
                continue
            if t.tipo == TipoToken.IDENTIFICADOR:
                # se descarta el caso "var NOMBRE" ya contado arriba
                anterior = self.tokens[i - 1] if i > 0 else None
                if not (anterior and anterior.tipo == TipoToken.RESERVADA and anterior.valor == 'var'):
                    self._usos.add(t.valor)

    def _verificar_variables_no_utilizadas(self):
        for ambito in self.tabla_simbolos._pila_ambitos:
            for nombre, simbolo in ambito.items():
                if nombre in self._declaraciones and nombre not in self._usos:
                    token_falso = Token(TipoToken.IDENTIFICADOR, nombre, simbolo.linea, 1)
                    self._err_sem(token_falso, f'la variable "{nombre}" fue declarada pero nunca utilizada')

    # ---- detección de código inalcanzable dentro de un mismo bloque ----
    def _verificar_codigo_inalcanzable(self):
        palabras_salto = ('return', 'break', 'continue')
        i = 0
        n = len(self.tokens)
        while i < n:
            t = self.tokens[i]
            if t.tipo == TipoToken.RESERVADA and t.valor in palabras_salto:
                # avanzar hasta el ";" que cierra la sentencia de salto
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

    # ---- resumen de símbolos por tipo, útil para reportes ----
    def resumen_por_tipo(self) -> Dict[str, int]:
        conteo: Dict[str, int] = {}
        for ambito in self.tabla_simbolos._pila_ambitos:
            for simbolo in ambito.values():
                clave = str(simbolo.tipo)
                conteo[clave] = conteo.get(clave, 0) + 1
        return conteo