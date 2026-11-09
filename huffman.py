"""Núcleo do algoritmo de Huffman (sobre bytes, alfabeto de 0 a 255).

Fluxo da compressão::

    dados ──contar_frequencias──▶ {símbolo: freq}
          ──construir_arvore────▶ árvore (só para descobrir o TAMANHO de cada código)
          ──gerar_codigos───────▶ {símbolo: "0101"}
          ──comprimentos_dos_codigos──▶ {símbolo: 4}
          ──gerar_codigos_canonicos───▶ {símbolo: "0110"}   ← códigos realmente usados
          ──codificar───────────▶ bytes empacotados + padding

Fluxo da descompressão::

    comprimentos (lidos do cabeçalho)
          ──gerar_codigos_canonicos──▶ códigos
          ──reconstruir_arvore───────▶ árvore de decodificação
          ──decodificar──────────────▶ dados originais

Por que códigos canônicos? Com eles o cabeçalho só precisa guardar o
COMPRIMENTO do código de cada símbolo (1 byte), e não a tabela de frequências
(até 8 bytes por símbolo) nem a árvore inteira. O descompactador regenera
exatamente os mesmos códigos a partir dos comprimentos. Isso reduz o
cabeçalho e melhora a taxa, principalmente em arquivos pequenos.

Regra do trabalho: este módulo deve ser implementado à mão. ``heapq`` e
``collections`` podem ser usados como estruturas auxiliares.
"""

from __future__ import annotations

import heapq
from collections import Counter
from dataclasses import dataclass

# Tipos auxiliares (apenas para deixar as assinaturas mais legíveis).
Frequencias = dict[int, int]   # símbolo (0..255) -> número de ocorrências
Codigos = dict[int, str]       # símbolo -> código em texto, ex.: "1011"
Comprimentos = dict[int, int]  # símbolo -> tamanho do código em bits


@dataclass(eq=False)
class NoHuffman:
    """Nó da árvore de Huffman.

    Uma folha tem ``simbolo`` definido e nenhum filho. Um nó interno tem
    ``simbolo = None`` e dois filhos (ou apenas o esquerdo, no caso especial
    de um arquivo com um único símbolo distinto).

    Por convenção, ir para a ``esquerda`` acrescenta o bit '0' ao código e ir
    para a ``direita`` acrescenta '1'.

    Attributes:
        frequencia: soma das frequências das folhas abaixo deste nó.
        simbolo: byte representado (0..255) se for folha; ``None`` se for interno.
        esquerda: filho do bit 0.
        direita: filho do bit 1.
        ordem: número usado para desempate determinístico na fila de
            prioridade (ex.: ordem de criação). Garante que a mesma entrada
            gere sempre a mesma árvore.
    """

    frequencia: int
    simbolo: int | None = None
    esquerda: NoHuffman | None = None
    direita: NoHuffman | None = None
    ordem: int = 0

    def eh_folha(self) -> bool:
        """Retorna ``True`` se o nó for uma folha (não tem filhos)."""
        return self.esquerda is None and self.direita is None

    def __lt__(self, outro: NoHuffman) -> bool:
        """Comparação usada pelo ``heapq`` para ordenar os nós.

        Critério: menor frequência primeiro; em caso de empate, menor ``ordem``.
        """
        return (self.frequencia, self.ordem) < (outro.frequencia, outro.ordem)


def contar_frequencias(dados: bytes) -> Frequencias:
    """Conta quantas vezes cada byte aparece em ``dados``.

    Args:
        dados: conteúdo a ser analisado.

    Returns:
        Dicionário ``{byte: quantidade}`` contendo apenas os bytes que aparecem.
        Para ``dados`` vazio, retorna ``{}``.
    """
    # Counter sobre bytes itera inteiros (0..255) e é implementado em C: rápido.
    return dict(Counter(dados))


