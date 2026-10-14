# Datathon Regional Inria — LLMs locais vs. cultura regional brasileira

> **EN:** A small, dependency-free Python tool that runs local LLMs (via [Ollama](https://ollama.com),
> fully offline, CPU-only) against a set of multiple-choice questions about Brazilian regional
> culture and measures each model's accuracy. Built during the Inria Regional Datathon to calibrate
> question difficulty: if every model gets a question right, it is too easy; if none does, the
> question or its answer key deserves a second look.

Ferramenta feita durante o **Datathon Regional Inria** para testar LLMs rodando **localmente, sem
internet e sem GPU** em perguntas sobre cultura regional brasileira (música, expressões populares,
culinária, história de bairros, leis municipais, notícias recentes) e medir a **taxa de acerto**
de cada modelo.

O objetivo era calibrar a dificuldade das perguntas criadas pelo time:

- se **todos** os modelos acertam → a pergunta está fácil demais;
- se **nenhum** acerta → vale revisar o enunciado ou o gabarito;
- se os modelos **divergem** → a pergunta provavelmente mede conhecimento regional de verdade.

## Destaques

- **Só Python 3 padrão**: nenhuma biblioteca externa; conversa com o Ollama via HTTP.
- **Roda em máquina modesta** (sem GPU, ~5,5 GB de RAM): descarrega cada modelo da memória antes
  de carregar o próximo, para não travar a máquina.
- **Lê direto do Google Sheets**: o time edita a planilha e o script sempre pega a versão mais
  recente (com mensagens claras quando a planilha não está pública ou a instituição bloqueia o acesso).
- **Correção automática** de múltipla escolha (extrai a letra mesmo de respostas prolixas como
  "Resposta: B" ou "B) Júpiter") e de perguntas abertas (compara sem diferenciar maiúsculas/acentos).
- **Teste de consistência**: repete cada pergunta N vezes com temperatura > 0.
- **Resultados salvos a cada modelo**: se a execução cair no meio, o que já rodou não se perde.

## Resultados

Perguntas de múltipla escolha com 4 alternativas (o chute aleatório acerta 25%), temperatura 0.
Para comparar os idiomas, a tabela usa as **12 perguntas presentes nas duas versões**:

| Modelo        | Português   | Inglês      |
|---------------|-------------|-------------|
| `qwen2.5:3b`  | 25,0% (3/12) | 41,7% (5/12) |
| `llama3.2:3b` | 8,3% (1/12)  | 41,7% (5/12) |
| `gemma3:1b`   | 25,0% (3/12) | 25,0% (3/12) |
| **média**     | **19,4%**    | **36,1%**    |

No conjunto completo em português (16 perguntas): qwen2.5 31,2%, gemma3 18,8%, llama3.2 12,5%.

O que os números mostram:

- **Modelos pequenos praticamente chutam em cultura regional brasileira.** Em português, a média
  ficou *abaixo* do acaso.
- **A mesma pergunta em inglês rende quase o dobro de acertos**; o `llama3.2:3b` foi de 8% para 42%.
  Os modelos "sabem" mais quando o enunciado está na língua em que foram mais treinados.
- **Nenhum modelo acertou, em nenhum idioma**, as perguntas sobre a lei municipal de Lavras de 2026
  (posterior ao treino dos modelos), uma expressão popular, os ingredientes de uma bebida regional
  e a origem do nome do brigadeiro. São as candidatas a perguntas "difíceis" (ou a revisar o gabarito).

> Amostra pequena (12–16 perguntas): os números servem para calibrar as perguntas, não como
> benchmark dos modelos.

## Início rápido

```bash
./setup.sh                                       # instala o Ollama (sem sudo) e baixa os modelos de modelos.txt
python3 avaliar.py                               # perguntas em português (perguntas/)
python3 avaliar.py -a perguntas_en/perguntas.csv # mesmas perguntas em inglês
```

## Estrutura

```
avaliar.py                  # script de avaliação
setup.sh                    # instala o Ollama e baixa os modelos
modelos.txt                 # modelos usados por padrão (um por linha)
planilha.txt                # link opcional da planilha do Google Sheets
perguntas/perguntas.csv     # perguntas em português (exportadas da planilha do time)
perguntas_en/perguntas.csv  # versão em inglês, com contexto cultural e notas de revisão
resultados/                 # saída de cada execução (fora do git)
```

## Formato das perguntas

CSV com as colunas `id,tipo,pergunta,alternativas,resposta` (colunas extras são ignoradas):

| tipo       | alternativas                           | resposta                                     |
|------------|----------------------------------------|----------------------------------------------|
| `multipla` | `A) ... \| B) ... \| C) ... \| D) ...` | letra correta (`B`)                          |
| `aberta`   | (vazio)                                | texto esperado; variações separadas por `\|` |

Sem `-a`, o script usa o link de `planilha.txt` ou, se não houver, o **CSV mais recente** da pasta
`perguntas/`. Linhas incompletas (sem pergunta, gabarito, tipo ou alternativas) são ignoradas com
aviso. Nas perguntas abertas, conta como acerto quando a resposta do modelo **contém** o texto esperado.

### Lendo direto do Google Sheets

1. Use a primeira linha como cabeçalho: `id | tipo | pergunta | alternativas | resposta`.
2. Compartilhar > "Qualquer pessoa com o link" > **Leitor**.
3. Cole o link em `planilha.txt` (para outra aba, copie o link com a aba aberta).

Ou pontualmente: `python3 avaliar.py -a "https://docs.google.com/spreadsheets/d/..."`.

## Opções

```bash
python3 avaliar.py -m qwen2.5:3b llama3.2:3b gemma3:1b   # escolhe os modelos
python3 avaliar.py -a perguntas/minhas.csv               # outro arquivo
python3 avaliar.py -r 5 -t 0.7                           # 5 tentativas com temperatura (consistência)
```

Cada execução apaga os resultados anteriores e salva em `resultados/`:

- `resultado.csv`: uma linha por pergunta, uma coluna por modelo, % de acerto e média final;
- `respostas_completas.csv`: resposta bruta de cada modelo, letra extraída e tempo;
- `perguntas_usadas.csv`: cópia exata das perguntas avaliadas (a planilha pode mudar depois).

## Modelos

Escolhidos para caber numa máquina sem GPU com ~5,5 GB de RAM:

| Modelo        | Tamanho | Observação                      |
|---------------|---------|---------------------------------|
| `qwen2.5:3b`  | ~2 GB   | bom em português                |
| `llama3.2:3b` | ~2 GB   | alternativa                     |
| `gemma3:1b`   | ~0,8 GB | mais rápido, para pouca memória |

Para trocar, edite `modelos.txt` e rode `./setup.sh` de novo. Modelos maiores (7B+) pedem GPU ou
o Google Colab.

## Licença

[MIT](LICENSE)
