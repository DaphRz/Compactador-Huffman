"""Linha de comando (alternativa à interface gráfica, útil como plano B na apresentação).

Exemplos::

    python cli.py compactar texto.txt texto.huf
    python cli.py compactar texto.txt texto.huf --sem-lz77
    python cli.py descompactar texto.huf texto_restaurado.txt
"""

from __future__ import annotations

import argparse
import sys

import compactador
import formato
import metricas


def main(argumentos: list[str] | None = None) -> int:
    """Ponto de entrada da linha de comando.

    Args:
        argumentos: lista de argumentos (``None`` = ``sys.argv[1:]``).

    Returns:
        Código de saída (0 = sucesso).
    """
    parser = argparse.ArgumentParser(description="Compactador de Huffman (+ LZ77)")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_comp = sub.add_parser("compactar", help="compacta um arquivo de texto")
    p_comp.add_argument("entrada")
    p_comp.add_argument("saida")
    p_comp.add_argument("--sem-lz77", action="store_true", help="usa só Huffman")

    p_desc = sub.add_parser("descompactar", help="restaura um arquivo .huf")
    p_desc.add_argument("entrada")
    p_desc.add_argument("saida")

    args = parser.parse_args(argumentos)

    try:
        if args.comando == "compactar":
            r = compactador.compactar_arquivo(args.entrada, args.saida, usar_lz77=not args.sem_lz77)
            if r is None:
                print("compactar_arquivo ainda não foi implementado.", file=sys.stderr)
                return 1
            print(f"Original:   {r.tamanho_original} bytes")
            print(f"Compactado: {r.tamanho_compactado} bytes "
                  f"(cabeçalho {r.tamanho_cabecalho} + payload {r.tamanho_payload})")
            print(f"Taxa:       {metricas.taxa_de_compressao(r.tamanho_original, r.tamanho_compactado)}")
            print(f"Redução:    {metricas.percentual_de_reducao(r.tamanho_original, r.tamanho_compactado)} %")
            print(f"Tempo:      {r.tempo_segundos:.3f} s")
        else:
            r = compactador.descompactar_arquivo(args.entrada, args.saida)
            if r is None:
                print("descompactar_arquivo ainda não foi implementado.", file=sys.stderr)
                return 1
            print(f"Restaurado: {len(r.dados)} bytes em {r.tempo_segundos:.3f} s -> {args.saida}")
    except formato.FormatoInvalidoError as erro:
        print(f"Arquivo inválido: {erro}", file=sys.stderr)
        return 2
    except OSError as erro:
        print(f"Erro de arquivo: {erro}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