def construir_arvore(frequencias: Frequencias) -> NoHuffman | None:
    """Monta a árvore de Huffman a partir das frequências.

    Algoritmo:
        1. Criar uma folha para cada símbolo e inserir todas em um min-heap.
        2. Enquanto houver mais de um nó no heap: remover os dois de menor
           frequência, criar um nó interno com eles como filhos (o primeiro
           removido à esquerda) e frequência igual à soma, e inserir de volta.
        3. O nó que sobrar é a raiz.

    Casos especiais:
        * ``frequencias`` vazio -> retornar ``None``.
        * apenas um símbolo -> retornar um nó interno cuja ``esquerda`` é a
          única folha (assim o símbolo recebe o código "0" em vez de "").

    Args:
        frequencias: dicionário ``{símbolo: frequência}``.

    Returns:
        A raiz da árvore, ou ``None`` se não houver símbolos.
    """
    if not frequencias:
        return None

    # Folhas em ordem crescente de símbolo: o desempate fica determinístico.
    contador = 0
    heap: list[NoHuffman] = []
    for simbolo in sorted(frequencias):
        heap.append(NoHuffman(frequencias[simbolo], simbolo=simbolo, ordem=contador))
        contador += 1
    heapq.heapify(heap)

    # Caso especial: um único símbolo -> raiz interna com só o filho esquerdo.
    if len(heap) == 1:
        folha = heap[0]
        return NoHuffman(folha.frequencia, esquerda=folha, ordem=contador)

    while len(heap) > 1:
        menor = heapq.heappop(heap)    # vai para a esquerda (bit 0)
        segundo = heapq.heappop(heap)  # vai para a direita (bit 1)
        pai = NoHuffman(
            menor.frequencia + segundo.frequencia,
            esquerda=menor,
            direita=segundo,
            ordem=contador,
        )
        contador += 1
        heapq.heappush(heap, pai)

    return heap[0]


def gerar_codigos(raiz: NoHuffman | None) -> Codigos:
    """Percorre a árvore e gera o código de cada símbolo.

    Args:
        raiz: raiz da árvore (pode ser ``None``).

    Returns:
        Dicionário ``{símbolo: código}``, ex.: ``{97: "0", 98: "10", 99: "11"}``.
        Retorna ``{}`` se ``raiz`` for ``None``.
    """
    codigos: Codigos = {}
    if raiz is None:
        return codigos

    # Pilha explícita (evita estourar a recursão em árvores muito profundas).
    pilha: list[tuple[NoHuffman, str]] = [(raiz, "")]
    while pilha:
        no, caminho = pilha.pop()
        if no.eh_folha():
            # Raiz que já é folha (não deve ocorrer): garante código de 1 bit.
            codigos[no.simbolo] = caminho or "0"  # type: ignore[index]
            continue
        if no.direita is not None:
            pilha.append((no.direita, caminho + "1"))
        if no.esquerda is not None:
            pilha.append((no.esquerda, caminho + "0"))
    return codigos


def comprimentos_dos_codigos(codigos: Codigos) -> Comprimentos:
    """Extrai o tamanho (em bits) de cada código.

    Args:
        codigos: dicionário ``{símbolo: código}``.

    Returns:
        Dicionário ``{símbolo: len(código)}``.
    """
    return {simbolo: len(codigo) for simbolo, codigo in codigos.items()}


def gerar_codigos_canonicos(comprimentos: Comprimentos) -> Codigos:
    """Gera os códigos de Huffman canônicos a partir dos comprimentos.

    Algoritmo (o mesmo do formato DEFLATE):
        1. Ordenar os símbolos por (comprimento, símbolo).
        2. código = 0 para o primeiro símbolo.
        3. Para cada símbolo seguinte: código += 1 e, se o comprimento
           aumentou, deslocar o código para a esquerda pela diferença
           (código <<= novo_comprimento - comprimento_anterior).
        4. Converter cada código para texto binário com zeros à esquerda
           até o comprimento (format(codigo, f"0{comprimento}b")).

    Os códigos gerados são livres de prefixo e têm os mesmos comprimentos
    dos originais, logo a taxa de compressão é idêntica.

    Args:
        comprimentos: dicionário ``{símbolo: comprimento}``.

    Returns:
        Dicionário ``{símbolo: código canônico}``.
    """
    codigos: Codigos = {}
    codigo = 0
    comprimento_anterior = 0

    for simbolo, comprimento in sorted(comprimentos.items(), key=lambda par: (par[1], par[0])):
        if comprimento <= 0:
            raise ValueError(f"comprimento inválido para o símbolo {simbolo}: {comprimento}")
        if codigos:  # a partir do segundo símbolo
            codigo += 1
            codigo <<= comprimento - comprimento_anterior  # 0 se o comprimento não mudou
        codigos[simbolo] = format(codigo, f"0{comprimento}b")
        comprimento_anterior = comprimento

    return codigos


