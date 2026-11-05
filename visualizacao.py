"""Funções de apresentação usadas pela interface (parte da GUI, já implementada).

Nada aqui comprime ou descomprime: são só formas de MOSTRAR os dados
(árvore em Graphviz/DOT, hexdump, bits e tabela de códigos).
"""

from __future__ import annotations

from typing import Any

from huffman import Codigos, Frequencias, NoHuffman

_NOMES_ESPECIAIS: dict[int, str] = {
    0x20: "␣ (espaço)",
    0x0A: "↵ (\\n)",
    0x0D: "⏎ (\\r)",
    0x09: "⇥ (\\t)",
}


def rotulo_simbolo(simbolo: int, curto: bool = False) -> str:
    """Texto legível para um byte.

    Args:
        simbolo: valor do byte (0..255).
        curto: se ``True``, omite a descrição entre parênteses dos especiais.

    Returns:
        O caractere (ASCII imprimível), um nome para espaço/quebras de linha,
        ou ``0xNN`` para os demais bytes (inclusive partes de caracteres UTF-8
        acentuados, que ocupam 2 bytes).
    """
    if simbolo in _NOMES_ESPECIAIS:
        nome = _NOMES_ESPECIAIS[simbolo]
        return nome.split(" ")[0] if curto else nome
    if 0x21 <= simbolo <= 0x7E:
        return chr(simbolo)
    return f"0x{simbolo:02X}"


def _escapar_dot(texto: str) -> str:
    """Escapa aspas e barras para uso dentro de um rótulo DOT."""
    return texto.replace("\\", "\\\\").replace('"', '\\"')


def arvore_para_dot(
    raiz: NoHuffman | None,
    codigos: Codigos | None = None,
    max_folhas: int | None = None,
) -> str:
    """Gera o código Graphviz (DOT) da árvore de Huffman.

    Nós internos viram círculos com a frequência; folhas viram caixas com o
    símbolo, a frequência e o código. Arestas são rotuladas com 0 e 1.

    Args:
        raiz: raiz da árvore (``None`` gera um grafo com aviso).
        codigos: tabela de códigos, para mostrar o código dentro da folha.
        max_folhas: se definido, mostra apenas as ``max_folhas`` folhas mais
            frequentes; subárvores sem nenhuma delas são resumidas em um nó
            "⋯ k símbolos". ``None`` ou 0 mostra a árvore inteira.

    Returns:
        String DOT, pronta para ``st.graphviz_chart``.
    """
    linhas: list[str] = [
        "digraph Huffman {",
        '  graph [rankdir=TB, nodesep=0.25, ranksep=0.45, bgcolor="transparent"];',
        '  node [fontname="Helvetica", fontsize=11];',
        '  edge [fontname="Helvetica", fontsize=10, color="#64748b", fontcolor="#334155"];',
    ]
    if raiz is None:
        linhas.append('  vazio [shape=plaintext, label="(árvore vazia)"];')
        linhas.append("}")
        return "\n".join(linhas)

    codigos = codigos or {}

    # 1) Contar folhas por subárvore e listar todas as folhas.
    folhas: list[NoHuffman] = []
    qtd_folhas: dict[int, int] = {}

    def contar(no: NoHuffman) -> int:
        if no.esquerda is None and no.direita is None:
            folhas.append(no)
            qtd_folhas[id(no)] = 1
            return 1
        total = sum(contar(f) for f in (no.esquerda, no.direita) if f is not None)
        qtd_folhas[id(no)] = total
        return total

    contar(raiz)

    # 2) Escolher quais folhas exibir.
    if max_folhas and len(folhas) > max_folhas:
        mais_frequentes = sorted(folhas, key=lambda n: (-n.frequencia, n.simbolo or 0))
        visiveis = {id(n) for n in mais_frequentes[:max_folhas]}
    else:
        visiveis = {id(n) for n in folhas}

    contem_visivel: dict[int, bool] = {}

    def marcar(no: NoHuffman) -> bool:
        if no.esquerda is None and no.direita is None:
            resultado = id(no) in visiveis
        else:
            resultado = False
            for filho in (no.esquerda, no.direita):
                if filho is not None and marcar(filho):
                    resultado = True
        contem_visivel[id(no)] = resultado
        return resultado

    marcar(raiz)

    # 3) Emitir nós e arestas (pilha explícita para não estourar a recursão).
    contador = 0
    pilha: list[tuple[NoHuffman, str | None, str]] = [(raiz, None, "")]
    while pilha:
        no, pai, bit = pilha.pop()
        nome = f"n{contador}"
        contador += 1

        eh_folha = no.esquerda is None and no.direita is None
        if eh_folha:
            simbolo = no.simbolo if no.simbolo is not None else 0
            codigo = codigos.get(simbolo, "")
            # Escapa só o símbolo; os "\n" abaixo são quebras de linha do DOT.
            rotulo = f"{_escapar_dot(rotulo_simbolo(simbolo, curto=True))}\\nf={no.frequencia}"
            if codigo:
                rotulo += f"\\n{codigo}"
            linhas.append(
                f'  {nome} [shape=box, style="rounded,filled", fillcolor="#dbeafe", '
                f'color="#2563eb", label="{rotulo}"];'
            )
        elif not contem_visivel[id(no)]:
            rotulo = f"⋯ {qtd_folhas[id(no)]} símbolos\\nf={no.frequencia}"
            linhas.append(
                f'  {nome} [shape=box, style="dashed,filled", fillcolor="#f1f5f9", '
                f'color="#94a3b8", fontcolor="#475569", label="{rotulo}"];'
            )
        else:
            linhas.append(
                f'  {nome} [shape=circle, style=filled, fillcolor="#fef3c7", '
                f'color="#d97706", width=0.5, fixedsize=false, label="{no.frequencia}"];'
            )
            # Empilha direita antes para a esquerda ser desenhada primeiro.
            if no.direita is not None:
                pilha.append((no.direita, nome, "1"))
            if no.esquerda is not None:
                pilha.append((no.esquerda, nome, "0"))

        if pai is not None:
            linhas.append(f'  {pai} -> {nome} [label=" {bit}"];')

    linhas.append("}")
    return "\n".join(linhas)


