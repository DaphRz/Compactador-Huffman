# Compactador de Huffman

Compactador de arquivos de texto com **Huffman Canônico**, combinado com **LZ77 (variante LZSS)**, com interface gráfica em **Streamlit**.

## Como executar - colocar passo a passo Windows UVV

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Plano B (linha de comando) e testes:

```bash
python cli.py compactar texto.txt texto.huf             # Huffman + LZ77
python cli.py compactar texto.txt texto.huf --sem-lz77  # só Huffman
python cli.py descompactar texto.huf restaurado.txt
python -m unittest discover -s tests -v
```

---

## 1. Requisitos do trabalho → onde cada um é atendido

| Req. | O que o trabalho pede | Onde está | Aba da interface |
|---|---|---|---|
| **a** | Escolher um `.txt` e compactar | `app.py` (upload) → `compactador.compactar()` | 📦 Compactar |
| **b** | Descompactar, voltando ao texto original | `compactador.descompactar()` | 📂 Descompactar (confere byte a byte com o original) |
| **c** | Mostrar o arquivo compactado | `visualizacao.hexdump()`, `bytes_em_bits()` | 🔍 Arquivo compactado (cabeçalho, hexadecimal, bits do payload) |
| **d** | Mostrar a árvore de Huffman montada | `huffman.construir_arvore()` + `visualizacao.arvore_para_dot()` | 🌳 Árvore de Huffman (desenho + tabela de códigos) |
| **e** | Mostrar e **explicar** a taxa de compactação | `metricas.py` | 📊 Taxa de compactação (números, gráfico e explicação em texto) |
| **f** | Combinar Huffman com outra técnica (ex.: LZ77) | `lz77.py` (liga/desliga na barra lateral) | ⚖️ Huffman × Huffman + LZ77 (compara os dois modos) |
| **g** | Arquivo padrão fornecido no dia da apresentação | pipeline inteiro, com atenção a velocidade (ver seção 6) | qualquer aba; `cli.py` como plano B |

---

## 2. Fluxo da compactação

```
 texto.txt (bytes)
      │
      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 1. LZ77  (opcional)                              lz77.py    │
 │    acha trechos repetidos e troca por (distância, tamanho)  │
 │    comprimir() → serializar()  →  bytes intermediários      │
 └─────────────────────────────────────────────────────────────┘
      │  (sem LZ77, o texto segue direto)
      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 2. Contar frequências                          huffman.py   │
 │    quantas vezes cada byte aparece                          │
 └─────────────────────────────────────────────────────────────┘
      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 3. Construir a árvore de Huffman               huffman.py   │
 │    junta repetidamente os 2 nós menos frequentes (min-heap) │
 └─────────────────────────────────────────────────────────────┘
      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 4. Gerar códigos                               huffman.py   │
 │    esquerda = 0, direita = 1; só o COMPRIMENTO é aproveitado│
 │    depois vira código canônico (mesmos tamanhos)            │
 └─────────────────────────────────────────────────────────────┘
      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 5. Codificar                       huffman.py + bitio.py    │
 │    cada byte vira seu código; os bits são empacotados em    │
 │    bytes (com padding no final)                             │
 └─────────────────────────────────────────────────────────────┘
      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 6. Gravar o arquivo .huf                       formato.py   │
 │    cabeçalho (metadados + comprimentos dos códigos) + bits  │
 └─────────────────────────────────────────────────────────────┘
      ▼
 texto.huf
```

Tudo isso é orquestrado por `compactador.compactar()`.

### Por que LZ77 e Huffman juntos?
As duas técnicas atacam problemas diferentes e se complementam:

- **LZ77** elimina repetição de *sequências* ("de que", "ção", palavras inteiras).
- **Huffman** explora a *distribuição de símbolos* (letras frequentes ganham códigos curtos).

Por isso a interface tem a chave **"Usar LZ77 antes do Huffman"** e a aba de comparação mostra o ganho dos dois modos lado a lado.

### Por que Huffman Canônico?
Com códigos canônicos o cabeçalho só precisa guardar o **comprimento** do código de cada símbolo (2 bytes por símbolo), em vez da tabela de frequências ou da árvore inteira. O descompactador regenera exatamente os mesmos códigos a partir dos comprimentos. A taxa de compressão é idêntica à do Huffman clássico e o cabeçalho fica menor, o que pesa em arquivos pequenos.

---

## 3. Fluxo da descompactação

```
 texto.huf
      ▼
 1. Ler e validar o cabeçalho                                  formato.py
      │   (assinatura, flags, tamanhos, padding, comprimentos)
      ▼
 2. Regenerar os códigos canônicos                             huffman.py
      ▼
 3. Reconstruir a árvore (trie binária)                        huffman.py
      ▼
 4. Decodificar os bits                                        huffman.py + bitio.py
      │   (desce na árvore: 0 = esquerda, 1 = direita; ao chegar numa
      │    folha emite o símbolo e volta à raiz; o padding é ignorado)
      ▼
 5. Desfazer o LZ77 (se a flag estiver ligada)                 lz77.py
      ▼
 texto restaurado  (idêntico ao original)
```

Orquestrado por `compactador.descompactar()`. A interface confere o resultado byte a byte com o original e avisa se o arquivo estiver corrompido (`FormatoInvalidoError`).

---

## 4. O que cada arquivo faz

### Núcleo (a implementar, hoje esqueletos com docstrings e `TODO`)

