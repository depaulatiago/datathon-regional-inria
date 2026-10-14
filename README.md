# Inria Regional Datathon — local LLMs vs. Brazilian regional culture

[Português](README.pt-BR.md) | **English**

A tool built during the **Inria Regional Datathon** to test LLMs running **locally, offline and
without a GPU** on questions about Brazilian regional culture (music, popular expressions, food,
neighborhood history, municipal laws, recent news) and measure each model's **accuracy**.

The goal was to calibrate the difficulty of the questions written by the team:

- if **every** model gets it right → the question is too easy;
- if **no** model gets it right → the wording or the answer key deserves a second look;
- if the models **disagree** → the question probably measures real regional knowledge.

## Highlights

- **Plain Python 3**: no external libraries; talks to Ollama over HTTP.
- **Runs on a modest machine** (no GPU, ~5.5 GB of RAM): unloads each model from memory before
  loading the next one, so the machine doesn't freeze.
- **Reads straight from Google Sheets**: the team edits the spreadsheet and the script always picks
  up the latest version (with clear messages when the sheet isn't public or the institution blocks
  access).
- **Automatic grading** of multiple-choice questions (extracts the letter even from verbose answers
  like "Answer: B" or "B) Jupiter") and open questions (case- and accent-insensitive comparison).
- **Consistency test**: repeats each question N times with temperature > 0.
- **Results saved after each model**: if a run crashes midway, what already ran isn't lost.

## Results

Multiple-choice questions with 4 options (random guessing scores 25%), temperature 0.
To compare languages, the table uses the **12 questions present in both versions**:

| Model         | Portuguese   | English      |
|---------------|--------------|--------------|
| `qwen2.5:3b`  | 25.0% (3/12) | 41.7% (5/12) |
| `llama3.2:3b` | 8.3% (1/12)  | 41.7% (5/12) |
| `gemma3:1b`   | 25.0% (3/12) | 25.0% (3/12) |
| **average**   | **19.4%**    | **36.1%**    |

On the full Portuguese set (16 questions): qwen2.5 31.2%, gemma3 18.8%, llama3.2 12.5%.

What the numbers show:

- **Small models are basically guessing on Brazilian regional culture.** In Portuguese, the
  average was *below* chance.
- **The same question in English gets almost twice as many correct answers**; `llama3.2:3b` went
  from 8% to 42%. The models "know" more when the question is in the language they were mostly
  trained on.
- **No model, in either language, got right** the questions about a 2026 municipal law from
  Lavras (newer than the models' training data), a popular expression, the ingredients of a
  regional drink and the origin of the name "brigadeiro". These are the candidates for "hard"
  questions (or for reviewing the answer key).

> Small sample (12–16 questions): the numbers are meant to calibrate the questions, not to
> benchmark the models.

## Quick start

```bash
./setup.sh                                       # installs Ollama (no sudo) and pulls the models in modelos.txt
python3 avaliar.py                               # questions in Portuguese (perguntas/)
python3 avaliar.py -a perguntas_en/perguntas.csv # same questions in English
```

## Structure

```
avaliar.py                  # evaluation script
setup.sh                    # installs Ollama and pulls the models
modelos.txt                 # default models (one per line)
planilha.txt                # optional Google Sheets link with the questions
perguntas/perguntas.csv     # questions in Portuguese (exported from the team's spreadsheet)
perguntas_en/perguntas.csv  # English version, with cultural context and review notes
resultados/                 # output of each run (not tracked by git)
```

## Question format

CSV with the columns `id,tipo,pergunta,alternativas,resposta` (extra columns are ignored):

| tipo       | alternativas                           | resposta                                   |
|------------|----------------------------------------|--------------------------------------------|
| `multipla` | `A) ... \| B) ... \| C) ... \| D) ...` | correct letter (`B`)                       |
| `aberta`   | (empty)                                | expected text; variants separated by `\|`  |

Without `-a`, the script uses the link in `planilha.txt` or, if there is none, the **most recent
CSV** in `perguntas/`. Incomplete rows (missing question, answer, type or options) are skipped with
a warning. For open questions, an answer counts as correct when it **contains** the expected text.

### Reading straight from Google Sheets

1. Use the first row as the header: `id | tipo | pergunta | alternativas | resposta`.
2. Share > "Anyone with the link" > **Viewer**.
3. Paste the link into `planilha.txt` (for another tab, copy the link with that tab open).

Or for a single run: `python3 avaliar.py -a "https://docs.google.com/spreadsheets/d/..."`.

## Options

```bash
python3 avaliar.py -m qwen2.5:3b llama3.2:3b gemma3:1b   # choose the models
python3 avaliar.py -a perguntas/my_questions.csv         # another file
python3 avaliar.py -r 5 -t 0.7                           # 5 attempts with temperature (consistency)
```

Each run deletes the previous results and saves to `resultados/`:

- `resultado.csv`: one row per question, one column per model, accuracy and final average;
- `respostas_completas.csv`: each model's raw answer, extracted letter and response time;
- `perguntas_usadas.csv`: exact copy of the evaluated questions (the spreadsheet may change later).

## Models

Chosen to fit on a machine with no GPU and ~5.5 GB of RAM:

| Model         | Size    | Note                          |
|---------------|---------|-------------------------------|
| `qwen2.5:3b`  | ~2 GB   | good at Portuguese            |
| `llama3.2:3b` | ~2 GB   | alternative                   |
| `gemma3:1b`   | ~0.8 GB | fastest, for low memory       |

To change them, edit `modelos.txt` and run `./setup.sh` again. Larger models (7B+) need a GPU or
Google Colab.

## License

[MIT](LICENSE)
