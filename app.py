"""
Interface gráfica do Compactador de Huffman (Streamlit).

Como executar::

    pip install -r requirements.txt
    streamlit run app.py

A interface só conversa com `compactador.py` (compactar/descompactar),
`formato.py` (leitura do cabeçalho para exibição), `metricas.py` e
`visualizacao.py`. Enquanto as funções do núcleo não estiverem
implementadas, a interface abre normalmente e avisa qual função ainda
retorna `None`.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, TypeVar

import pandas as pd
import streamlit as st

import compactador
import formato
import metricas
from compactador import ResultadoCompressao, ResultadoDescompressao
from visualizacao import (
    arvore_para_dot,
    bytes_em_bits,
    codificar_trecho_para_exibicao,
    hexdump,
    rotulo_simbolo,
    tabela_de_codigos,
)

T = TypeVar("T")

st.set_page_config(
    page_title="Compactador de Huffman",
    page_icon="🗜️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ──────────────────────────────────────────────────────────────────────────────
# Utilitários da Interface
# ──────────────────────────────────────────────────────────────────────────────

def executar(rotulo: str, funcao: Callable[..., Optional[T]], *args: Any, **kwargs: Any) -> Optional[T]:

    """
    Chama uma função do núcleo mostrando erros de forma amigável.

    Args:
        rotulo: nome exibido nas mensagens (ex.: "compactador.compactar").
        funcao: função a executar.
        *args: argumentos posicionais repassados.
        **kwargs: argumentos nomeados repassados.

    Returns:
        O retorno da função, ou `None` se ela falhou ou ainda não foi implementada.
    """

    try:
        resultado = funcao(*args, **kwargs)

    except formato.FormatoInvalidoError as erro:
        st.error(f"Arquivo inválido ou corrompido: {erro}")
        return None
    
    except Exception as erro:  # noqa: BLE001 - a GUI não pode cair

        st.error(f"Erro em `{rotulo}`: **{type(erro).__name__}**: {erro}")
        with st.expander("Detalhes técnicos"):
            st.exception(erro)
        return None
    
    if resultado is None:
        st.warning(
            f"`{rotulo}` retornou `None`. Essa função (ou alguma que ela chama) "
            "ainda não foi implementada."
        )

    return resultado


def metrica(funcao: Callable[..., Any], *args: Any) -> Optional[float]:

    """ Calcula uma métrica sem quebrar a interface se ela não estiver pronta. """

    try:
        valor = funcao(*args)

    except Exception:  # noqa: BLE001
        return None
    
    return float(valor) if isinstance(valor, (int, float)) else None


def fmt(valor: Optional[float], molde: str = "{:.2f}") -> str:

    """ Formata um número (ou "—" se ausente) usando vírgula decimal. """

    if valor is None:
        return "—"
    
    texto = molde.format(valor)

    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_bytes(n: Optional[int]) -> str:

    """ Formata um tamanho em bytes de forma legível (B, KB, MB). """

    if n is None:
        return "—"
    
    if n < 1024:
        return f"{n} B"
    
    if n < 1024 ** 2:
        return fmt(n / 1024, "{:.2f}") + " KB"
    
    return fmt(n / 1024 ** 2, "{:.2f}") + " MB"


def decodificar_texto(dados: bytes) -> str:

    """ Converte bytes em texto para exibição (UTF-8, ou Latin-1 se falhar). """

    try:
        return dados.decode("utf-8")
    
    except UnicodeDecodeError:
        return dados.decode("latin-1")


def primeiro_byte_diferente(a: bytes, b: bytes) -> Optional[int]:

    """ Posição do primeiro byte diferente entre `a` e `b` (`None` se iguais).
    """

    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
        
    return None if len(a) == len(b) else min(len(a), len(b))


def mostrar_previa(texto: str, chave: str, limite: int = 5000) -> None:

    """ Mostra o começo de um texto numa caixa somente leitura. """

    trecho = texto[:limite]

    if len(texto) > limite:
        trecho += f"\n\n[... mais {len(texto) - limite:,} caracteres ...]".replace(",", ".")

    st.text_area("Prévia", trecho, height=220, disabled=True, key=chave, label_visibility="collapsed")


def iniciar_estado() -> None:

    """ Cria as chaves do `st.session_state` usadas pela aplicação. """

    padrao: dict[str, Any] = {
        "original": None,         # bytes do .txt escolhido
        "nome_original": None,    # nome do .txt
        "chave_original": None,   # (nome, tamanho) para detectar troca de arquivo
        "resultado": None,        # ResultadoCompressao da última compressão
        "huf": None,              # bytes do .huf em foco (compactado ou enviado)
        "nome_huf": None,
        "restaurado": None,       # ResultadoDescompressao
        "verificacao": None,      # (bool, posição) da última conferência
        "comparacao": None,       # lista de linhas da comparação
    }

    for chave, valor in padrao.items():
        st.session_state.setdefault(chave, valor)


iniciar_estado()


# ──────────────────────────────────────────────────────────────────────────────
# Barra Lateral
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🗜️ Huffman")
    st.caption("Compactador de texto com Huffman canônico + LZ77 (LZSS)")

    st.subheader("Opções")
    usar_lz77: bool = st.toggle(
        "Usar LZ77 antes do Huffman",
        value=True,
        help="O LZ77 troca trechos repetidos por referências ao passado; "
        "depois o Huffman comprime o resultado.",
    )

    max_folhas: int = st.slider(
        "Folhas exibidas na árvore",
        min_value=0,
        max_value=256,
        value=25,
        step=5,
        help="0 = árvore inteira. Com um limite, só as folhas mais frequentes "
        "aparecem e o resto é resumido em nós '⋯'.",
    )

    limite_hex: int = st.slider("Bytes no hexdump", 64, 4096, 512, step=64)

    st.divider()

    st.subheader("Estado")

    if st.session_state.nome_original:
        st.write(f"📄 **{st.session_state.nome_original}** · {fmt_bytes(len(st.session_state.original))}")

    else:
        st.write("📄 nenhum .txt carregado")
        
    resultado_lateral: Optional[ResultadoCompressao] = st.session_state.resultado

    if resultado_lateral is not None:
        st.write(
            f"🗜️ compactado: {fmt_bytes(resultado_lateral.tamanho_compactado)} "
            f"({'com' if resultado_lateral.usa_lz77 else 'sem'} LZ77)"
        )

    if st.session_state.restaurado is not None:
        st.write("📂 descompactação feita")

    with st.expander("Como usar"):
        st.markdown(
            "1. **Compactar**: escolha o `.txt` e clique em *Compactar*.\n"
            "2. Baixe o `.huf` gerado.\n"
            "3. **Descompactar**: use o arquivo recém-gerado ou envie um `.huf`.\n"
            "4. Veja o arquivo por dentro, a árvore e a taxa nas outras abas.\n"
            "5. **Comparar** mostra Huffman puro × Huffman + LZ77."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Abas
# ──────────────────────────────────────────────────────────────────────────────

st.title("Compactador de Huffman")

aba_comp, aba_desc, aba_arq, aba_arvore, aba_taxa, aba_cmp = st.tabs(

    [
        "📦 Compactar",
        "📂 Descompactar",
        "🔍 Arquivo compactado",
        "🌳 Árvore de Huffman",
        "📊 Taxa de compactação",
        "⚖️ Huffman × Huffman + LZ77",
    ]
)

# ── 1. Compactar ─────────────────────────────────────────────────────────────

with aba_comp:
    st.subheader("Escolha o arquivo de texto")
    enviado = st.file_uploader("Arquivo .txt", type=["txt"], key="upload_txt")

    if enviado is not None:
        conteudo = enviado.getvalue()
        chave = (enviado.name, len(conteudo))

        if st.session_state.chave_original != chave:
            st.session_state.original = conteudo
            st.session_state.nome_original = enviado.name
            st.session_state.chave_original = chave
            st.session_state.resultado = None
            st.session_state.comparacao = None
            st.session_state.verificacao = None

    original: Optional[bytes] = st.session_state.original

    if original is None:
        st.info("Nenhum arquivo selecionado ainda.")

    else:
        texto_original = decodificar_texto(original)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Arquivo", st.session_state.nome_original)

        c2.metric("Tamanho", fmt_bytes(len(original)))

        c3.metric("Caracteres", f"{len(texto_original):,}".replace(",", "."))

        c4.metric("Bytes distintos", len(set(original)))

        if len(original) == 0:
            st.warning("O arquivo está vazio. O compactador precisa tratar esse caso.")
            
        with st.expander("Prévia do texto", expanded=False):
            mostrar_previa(texto_original, "previa_original")

        if st.button("🗜️ Compactar", type="primary", width="stretch"):

            with st.spinner("Compactando..."):

                resultado = executar(
                    "compactador.compactar", compactador.compactar, original, usar_lz77=usar_lz77
                )

            if resultado is not None:
                st.session_state.resultado = resultado
                st.session_state.huf = resultado.arquivo

                base = st.session_state.nome_original.rsplit(".", 1)[0]

                st.session_state.nome_huf = f"{base}.huf"
                st.session_state.restaurado = None
                st.session_state.verificacao = None

    resultado_atual: Optional[ResultadoCompressao] = st.session_state.resultado

    if resultado_atual is not None:
        st.divider()
        st.success(
            f"Arquivo compactado {'com' if resultado_atual.usa_lz77 else 'sem'} LZ77 "
            f"em {fmt(resultado_atual.tempo_segundos, '{:.3f}')} s."
        )

        reducao = metrica(
            metricas.percentual_de_reducao,
            resultado_atual.tamanho_original,
            resultado_atual.tamanho_compactado,
        )

        taxa = metrica(
            metricas.taxa_de_compressao,
            resultado_atual.tamanho_original,
            resultado_atual.tamanho_compactado,
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Original", fmt_bytes(resultado_atual.tamanho_original))

        c2.metric(
            "Compactado",
            fmt_bytes(resultado_atual.tamanho_compactado),
            delta=None if reducao is None else f"-{fmt(reducao, '{:.1f}')}%",
            delta_color="inverse",
        )

        c3.metric("Taxa (compactado/original)", fmt(taxa, "{:.3f}"))

        c4.metric("Símbolos distintos", len(resultado_atual.codigos))

        if resultado_atual.usa_lz77 != usar_lz77:
            st.info(
                "A opção de LZ77 mudou depois desta compressão. "
                "Clique em **Compactar** de novo para aplicar."
            )

        st.download_button(
            "⬇️ Baixar arquivo compactado (.huf)",
            data=resultado_atual.arquivo,
            file_name=st.session_state.nome_huf or "arquivo.huf",
            mime="application/octet-stream",
            width="stretch",
        )

        st.caption("Veja o conteúdo do arquivo, a árvore e a taxa nas próximas abas.")

# ── 2. Descompactar ──────────────────────────────────────────────────────────

with aba_desc:
    st.subheader("Restaurar o texto original")

    opcoes = ["Enviar um arquivo .huf"]

    if st.session_state.resultado is not None:
        opcoes.insert(0, "Usar o arquivo que acabei de compactar")

    origem = st.radio("Origem", opcoes, horizontal=True, label_visibility="collapsed")

    huf_para_abrir: Optional[bytes] = None

    nome_huf: str = "arquivo.huf"

    if origem == "Usar o arquivo que acabei de compactar":
        huf_para_abrir = st.session_state.resultado.arquivo
        nome_huf = st.session_state.nome_huf or nome_huf
        st.write(f"Usando **{nome_huf}** ({fmt_bytes(len(huf_para_abrir))}).")

    else:
        enviado_huf = st.file_uploader("Arquivo .huf", type=["huf"], key="upload_huf")

        if enviado_huf is not None:
            huf_para_abrir = enviado_huf.getvalue()
            nome_huf = enviado_huf.name
            st.write(f"Arquivo **{nome_huf}** ({fmt_bytes(len(huf_para_abrir))}).")

    original_para_conferir: Optional[bytes] = None

    with st.expander("Conferir com o arquivo original (opcional)"):

        st.caption(
            "Se você compactou nesta sessão, a conferência é automática. "
            "Para um .huf externo, envie aqui o .txt original."
        )

        enviado_conf = st.file_uploader("Original .txt", type=["txt"], key="upload_conferencia")

        if enviado_conf is not None:
            original_para_conferir = enviado_conf.getvalue()

    if st.button(
        "📂 Descompactar",
        type="primary",
        width="stretch",
        disabled=huf_para_abrir is None,
    ):
        with st.spinner("Descompactando..."):
            restaurado = executar("compactador.descompactar", compactador.descompactar, huf_para_abrir)

        if restaurado is not None:
            st.session_state.restaurado = restaurado
            st.session_state.huf = huf_para_abrir
            st.session_state.nome_huf = nome_huf
            referencia = original_para_conferir

            if referencia is None and origem == "Usar o arquivo que acabei de compactar":
                referencia = st.session_state.original

            if referencia is not None:
                pos = primeiro_byte_diferente(referencia, restaurado.dados)
                st.session_state.verificacao = (pos is None, pos)

            else:
                st.session_state.verificacao = None

    restaurado_atual: Optional[ResultadoDescompressao] = st.session_state.restaurado

    if restaurado_atual is not None:
        st.divider()

        st.success(f"Descompactado em {fmt(restaurado_atual.tempo_segundos, '{:.3f}')} s.")

        c1, c2, c3 = st.columns(3)

        c1.metric("Compactado", fmt_bytes(len(st.session_state.huf or b"")))

        c2.metric("Restaurado", fmt_bytes(len(restaurado_atual.dados)))

        c3.metric("LZ77 no arquivo", "sim" if restaurado_atual.cabecalho.usa_lz77 else "não")

        verificacao = st.session_state.verificacao

        if verificacao is not None:
            identico, posicao = verificacao

            if identico:
                st.success("✅ O texto restaurado é **idêntico** ao original, byte a byte.")

            else:
                st.error(f"❌ O texto restaurado difere do original a partir do byte {posicao}.")

        else:
            st.info("Sem arquivo original para conferir. Envie-o no campo acima, se quiser.")

        with st.expander("Texto restaurado", expanded=True):
            mostrar_previa(decodificar_texto(restaurado_atual.dados), "previa_restaurado")

        base = (st.session_state.nome_huf or "arquivo.huf").rsplit(".", 1)[0]

        st.download_button(
            "⬇️ Baixar texto restaurado (.txt)",
            data=restaurado_atual.dados,
            file_name=f"{base}_restaurado.txt",
            mime="text/plain",
            width="stretch",
        )

# ── 3. Arquivo compactado ────────────────────────────────────────────────────

with aba_arq:
    st.subheader("O arquivo .huf por dentro")

    huf_atual: Optional[bytes] = st.session_state.huf

    if huf_atual is None:
        st.info("Compacte um texto ou descompacte um .huf para ver o arquivo aqui.")

    else:
        lido = executar("formato.ler_cabecalho", formato.ler_cabecalho, huf_atual)

        if lido is not None:
            cab, inicio_payload = lido
            payload = huf_atual[inicio_payload:]
            total = len(huf_atual)

            c1, c2, c3 = st.columns(3)
            c1.metric("Tamanho total", fmt_bytes(total))
            c2.metric("Cabeçalho", fmt_bytes(inicio_payload))
            c3.metric("Payload (dados)", fmt_bytes(len(payload)))

            if total:
                st.progress(
                    inicio_payload / total,
                    text=f"Cabeçalho = {fmt(100 * inicio_payload / total, '{:.1f}')}% do arquivo",
                )

            st.markdown("#### Campos do cabeçalho")

            n_pares = len(cab.comprimentos)

            campos = [
                {"Campo": "Assinatura (mágica)", "Offset": 0, "Bytes": 4, "Valor": formato.MAGICA.decode()},

                {"Campo": "Flags (bit 0 = LZ77)", "Offset": 4, "Bytes": 1, "Valor": "LZ77" if cab.usa_lz77 else "só Huffman"},

                {"Campo": "Tamanho original", "Offset": 5, "Bytes": 8, "Valor": f"{cab.tamanho_original} bytes"},

                {"Campo": "Símbolos codificados", "Offset": 13, "Bytes": 8, "Valor": f"{cab.quantidade_simbolos}"},

                {"Campo": "Bits de padding", "Offset": 21, "Bytes": 1, "Valor": f"{cab.bits_padding}"},

                {"Campo": "Tamanho da tabela (n)", "Offset": 22, "Bytes": 2, "Valor": f"{n_pares}"},

                {"Campo": "Pares (símbolo, comprimento)", "Offset": 24, "Bytes": 2 * n_pares, "Valor": f"{n_pares} pares"},

                {"Campo": "Payload", "Offset": inicio_payload, "Bytes": len(payload), "Valor": "bits do Huffman"},
            ]

            st.dataframe(pd.DataFrame(campos), hide_index=True, width="stretch")

            v_hex, v_bits, v_tabela, v_exemplo = st.tabs(
                ["Hexadecimal", "Bits do payload", "Tabela de comprimentos", "Do texto aos bits"]
            )

            with v_hex:
                st.code(hexdump(huf_atual, limite_bytes=limite_hex, inicio_payload=inicio_payload), language=None)

                st.download_button(
                    "⬇️ Baixar .huf",
                    data=huf_atual,
                    file_name=st.session_state.nome_huf or "arquivo.huf",
                    mime="application/octet-stream",
                )

            with v_bits:
                st.caption(
                    f"Primeiros bytes do payload em binário. Os últimos {cab.bits_padding} "
                    "bit(s) do último byte são padding (zeros de preenchimento)."
                )

                st.code(bytes_em_bits(payload, limite_bytes=min(limite_hex, 256)), language=None)

            with v_tabela:
                st.caption(
                    "Só os comprimentos são gravados; o descompactador regenera os "
                    "códigos canônicos a partir deles."
                )

                linhas_tab = [
                    {"Símbolo": rotulo_simbolo(s), "Byte": s, "Comprimento (bits)": c}

                    for s, c in sorted(cab.comprimentos.items(), key=lambda kv: (kv[1], kv[0]))
                ]

                st.dataframe(pd.DataFrame(linhas_tab), hide_index=True, width="stretch")

            with v_exemplo:
                res: Optional[ResultadoCompressao] = st.session_state.resultado

                if res is None or res.arquivo != huf_atual:
                    st.info("Disponível para o arquivo compactado nesta sessão.")

                elif res.usa_lz77:
                    st.info(
                        "Com LZ77, o Huffman recebe a saída do LZ77 (flags, literais e "
                        "referências), não o texto. Compacte sem LZ77 para ver o texto "
                        "virando bits diretamente."
                    )

                else:
                    original_bytes: bytes = st.session_state.original or b""

                    exemplo = codificar_trecho_para_exibicao(original_bytes, res.codigos, limite=24)

                    st.dataframe(pd.DataFrame(exemplo).T, width="stretch")
                    
                    bits_concat = "".join(linha["Código"] for linha in exemplo)

                    st.markdown("**Bits concatenados:**")

                    st.code(" ".join(bits_concat[i : i + 8] for i in range(0, len(bits_concat), 8)), language=None)

                    st.markdown("**Começo do payload (deve ser igual):**")

                    st.code(bytes_em_bits(payload, limite_bytes=(len(bits_concat) + 7) // 8, por_linha=64), language=None)

# ── 4. Árvore de Huffman ─────────────────────────────────────────────────────

with aba_arvore:
    st.subheader("Árvore de Huffman")
    res_arv: Optional[ResultadoCompressao] = st.session_state.resultado

    if res_arv is None:
        st.info("Compacte um arquivo para ver a árvore.")

    else:
        if res_arv.usa_lz77:
            st.caption(
                "ℹ️ Com LZ77 ligado, as folhas são os bytes da saída do LZ77 "
                "(literais, bytes de flags e de referências), não apenas os "
                "caracteres do texto. Desligue o LZ77 e compacte de novo para "
                "ver a árvore dos caracteres."
            )

        comprimentos = [len(c) for c in res_arv.codigos.values()] or [0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Folhas (símbolos)", len(res_arv.codigos))
        c2.metric("Altura (maior código)", max(comprimentos))
        c3.metric("Menor código", min(comprimentos))
        c4.metric("Símbolos codificados", f"{res_arv.tamanho_entrada_huffman:,}".replace(",", "."))

        if res_arv.arvore is None and res_arv.codigos:
            st.warning("`ResultadoCompressao.arvore` está vazia. Preencha-a com `huffman.reconstruir_arvore`.")

        else:
            dot = arvore_para_dot(res_arv.arvore, res_arv.codigos, max_folhas or None)

            if max_folhas and len(res_arv.codigos) > max_folhas:
                st.caption(
                    f"Mostrando as {max_folhas} folhas mais frequentes de {len(res_arv.codigos)}. "
                    "Ajuste na barra lateral (0 = todas)."
                )

            st.graphviz_chart(dot, width="stretch")
            st.caption(
                "Círculos: nós internos (soma das frequências). Caixas: folhas com "
                "símbolo, frequência (f) e código. Esquerda = 0, direita = 1."
            )

            st.download_button("⬇️ Baixar árvore (.dot)", data=dot, file_name="arvore_huffman.dot", mime="text/vnd.graphviz")

        st.markdown("#### Tabela de códigos")

        tabela = tabela_de_codigos(res_arv.frequencias, res_arv.codigos)

        st.dataframe(pd.DataFrame(tabela), hide_index=True, width="stretch")

# ── 5. Taxa de compactação ───────────────────────────────────────────────────

with aba_taxa:
    st.subheader("Taxa de compactação")
    res_taxa: Optional[ResultadoCompressao] = st.session_state.resultado

    if res_taxa is None:
        st.info("Compacte um arquivo para ver as métricas.")

    else:
        orig, comp = res_taxa.tamanho_original, res_taxa.tamanho_compactado

        taxa = metrica(metricas.taxa_de_compressao, orig, comp)

        reducao = metrica(metricas.percentual_de_reducao, orig, comp)

        fator = metrica(metricas.fator_de_compressao, orig, comp)

        bpc = metrica(metricas.bits_por_caractere, orig, comp)

        h = metrica(metricas.entropia, res_taxa.frequencias)

        lmed = metrica(metricas.comprimento_medio, res_taxa.frequencias, res_taxa.codigos)

        efic = None if h is None or lmed is None else metrica(metricas.eficiencia, h, lmed)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Original", fmt_bytes(orig))
        c2.metric("Compactado", fmt_bytes(comp))
        c3.metric("Taxa", fmt(taxa, "{:.3f}"))
        c4.metric("Redução", fmt(reducao, "{:.1f}") + "%")
        c5, c6, c7, c8, c9 = st.columns(5)
        c5.metric("Fator", fmt(fator, "{:.2f}") + ":1")
        c6.metric("Bits por caractere", fmt(bpc, "{:.3f}"))
        c7.metric("Entropia H", fmt(h, "{:.3f}") + " bits")
        c8.metric("Comprimento médio L", fmt(lmed, "{:.3f}") + " bits")
        c9.metric("Eficiência H/L", fmt(None if efic is None else 100 * efic, "{:.1f}") + "%")

        if None in (taxa, reducao, fator, bpc, h, lmed):
            st.warning("Algumas métricas aparecem como “—” porque `metricas.py` ainda não está implementado.")

        st.markdown("#### Para onde foram os bytes")

        barras = {"Original": orig}

        if res_taxa.usa_lz77:
            barras["Após LZ77"] = res_taxa.tamanho_entrada_huffman

        barras["Cabeçalho"] = res_taxa.tamanho_cabecalho
        barras["Payload"] = res_taxa.tamanho_payload
        barras["Compactado (total)"] = comp

        # Prefixo numérico mantém a ordem das barras (o gráfico ordena alfabeticamente).

        rotulos = [f"{i}. {nome}" for i, nome in enumerate(barras, start=1)]

        df_barras = pd.DataFrame({"Etapa": rotulos, "Bytes": list(barras.values())})

        st.bar_chart(df_barras, x="Etapa", y="Bytes", width="stretch")

        st.markdown("#### Como ler esses números")

        st.latex(r"\text{taxa} = \frac{\text{tamanho compactado}}{\text{tamanho original}}"
                 rf"= \frac{{{comp}}}{{{orig}}} \approx {fmt(taxa, '{:.3f}').replace(',', '{,}')}")
        
        st.markdown(
            f"""