def reconstruir_arvore(
    codigos: Codigos,
    frequencias: Frequencias | None = None,
) -> NoHuffman | None:
    """Monta uma árvore (trie binária) a partir de uma tabela de códigos.

    Usada na descompressão (para decodificar bit a bit) e na interface (para
    desenhar a árvore que corresponde exatamente aos códigos gravados no
    arquivo).

    Args:
        codigos: dicionário ``{símbolo: código}``.
        frequencias: opcional. Se informado, as folhas recebem a frequência
            do símbolo e cada nó interno recebe a soma dos filhos (útil para
            exibir a árvore). Se ``None``, as frequências ficam 0.

    Returns:
        A raiz da árvore, ou ``None`` se ``codigos`` estiver vazio.
    """
    if not codigos:
        return None

    raiz = NoHuffman(0)
    for simbolo, codigo in codigos.items():
        no = raiz
        for bit in codigo:
            if bit == "0":
                if no.esquerda is None:
                    no.esquerda = NoHuffman(0)
                no = no.esquerda
            else:
                if no.direita is None:
                    no.direita = NoHuffman(0)
                no = no.direita
        no.simbolo = simbolo  # o último nó do caminho é a folha

    if frequencias is not None:
        # Pós-ordem: os filhos são calculados antes do pai.
        def preencher(no: NoHuffman) -> int:
            if no.eh_folha():
                no.frequencia = frequencias.get(no.simbolo, 0)  # type: ignore[arg-type]
            else:
                no.frequencia = sum(
                    preencher(filho) for filho in (no.esquerda, no.direita) if filho is not None
                )
            return no.frequencia

        preencher(raiz)

    return raiz


def codificar(dados: bytes, codigos: Codigos) -> tuple[bytes, int]:
    """Substitui cada byte de ``dados`` pelo seu código e empacota os bits.

    Args:
        dados: conteúdo original (ou a saída serializada do LZ77).
        codigos: tabela ``{símbolo: código}``; deve conter todos os bytes de ``dados``.

    Returns:
        Tupla ``(bytes_empacotados, bits_padding)``.
    """
    if not dados:
        return b"", 0

    # Junta todos os códigos numa única string de '0'/'1' (rápido, feito em C).
    bits = "".join(map(codigos.__getitem__, dados))

    # Completa com zeros até um múltiplo de 8 (padding).
    padding = (-len(bits)) % 8
    bits += "0" * padding

    # Converte a string inteira de uma vez: MSB primeiro, igual ao bitio.py.
    return int(bits, 2).to_bytes(len(bits) // 8, "big"), padding


def decodificar(
    dados: bytes,
    bits_padding: int,
    raiz: NoHuffman | None,
    quantidade_simbolos: int,
) -> bytes:
    """Decodifica os bits de volta para os bytes originais.

    Algoritmo: começar na raiz; para cada bit, ir para a esquerda (0) ou
    direita (1); ao chegar numa folha, emitir o símbolo e voltar para a raiz.
    Parar quando ``quantidade_simbolos`` símbolos tiverem sido emitidos.

    Args:
        dados: bytes empacotados (payload do arquivo compactado).
        bits_padding: bits de preenchimento no final do último byte.
        raiz: árvore de decodificação (de ``reconstruir_arvore``).
        quantidade_simbolos: quantos bytes devem ser produzidos.

    Returns:
        Os bytes decodificados.

    Raises:
        ValueError: se os bits terminarem antes do esperado ou levarem a um
            caminho inexistente na árvore (arquivo corrompido).
    """
    if quantidade_simbolos == 0:
        return b""
    if raiz is None:
        raise ValueError("árvore vazia, mas há símbolos a decodificar")
    if not dados:
        raise ValueError("sem dados para decodificar")
    if not 0 <= bits_padding <= 7:
        raise ValueError(f"bits de padding inválido: {bits_padding}")

    # Bytes -> string de bits (MSB primeiro) e descarta o padding do final.
    bits = bin(int.from_bytes(dados, "big"))[2:].zfill(len(dados) * 8)
    if bits_padding:
        bits = bits[:-bits_padding]

    saida = bytearray()
    no = raiz
    for bit in bits:
        proximo = no.esquerda if bit == "0" else no.direita
        if proximo is None:
            raise ValueError("sequência de bits inválida (arquivo corrompido)")
        no = proximo
        if no.eh_folha():
            saida.append(no.simbolo)  # type: ignore[arg-type]
            if len(saida) == quantidade_simbolos:
                return bytes(saida)
            no = raiz

    raise ValueError("os bits terminaram antes de decodificar todos os símbolos")