def tabela_de_codigos(frequencias: Frequencias, codigos: Codigos) -> list[dict[str, Any]]:
    """Monta as linhas da tabela "símbolo / frequência / código".

    Args:
        frequencias: ``{símbolo: frequência}``.
        codigos: ``{símbolo: código}``.

    Returns:
        Lista de dicionários ordenada da maior para a menor frequência.
    """
    total = sum(frequencias.values()) or 1
    linhas: list[dict[str, Any]] = []
    for simbolo, freq in sorted(frequencias.items(), key=lambda kv: (-kv[1], kv[0])):
        codigo = codigos.get(simbolo, "")
        linhas.append(
            {
                "Símbolo": rotulo_simbolo(simbolo),
                "Byte": simbolo,
                "Frequência": freq,
                "Probabilidade (%)": round(100 * freq / total, 3),
                "Código": codigo,
                "Bits": len(codigo),
                "Bits gastos": freq * len(codigo),
            }
        )
    return linhas


def hexdump(
    dados: bytes,
    limite_bytes: int = 512,
    largura: int = 16,
    inicio_payload: int | None = None,
) -> str:
    """Formata bytes no estilo ``hexdump -C`` (offset, hex, ASCII).

    Args:
        dados: bytes a exibir.
        limite_bytes: quantos bytes mostrar no máximo.
        largura: bytes por linha.
        inicio_payload: se informado, insere uma linha separando cabeçalho
            e payload nesse offset.

    Returns:
        Texto multilinha.
    """
    trecho = dados[:limite_bytes]

    def linhas_de(bloco_total: bytes, base: int) -> list[str]:
        saida: list[str] = []
        for i in range(0, len(bloco_total), largura):
            bloco = bloco_total[i : i + largura]
            hex_parte = " ".join(f"{b:02X}" for b in bloco)
            meio = largura // 2 * 3
            hex_parte = hex_parte[:meio] + " " + hex_parte[meio:]
            ascii_parte = "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in bloco)
            saida.append(f"{base + i:08X}  {hex_parte:<{largura * 3 + 1}} |{ascii_parte}|")
        return saida

    if inicio_payload is not None and 0 < inicio_payload < len(trecho):
        linhas = ["── cabeçalho " + "─" * 50]
        linhas += linhas_de(trecho[:inicio_payload], 0)
        linhas.append("── payload (bits do Huffman) " + "─" * 34)
        linhas += linhas_de(trecho[inicio_payload:], inicio_payload)
    else:
        linhas = linhas_de(trecho, 0)
    if len(dados) > limite_bytes:
        linhas.append(f"... ({len(dados) - limite_bytes} bytes omitidos)")
    return "\n".join(linhas)


def bytes_em_bits(dados: bytes, limite_bytes: int = 64, por_linha: int = 8) -> str:
    """Mostra bytes como grupos de 8 bits (ex.: ``10110010 01100001``).

    Args:
        dados: bytes a exibir.
        limite_bytes: quantos bytes mostrar no máximo.
        por_linha: quantos bytes por linha.

    Returns:
        Texto multilinha.
    """
    trecho = dados[:limite_bytes]
    linhas = [
        " ".join(f"{b:08b}" for b in trecho[i : i + por_linha])
        for i in range(0, len(trecho), por_linha)
    ]
    if len(dados) > limite_bytes:
        linhas.append(f"... ({len(dados) - limite_bytes} bytes omitidos)")
    return "\n".join(linhas)


def codificar_trecho_para_exibicao(texto: bytes, codigos: Codigos, limite: int = 40) -> list[dict[str, str]]:
    """Mostra como os primeiros bytes de um texto viram códigos (para a explicação).

    Args:
        texto: bytes de entrada do Huffman.
        codigos: tabela de códigos.
        limite: quantos bytes mostrar.

    Returns:
        Lista de ``{"Símbolo": ..., "Código": ...}``.
    """
    return [
        {"Símbolo": rotulo_simbolo(b, curto=True), "Código": codigos.get(b, "?")}
        for b in texto[:limite]
    ]