- **Taxa**: quanto sobrou do arquivo. Quanto menor, melhor. A **redução** é
  o complemento: o arquivo encolheu **{fmt(reducao, '{:.1f}')}%**.
- **Bits por caractere**: o texto original gasta 8 bits por byte; depois da
  compressão a média caiu para **{fmt(bpc, '{:.3f}')}** bits.
- **Entropia (H)**: o mínimo teórico de bits por símbolo para um código que
  olha um símbolo por vez. O Huffman garante **H ≤ L < H + 1**; aqui
  H = {fmt(h, '{:.3f}')} e L = {fmt(lmed, '{:.3f}')}.
- **Cabeçalho**: ocupa **{fmt_bytes(res_taxa.tamanho_cabecalho)}** (assinatura,
  tamanhos e a tabela de comprimentos dos códigos). Em arquivos muito pequenos
  ele pode deixar o “compactado” maior que o original.
- **Por que funciona**: símbolos frequentes (espaço, vogais) recebem códigos
  curtos e os raros recebem códigos longos. Quanto mais desigual a
  distribuição, maior o ganho.
"""
        )
        if res_taxa.usa_lz77:
            st.markdown(
                f"""
- **LZ77**: gerou **{res_taxa.quantidade_tokens_lz77}** tokens, dos quais
  **{res_taxa.quantidade_referencias_lz77}** são referências a trechos
  repetidos. A entrada do Huffman foi de {fmt_bytes(orig)} para
  {fmt_bytes(res_taxa.tamanho_entrada_huffman)}. Como o LZ77 elimina
  repetições de *sequências*, o resultado final pode ficar abaixo do que a
  entropia dos caracteres sozinha permitiria.
