"""Lógica da janela sem Tkinter (testável): velocidade da tradução, imagem do mod e passos do tour."""
from __future__ import annotations

import math
from pathlib import Path

ICON_EXTS = (".png", ".gif", ".jpg", ".jpeg", ".bmp")
ICON_HINTS = ("icon", "preview", "thumb", "logo", "image", "cover")
MAX_ICON_BYTES = 4 * 1024 * 1024  # imagem maior que isso não vira ícone (evita travar a lista)


class RateTracker:
    """
    Guarda a velocidade (textos por minuto) ao longo da tradução, para o gráfico.

    add(agora, feitos) é chamado a cada aviso de progresso. A cada `step` segundos
    sai um ponto novo, calculado numa janela de `window` segundos. Se o contador
    de feitos voltar a zero (outro mod da fila), recomeça a conta sem ponto falso.
    """

    def __init__(self, step: float = 2.0, window: float = 10.0, keep: int = 90) -> None:
        self.step, self.window, self.keep = step, window, keep
        self.points: list[float] = []
        self._samples: list[tuple[float, int]] = []
        self._last_point = 0.0

    def reset(self) -> None:
        self.points.clear()
        self._samples.clear()
        self._last_point = 0.0

    def add(self, now: float, done: int) -> bool:
        """Registra um aviso de progresso; devolve True se saiu um ponto novo no gráfico."""
        if self._samples and done < self._samples[-1][1]:
            self._samples.clear()  # outro mod: a contagem começou de novo
        self._samples.append((now, done))
        self._samples = [s for s in self._samples if now - s[0] <= self.window * 2]
        if self._last_point == 0.0:
            self._last_point = now
            return False
        if now - self._last_point < self.step:
            return False
        old = [s for s in self._samples if now - s[0] >= self.step]
        base = old[-1] if old else self._samples[0]
        # janela: o ponto mais antigo ainda dentro de `window` segundos
        inside = [s for s in self._samples if now - s[0] <= self.window]
        if inside:
            base = inside[0] if inside[0][0] < now else base
        dt = now - base[0]
        if dt <= 0:
            return False
        rate = max(0, done - base[1]) / dt * 60.0
        self._last_point = now
        self.points.append(rate)
        del self.points[: -self.keep]
        return True

    @property
    def current(self) -> float:
        return self.points[-1] if self.points else 0.0

    @property
    def peak(self) -> float:
        return max(self.points) if self.points else 0.0


def sparkline_coords(points: list[float], width: int, height: int, pad: int = 3) -> list[float]:
    """Pontos do gráfico em pixels (x1, y1, x2, y2, ...). Eixo Y de 0 até o pico."""
    if len(points) < 2:
        return []
    top = (max(points) or 1.0) * 1.25  # folga em cima: velocidade constante não fica colada na borda
    n = len(points)
    out: list[float] = []
    for i, v in enumerate(points):
        x = pad + (width - 2 * pad) * i / (n - 1)
        y = height - pad - (height - 2 * pad) * (v / top)
        out += [round(x, 1), round(y, 1)]
    return out


def pick_icon_file(mod_path: str | Path, strict: bool = False) -> Path | None:
    """
    Imagem que acompanha o mod (na mesma pasta). Prefere a que tem o nome do mod,
    depois nomes como icon/preview; se `strict`, só aceita a que tem o nome do mod
    (para arquivos soltos em pastas como Downloads, onde qualquer imagem seria de outra coisa).
    """
    p = Path(mod_path)
    try:
        files = [f for f in p.parent.iterdir() if f.is_file() and f.suffix.lower() in ICON_EXTS]
    except OSError:
        return None
    files = [f for f in files if _size(f) <= MAX_ICON_BYTES]
    stem = p.stem.casefold()
    for f in sorted(files):
        if f.stem.casefold() == stem:
            return f
    if strict:
        return None
    for hint in ICON_HINTS:
        for f in sorted(files):
            if hint in f.stem.casefold():
                return f
    return sorted(files)[0] if files else None


def _size(f: Path) -> int:
    try:
        return f.stat().st_size
    except OSError:
        return MAX_ICON_BYTES + 1


def icon_factor(width: int, height: int, target: int) -> int:
    """Quanto reduzir (Tk só reduz em números inteiros) para a imagem caber em `target` pixels."""
    return max(1, math.ceil(max(width, height, 1) / max(target, 1)))


