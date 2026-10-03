# Datathon Regional Inria — Avaliação com LLM local

Roda um LLM localmente (via [Ollama](https://ollama.com)) para responder às perguntas
que o time está criando e medir a **taxa de acerto** da IA. Serve para calibrar a
dificuldade das perguntas: se todos os modelos acertam, está fácil demais; se nenhum
acerta, vale revisar o enunciado ou o gabarito.

## Início rápido

```bash
./setup.sh              # instala o Ollama e baixa os modelos de modelos.txt
python3 avaliar.py      # roda as perguntas em todos os modelos de modelos.txt
```

Só precisa de Python 3 (sem bibliotecas extras).

## Escrevendo perguntas

Crie um CSV em `perguntas/` com as colunas `id,tipo,pergunta,alternativas,resposta`:

| tipo       | alternativas                       | resposta                                   |
|------------|------------------------------------|--------------------------------------------|
| `multipla` | `A) ... \| B) ... \| C) ... \| D) ...` | letra correta (`B`)                        |
| `aberta`   | (vazio)                            | texto esperado; variações separadas por `\|` |

Veja `perguntas/exemplo.csv`. Sem `-a`, o script usa o **CSV mais recente** da pasta
`perguntas/`: basta baixar a planilha (Arquivo > Fazer download > .csv) para lá. Linhas
incompletas (sem pergunta, gabarito, tipo ou alternativas) são ignoradas, com aviso. Nas perguntas abertas, conta como acerto quando a
resposta do modelo **contém** o texto esperado (sem diferenciar maiúsculas nem acentos).

## Usando uma planilha do Google Sheets

Em vez de baixar o CSV toda vez, o script pode ler direto da planilha do time:

1. No Google Sheets, use a primeira linha como cabeçalho: `id | tipo | pergunta | alternativas | resposta`.
2. Compartilhar > "Qualquer pessoa com o link" > **Leitor**.
3. Cole o link da planilha em `planilha.txt`. Para usar outra aba, copie o link com a aba aberta.

A partir daí, `python3 avaliar.py` sempre baixa a versão mais recente. Linhas vazias são
ignoradas, e uma cópia das perguntas usadas fica salva em `resultados/` junto com o resultado.
Para usar um link pontualmente: `python3 avaliar.py -a "https://docs.google.com/spreadsheets/d/..."`.

## Comandos úteis

```bash
python3 avaliar.py -a perguntas/minhas.csv               # outro arquivo
python3 avaliar.py -m qwen2.5:3b llama3.2:3b gemma3:1b   # compara modelos
python3 avaliar.py -r 5 -t 0.7                           # 5 tentativas c/ temperatura (consistência)
```

Cada execução **apaga os resultados anteriores** e salva em `resultados/` (fora do git):
`resultado.csv` (resposta bruta do modelo, o que foi extraído, se acertou e o tempo) e
`perguntas_usadas.csv` (cópia das perguntas avaliadas).

## Modelos recomendados

A máquina de desenvolvimento não tem GPU e tem ~5,5 GB de RAM, por isso os modelos são pequenos:

| Modelo        | Tamanho | Observação                       |
|---------------|---------|----------------------------------|
| `qwen2.5:3b`  | ~2 GB   | padrão, bom em português         |
| `llama3.2:3b` | ~2 GB   | alternativa                      |
| `gemma3:1b`   | ~0,8 GB | mais rápido, para pouca memória  |

Para mudar os modelos usados por padrão, edite `modelos.txt` (um por linha) e rode `./setup.sh` de novo para baixar os novos. Para modelos
maiores (7B+), use uma máquina com GPU ou o Google Colab.
