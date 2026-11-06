"""Formato binário do arquivo compactado (.huf).

Layout (todos os inteiros em little-endian)::

    offset  tamanho  campo
    ------  -------  ---------------------------------------------------------
    0       4        MAGICA = b"HUF1"  (identifica o arquivo e a versão)
    4       1        flags: bit 0 = 1 se o LZ77 foi aplicado
    5       8        tamanho_original      (uint64) bytes do arquivo original
    13      8        quantidade_simbolos   (uint64) bytes que entraram no Huffman
                                           (= tamanho_original sem LZ77)
    21      1        bits_padding          (uint8, 0..7)
    22      2        n = quantidade de símbolos na tabela (uint16, 0..256)
    24      2*n      n pares (símbolo: uint8, comprimento do código: uint8)
    24+2n   ...      payload: bits do Huffman empacotados

Os pares guardam só os COMPRIMENTOS dos códigos; os códigos em si são
regenerados com ``huffman.gerar_codigos_canonicos``.

Por que 1 byte para o comprimento basta? Na prática, com até 2^64 bytes de
entrada, o maior código de Huffman fica bem abaixo de 255 bits.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

MAGICA: bytes = b"HUF1"
"""Assinatura no início de todo arquivo .huf."""

FORMATO_FIXO: str = "<4sBQQBH"
"""Formato ``struct`` da parte de tamanho fixo do cabeçalho."""

TAMANHO_FIXO: int = struct.calcsize(FORMATO_FIXO)
"""Tamanho em bytes da parte fixa do cabeçalho (24)."""

FLAG_LZ77: int = 0b0000_0001
"""Máscara do bit que indica uso do LZ77."""


class FormatoInvalidoError(ValueError):
    """Erro lançado quando o arquivo não é um .huf válido ou está corrompido."""


@dataclass
class Cabecalho:
    """Metadados necessários para descompactar.

    Attributes:
        usa_lz77: se o LZ77 foi aplicado antes do Huffman.
        tamanho_original: tamanho, em bytes, do arquivo original.
        quantidade_simbolos: quantos bytes foram codificados pelo Huffman.
        bits_padding: bits de preenchimento no último byte do payload (0..7).
        comprimentos: ``{símbolo: comprimento do código}``.
    """

    usa_lz77: bool
    tamanho_original: int
    quantidade_simbolos: int
    bits_padding: int
    comprimentos: dict[int, int] = field(default_factory=dict)

    def tamanho_em_bytes(self) -> int:
        """Quantos bytes este cabeçalho ocupa quando serializado.

        Returns:
            ``TAMANHO_FIXO + 2 * len(comprimentos)``.
        """
        return TAMANHO_FIXO + 2 * len(self.comprimentos)


def serializar_cabecalho(cabecalho: Cabecalho) -> bytes:
    """Converte o cabeçalho em bytes, seguindo o layout do topo do módulo.

    Args:
        cabecalho: metadados a gravar.

    Returns:
        Os bytes do cabeçalho.
    """
    if not 0 <= cabecalho.bits_padding <= 7:
        raise ValueError(f"bits_padding inválido: {cabecalho.bits_padding}")
    if len(cabecalho.comprimentos) > 256:
        raise ValueError("a tabela não pode ter mais de 256 símbolos")

    flags = FLAG_LZ77 if cabecalho.usa_lz77 else 0
    parte_fixa = struct.pack(
        FORMATO_FIXO,
        MAGICA,
        flags,
        cabecalho.tamanho_original,
        cabecalho.quantidade_simbolos,
        cabecalho.bits_padding,
        len(cabecalho.comprimentos),
    )

    pares = bytearray()
    for simbolo in sorted(cabecalho.comprimentos):
        comprimento = cabecalho.comprimentos[simbolo]
        if not 0 <= simbolo <= 255:
            raise ValueError(f"símbolo fora de 0..255: {simbolo}")
        if not 1 <= comprimento <= 255:
            raise ValueError(f"comprimento de código fora de 1..255: {comprimento}")
        pares += bytes((simbolo, comprimento))

    return parte_fixa + bytes(pares)


def ler_cabecalho(arquivo: bytes) -> tuple[Cabecalho, int]:
    """Lê e valida o cabeçalho no início de ``arquivo``.

    Args:
        arquivo: conteúdo completo do arquivo .huf.

    Returns:
        Tupla ``(cabecalho, inicio_payload)``, em que ``inicio_payload`` é o
        offset onde começam os bits do Huffman.

    Raises:
        FormatoInvalidoError: se o arquivo for menor que o cabeçalho, se a
            assinatura não for ``MAGICA``, se ``bits_padding > 7``, se a tabela
            estiver truncada ou se algum comprimento for 0.
    """
    if len(arquivo) < TAMANHO_FIXO:
        raise FormatoInvalidoError(
            f"arquivo muito pequeno ({len(arquivo)} bytes); "
            f"o cabeçalho ocupa pelo menos {TAMANHO_FIXO} bytes"
        )

    magica, flags, tamanho_original, quantidade_simbolos, bits_padding, n = (
        struct.unpack_from(FORMATO_FIXO, arquivo, 0)
    )

    if magica != MAGICA:
        raise FormatoInvalidoError(f"assinatura inválida: {magica!r} (esperado {MAGICA!r})")
    if bits_padding > 7:
        raise FormatoInvalidoError(f"bits_padding inválido: {bits_padding} (esperado 0..7)")
    if n > 256:
        raise FormatoInvalidoError(f"tabela com {n} símbolos (máximo 256)")

    inicio_payload = TAMANHO_FIXO + 2 * n
    if len(arquivo) < inicio_payload:
        raise FormatoInvalidoError("tabela de comprimentos truncada")

    comprimentos: dict[int, int] = {}
    for i in range(n):
        simbolo = arquivo[TAMANHO_FIXO + 2 * i]
        comprimento = arquivo[TAMANHO_FIXO + 2 * i + 1]
        if comprimento == 0:
            raise FormatoInvalidoError(f"comprimento 0 para o símbolo {simbolo}")
        if simbolo in comprimentos:
            raise FormatoInvalidoError(f"símbolo {simbolo} repetido na tabela")
        comprimentos[simbolo] = comprimento

    if quantidade_simbolos > 0 and n == 0:
        raise FormatoInvalidoError("há símbolos a decodificar, mas a tabela está vazia")

    cabecalho = Cabecalho(
        usa_lz77=bool(flags & FLAG_LZ77),
        tamanho_original=tamanho_original,
        quantidade_simbolos=quantidade_simbolos,
        bits_padding=bits_padding,
        comprimentos=comprimentos,
    )
    return cabecalho, inicio_payload
