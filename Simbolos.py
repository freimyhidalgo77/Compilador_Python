"""
CAPA DE TABLA DE SIMBOLOS
──────────────────────────────────────────────────────────────
Reemplaza el diccionario plano `Dict[str, Symbol]` de la version original por una pila de
ambitos (uno por cada bloque begin/end, funcion o for), igual que
la pila de ArrayDeque<MutableMap<String, Simbolo>> de Kotlin.

Ademas del stack de ambitos (que se vacia a medida que se cierran bloques),
se mantiene un historial plano de TODOS los simbolos declarados durante
toda la compilacion. Esto es necesario porque AnalizadorSemantico corre
DESPUES de que AnalizadorSintactico ya cerro (salir_ambito()) los ambitos
de funciones, for y begin..end -- si solo mirara _pila_ambitos, jamas
podria detectar variables locales sin usar, porque ya no existirian ahi.
"""

from typing import List, Dict, Optional

from Modelo import Simbolo


class TablaSimbolos:
    def __init__(self):
        self._pila_ambitos: List[Dict[str, Simbolo]] = []
        self._historial: List[Simbolo] = []

    def entrar_ambito(self):
        self._pila_ambitos.append({})

    def salir_ambito(self):
        if self._pila_ambitos:
            self._pila_ambitos.pop()

    def declarar(self, s: Simbolo) -> bool:
        if not self._pila_ambitos:
            return False
        ambito = self._pila_ambitos[-1]
        if s.nombre in ambito:
            return False
        ambito[s.nombre] = s
        self._historial.append(s)
        return True

    def buscar(self, nombre: str) -> Optional[Simbolo]:
        for ambito in reversed(self._pila_ambitos):
            if nombre in ambito:
                return ambito[nombre]
        return None

    def actualizar(self, nombre: str, valor):
        for ambito in reversed(self._pila_ambitos):
            if nombre in ambito:
                ambito[nombre].valor = valor
                return

    def obtener_historial(self) -> List[Simbolo]:
        """Todos los simbolos declarados durante toda la compilacion,
        incluyendo los de ambitos ya cerrados (funciones, for, begin..end)."""
        return self._historial

    def imprimir(self):
        print("\n+----------------+----------+-----------+-------------+")
        print("|  TABLA DE SIMBOLOS                                   |")
        print("+----------------+----------+-----------+-------------+")
        print("| Nombre         | Tipo     | Constante | Valor       |")
        print("+----------------+----------+-----------+-------------+")
        hay_simbolos = False
        for ambito in self._pila_ambitos:
            for s in ambito.values():
                hay_simbolos = True
                const = "Si" if s.es_constante else "No"
                print(f"| {s.nombre:<14} | {str(s.tipo):<8} | {const:<9} | {str(s.valor):<11} |")
        if not hay_simbolos:
            print("|  (tabla vacia)                                       |")
        print("+----------------+----------+-----------+-------------+")