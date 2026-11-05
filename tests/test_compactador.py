"""Testes de ida e volta e de casos de borda (biblioteca padrão ``unittest``).

Execute na raiz do projeto::

    python -m unittest discover -s tests -v

Os testes já estão completos: eles descrevem o comportamento esperado e vão
passar conforme as funções forem implementadas.
"""

from __future__ import annotations

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import compactador  # noqa: E402
import formato      # noqa: E402
import huffman      # noqa: E402
import lz77         # noqa: E402
from bitio import EscritorDeBits, LeitorDeBits  # noqa: E402

TEXTO_PT = (
    "O rato roeu a roupa do rei de Roma. A rainha, com raiva, resolveu remendar. "
    "Ação, coração, informação: acentos também precisam funcionar! \n"
) * 50

CASOS: dict[str, bytes] = {
    "vazio": b"",
    "um_byte": b"a",
    "um_simbolo_repetido": b"z" * 1000,
    "dois_simbolos": b"abababababbbbbaaaa",
    "texto_portugues_utf8": TEXTO_PT.encode("utf-8"),
    "todos_os_bytes": bytes(range(256)) * 4,
    "aleatorio": bytes(random.Random(42).randrange(256) for _ in range(5000)),
}


class TestBitIO(unittest.TestCase):

    def test_escrever_e_ler(self) -> None:
        escritor = EscritorDeBits()
        escritor.escrever_bits("101")
        dados, padding = escritor.finalizar()
        self.assertEqual(dados, b"\xa0")
        self.assertEqual(padding, 5)
        self.assertEqual(list(LeitorDeBits(dados, padding)), [1, 0, 1])

    def test_byte_completo_sem_padding(self) -> None:
        escritor = EscritorDeBits()
        escritor.escrever_bits("11110000")
        self.assertEqual(escritor.finalizar(), (b"\xf0", 0))


class TestHuffman(unittest.TestCase):

    def test_frequencias(self) -> None:
        self.assertEqual(huffman.contar_frequencias(b"aab"), {97: 2, 98: 1})

    def test_codigos_livres_de_prefixo(self) -> None:
        freq = huffman.contar_frequencias(TEXTO_PT.encode())
        codigos = huffman.gerar_codigos(huffman.construir_arvore(freq))
        lista = list(codigos.values())
        for i, a in enumerate(lista):
            for j, b in enumerate(lista):
                if i != j:
                    self.assertFalse(b.startswith(a), f"{a} é prefixo de {b}")

    def test_mais_frequente_tem_codigo_mais_curto(self) -> None:
        freq = {ord("a"): 50, ord("b"): 10, ord("c"): 5, ord("d"): 1}
        codigos = huffman.gerar_codigos(huffman.construir_arvore(freq))
        self.assertLessEqual(len(codigos[ord("a")]), len(codigos[ord("d")]))

    def test_canonicos_preservam_comprimentos(self) -> None:
        freq = huffman.contar_frequencias(TEXTO_PT.encode())
        comp = huffman.comprimentos_dos_codigos(huffman.gerar_codigos(huffman.construir_arvore(freq)))
        canon = huffman.gerar_codigos_canonicos(comp)
        self.assertEqual(huffman.comprimentos_dos_codigos(canon), comp)

    def test_um_simbolo_recebe_codigo_de_um_bit(self) -> None:
        codigos = huffman.gerar_codigos(huffman.construir_arvore({65: 10}))
        self.assertEqual(codigos, {65: "0"})


class TestLZ77(unittest.TestCase):

    def test_ida_e_volta_tokens(self) -> None:
        for nome, dados in CASOS.items():
            with self.subTest(nome):
                tokens = lz77.comprimir(dados)
                self.assertEqual(lz77.descomprimir(tokens), dados)
                self.assertEqual(lz77.desserializar(lz77.serializar(tokens)), tokens)

    def test_encontra_repeticao(self) -> None:
        tokens = lz77.comprimir(b"abcabcabcabc")
        self.assertTrue(any(isinstance(t, lz77.TokenReferencia) for t in tokens))


class TestFormato(unittest.TestCase):

    def test_cabecalho_ida_e_volta(self) -> None:
        cab = formato.Cabecalho(True, 1234, 999, 3, {97: 2, 98: 3, 10: 5})
        dados = formato.serializar_cabecalho(cab)
        lido, inicio = formato.ler_cabecalho(dados + b"payload")
        self.assertEqual(lido, cab)
        self.assertEqual(inicio, len(dados))
        self.assertEqual(cab.tamanho_em_bytes(), len(dados))

    def test_assinatura_invalida(self) -> None:
        with self.assertRaises(formato.FormatoInvalidoError):
            formato.ler_cabecalho(b"XXXX" + bytes(40))

    def test_arquivo_truncado(self) -> None:
        with self.assertRaises(formato.FormatoInvalidoError):
            formato.ler_cabecalho(b"HUF1")


class TestPipeline(unittest.TestCase):
    
    def test_ida_e_volta(self) -> None:
        for usar_lz77 in (False, True):
            for nome, dados in CASOS.items():
                with self.subTest(caso=nome, lz77=usar_lz77):
                    resultado = compactador.compactar(dados, usar_lz77=usar_lz77)
                    self.assertEqual(resultado.tamanho_compactado, len(resultado.arquivo))
                    volta = compactador.descompactar(resultado.arquivo)
                    self.assertEqual(volta.dados, dados)

    def test_texto_comprime(self) -> None:
        dados = TEXTO_PT.encode()
        so_huffman = compactador.compactar(dados, usar_lz77=False)
        com_lz77 = compactador.compactar(dados, usar_lz77=True)
        self.assertLess(so_huffman.tamanho_compactado, len(dados))
        self.assertLess(com_lz77.tamanho_compactado, so_huffman.tamanho_compactado)

    def test_arquivo_corrompido(self) -> None:
        resultado = compactador.compactar(TEXTO_PT.encode(), usar_lz77=False)
        with self.assertRaises(formato.FormatoInvalidoError):
            compactador.descompactar(resultado.arquivo[: len(resultado.arquivo) // 2])


if __name__ == "__main__":
    unittest.main()