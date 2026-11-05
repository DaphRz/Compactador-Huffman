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
        # TODO: retornar True quando esquerda e direita forem None.
        pass

    def __lt__(self, outro: NoHuffman) -> bool:
        """Comparação usada pelo ``heapq`` para ordenar os nós.

        Critério: menor frequência primeiro; em caso de empate, menor ``ordem``.
        """
        # TODO: comparar a tupla (self.frequencia, self.ordem) com a do outro nó.
        pass


def contar_frequencias(dados: bytes) -> Frequencias:
    """Conta quantas vezes cada byte aparece em ``dados``.

    Args:
        dados: conteúdo a ser analisado.

    Returns:
        Dicionário ``{byte: quantidade}`` contendo apenas os bytes que aparecem.
        Para ``dados`` vazio, retorna ``{}``.
    """
    # TODO: percorrer os bytes e contar (pode usar collections.Counter).
    pass


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
    # TODO: implementar com heapq (heappush / heappop) e um contador para ``ordem``.
    # Dica: insira as folhas em ordem crescente de símbolo para o resultado
    # ser determinístico.
    pass


def gerar_codigos(raiz: NoHuffman | None) -> Codigos:
    """Percorre a árvore e gera o código de cada símbolo.

    Args:
        raiz: raiz da árvore (pode ser ``None``).

    Returns:
        Dicionário ``{símbolo: código}``, ex.: ``{97: "0", 98: "10", 99: "11"}``.
        Retorna ``{}`` se ``raiz`` for ``None``.
    """
    # TODO: busca em profundidade (recursiva ou com pilha), acumulando o
    # caminho: esquerda -> '0', direita -> '1'. Ao chegar numa folha, salvar.
    pass


def comprimentos_dos_codigos(codigos: Codigos) -> Comprimentos:
    """Extrai o tamanho (em bits) de cada código.

    Args:
        codigos: dicionário ``{símbolo: código}``.

    Returns:
        Dicionário ``{símbolo: len(código)}``.
    """
    # TODO: uma linha com dict comprehension.
    pass


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
    # TODO: implementar o algoritmo acima.
    pass


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
    # TODO:
    #   1. criar a raiz
    #   2. para cada (símbolo, código): descer a partir da raiz criando nós
    #      ('0' -> esquerda, '1' -> direita); no último bit criar a folha
    #   3. se ``frequencias`` foi dado, preencher as frequências dos nós
    #      internos com um percurso pós-ordem (filhos antes do pai)
    pass


def codificar(dados: bytes, codigos: Codigos) -> tuple[bytes, int]:
    """Substitui cada byte de ``dados`` pelo seu código e empacota os bits.

    Args:
        dados: conteúdo original (ou a saída serializada do LZ77).
        codigos: tabela ``{símbolo: código}``; deve conter todos os bytes de ``dados``.

    Returns:
        Tupla ``(bytes_empacotados, bits_padding)``.
    """
    # TODO: usar bitio.EscritorDeBits (ou a otimização com "".join + int(...,2),
    # descrita em bitio.EscritorDeBits.escrever_bits).
    pass


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
    # TODO: usar bitio.LeitorDeBits e um bytearray de saída.
    # Caso especial: raiz None e quantidade_simbolos == 0 -> retornar b"".
    pass