| Arquivo | Responsabilidade | Principais funções/classes |
|---|---|---|
| `bitio.py` | **Ponte entre bits e bytes.** Huffman gera códigos de tamanho variável (`0`, `101`, `1100`), mas um arquivo só guarda bytes inteiros. O escritor agrupa os bits de 8 em 8 e completa o último byte com zeros (*padding*); o leitor devolve os bits um a um ignorando o padding. | `EscritorDeBits`, `LeitorDeBits` |
| `huffman.py` | **O algoritmo de Huffman.** Frequências, árvore (min-heap), códigos, códigos canônicos, codificação e decodificação. | `NoHuffman`, `contar_frequencias`, `construir_arvore`, `gerar_codigos`, `gerar_codigos_canonicos`, `reconstruir_arvore`, `codificar`, `decodificar` |
| `lz77.py` | **Segunda técnica (LZSS).** Troca repetições por referências `(distância, comprimento)` e serializa os tokens em bytes para o Huffman comprimir. | `comprimir`, `descomprimir`, `serializar`, `desserializar`, `TokenLiteral`, `TokenReferencia` |
| `formato.py` | **Layout do arquivo `.huf`.** Grava e lê o cabeçalho, validando assinatura e tamanhos. | `Cabecalho`, `serializar_cabecalho`, `ler_cabecalho`, `FormatoInvalidoError` |
| `compactador.py` | **Pipeline completo.** Liga LZ77, Huffman e formato. É a única camada que a interface chama. | `compactar`, `descompactar`, `compactar_arquivo`, `descompactar_arquivo` |
| `metricas.py` | **Números da taxa de compactação** exibidos e explicados (req. e). | `taxa_de_compressao`, `percentual_de_reducao`, `fator_de_compressao`, `bits_por_caractere`, `entropia`, `comprimento_medio`, `eficiencia` |

### Interface e apoio (prontos)

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Interface Streamlit com as 6 abas. |
| `visualizacao.py` | Só **exibição**: árvore em Graphviz, hexdump, bits, tabela de códigos. Não comprime nada. |
| `cli.py` | Mesma funcionalidade pela linha de comando (plano B na apresentação). |
| `tests/test_compactador.py` | Testes de ida e volta e casos de borda (vazio, um único símbolo, acentos, arquivo corrompido). |
| `requirements.txt` | Dependências (apenas Streamlit). |

### Quem chama quem

```
app.py / cli.py
    └── compactador.py
          ├── lz77.py
          ├── huffman.py ── bitio.py
          ├── formato.py
          └── (métricas em metricas.py, exibição em visualizacao.py)
```

---

## 5. Formato do arquivo `.huf`

```
offset  tam.  campo
0       4     assinatura "HUF1"
4       1     flags (bit 0 = LZ77 aplicado)
5       8     tamanho_original
13      8     quantidade_simbolos (bytes que entraram no Huffman)
21      1     bits_padding (0..7)
22      2     n = quantidade de símbolos na tabela
24      2n    n pares (símbolo, comprimento do código)
24+2n   ...   payload: bits do Huffman empacotados
```

É exatamente o que a aba **Arquivo compactado** mostra (req. c).

---

## 6. Taxa de compactação (req. e)

| Métrica | Definição | Como ler |
|---|---|---|
| **Taxa** | `tamanho_compactado / tamanho_original` | Quanto menor, melhor. 0,40 = sobrou 40%. |
| **Redução** | `(1 − taxa) × 100` | Economia de espaço em %. |
| **Fator** | `original / compactado` | 2,5:1 = ficou 2,5 vezes menor. |
| **Bits por caractere** | `8 × compactado / original` | O texto original gasta 8 bits por byte. |
| **Entropia H** | `−Σ p·log₂ p` | Limite teórico mínimo de bits/símbolo olhando um símbolo por vez. |
| **Comprimento médio L** | `Σ p · tamanho_do_código` | Média real do Huffman; vale `H ≤ L < H + 1`. |
| **Eficiência** | `H / L` | 100% = código ótimo. |

Pontos para explicar na apresentação:

- Símbolos frequentes recebem códigos curtos; os raros, códigos longos. Quanto mais desigual a distribuição, maior o ganho.
- O cabeçalho conta no tamanho final; em arquivos muito pequenos o "compactado" pode ficar maior que o original.
- Com LZ77, o resultado pode ficar abaixo da entropia dos caracteres, porque o LZ77 explora repetição de sequências, algo que a entropia de ordem 0 não enxerga.

---

## 7. Dicas para o dia da apresentação (req. g)

O arquivo padrão será a métrica de sucesso, então:

- **Correção primeiro:** compactar → descompactar → texto idêntico. A aba Descompactar confere byte a byte; envie o `.txt` original no campo de conferência.
- **Velocidade:** escrever bit a bit em Python é lento. Em `huffman.codificar`, junte os códigos em uma string só (`"".join(...)`) e converta de uma vez com `int(bits, 2).to_bytes(...)`. No LZ77, use o índice por trinca de bytes (já descrito em `lz77.py`) em vez de comparar com a janela inteira.
- **Casos de borda:** arquivo vazio, um único símbolo distinto (o código precisa ter 1 bit) e acentos (trabalha-se em bytes, então UTF-8 funciona).
- **Plano B:** `cli.py` funciona sem a interface.

---

## 8. Ordem sugerida de implementação

1. `bitio.py` → `TestBitIO`
2. `huffman.py` → `TestHuffman`
3. `formato.py` → `TestFormato`
4. `compactador.py` (primeiro com `usar_lz77=False`) → a interface já funciona
5. `metricas.py` → aba de taxa completa
6. `lz77.py` → `TestLZ77` e depois `TestPipeline`

A interface abre desde o início: enquanto uma função retornar `None`, ela avisa qual está faltando.
