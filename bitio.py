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
        self._saida = bytearray()
        self._acumulador = 0
        self._bits_no_acumulador = 0
        self._total_bits = 0

    @property
    def total_bits(self) -> int:
        """Quantidade total de bits escritos até agora (sem contar padding)."""
        return self._total_bits

    def escrever_bit(self, bit: int) -> None:
        """Escreve um único bit (0 ou 1).

        Args:
            bit: valor do bit; deve ser 0 ou 1.

        Raises:
            ValueError: se ``bit`` não for 0 nem 1.
        """
        if bit not in (0, 1):
            raise ValueError(f"bit inválido: {bit!r} (esperado 0 ou 1)")
        self._acumulador = (self._acumulador << 1) | bit
        self._bits_no_acumulador += 1
        self._total_bits += 1
        if self._bits_no_acumulador == 8:
            self._saida.append(self._acumulador)
            self._acumulador = 0
            self._bits_no_acumulador = 0

    def escrever_bits(self, codigo: str) -> None:
        """Escreve uma sequência de bits representada como texto.

        Args:
            codigo: string formada apenas por '0' e '1' (ex.: um código de Huffman).
        """
        # DICA DE DESEMPENHO: para arquivos grandes, escrever bit a bit em Python
        # é lento. Uma alternativa é, em huffman.codificar, juntar todos os
        # códigos em uma única string ("".join(...)) e converter em blocos com
        # int(bloco, 2).to_bytes(...). Se fizer isso, este método pode ficar
        # apenas como versão didática.
        for caractere in codigo:
            if caractere == "0":
                self.escrever_bit(0)
            elif caractere == "1":
                self.escrever_bit(1)
            else:
                raise ValueError(f"caractere inválido no código: {caractere!r}")

    def finalizar(self) -> tuple[bytes, int]:
        """Completa o último byte com zeros e devolve o resultado.

        Returns:
            Uma tupla ``(dados, bits_padding)`` em que ``dados`` são os bytes
            empacotados e ``bits_padding`` (0..7) é a quantidade de zeros
            adicionados ao final do último byte.
        """
        padding = (8 - self._bits_no_acumulador) % 8
        if self._bits_no_acumulador:
            self._saida.append((self._acumulador << padding) & 0xFF)
            self._acumulador = 0
            self._bits_no_acumulador = 0
        return bytes(self._saida), padding


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
        if not 0 <= bits_padding <= 7:
            raise ValueError(f"bits_padding inválido: {bits_padding} (esperado 0..7)")
        if not dados and bits_padding:
            raise ValueError("bits_padding sem nenhum byte de dados")
        self._dados = dados
        self._total_bits = len(dados) * 8 - bits_padding

    @property
    def total_bits(self) -> int:
        """Quantidade de bits válidos (sem o padding)."""
        return self._total_bits

    def __iter__(self) -> Iterator[int]:
        """Gera os bits válidos, um por vez, na ordem em que foram escritos.

        Yields:
            0 ou 1.
        """
        restantes = self._total_bits
        for byte in self._dados:
            for deslocamento in range(7, -1, -1):
                if restantes == 0:
                    return
                yield (byte >> deslocamento) & 1
                restantes -= 1
