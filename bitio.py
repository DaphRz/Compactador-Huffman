"""Escrita e leitura de bits individuais empacotados em bytes.

O Huffman produz códigos de tamanho variável (ex.: "0", "101", "1100"), mas
arquivos só guardam bytes inteiros. Este módulo faz a ponte:

* ``EscritorDeBits`` recebe bits e os agrupa de 8 em 8 (o bit mais
  significativo primeiro). No final, completa o último byte com zeros
  ("padding") e informa quantos bits de padding foram adicionados.
* ``LeitorDeBits`` faz o caminho inverso: percorre os bytes e devolve os bits
  um a um, ignorando o padding do final.

Convenção adotada (MSB first): o primeiro bit escrito vai para o bit 7 do
primeiro byte. Ex.: escrever "101" e finalizar gera o byte 0b1010_0000 (0xA0)
com 5 bits de padding.
"""

from __future__ import annotations

from collections.abc import Iterator


class EscritorDeBits:
    """Acumula bits e os empacota em bytes (bit mais significativo primeiro).

    Exemplo de uso esperado::

        escritor = EscritorDeBits()
        escritor.escrever_bits("101")
        escritor.escrever_bit(1)
        dados, padding = escritor.finalizar()   # (b'\\xb0', 4)
    """

    def __init__(self) -> None:
        """Cria um escritor vazio."""
        # TODO: inicializar os atributos internos:
        #   self._saida: bytearray      -> bytes já completos
        #   self._acumulador: int       -> byte em construção (0..255)
        #   self._bits_no_acumulador: int -> quantos bits já estão no acumulador (0..7)
        #   self._total_bits: int       -> total de bits escritos (útil para estatísticas)
        pass

    @property
    def total_bits(self) -> int:
        """Quantidade total de bits escritos até agora (sem contar padding)."""
        # TODO: retornar self._total_bits
        pass

    def escrever_bit(self, bit: int) -> None:
        """Escreve um único bit (0 ou 1).

        Args:
            bit: valor do bit; deve ser 0 ou 1.

        Raises:
            ValueError: se ``bit`` não for 0 nem 1.
        """
        # TODO:
        #   1. validar o bit
        #   2. acumulador = (acumulador << 1) | bit ; incrementar contadores
        #   3. se o acumulador completou 8 bits -> append em self._saida e zerar
        pass

    def escrever_bits(self, codigo: str) -> None:
        """Escreve uma sequência de bits representada como texto.

        Args:
            codigo: string formada apenas por '0' e '1' (ex.: um código de Huffman).
        """
        # TODO: chamar escrever_bit para cada caractere de ``codigo``.
        # DICA DE DESEMPENHO: para arquivos grandes, escrever bit a bit em Python
        # é lento. Uma alternativa é, em huffman.codificar, juntar todos os
        # códigos em uma única string ("".join(...)) e converter em blocos com
        # int(bloco, 2).to_bytes(...). Se fizer isso, este método pode ficar
        # apenas como versão didática.
        pass

    def finalizar(self) -> tuple[bytes, int]:
        """Completa o último byte com zeros e devolve o resultado.

        Returns:
            Uma tupla ``(dados, bits_padding)`` em que ``dados`` são os bytes
            empacotados e ``bits_padding`` (0..7) é a quantidade de zeros
            adicionados ao final do último byte.
        """
        # TODO:
        #   1. se houver bits no acumulador, deslocar para a esquerda
        #      (8 - bits_no_acumulador) posições e fazer append
        #   2. padding = (8 - bits_no_acumulador) % 8
        #   3. retornar (bytes(self._saida), padding)
        pass


class LeitorDeBits:
    """Percorre um bloco de bytes devolvendo seus bits (MSB primeiro).

    Exemplo de uso esperado::

        leitor = LeitorDeBits(b'\\xa0', bits_padding=5)
        list(leitor)   # [1, 0, 1]
    """

    def __init__(self, dados: bytes, bits_padding: int = 0) -> None:
        """Prepara a leitura.

        Args:
            dados: bytes que contêm os bits.
            bits_padding: quantos bits do final do último byte devem ser ignorados.
        """
        # TODO: guardar ``dados`` e calcular self._total_bits = len(dados) * 8 - bits_padding
        pass

    @property
    def total_bits(self) -> int:
        """Quantidade de bits válidos (sem o padding)."""
        # TODO: retornar self._total_bits
        pass

    def __iter__(self) -> Iterator[int]:
        """Gera os bits válidos, um por vez, na ordem em que foram escritos.

        Yields:
            0 ou 1.
        """
        # TODO: para cada byte e para cada deslocamento de 7 até 0:
        #   yield (byte >> deslocamento) & 1
        # parando depois de self._total_bits bits.
        pass