"""
            )

# ── 6. Comparação ────────────────────────────────────────────────────────────

with aba_cmp:
    st.subheader("Huffman puro × Huffman + LZ77")
    original_cmp: Optional[bytes] = st.session_state.original

    if original_cmp is None:
        st.info("Escolha um .txt na aba **Compactar** primeiro.")

    else:
        st.write(
            f"Compacta **{st.session_state.nome_original}** dos dois jeitos e "
            "confere se a ida e volta devolve o texto original."
        )

        if st.button("⚖️ Rodar comparação", type="primary", width="stretch"):

            linhas_cmp: list[dict[str, Any]] = []

            with st.spinner("Comparando..."):

                for nome_modo, flag in (("Só Huffman", False), ("Huffman + LZ77", True)):

                    res_cmp = executar(f"compactar(usar_lz77={flag})", compactador.compactar, original_cmp, usar_lz77=flag)

                    if res_cmp is None:
                        continue

                    volta = executar("descompactar", compactador.descompactar, res_cmp.arquivo)
                    
                    ok = volta is not None and volta.dados == original_cmp
                    linhas_cmp.append(
                        {
                            "Modo": nome_modo,
                            "Tamanho (bytes)": res_cmp.tamanho_compactado,
                            "Taxa": metrica(metricas.taxa_de_compressao, len(original_cmp), res_cmp.tamanho_compactado),
                            "Redução (%)": metrica(metricas.percentual_de_reducao, len(original_cmp), res_cmp.tamanho_compactado),
                            "Compactar (s)": res_cmp.tempo_segundos,
                            "Descompactar (s)": None if volta is None else volta.tempo_segundos,
                            "Ida e volta": "✅" if ok else "❌",
                        }
                    )
            st.session_state.comparacao = linhas_cmp

        linhas_salvas: Optional[list[dict[str, Any]]] = st.session_state.comparacao
        if linhas_salvas:
            df_cmp = pd.DataFrame(linhas_salvas)
            st.dataframe(
                df_cmp,
                hide_index=True,
                width="stretch",
                column_config={
                    "Taxa": st.column_config.NumberColumn(format="%.3f"),
                    "Redução (%)": st.column_config.NumberColumn(format="%.1f"),
                    "Compactar (s)": st.column_config.NumberColumn(format="%.3f"),
                    "Descompactar (s)": st.column_config.NumberColumn(format="%.3f"),
                },
            )
            grafico = pd.DataFrame(
                {
                    "Modo": [f"{i}. {m}" for i, m in enumerate(["Original"] + [linha["Modo"] for linha in linhas_salvas], start=1)],
                    "Bytes": [len(original_cmp)] + [linha["Tamanho (bytes)"] for linha in linhas_salvas],
                }
            )
            st.bar_chart(grafico, x="Modo", y="Bytes", width="stretch")
            if len(linhas_salvas) == 2:
                a, b = linhas_salvas
                ganho = a["Tamanho (bytes)"] - b["Tamanho (bytes)"]
                if ganho > 0:
                    st.success(f"O LZ77 economizou mais **{fmt_bytes(ganho)}** em relação ao Huffman puro.")
                elif ganho < 0:
                    st.info(f"Neste arquivo o Huffman puro ficou **{fmt_bytes(-ganho)}** menor.")
                else:
                    st.info("Os dois modos produziram o mesmo tamanho.")

st.divider()
st.caption("Compactador de Huffman · Huffman canônico + LZ77 (LZSS) · interface em Streamlit")
