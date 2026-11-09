"""Pipeline completo: junta LZ77, Huffman e o formato de arquivo.

Compressão::

    texto (bytes)
      └─[opcional] lz77.comprimir + lz77.serializar
            └─ huffman: frequências -> árvore -> comprimentos -> códigos canônicos
                  └─ huffman.codificar
                        └─ formato.serializar_cabecalho + payload  =  arquivo .huf

Descompressão: o caminho inverso, a partir do cabeçalho.

A interface (``app.py``) só conversa com este módulo para compactar e
descompactar, nunca diretamente com os outros.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import formato
import huffman
import lz77
from formato import Cabecalho, FormatoInvalidoError
from huffman import Codigos, Frequencias, NoHuffman


@dataclass
class ResultadoCompressao:
    """Tudo o que a interface precisa saber sobre uma compressão.

    Attributes:
        arquivo: bytes completos do .huf (cabeçalho + payload).
        cabecalho: cabeçalho gravado no arquivo.
        usa_lz77: se o LZ77 foi aplicado.
        tamanho_original: bytes da entrada.
        tamanho_entrada_huffman: bytes que entraram no Huffman (igual ao
            original sem LZ77; tamanho da saída serializada do LZ77 com ele).
        tamanho_cabecalho: bytes do cabeçalho.
        tamanho_payload: bytes dos dados codificados.
        tamanho_compactado: ``len(arquivo)`` = cabeçalho + payload.
        frequencias: frequência de cada byte que entrou no Huffman.
        codigos: códigos canônicos usados ``{símbolo: "0101"}``.
        arvore: árvore correspondente aos códigos canônicos, com as
            frequências preenchidas (use ``huffman.reconstruir_arvore(codigos,
            frequencias)``), para ser desenhada na interface.
        quantidade_tokens_lz77: número de tokens do LZ77 (``None`` sem LZ77).
        quantidade_referencias_lz77: quantos desses tokens são referências
            (``None`` sem LZ77).
        tempo_segundos: duração da compressão.
    """

    arquivo: bytes
    cabecalho: Cabecalho
    usa_lz77: bool
    tamanho_original: int
    tamanho_entrada_huffman: int
    tamanho_cabecalho: int
    tamanho_payload: int
    tamanho_compactado: int
    frequencias: Frequencias
    codigos: Codigos
    arvore: NoHuffman | None
    quantidade_tokens_lz77: int | None
    quantidade_referencias_lz77: int | None
    tempo_segundos: float


@dataclass
class ResultadoDescompressao:
    """Resultado de uma descompressão.

    Attributes:
        dados: bytes restaurados (devem ser idênticos ao original).
        cabecalho: cabeçalho lido do arquivo.
        tempo_segundos: duração da descompressão.
    """

    dados: bytes
    cabecalho: Cabecalho
    tempo_segundos: float


def compactar(dados: bytes, usar_lz77: bool = True) -> ResultadoCompressao:
    """Compacta ``dados`` e devolve o arquivo .huf junto com as estatísticas.

    Args:
        dados: conteúdo original (ex.: bytes de um .txt).
        usar_lz77: se ``True``, aplica LZ77 antes do Huffman.

    Returns:
        Um ``ResultadoCompressao`` completo.
    """
    inicio = time.perf_counter()
    dados = bytes(dados)

    # 1. LZ77 (opcional)
    quantidade_tokens: int | None = None
    quantidade_referencias: int | None = None
    if usar_lz77:
        tokens = lz77.comprimir(dados)
        quantidade_tokens = len(tokens)
        quantidade_referencias = sum(1 for t in tokens if isinstance(t, lz77.TokenReferencia))
        entrada = lz77.serializar(tokens)
    else:
        entrada = dados

    # 2-4. Frequências -> árvore -> comprimentos -> códigos canônicos
    frequencias = huffman.contar_frequencias(entrada)
    arvore_inicial = huffman.construir_arvore(frequencias)
    comprimentos = huffman.comprimentos_dos_codigos(huffman.gerar_codigos(arvore_inicial))
    codigos = huffman.gerar_codigos_canonicos(comprimentos)

    # 5. Codificação
    payload, padding = huffman.codificar(entrada, codigos)

    # 6. Cabeçalho + payload
    cabecalho = Cabecalho(
        usa_lz77=usar_lz77,
        tamanho_original=len(dados),
        quantidade_simbolos=len(entrada),
        bits_padding=padding,
        comprimentos=comprimentos,
    )
    bytes_cabecalho = formato.serializar_cabecalho(cabecalho)
    arquivo = bytes_cabecalho + payload

    # Árvore que corresponde exatamente aos códigos gravados (para exibição).
    arvore = huffman.reconstruir_arvore(codigos, frequencias)

    return ResultadoCompressao(
        arquivo=arquivo,
        cabecalho=cabecalho,
        usa_lz77=usar_lz77,
        tamanho_original=len(dados),
        tamanho_entrada_huffman=len(entrada),
        tamanho_cabecalho=len(bytes_cabecalho),
        tamanho_payload=len(payload),
        tamanho_compactado=len(arquivo),
        frequencias=frequencias,
        codigos=codigos,
        arvore=arvore,
        quantidade_tokens_lz77=quantidade_tokens,
        quantidade_referencias_lz77=quantidade_referencias,
        tempo_segundos=time.perf_counter() - inicio,
    )


def descompactar(arquivo: bytes) -> ResultadoDescompressao:
    """Restaura os dados originais a partir de um arquivo .huf.

    Args:
        arquivo: conteúdo completo do .huf.

    Returns:
        Um ``ResultadoDescompressao``.

    Raises:
        formato.FormatoInvalidoError: se o arquivo for inválido ou corrompido.
    """
    inicio_tempo = time.perf_counter()
    arquivo = bytes(arquivo)

    # 1. Cabeçalho (já lança FormatoInvalidoError se estiver inválido)
    cabecalho, inicio = formato.ler_cabecalho(arquivo)
    payload = arquivo[inicio:]

    if not payload and cabecalho.bits_padding:
        raise FormatoInvalidoError("padding informado, mas o payload está vazio")

    try:
        # 2-3. Códigos canônicos -> árvore de decodificação
        codigos = huffman.gerar_codigos_canonicos(cabecalho.comprimentos)
        raiz = huffman.reconstruir_arvore(codigos)

        # 4. Decodificar os bits
        intermediario = huffman.decodificar(
            payload, cabecalho.bits_padding, raiz, cabecalho.quantidade_simbolos
        )
        if len(intermediario) != cabecalho.quantidade_simbolos:
            raise FormatoInvalidoError(
                f"esperados {cabecalho.quantidade_simbolos} símbolos, "
                f"decodificados {len(intermediario)}"
            )

        # 5. Desfazer o LZ77
        if cabecalho.usa_lz77:
            dados = lz77.descomprimir(lz77.desserializar(intermediario))
        else:
            dados = intermediario
    except FormatoInvalidoError:
        raise
    except (ValueError, IndexError, KeyError) as erro:
        raise FormatoInvalidoError(f"arquivo corrompido: {erro}") from erro

    # 6. Conferir o tamanho final
    if len(dados) != cabecalho.tamanho_original:
        raise FormatoInvalidoError(
            f"tamanho restaurado ({len(dados)} bytes) difere do original "
            f"registrado no cabeçalho ({cabecalho.tamanho_original} bytes)"
        )

    return ResultadoDescompressao(
        dados=bytes(dados),
        cabecalho=cabecalho,
        tempo_segundos=time.perf_counter() - inicio_tempo,
    )


def compactar_arquivo(
    caminho_entrada: str | Path,
    caminho_saida: str | Path,
    usar_lz77: bool = True,
) -> ResultadoCompressao:
    """Lê um arquivo do disco, compacta e grava o .huf.

    Args:
        caminho_entrada: arquivo .txt de origem.
        caminho_saida: onde gravar o .huf.
        usar_lz77: repassado para ``compactar``.

    Returns:
        O ``ResultadoCompressao``.
    """
    dados = Path(caminho_entrada).read_bytes()
    resultado = compactar(dados, usar_lz77=usar_lz77)
    Path(caminho_saida).write_bytes(resultado.arquivo)
    return resultado


def descompactar_arquivo(
    caminho_entrada: str | Path,
    caminho_saida: str | Path,
) -> ResultadoDescompressao:
    """Lê um .huf do disco, descompacta e grava o arquivo restaurado.

    Args:
        caminho_entrada: arquivo .huf.
        caminho_saida: onde gravar o texto restaurado.

    Returns:
        O ``ResultadoDescompressao``.
    """
    arquivo = Path(caminho_entrada).read_bytes()
    resultado = descompactar(arquivo)
    Path(caminho_saida).write_bytes(resultado.dados)
    return resultado
