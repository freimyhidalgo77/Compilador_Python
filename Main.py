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


def leer_codigo_interactivo() -> str:
    print(f"\n{'='*60}")
    print("MODO INTERACTIVO — Escribe tu código Pascal-like")
    print("Termina con una línea que diga: FIN")
    print("(o Ctrl+Z + Enter en Windows / Ctrl+D en Linux-Mac)")
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


def compilar(fuente: str, nombre: str = "(entrada interactiva)"):
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

    # Mostrar tabla de simbolos
    print("TABLA DE SIMBOLOS FINAL:")
    sintactico.tabla_simbolos.imprimir()

    # Resumen de simbolos por tipo
    print("\nRESUMEN DE SIMBOLOS POR TIPO:")
    for tipo, cantidad in semantico.resumen_por_tipo().items():
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