# Passos do tour da primeira abertura: (alvo, título, texto). Textos em português; a tradução fica em i18n_more.
TOUR_STEPS = (
    ("mods", "1. Escolha o mod",
     "Aqui ficam os mods que o programa achou no Kenshi e no Workshop. Clique em um para abrir. "
     "Ctrl+clique escolhe vários para traduzir em fila. A coluna “Feito” mostra quanto já foi traduzido."),
    ("how", "2. Escolha como traduzir",
     "Diga para qual idioma quer traduzir e qual serviço usar. O agregado, que já vem escolhido, usa vários serviços "
     "gratuitos e troca sozinho quando um bloqueia. Depois clique em “Traduzir este mod”."),
    ("review", "3. Revise e gere o mod",
     "Aqui você confere o resultado. As linhas “Conferir” merecem um olhar. Quando estiver bom, clique em "
     "“Gerar mod de tradução” ou “Instalar no jogo”. O arquivo do mod original não é alterado ao gerar; ao instalar, o original fica guardado como backup."),
    ("help", "Dicas e ajuda",
     "Passe o mouse sobre os campos para ver uma explicação. O botão “Atalhos” mostra as teclas rápidas e "
     "⚙ Configurações muda o idioma do programa, o tema e o tamanho da letra. Este passo a passo pode ser aberto de novo aqui."),
)

# Dicas ao passar o mouse: (parte do texto do widget ou nome do atributo, texto da dica).
TIPS_BY_TEXT = (
    ("Idioma do mod:", "Idioma em que o mod está escrito. “Detectar automaticamente” costuma acertar."),
    ("Traduzir para:", "Idioma para o qual o mod será traduzido. Cada idioma guarda o seu próprio projeto."),
    ("Este mod tem mais de um idioma", "Marque se o mod mistura idiomas (ex.: inglês e chinês). Cada texto é identificado sozinho e traduzido a partir do idioma certo."),
    ("Não traduzir nomes de personagens", "Mantém os nomes próprios como no original, para o jogo e os outros mods continuarem se entendendo."),
    ("Serviço:", "Quem faz a tradução. O agregado junta vários serviços e troca sozinho quando um falha."),
    ("Chave:", "Chave de acesso do serviço escolhido. Com mais de uma, separe com ; e o trabalho é dividido entre elas."),
    ("Servidor:", "Endereço do servidor de tradução (para o LibreTranslate)."),
    ("Testar serviço", "Envia uma frase de teste para ver se o serviço responde."),
    ("Serviços do agregado", "Abre a lista de serviços (IAs, DeepL, Google Cloud…) que trabalham juntos."),
    ("Velocidade:", "Quantos pedidos vão ao serviço ao mesmo tempo. Mais é mais rápido, até o limite do serviço; se ele reclamar, o programa diminui sozinho."),
    ("Traduzir este mod", "Traduz os textos pendentes do mod aberto. O que já foi feito fica salvo."),
    ("Traduzir selecionados", "Traduz em fila todos os mods escolhidos na lista (Ctrl+clique)."),
    ("Parar", "Interrompe a tradução. O que já foi traduzido fica salvo."),
    ("Refazer automáticas", "Traduz de novo o que o programa fez sozinho. O que você revisou não é alterado."),
    ("Instalar no jogo ao terminar", "Na fila, instala cada mod traduzido no Kenshi assim que ficar pronto."),
    ("Mostrar:", "Filtra a tabela: só pendentes, só os para conferir etc."),
    ("Buscar:", "Procura uma palavra no texto original ou na tradução."),
    ("Aplicar e próximo", "Grava a sua edição como revisada e vai para o próximo texto."),
    ("Copiar original", "Copia o texto original para a caixa de tradução (útil para nomes que não devem mudar)."),
    ("Gerar mod de tradução", "Cria o mod traduzido: uma cópia completa do original com os textos traduzidos e o MESMO nome. Não altera o original."),
    ("Instalar no jogo", "Instala o mod traduzido na pasta do Kenshi, no lugar do original (que fica guardado como backup), e garante que ele está no mods.cfg (com backup)."),
    ("Glossário", "Termos que devem sair sempre do mesmo jeito, ou que nunca devem ser traduzidos."),
    ("Exportar PO", "Salva os textos num arquivo PO para editar em outro programa (ex.: Poedit)."),
    ("Importar PO", "Traz de volta as traduções de um arquivo PO editado fora."),
    ("Atualizar", "Lê a pasta do jogo de novo e atualiza a lista de mods."),
    ("Abrir arquivo", "Abre um mod que não está na lista."),
    ("Pasta do Kenshi", "Escolha a pasta onde o Kenshi está instalado, se o programa não a achou."),
    ("Copiar mod para a pasta do jogo", "Copia mods do Workshop para a pasta mods do Kenshi. O Workshop não é alterado."),
    ("Zerar tradução deste mod", "Apaga o progresso salvo do mod escolhido (fica uma cópia de segurança). O mod não é alterado."),
    ("Abrir pasta dos projetos", "Abre a pasta onde o programa guarda o progresso de cada mod."),
)
