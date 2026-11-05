"""Métricas de compressão exibidas na interface e na apresentação.

Definições usadas no trabalho:

* Taxa de compressão = tamanho_compactado / tamanho_original
  (quanto MENOR, melhor; 0,40 significa que sobrou 40% do tamanho).
* Redução (economia) = 1 - taxa, em porcentagem (60% no exemplo acima).
* Fator de compressão = tamanho_original / tamanho_compactado (2,5:1).
* Bits por caractere = 8 * tamanho_compactado / tamanho_original
  (o texto original usa 8 bits por byte).
* Entropia de Shannon H = -Σ p(s) · log2 p(s): limite teórico mínimo de
  bits por símbolo para um código que olha um símbolo de cada vez.
* Comprimento médio L = Σ p(s) · len(código(s)). O Huffman garante
  H <= L < H + 1.
* Eficiência = H / L (100% = ótimo).

Observação para a apresentação: com LZ77 a entropia é calculada sobre a saída
do LZ77, não sobre o texto. Por isso o resultado final pode ficar ABAIXO da
entropia do texto original: o LZ77 explora repetição de sequências, algo que
a entropia de ordem 0 não enxerga.
"""

from __future__ import annotations

from huffman import Codigos, Frequencias


def taxa_de_compressao(tamanho_original: int, tamanho_compactado: int) -> float:
    """Calcula ``tamanho_compactado / tamanho_original``.

    Args:
        tamanho_original: bytes antes da compressão.
        tamanho_compactado: bytes depois da compressão (incluindo cabeçalho).

    Returns:
        A razão (ex.: 0.42). Retorna 0.0 se ``tamanho_original`` for 0.
    """
    # TODO: tratar divisão por zero.
    pass


def percentual_de_reducao(tamanho_original: int, tamanho_compactado: int) -> float:
    """Calcula a economia de espaço em porcentagem.

    Returns:
        ``(1 - taxa) * 100``. Pode ser negativa se o "compactado" ficou maior
        (acontece com arquivos muito pequenos por causa do cabeçalho).
    """
    # TODO: reutilizar taxa_de_compressao.
    pass


def fator_de_compressao(tamanho_original: int, tamanho_compactado: int) -> float:
    """Calcula ``tamanho_original / tamanho_compactado`` (ex.: 2.4 -> "2,4:1").

    Returns:
        O fator; 0.0 se ``tamanho_compactado`` for 0.
    """
    # TODO
    pass


def bits_por_caractere(tamanho_original: int, tamanho_compactado: int) -> float:
    """Média de bits gastos por byte do original no arquivo final.

    Returns:
        ``8 * tamanho_compactado / tamanho_original``; 0.0 se o original for vazio.
    """
    # TODO
    pass


def entropia(frequencias: Frequencias) -> float:
    """Entropia de Shannon (ordem 0) em bits por símbolo.

    Args:
        frequencias: ``{símbolo: frequência}``.

    Returns:
        ``-Σ p · log2(p)``; 0.0 para um dicionário vazio ou com um único símbolo.
    """
    # TODO: total = soma das frequências; p = f / total; usar math.log2.
    pass


def comprimento_medio(frequencias: Frequencias, codigos: Codigos) -> float:
    """Comprimento médio ponderado dos códigos de Huffman, em bits por símbolo.

    Args:
        frequencias: ``{símbolo: frequência}``.
        codigos: ``{símbolo: código}``.

    Returns:
        ``Σ f(s) · len(código(s)) / Σ f(s)``; 0.0 se vazio.
    """
    # TODO
    pass


def eficiencia(entropia_bits: float, comprimento_medio_bits: float) -> float:
    """Eficiência do código: entropia / comprimento médio.

    Returns:
        Valor entre 0 e 1 (1 = código ótimo). Retorna 1.0 se o comprimento
        médio for 0.
    """
    # TODO
    pass
