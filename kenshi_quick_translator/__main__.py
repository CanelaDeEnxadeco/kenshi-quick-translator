import sys

from .cli import main

# Sem argumentos (duplo clique), abre a janela.
raise SystemExit(main(sys.argv[1:] or ["gui"]))
