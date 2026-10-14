#!/usr/bin/env python3
"""Avalia a taxa de acerto de LLMs locais (via Ollama) em um conjunto de perguntas.

Uso:
    python3 avaliar.py                                   # modelos de modelos.txt; perguntas do link
                                                         # em planilha.txt ou do CSV mais recente em perguntas/
    python3 avaliar.py -m qwen2.5:3b gemma3:1b           # compara vários modelos
    python3 avaliar.py -a perguntas_en/perguntas.csv     # perguntas em inglês
    python3 avaliar.py -r 3 -t 0.7                       # 3 repetições por pergunta

Formato do CSV (colunas):
    id, tipo, pergunta, alternativas, resposta
    - tipo "multipla": alternativas no formato "A) ... | B) ... | C) ...", resposta = letra
    - tipo "aberta":   alternativas vazio, resposta = texto esperado
                       (aceita variações separadas por "|", ex.: "oxigênio|oxigenio")
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
PASTA = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_MODELOS = os.path.join(PASTA, "modelos.txt")
ARQUIVO_PLANILHA = os.path.join(PASTA, "planilha.txt")

PROMPT_MULTIPLA = (
    "Responda à questão de múltipla escolha abaixo.\n\n"
    "{pergunta}\n\n{alternativas}\n\n"
    "Responda APENAS com a letra da alternativa correta (A, B, C, D ou E), sem explicação."
)
PROMPT_ABERTA = (
    "Responda à pergunta abaixo de forma curta e direta, sem explicação.\n\n{pergunta}"
)


def ollama(caminho, dados=None, timeout=600):
    req = urllib.request.Request(
        OLLAMA_URL + caminho,
        data=json.dumps(dados).encode() if dados is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def modelos_padrao():
    """Lê modelos.txt (um por linha, # para comentário)."""
    try:
        with open(ARQUIVO_MODELOS, encoding="utf-8") as f:
            modelos = [l.split("#")[0].strip() for l in f]
    except FileNotFoundError:
        return ["qwen2.5:3b"]
    return [m for m in modelos if m] or ["qwen2.5:3b"]


def checar_ollama(modelos):
    """Retorna só os modelos já baixados; avisa sobre os que faltam."""
    try:
        instalados = {m["name"] for m in ollama("/api/tags", timeout=5)["models"]}
    except (urllib.error.URLError, ConnectionError):
        sys.exit(f"Ollama não está rodando em {OLLAMA_URL}. Rode ./setup.sh ou `ollama serve`.")
    disponiveis = []
    for m in modelos:
        if (m if ":" in m else m + ":latest") in instalados:
            disponiveis.append(m)
        else:
            print(f"AVISO: modelo '{m}' não está baixado, pulando. Baixe com: ollama pull {m}")
    if not disponiveis:
        sys.exit("Nenhum modelo disponível. Rode ./setup.sh")
    return disponiveis


def perguntar(modelo, prompt, temperatura):
    resp = ollama("/api/generate", {
        "model": modelo,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperatura},
    })
    return resp["response"].strip()


def descarregar(modelo):
    """Tira o modelo da RAM na hora (o Ollama o manteria carregado por 5 min).
    Com pouca memória, dois modelos carregados juntos podem travar a máquina."""
    try:
        ollama("/api/generate", {"model": modelo, "keep_alive": 0}, timeout=60)
    except (urllib.error.URLError, ConnectionError):
        pass


def descarregar_todos():
    try:
        carregados = [m["name"] for m in ollama("/api/ps", timeout=5).get("models", [])]
    except (urllib.error.URLError, ConnectionError):
        return
    for m in carregados:
        descarregar(m)


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip()


def extrair_letra(resposta):
    # Só letras maiúsculas: "e"/"a" minúsculos são palavras comuns em português.
    padroes = [
        r"^\s*\(?([A-E])\)?[\s.):]*$",                      # "B", "B)", "(B)."
        r"(?i:resposta|alternativa|letra)\W{0,3}([A-E])\b",  # "Resposta: B"
        r"^\s*\(?([A-E])[).:]",                             # "B) Júpiter"
        r"\b([A-E])\)",                                     # "... B) ..."
        r"\b([BCD]|[AE](?!\s+[a-zà-ú]))\b",                 # letra isolada ("A"/"E" + palavra é artigo/conjunção)
    ]
    for p in padroes:
        m = re.search(p, resposta)
        if m:
            return m.group(1).upper()
    return "?"


def corrigir(linha, resposta):
    """Retorna (acertou, resposta_extraida)."""
    if linha["tipo"].strip().lower() == "multipla":
        letra = extrair_letra(resposta)
        return letra == linha["resposta"].strip().upper(), letra
    aceitas = [normalizar(a) for a in linha["resposta"].split("|") if a.strip()]
    r = normalizar(resposta)
    return any(a in r for a in aceitas), resposta[:80]


