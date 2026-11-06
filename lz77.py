"""Etapa LZ77 (variante LZSS) aplicada ANTES do Huffman.

Ideia: textos repetem trechos ("de", "que", "ção", palavras inteiras). O LZ77
troca uma repetição por uma referência ao passado: "volte ``distancia`` bytes
e copie ``comprimento`` bytes". O Huffman, depois, comprime os bytes dessa
saída explorando a frequência dos símbolos. As duas técnicas se completam:
LZ77 elimina repetições de sequências; Huffman explora a distribuição de
símbolos.

Variante usada (LZSS): cada token é OU um literal (1 byte) OU uma referência.
Só vale emitir uma referência se ela tiver pelo menos ``COMPRIMENTO_MINIMO``
bytes, porque ela ocupa 2 bytes.

Formato da serialização (``serializar``/``desserializar``)::

    [flags][token][token]...[token]   (até 8 tokens por grupo)
     │
     └─ 1 byte; bit i (do menos significativo para o mais) diz se o
        i-ésimo token do grupo é literal (0) ou referência (1)

    literal    -> 1 byte: o próprio byte
    referência -> 2 bytes: 12 bits de distância (1..4095)
                           +  4 bits de (comprimento - 3)  (3..18)

    Ex.: distancia=10, comprimento=5 -> valor = (10 << 4) | (5 - 3)
         -> bytes: valor >> 8, valor & 0xFF

MELHORIA OPCIONAL (estilo DEFLATE/gzip): em vez de serializar em bytes e
passar ao Huffman, aplicar Huffman diretamente sobre um alfabeto de tokens
(literais 0..255 + códigos de comprimento) e outro para as distâncias.
Comprime mais, porém é mais trabalhoso. Bom tópico para a apresentação.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Union

TAMANHO_JANELA: int = 4095
"""Maior distância que uma referência pode apontar (cabe em 12 bits)."""

COMPRIMENTO_MINIMO: int = 3
"""Menor repetição que compensa virar referência (referência ocupa 2 bytes)."""

COMPRIMENTO_MAXIMO: int = 18
"""Maior repetição representável: 4 bits guardam (comprimento - 3) -> 0..15."""

MAX_CANDIDATOS: int = 64
"""Quantas posições anteriores testar por busca (troca velocidade por taxa)."""


@dataclass(frozen=True)
class TokenLiteral:
    """Token que representa um byte copiado sem compressão.

    Attributes:
        byte: valor do byte (0..255).
    """

    byte: int


@dataclass(frozen=True)
class TokenReferencia:
    """Token que manda copiar um trecho já visto.

    Attributes:
        distancia: quantos bytes voltar a partir da posição atual (1..TAMANHO_JANELA).
        comprimento: quantos bytes copiar (COMPRIMENTO_MINIMO..COMPRIMENTO_MAXIMO).
            Pode ser maior que ``distancia`` (sobreposição), ex.: "aaaaaa"
            vira literal 'a' + referência(distancia=1, comprimento=5).
    """

    distancia: int
    comprimento: int


Token = Union[TokenLiteral, TokenReferencia]


def comprimir(dados: bytes) -> list[Token]:
    """Converte ``dados`` em uma lista de tokens LZ77.

    Algoritmo (guloso):
        posicao = 0
        enquanto posicao < len(dados):
            procurar a maior correspondência na janela (``_maior_correspondencia``)
            se comprimento >= COMPRIMENTO_MINIMO:
                emitir TokenReferencia e avançar ``comprimento`` posições
            senão:
                emitir TokenLiteral e avançar 1 posição
            (a cada posição avançada, registrar a posição no índice)

    Args:
        dados: conteúdo original.

    Returns:
        Lista de tokens. Para ``dados`` vazio, ``[]``.
    """
    # Índice ``dict[bytes, deque[int]]``: cada trinca de bytes (dados[i:i+3])
    # aponta para as posições em que ela apareceu. Isso evita comparar com a
    # janela inteira (busca ingênua O(n * janela)). O deque(maxlen=...) limita
    # a memória e o número de candidatos testados.
    tokens: list[Token] = []
    indice: dict[bytes, deque[int]] = {}
    tamanho = len(dados)
    ultima_indexavel = tamanho - COMPRIMENTO_MINIMO  # última posição com trinca completa

    def registrar(i: int) -> None:
        if i <= ultima_indexavel:
            trinca = dados[i:i + COMPRIMENTO_MINIMO]
            posicoes = indice.get(trinca)
            if posicoes is None:
                posicoes = deque(maxlen=MAX_CANDIDATOS)
                indice[trinca] = posicoes
            posicoes.append(i)

    posicao = 0
    while posicao < tamanho:
        distancia, comprimento = _maior_correspondencia(dados, posicao, indice)
        if comprimento >= COMPRIMENTO_MINIMO:
            tokens.append(TokenReferencia(distancia, comprimento))
            for i in range(posicao, posicao + comprimento):
                registrar(i)
            posicao += comprimento
        else:
            tokens.append(TokenLiteral(dados[posicao]))
            registrar(posicao)
            posicao += 1
    return tokens


def _maior_correspondencia(
    dados: bytes,
    posicao: int,
    indice: dict[bytes, deque[int]],
) -> tuple[int, int]:
    """Procura a maior repetição de ``dados[posicao:]`` dentro da janela.

    Args:
        dados: conteúdo completo.
        posicao: posição atual.
        indice: trinca de bytes -> posições anteriores em que ela apareceu.

    Returns:
        Tupla ``(distancia, comprimento)``. Se nada for encontrado, ``(0, 0)``.
    """
    candidatos = indice.get(dados[posicao:posicao + COMPRIMENTO_MINIMO])
    if not candidatos:
        return 0, 0

    limite = min(COMPRIMENTO_MAXIMO, len(dados) - posicao)
    melhor_distancia, melhor_comprimento = 0, 0

    # Do mais recente para o mais antigo: em caso de empate fica a menor distância.
    for candidato in reversed(candidatos):
        distancia = posicao - candidato
        if distancia > TAMANHO_JANELA:
            break  # os demais são ainda mais antigos, também fora da janela
        # A trinca já coincide; continuar a partir do 4º byte.
        comprimento = COMPRIMENTO_MINIMO
        while comprimento < limite and dados[candidato + comprimento] == dados[posicao + comprimento]:
            comprimento += 1
        if comprimento > melhor_comprimento:
            melhor_distancia, melhor_comprimento = distancia, comprimento
            if comprimento == limite:
                break

    return melhor_distancia, melhor_comprimento


def descomprimir(tokens: Iterable[Token]) -> bytes:
    """Reconstrói os dados originais a partir dos tokens.

    Args:
        tokens: sequência de ``TokenLiteral``/``TokenReferencia``.

    Returns:
        Os bytes originais.

    Raises:
        ValueError: se uma referência apontar para antes do início dos dados.
    """
    saida = bytearray()
    for token in tokens:
        if isinstance(token, TokenLiteral):
            saida.append(token.byte)
        else:
            distancia, comprimento = token.distancia, token.comprimento
            if distancia <= 0 or distancia > len(saida):
                raise ValueError(
                    f"referência inválida: distância {distancia} com apenas {len(saida)} bytes gerados"
                )
            if comprimento <= distancia:
                inicio = len(saida) - distancia
                saida += saida[inicio:inicio + comprimento]
            else:
                # Sobreposição (ex.: "aaaaaa"): copiar byte a byte.
                for _ in range(comprimento):
                    saida.append(saida[-distancia])
    return bytes(saida)


def serializar(tokens: list[Token]) -> bytes:
    """Converte os tokens em bytes no formato descrito no topo do módulo.

    Args:
        tokens: saída de ``comprimir``.

    Returns:
        Bytes prontos para serem comprimidos pelo Huffman.
    """
    saida = bytearray()
    for inicio in range(0, len(tokens), 8):
        grupo = tokens[inicio:inicio + 8]
        flags = 0
        corpo = bytearray()
        for i, token in enumerate(grupo):
            if isinstance(token, TokenReferencia):
                if not 1 <= token.distancia <= TAMANHO_JANELA:
                    raise ValueError(f"distância fora de 1..{TAMANHO_JANELA}: {token.distancia}")
                if not COMPRIMENTO_MINIMO <= token.comprimento <= COMPRIMENTO_MAXIMO:
                    raise ValueError(f"comprimento fora de {COMPRIMENTO_MINIMO}..{COMPRIMENTO_MAXIMO}: {token.comprimento}")
                flags |= 1 << i
                valor = (token.distancia << 4) | (token.comprimento - COMPRIMENTO_MINIMO)
                corpo.append(valor >> 8)
                corpo.append(valor & 0xFF)
            else:
                corpo.append(token.byte)
        saida.append(flags)
        saida += corpo
    return bytes(saida)


def desserializar(dados: bytes) -> list[Token]:
    """Inverso de ``serializar``: lê os bytes e recria a lista de tokens.

    Args:
        dados: bytes gerados por ``serializar``.

    Returns:
        Lista de tokens.

    Raises:
        ValueError: se os dados terminarem no meio de um token.
    """
    tokens: list[Token] = []
    posicao = 0
    tamanho = len(dados)
    while posicao < tamanho:
        flags = dados[posicao]
        posicao += 1
        # O último grupo pode ter menos de 8 tokens: para quando os dados acabam.
        for i in range(8):
            if posicao >= tamanho:
                if flags >> i:
                    raise ValueError("dados terminaram antes de uma referência indicada nas flags")
                break
            if flags & (1 << i):
                if posicao + 2 > tamanho:
                    raise ValueError("dados terminaram no meio de uma referência")
                valor = (dados[posicao] << 8) | dados[posicao + 1]
                posicao += 2
                distancia = valor >> 4
                if distancia == 0:
                    raise ValueError("referência com distância 0")
                tokens.append(TokenReferencia(distancia, (valor & 0x0F) + COMPRIMENTO_MINIMO))
            else:
                tokens.append(TokenLiteral(dados[posicao]))
                posicao += 1
    return tokens
