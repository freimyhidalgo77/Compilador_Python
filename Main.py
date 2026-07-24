"""
MAIN - PUNTO DE ENTRADA DEL COMPILADOR
──────────────────────────────────────────────────────────────
"""

import sys
from pathlib import Path
from Modelo import Token, TipoToken, Simbolo, TipoDato
from Lexico import AnalizadorLexico
from Sintactico import AnalizadorSintactico
from Semantico import AnalizadorSemantico
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings


def _leer_codigo_con_prompt_toolkit() -> str:
    """
    Editor multilínea real: permite moverse con las flechas (arriba/abajo/
    izquierda/derecha), borrar con Backspace/Delete a través de líneas,
    e insertar/editar libremente antes de compilar.

    Enter inserta una nueva línea (como en cualquier editor de texto).
    Para terminar y compilar: Esc y luego Enter (o Ctrl+D con el buffer vacío).
    """

    bindings = KeyBindings()

    @bindings.add("escape", "enter")
    def _finalizar(event):
        event.current_buffer.validate_and_handle()

    session = PromptSession(multiline=True, key_bindings=bindings)

    print(f"\n{'='*60}")
    print("MODO INTERACTIVO — Escribe tu código Pascal-like")
    print("Muévete con las flechas y borra libremente con Backspace/Delete.")
    print("Enter agrega una nueva línea.")
    print("Para compilar: presiona Esc y luego Enter (o Ctrl+D).")
    print(f"{'='*60}\n")

    try:
        fuente = session.prompt("")
    except EOFError:
        fuente = ""
    return fuente


def _leer_codigo_basico() -> str:
    """Modo de respaldo (sin dependencias externas): línea por línea."""
    print(f"\n{'='*60}")
    print("MODO INTERACTIVO — Escribe tu código Pascal-like")
    print("Termina con una línea que diga: FIN")
    print("(o Ctrl+Z + Enter en Windows / Ctrl+D en Linux-Mac)")
    print("Nota: instala 'prompt_toolkit' (pip install prompt_toolkit)")
    print("para poder retroceder de línea y editar con las flechas.")
    print(f"{'='*60}\n")

    lineas = []
    while True:
        try:
            linea = input()
        except EOFError:
            break
        if linea.strip().upper() == "FIN":
            break
        lineas.append(linea)
    return "\n".join(lineas)


def leer_codigo_interactivo() -> str:
    try:
        return _leer_codigo_con_prompt_toolkit()
    except ImportError:
        return _leer_codigo_basico()


def compilar(fuente: str, nombre: str = "(entrada interactiva)", mostrar_tabla_consola: bool = True):
    """
    Ejecuta las 3 fases del compilador e imprime el progreso por consola.

    mostrar_tabla_consola:
        Si es True (uso normal por consola) imprime la tabla de simbolos
        en ASCII como siempre. Si es False (uso desde la GUI), se omite
        ese bloque porque la interfaz grafica va a dibujar su propia
        tabla interactiva a partir del valor devuelto por esta funcion.

    Devuelve un diccionario con los resultados de la compilacion para que
    quien llame (la GUI, por ejemplo) pueda construir su propia
    presentacion sin tener que volver a parsear el texto impreso.
    """
    print(f"\n{'='*60}")
    print(f"COMPILADOR PASCAL-LIKE")
    print(f"Fuente: {nombre}")
    print(f"{'='*60}\n")

    # FASE 1: ANALISIS LEXICO
    print("FASE 1: ANÁLISIS LÉXICO")
    print("-" * 40)

    lexico = AnalizadorLexico(fuente)
    tokens = lexico.analizar()

    if lexico.errores:
        print("ERRORES LÉXICOS ENCONTRADOS:")
        for error in lexico.errores:
            print(f"  {error}")
        print()

    print(f"Tokens generados: {len(tokens)}")
    print("Lista de tokens:")
    for i, token in enumerate(tokens):
        print(f"  {i+1:3d}. {token}")

    # FASE 2: ANALISIS SINTACTICO (incluye validaciones semanticas en linea)
    print("FASE 2: ANÁLISIS SINTÁCTICO")
    print("-" * 40)

    sintactico = AnalizadorSintactico(tokens)
    sintactico.analizar()

    if sintactico.errores:
        print("ERRORES ENCONTRADOS:")
        for error in sintactico.errores:
            print(f"  {error}")
        print()
    else:
        print("✓ Análisis sintáctico completado sin errores\n")

    # FASE 3: ANALISIS SEMANTICO (verificaciones globales)
    print("FASE 3: ANÁLISIS SEMÁNTICO")
    print("-" * 40)

    semantico = AnalizadorSemantico(tokens, sintactico.tabla_simbolos)
    semantico.analizar()

    if semantico.errores:
        print("ERRORES SEMANTICOS ENCONTRADOS:")
        for error in semantico.errores:
            print(f"  {error}")
        print()
    else:
        print("✓ Analisis semantico completado sin errores\n")

    # Mostrar tabla de simbolos (solo en modo consola; la GUI la dibuja aparte)
    if mostrar_tabla_consola:
        print("TABLA DE SIMBOLOS FINAL:")
        sintactico.tabla_simbolos.imprimir()

    # Resumen de simbolos por tipo
    resumen_tipos = semantico.resumen_por_tipo()
    print("\nRESUMEN DE SIMBOLOS POR TIPO:")
    for tipo, cantidad in resumen_tipos.items():
        print(f"  {tipo}: {cantidad}")

    # Resumen final
    print(f"\n{'='*60}")
    total_errores = len(lexico.errores) + len(sintactico.errores) + len(semantico.errores)
    if total_errores == 0:
        print("✅ COMPILACION EXITOSA - Sin errores")
    else:
        print(f"❌ COMPILACION CON ERRORES - Total: {total_errores}")
        print(f"   Léxicos: {len(lexico.errores)}")
        print(f"   Sintácticos/Semanticos (en línea): {len(sintactico.errores)}")
        print(f"   Semánticos (globales): {len(semantico.errores)}")
    print(f"{'='*60}\n")

    return {
        "tokens": tokens,
        "tabla_simbolos": sintactico.tabla_simbolos,
        "errores_lexico": lexico.errores,
        "errores_sintactico": sintactico.errores,
        "errores_semantico": semantico.errores,
        "resumen_tipos": resumen_tipos,
        "total_errores": total_errores,
    }


def main():
    # Si se pasa un archivo como argumento, se compila ese archivo.
    if len(sys.argv) >= 2:
        archivo = sys.argv[1]
        ruta = Path(archivo)

        if not ruta.exists():
            print(f"Error: El archivo '{archivo}' no existe")
            sys.exit(1)

        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                fuente = f.read()
        except Exception as e:
            print(f"Error al leer el archivo: {e}")
            sys.exit(1)

        compilar(fuente, nombre=archivo)
        return

    # Sin argumentos: modo interactivo en vivo.
    fuente = leer_codigo_interactivo()
    if not fuente.strip():
        print("No se ingresó ningún código. Saliendo.")
        sys.exit(0)

    compilar(fuente)


if __name__ == "__main__":
    main()