def montar_prompt(linha):
    if linha["tipo"].strip().lower() == "multipla":
        alternativas = "\n".join(a.strip() for a in linha["alternativas"].split("|"))
        return PROMPT_MULTIPLA.format(pergunta=linha["pergunta"], alternativas=alternativas)
    return PROMPT_ABERTA.format(pergunta=linha["pergunta"])


def url_csv_google_sheets(url):
    """Converte um link do Google Sheets (de edição/compartilhamento) no link de exportação CSV."""
    if "/spreadsheets/d/e/" in url:  # link de "Publicar na Web"
        if "output=csv" in url:
            return url
        base = re.sub(r"/pub(html)?.*$", "", url)
        gid = re.search(r"[#&?]gid=(\d+)", url)
        return base + "/pub?output=csv" + (f"&gid={gid.group(1)}" if gid else "")
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not m or "/export" in url or "output=csv" in url:
        return url
    gid = re.search(r"[#&?]gid=(\d+)", url)
    return (f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv"
            + (f"&gid={gid.group(1)}" if gid else ""))


def fonte_padrao():
    """Usa o link de planilha.txt se houver; senão, o CSV mais recente da pasta perguntas/."""
    try:
        with open(ARQUIVO_PLANILHA, encoding="utf-8") as f:
            for l in f:
                l = l.strip()
                if l and not l.startswith("#"):  # não corta no meio: links têm "#gid="
                    return l
    except FileNotFoundError:
        pass
    pasta = os.path.join(PASTA, "perguntas")
    csvs = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.lower().endswith(".csv")]
    if not csvs:
        sys.exit("Nenhum CSV em perguntas/. Baixe a planilha (Arquivo > Fazer download > .csv) para lá.")
    return os.path.relpath(max(csvs, key=os.path.getmtime))


def ler_csv(fonte):
    if not fonte.startswith(("http://", "https://")):
        with open(fonte, encoding="utf-8") as f:
            return f.read()
    url = url_csv_google_sheets(fonte)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            texto = r.read().decode("utf-8-sig")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            sys.exit("O Google pediu login para acessar a planilha (erro %d).\n"
                     "Ela precisa abrir numa janela anônima. Contas institucionais (ex.: UFLA)\n"
                     "costumam bloquear acesso público, mesmo publicando na web: use uma cópia\n"
                     "num Gmail pessoal com Compartilhar > 'Qualquer pessoa com o link' > Leitor." % e.code)
        sys.exit(f"Não consegui baixar a planilha ({e}).")
    except urllib.error.URLError as e:
        sys.exit(f"Não consegui baixar a planilha ({e}).")
    if texto.lstrip().lower().startswith(("<!doctype", "<html")):
        sys.exit("A planilha não está pública. No Google Sheets: Compartilhar > "
                 "'Qualquer pessoa com o link' > Leitor.")
    return texto


def problemas_da_linha(linha):
    """Lista o que falta numa linha (vazio = linha completa)."""
    faltando = []
    tipo = linha.get("tipo", "").lower()
    if not linha.get("pergunta"):
        faltando.append("pergunta")
    if not linha.get("resposta"):
        faltando.append("resposta")
    if tipo not in ("multipla", "aberta"):
        faltando.append("tipo (multipla/aberta)")
    elif tipo == "multipla" and not re.sub(r"[A-E]\)|\|", "", linha.get("alternativas", "")).strip():
        faltando.append("alternativas")
    return faltando


def carregar_perguntas(arquivo):
    """Lê o CSV (arquivo local ou link do Google Sheets) e ignora linhas incompletas."""
    texto = ler_csv(arquivo)
    linhas = list(csv.DictReader(io.StringIO(texto), skipinitialspace=True))
    validas, ignoradas = [], []
    for num, linha in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        linha = {k: (v or "").strip() for k, v in linha.items() if k}
        faltando = problemas_da_linha(linha)
        if not faltando:
            validas.append(linha)
        elif linha.get("pergunta") or linha.get("resposta"):
            # Só avisa sobre linhas começadas; linhas vazias/modelo são ignoradas em silêncio.
            ignoradas.append(f"linha {num} (id {linha.get('id') or '?'}): falta {', '.join(faltando)}")
    if not validas:
        sys.exit(f"Nenhuma pergunta completa em {arquivo}.")
    print(f"{len(validas)} perguntas carregadas de {arquivo}")
    if ignoradas:
        print(f"{len(ignoradas)} linha(s) incompleta(s) ignorada(s):\n  " + "\n  ".join(ignoradas))
    return validas, texto


