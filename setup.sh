#!/usr/bin/env bash
# Instala o Ollama e baixa o(s) modelo(s) usados na avaliação.
# Uso: ./setup.sh                 -> baixa todos os modelos listados em modelos.txt
#      ./setup.sh gemma3:1b ...   -> baixa só os modelos indicados
set -e
cd "$(dirname "$0")"

MODELOS=("$@")
if [ ${#MODELOS[@]} -eq 0 ]; then
  mapfile -t MODELOS < <(sed 's/#.*//; s/[[:space:]]//g; /^$/d' modelos.txt 2>/dev/null)
  [ ${#MODELOS[@]} -eq 0 ] && MODELOS=("qwen2.5:3b")
fi

# Instalação local (sem sudo) em ~/.local/ollama, se existir
[ -x "$HOME/.local/ollama/bin/ollama" ] && export PATH="$HOME/.local/ollama/bin:$PATH"

if ! command -v ollama >/dev/null 2>&1; then
  echo ">> Instalando Ollama em ~/.local/ollama (sem sudo)..."
  mkdir -p "$HOME/.local/ollama"
  curl -fL https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst \
    | tar --zstd -x -C "$HOME/.local/ollama"
  export PATH="$HOME/.local/ollama/bin:$PATH"
  grep -q '.local/ollama/bin' "$HOME/.bashrc" 2>/dev/null \
    || echo 'export PATH="$HOME/.local/ollama/bin:$PATH"' >> "$HOME/.bashrc"
fi

if ! curl -s http://localhost:11434/api/tags >/dev/null; then
  echo ">> Iniciando o servidor Ollama em segundo plano..."
  nohup ollama serve >/tmp/ollama.log 2>&1 &
  sleep 3
fi

for m in "${MODELOS[@]}"; do
  echo ">> Baixando modelo $m ..."
  ollama pull "$m"
done

echo
echo "Pronto! Rode:  python3 avaliar.py"