def salvar_tabela(saida, res, gabarito, modelos):
    """Tabela organizada: uma linha por pergunta, uma coluna por modelo.
    Retorna a taxa de acerto de cada modelo."""
    total = len(res)
    medias = [sum(res[k][m][0] for k in res) / total for m in modelos]
    with open(saida, "w", newline="", encoding="utf-8-sig") as fout:
        w = csv.writer(fout)
        w.writerow(["id", "repeticao", "gabarito", *modelos, "media_acerto", "resultado_geral"])
        for (pid, rep), por_modelo in res.items():
            acertos = sum(por_modelo[m][0] for m in modelos)
            media = acertos / len(modelos)
            celulas = [f"{extr} ({'acertou' if ok else 'errou'})" for ok, extr in
                       (por_modelo[m] for m in modelos)]
            # Maioria dos modelos acertou = ACERTOU.
            w.writerow([pid, rep, gabarito[pid], *celulas, f"{100 * media:.0f}%",
                        "ACERTOU" if media > 0.5 else "ERROU"])
        geral = sum(medias) / len(medias)
        acertadas = sum(1 for v in res.values()
                        if sum(v[m][0] for m in modelos) / len(modelos) > 0.5)
        w.writerow([])
        w.writerow(["MÉDIA", "", "", *[f"{100 * x:.1f}%" for x in medias], f"{100 * geral:.1f}%",
                    f"{acertadas}/{total} acertadas"])
    return medias


def main():
    ap = argparse.ArgumentParser(description="Avalia LLMs locais em um conjunto de perguntas.")
    ap.add_argument("-m", "--modelos", nargs="+", default=None,
                    help="modelos a avaliar (padrão: os listados em modelos.txt)")
    ap.add_argument("-a", "--arquivo", default=None,
                    help="CSV local ou link do Google Sheets (padrão: link em planilha.txt)")
    ap.add_argument("-r", "--repeticoes", type=int, default=1,
                    help="vezes que cada pergunta é feita (útil com temperatura > 0)")
    ap.add_argument("-t", "--temperatura", type=float, default=0.0)
    args = ap.parse_args()

    args.arquivo = args.arquivo or fonte_padrao()
    perguntas, texto_csv = carregar_perguntas(args.arquivo)
    args.modelos = checar_ollama(args.modelos or modelos_padrao())

    # Apaga os resultados da execução anterior (só depois de validar perguntas e modelos).
    pasta_res = os.path.join(PASTA, "resultados")
    os.makedirs(pasta_res, exist_ok=True)
    for nome in os.listdir(pasta_res):
        if nome != ".gitkeep" and os.path.isfile(os.path.join(pasta_res, nome)):
            os.remove(os.path.join(pasta_res, nome))
    saida = os.path.relpath(os.path.join(pasta_res, "resultado.csv"))
    saida_bruta = os.path.relpath(os.path.join(pasta_res, "respostas_completas.csv"))
    # Cópia exata das perguntas usadas, pois a planilha pode mudar depois.
    with open(os.path.join(pasta_res, "perguntas_usadas.csv"), "w", encoding="utf-8") as f:
        f.write(texto_csv)

    # res[(id, repeticao)][modelo] = (acertou, resposta_extraida)
    res = {(l["id"], rep): {} for l in perguntas for rep in range(1, args.repeticoes + 1)}
    gabarito = {l["id"]: l["resposta"] for l in perguntas}

    with open(saida_bruta, "w", newline="", encoding="utf-8-sig") as fout:
        w = csv.writer(fout)
        w.writerow(["modelo", "id", "repeticao", "gabarito", "resposta", "acertou",
                    "segundos", "resposta_completa"])
        descarregar_todos()
        concluidos = []
        for modelo in args.modelos:
            print(f"\n=== {modelo} ===")
            for linha in perguntas:
                for rep in range(1, args.repeticoes + 1):
                    inicio = time.time()
                    resposta = perguntar(modelo, montar_prompt(linha), args.temperatura)
                    seg = time.time() - inicio
                    ok, extraido = corrigir(linha, resposta)
                    res[(linha["id"], rep)][modelo] = (ok, extraido)
                    w.writerow([modelo, linha["id"], rep, linha["resposta"], extraido,
                                "sim" if ok else "não", f"{seg:.1f}", resposta])
                    fout.flush()
                    print(f"  [{'OK ' if ok else 'ERR'}] #{linha['id']} gabarito={linha['resposta']!r} "
                          f"resposta={extraido!r} ({seg:.1f}s)")
            descarregar(modelo)
            # Salva a tabela a cada modelo: se a execução cair, o que já rodou fica salvo.
            concluidos.append(modelo)
            medias = salvar_tabela(saida, res, gabarito, concluidos)
    geral = sum(medias) / len(medias)

    print("\n=== RESUMO ===")
    for m, x in zip(args.modelos, medias):
        print(f"  {m:<20} {100 * x:.1f}%")
    print(f"  {'média geral':<20} {100 * geral:.1f}%")
    print(f"\nTabela salva em {saida}  (respostas completas em {saida_bruta})")


if __name__ == "__main__":
    main()
