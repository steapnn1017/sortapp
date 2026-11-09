"""
app.py – desktopová aplikace SortApp (Tkinter)
==============================================

Grafické rozhraní pro porovnání třídících algoritmů ze souboru sort.py.
Samotné třídění vždy provádějí funkce ze sort.py – tento soubor se stará
jen o okno: přípravu dat, výběr algoritmů, měření, výsledky a animaci.

Jak spustit (ve složce projektu):

    python3 app.py

Na macOS s Pythonem z Homebrew je potřeba jednou doinstalovat Tk:

    brew install python-tk@3.14

JAK JE SOUBOR USPOŘÁDANÝ (shora dolů):

    1. Vzhled          – barvy (BARVY, TONY) a písma (PISMO).
    2. Popis algoritmů – texty do rozhraní (název, štítky, vysvětlení).
                         Kód algoritmů je v sort.py, tady je jen „cedulka“.
    3. Data            – generování náhodných dat, rozpoznání typu dat
                         ze souboru / ručního vstupu (celá a desetinná
                         čísla, data, text) a převod hodnot na text.
    4. Stavební prvky  – vlastní tlačítko, karta, zaškrtávací karta
                         algoritmu, záložky, seznam hodnot, posuvník.
    5. Modální okna    – Dialog (společný základ), OknoKontroly (co se
                         načetlo ze souboru a jestli to třídit) a
                         OknoAnimace (přehrává kroky třídění).
    6. SortApp         – hlavní okno: skládá prvky dohromady a obsluhuje
                         tlačítka (generuj, porovnej, animuj, export …).
    7. main()          – vytvoří okno a spustí aplikaci.

ZÁKLADNÍ POJMY TKINTERU, KTERÉ SE V SOUBORU OPAKUJÍ:

  * Widget       – prvek okna (tk.Label = text, tk.Frame = obdélníkový
                   kontejner, tk.Canvas = plátno na kreslení, tk.Text =
                   víceřádkový text). Každý widget má RODIČE, do kterého
                   patří – tak vzniká strom okna.
  * pack / grid  – správci rozložení. pack() skládá prvky za sebe
                   (nahoru/dolů nebo vlevo/vpravo), grid() je rozmisťuje
                   do mřížky řádků a sloupců.
  * bind         – navázání funkce na událost (klik myší, klávesa, změna
                   velikosti …). Funkce dostane objekt události `e`.
  * after(ms, f) – naplánuje zavolání funkce f za ms milisekund. Tkinter
                   běží v jedné smyčce (mainloop), takže pravidelné
                   opakování (animace, čtení fronty) se dělá právě přes
                   after(), ne přes nekonečný cyklus, který by okno zamrazil.
"""

import csv              # zápis výsledků do CSV (Export CSV)
import datetime         # práce s daty (typ hodnot „Data“)
import math             # logaritmus pro délku pruhů, kontrola NaN/nekonečna
import queue            # bezpečná fronta zpráv mezi vláknem a oknem
import random           # generátor náhodných dat (se seedem)
import re               # regulární výrazy – rozdělení vstupního textu
import statistics       # medián z naměřených časů
import threading        # měření běží ve vedlejším vlákně, aby okno nezamrzlo
import time             # přesné měření času (perf_counter)
import tkinter as tk                # základní widgety Tkinteru
import tkinter.font as tkfont       # zjištění dostupných písem a šířky znaků
from tkinter import filedialog, messagebox, ttk   # výběr souboru, chybové okno, „hezčí“ widgety ttk

import sort             # NAŠE algoritmy – bubble_sort, quick_sort … (soubor sort.py)

# ---------------------------------------------------------------------------
# 1) Vzhled – stejné barvy jako ve webové verzi (teplá světlá paleta)
# ---------------------------------------------------------------------------
# Všechny barvy jsou na jednom místě ve slovníku. Když chceme změnit vzhled,
# stačí upravit hodnotu tady a změní se všude, kde se BARVY["…"] používá.

BARVY = {
    "bg": "#F7F6F3",          # pozadí okna
    "surface": "#FFFFFF",     # karty
    "surface2": "#FBFBFA",    # vnitřní plochy (seznamy hodnot, graf)
    "sunken": "#F2F1EE",      # zapuštěné prvky (záložky, čipy)
    "border": "#EAEAEA",      # jemný rámeček karet
    "border_strong": "#DCDAD4",  # výraznější rámeček (políčka formuláře)
    "text": "#1F1F1E",        # hlavní text
    "text2": "#57564F",       # vedlejší text (popisky)
    "text3": "#787774",       # nejméně důležitý text (nápovědy)
    "ink": "#111111",         # primární tlačítka
    "ink_hover": "#2E2E2C",   # primární tlačítko pod myší
    "ink_disabled": "#C9C7C1",  # vypnuté primární tlačítko
    "focus": "#1F6C9F",       # rámeček prvku, který má fokus klávesnice
    "red_bg": "#FDEBEC", "red": "#9F2F2D",        # štítky: pomalé / chyba
    "blue_bg": "#E1F3FE", "blue": "#1F6C9F",      # štítky: informace / běží
    "green_bg": "#EDF3EC", "green": "#346538",    # štítky: rychlé / ověřeno
    "yellow_bg": "#FBF3DB", "yellow": "#956400",  # štítky: varování / nejrychlejší
    "bar": "#D6D3CC",         # sloupec v animaci
    "bar_active": "#E0822E",  # právě porovnávané prvky
    "bar_done": "#5A9467",    # prvky na konečném místě
}

# Dvojice (pozadí, text) pro štítky a odznaky.
# Klíč je „tón“ štítku – např. stitek(..., "ok") použije zelené pozadí
# a zelený text. Hodnoty jsou názvy barev ze slovníku BARVY.
TONY = {
    "slow": ("red_bg", "red"), "err": ("red_bg", "red"),
    "fast": ("green_bg", "green"), "ok": ("green_bg", "green"),
    "info": ("blue_bg", "blue"), "run": ("blue_bg", "blue"),
    "warn": ("yellow_bg", "yellow"), "best": ("yellow_bg", "yellow"),
    "wait": ("sunken", "text3"),
}

PISMO = {}   # naplní se v priprav_pisma(), až existuje okno Tk


def priprav_pisma(root):
    """Vybere první dostupné písmo z každé skupiny a připraví velikosti.

    Písma se dají zjistit až ve chvíli, kdy existuje okno Tk (root), proto
    se slovník PISMO plní až tady, a ne hned při načtení souboru.
    Každá položka je n-tice (název písma, velikost[, styl]), kterou Tkinter
    přijímá v parametru font=.
    """
    dostupna = set(tkfont.families(root))      # všechna písma nainstalovaná v systému

    def prvni(*kandidati):
        # Vrátí první písmo ze seznamu, které v systému opravdu je.
        # next(...) vezme první prvek z generátoru; když žádný není,
        # použije se náhradní "TkDefaultFont" (výchozí písmo Tkinteru).
        return next((k for k in kandidati if k in dostupna), "TkDefaultFont")

    sans = prvni("Geist", "Inter", "Helvetica Neue")        # běžný text
    mono = prvni("Geist Mono", "SF Mono", "Menlo")          # čísla, kód (stejně široké znaky)
    serif = prvni("Instrument Serif", "New York", "Georgia")  # velké nadpisy
    PISMO.update({
        "body": (sans, 13), "small": (sans, 12), "tiny": (sans, 11),
        "bold": (sans, 13, "bold"), "card_title": (sans, 17, "bold"),
        "brand": (sans, 14, "bold"),
        "mono": (mono, 12), "mono_small": (mono, 11),
        "hero": (serif, 40), "hero_italic": (serif, 40, "italic"),
        "dialog_title": (serif, 30),
    })


# ---------------------------------------------------------------------------
# 2) Popis algoritmů pro rozhraní (implementace je v sort.py)
# ---------------------------------------------------------------------------
# Každý slovník popisuje jeden algoritmus:
#   "klic"       – stejný klíč jako ve slovníku sort.ALGORITMY; podle něj
#                  aplikace najde správnou funkci ze sort.py
#   "nazev"      – název zobrazený v okně
#   "kratce"     – jednořádkový popis na kartě algoritmu
#   "stitky"     – barevné štítky (text, tón z TONY): složitost a stabilita
#   "vysvetleni" – delší vysvětlení principu, zobrazí se v okně animace

ALGORITMY_INFO = [
    {"klic": "bubble", "nazev": "Bubble sort",
     "kratce": "Prohazuje sousedy, největší prvek „probublá“ na konec.",
     "stitky": [("O(n²)", "slow"), ("stabilní", "info")],
     "vysvetleni": "Porovnává sousední prvky a vymění je, pokud jsou ve špatném "
                   "pořadí. Po každém průchodu „probublá“ největší zbývající prvek "
                   "na konec. Průchody se opakují, dokud je potřeba nějaká výměna."},
    {"klic": "selection", "nazev": "Selection sort",
     "kratce": "Najde minimum a přesune ho na začátek neseřazené části.",
     "stitky": [("O(n²)", "slow"), ("nestabilní", "warn")],
     "vysvetleni": "V neseřazené části pole vždy najde nejmenší prvek a prohodí ho "
                   "na začátek této části. Seřazená část se tak po každém průchodu "
                   "prodlouží o jeden prvek."},
    {"klic": "insertion", "nazev": "Insertion sort",
     "kratce": "Bere prvky jeden po druhém a vkládá je na správné místo vlevo.",
     "stitky": [("O(n²)", "slow"), ("stabilní", "info")],
     "vysvetleni": "Funguje jako řazení karet v ruce: vezme další prvek (klíč), větší "
                   "prvky v seřazené části posune o jedno doprava a klíč vloží do "
                   "vzniklé mezery. Na téměř seřazených datech je velmi rychlý."},
    {"klic": "merge", "nazev": "Merge sort",
     "kratce": "Rozdělí pole na poloviny a seřazené úseky slévá.",
     "stitky": [("O(n log n)", "fast"), ("stabilní", "info")],
     "vysvetleni": "Rozděl a panuj: pole rekurzivně půlí až na jednotlivé prvky a pak "
                   "dvojice seřazených úseků slévá (merguje) do většího seřazeného celku."},
    {"klic": "quick", "nazev": "Quick sort",
     "kratce": "Rozdělí úsek kolem náhodného pivota a opakuje.",
     "stitky": [("O(n log n)", "fast"), ("nestabilní", "warn")],
     "vysvetleni": "Vybere náhodný pivot, přeskládá úsek tak, aby menší prvky byly "
                   "vlevo a větší vpravo (pivot je pak na své konečné pozici), a totéž "
                   "rekurzivně opakuje pro obě části."},
    {"klic": "heap", "nazev": "Heap sort",
     "kratce": "Postaví z pole max-haldu a maximum opakovaně přesouvá na konec.",
     "stitky": [("O(n log n)", "fast"), ("nestabilní", "warn")],
     "vysvetleni": "Nejprve přeskládá pole na max-haldu (každý rodič je větší než jeho "
                   "potomci, maximum je na první pozici). Pak maximum prohodí s posledním "
                   "prvkem haldy, haldu zmenší a nový kořen „probublá“ dolů. Opakuje, "
                   "dokud halda nezmizí."},
]
# Stejná data jako slovník podle klíče: INFO["quick"] -> popis quick sortu.
# Hodí se tam, kde máme jen klíč a potřebujeme název nebo vysvětlení.
INFO = {a["klic"]: a for a in ALGORITMY_INFO}

MAX_PRVKU = 3000      # víc prvků by pomalé O(n²) algoritmy měřily příliš dlouho
MAX_ANIMACE = 100     # animace s víc sloupci by byla nečitelná

# Možnosti rozbalovacích seznamů: (vnitřní klíč, text zobrazený uživateli).
# Program pracuje s klíčem, uživatel vidí český text.
TYPY = [("auto", "Automaticky"), ("integer", "Celá čísla"),
        ("float", "Desetinná čísla"), ("date", "Data (RRRR-MM-DD)")]
ROZLOZENI = [("random", "Náhodně"), ("ascending", "Vzestupně – nejlepší případ"),
             ("descending", "Sestupně – nejhorší případ"),
             ("nearly", "Skoro seřazeno"), ("duplicates", "Mnoho duplicit")]


# ---------------------------------------------------------------------------
# 3) Data: generování, načtení a formátování
# ---------------------------------------------------------------------------
# Data (datumy) ukládáme jako celé číslo – pořadové číslo dne
# (date.toordinal()). Algoritmy tak vždy třídí obyčejná čísla a datum
# se z čísla vytvoří až při zobrazení.
# Příklad: 1. 1. 2016 -> 735964, 2. 1. 2016 -> 735965. Pozdější datum má
# vždy větší číslo, takže seřazení čísel = seřazení dat.

DATUM_OD = datetime.date(2016, 1, 1).toordinal()   # nejstarší generované datum
DATUM_DO = datetime.date(2026, 1, 1).toordinal()   # hranice (už se negeneruje)


def jedna_hodnota(typ, rng):
    """Vygeneruje jednu náhodnou hodnotu daného typu.

    rng je vlastní generátor random.Random(seed) – díky němu stejný seed
    vytvoří vždy stejnou posloupnost čísel (měření jde zopakovat).
    """
    if typ == "float":
        return round(rng.random() * 1000, 2)       # 0.00 až 999.99
    if typ == "date":
        return rng.randrange(DATUM_OD, DATUM_DO)   # pořadové číslo dne 2016–2025
    return rng.randrange(1_000_000)                # celé číslo 0 až 999 999


def generuj_hodnoty(typ, pocet, seed, rozlozeni):
    """Vytvoří `pocet` hodnot; stejný seed dá vždy stejná data.

    rozlozeni určuje, jak budou data na začátku uspořádaná – tím se dá
    vyzkoušet nejlepší a nejhorší případ jednotlivých algoritmů.
    """
    rng = random.Random(seed)
    if rozlozeni == "duplicates":
        # malá zásoba hodnot, ze které se losuje -> hodně opakování
        # (zásoba má pocet // 15 hodnot, ale nejméně 5)
        zasoba = [jedna_hodnota(typ, rng) for _ in range(max(5, pocet // 15))]
        hodnoty = [rng.choice(zasoba) for _ in range(pocet)]
    else:
        hodnoty = [jedna_hodnota(typ, rng) for _ in range(pocet)]

    # Přednastavené pořadí jen připravuje vstup (nejlepší / nejhorší případ),
    # porovnávané třídění pak probíhá v sort.py.
    # Vestavěné .sort() tu NENÍ porovnávaný algoritmus – jen vyrábí vstup.
    if rozlozeni == "ascending":
        hodnoty.sort()                     # už seřazená data (nejlepší případ)
    elif rozlozeni == "descending":
        hodnoty.sort(reverse=True)         # obráceně seřazená data (nejhorší případ)
    elif rozlozeni == "nearly":
        hodnoty.sort()
        for _ in range(max(1, pocet // 50)):          # prohodí ~2 % dvojic
            i, j = rng.randrange(pocet), rng.randrange(pocet)
            hodnoty[i], hodnoty[j] = hodnoty[j], hodnoty[i]
    return hodnoty


# Vzory (regulární výrazy), podle kterých se pozná typ jedné hodnoty.
# [0-9] = jedna číslice, + = jednou nebo víckrát, * = nula nebo víckrát,
# ? = nepovinné, [+-] = znaménko, [.,] = desetinná tečka nebo česká čárka.
CELE_CISLO = re.compile(r"[+-]?[0-9]+")                  # 42, -7, +3
DESETINNE_CISLO = re.compile(r"[+-]?[0-9]*[.,]?[0-9]+")  # 3.14, -0,5, .5 (i celé číslo)
DATUM = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")        # 2024-03-15

# Věta pro uživatele: PROČ aplikace zvolila daný typ (okno kontroly souboru)
PROC_TYP = {
    "integer": "Všechny hodnoty jsou celá čísla.",
    "float": "Všechny hodnoty jsou čísla a aspoň jedno má desetinnou část.",
    "date": "Všechny hodnoty jsou data ve tvaru RRRR-MM-DD.",
    "text": "Hodnoty nejsou jen čísla ani data, budou se proto řadit abecedně jako text.",
}

# Text se řadí podle české abecedy: č je až za c, ř za r, š za s, ž za z.
# Znak "￿" je větší než všechna písmena, takže "c￿" (= č) se
# zařadí za všechna slova na c, ale pořád před d. Čárky a kroužky
# (á, é, ů …) pořadí nemění – á se řadí jako a. Spřežku ch pro
# jednoduchost řadíme jako c + h.
CESKA_ABECEDA = str.maketrans({
    "á": "a", "č": "c￿", "ď": "d", "é": "e", "ě": "e", "í": "i", "ň": "n",
    "ó": "o", "ř": "r￿", "š": "s￿", "ť": "t", "ú": "u", "ů": "u",
    "ý": "y", "ž": "z￿",
})


def text_na_hodnotu(t):
    """Text uložíme jako dvojici (klíč pro řazení, původní text).

    Podobně jako u dat: algoritmy porovnávají dvojice a Python dvojice
    porovná nejdřív podle prvního prvku – klíče. Klíč je malými písmeny
    a upravený podle české abecedy, takže "Adam" i "adam" stojí vedle
    sebe a "čaj" je až za "cukr". Při stejném klíči rozhodne původní text.
    Zobrazuje se vždy jen původní text (druhý prvek dvojice).
    """
    return (t.casefold().translate(CESKA_ABECEDA), t)   # "Čaj" -> ("c￿aj", "Čaj")


def rozpoznej_hodnoty(text):
    """Zjistí, jaký typ dat text obsahuje (soubor i ruční vstup), a převede
    ho na hodnoty. Vrátí (typ, hodnoty, upozorneni) – upozorneni je ""
    nebo věta pro uživatele. Při chybě vyhodí ValueError s českou zprávou.

    Typ se určí podle toho, čemu odpovídají VŠECHNY hodnoty:
      1. všechny jsou data RRRR-MM-DD  -> "date"
      2. všechny jsou celá čísla       -> "integer"
      3. všechny jsou čísla            -> "float"
      4. cokoli jiného                 -> "text"

    Čísla a data se oddělují mezerou, středníkem nebo novým řádkem.
    Text jen středníkem nebo novým řádkem, protože i jedna hodnota
    může obsahovat mezeru (např. „Jan Novák“).
    """
    # [\s;]+ = jedna nebo víc mezer/tabulátorů/nových řádků nebo středníků.
    # Podmínka `if t` vyhodí prázdné řetězce (např. na začátku textu).
    tokeny = [t for t in re.split(r"[\s;]+", text) if t]
    if not tokeny:
        raise ValueError("Nebyly nalezeny žádné hodnoty.")

    upozorneni = ""
    if all(DATUM.fullmatch(t) for t in tokeny):
        try:
            # Data ukládáme jako pořadové číslo dne (viz začátek této části)
            typ, hodnoty = "date", [datetime.date.fromisoformat(t).toordinal() for t in tokeny]
        except ValueError:
            # tvar sedí, ale datum neexistuje (např. 2024-02-31)
            raise ValueError("Vstup obsahuje neplatné datum.") from None
    elif all(CELE_CISLO.fullmatch(t) for t in tokeny):
        typ, hodnoty = "integer", [int(t) for t in tokeny]                      # "42" -> 42
    elif all(DESETINNE_CISLO.fullmatch(t) for t in tokeny):
        # float() zná jen desetinnou tečku, českou čárku proto nejdřív nahradíme
        typ, hodnoty = "float", [float(t.replace(",", ".")) for t in tokeny]    # "3,5" -> 3.5
    else:
        typ = "text"
        # [\n;] = nový řádek nebo středník; strip() ořízne mezery na krajích
        hodnoty = [text_na_hodnotu(t.strip()) for t in re.split(r"[\n;]", text) if t.strip()]
        # Jsou-li mezi hodnotami i čísla nebo data, uživatele upozorníme:
        # text se řadí znak po znaku, takže čísla vyjdou jinak, než čeká.
        if any(DESETINNE_CISLO.fullmatch(t) or DATUM.fullmatch(t) for t in tokeny):
            upozorneni = ("Mezi hodnotami jsou čísla nebo data i text. Vše se proto bude "
                          "řadit jako text, znak po znaku – např. 10 bude před 9.")
    if len(hodnoty) > MAX_PRVKU:
        raise ValueError(f"Hodnot je {cesky_pocet(len(hodnoty))}, maximum je 3 000.")
    return typ, hodnoty, upozorneni


def formatuj_hodnotu(v, typ):
    """Převede uloženou hodnotu na text pro zobrazení v okně."""
    if typ == "date":
        return datetime.date.fromordinal(v).isoformat()   # 735964 -> "2016-01-01"
    if typ == "text":
        return v[1]                                        # (klíč, "Čaj") -> "Čaj"
    # Čísla: str() vypíše přesně to, co je uložené (12.125 -> "12.125"),
    # takže uživatel při kontrole souboru vidí všechna desetinná místa.
    return str(v)


def formatuj_ms(v):
    """Čas v milisekundách jako text: méně desetinných míst u větších čísel.

    0.4567 -> "0,46 ms", 45.67 -> "45,7 ms", 456.7 -> "457 ms".
    Desetinná tečka se mění na českou čárku.
    """
    text = f"{v:.2f}" if v < 10 else f"{v:.1f}" if v < 100 else f"{v:.0f}"
    return text.replace(".", ",") + " ms"


def cesky_pocet(n):
    """Číslo s mezerou mezi tisíci, jak se píše česky: 3000 -> "3 000"."""
    return f"{n:,}".replace(",", " ")      # 3 000 s pevnou mezerou (nezalomí se na konci řádku)


def popis_typu(typ):
    """Krátký český popis typu dat pro informační čip."""
    return {"date": "data", "float": "desetinná čísla", "text": "text"}.get(typ, "celá čísla")


# ---------------------------------------------------------------------------
# 4) Malé stavební prvky rozhraní
# ---------------------------------------------------------------------------
# Tkinter má jen základní widgety a na macOS je nejde dobře obarvit.
# Proto si tu skládáme vlastní prvky z jednodušších (Frame + Label + Canvas).

def zaobleny_obdelnik(canvas, x1, y1, x2, y2, r, **kw):
    """Nakreslí na plátno obdélník se zaoblenými rohy.

    Tkinter zaoblený obdélník nemá. Trik: nakreslíme mnohoúhelník
    (polygon) přes body kolem obdélníku a zapneme smooth=True – Tkinter
    pak hrany proloží křivkou a rohy se zakulatí. r je poloměr rohu.
    **kw předá další parametry (fill = výplň, outline = obrys).
    """
    body = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(body, smooth=True, **kw)


def animuj(widget, trvani_ms, krok):
    """Plynulá animace: volá krok(t) pro t od 0 do 1 s náběhem ease-out.

    Každých 16 ms (≈ 60 snímků za sekundu) spočítá, jaká část času už
    uplynula (t od 0 do 1), a zavolá krok(t). Funkce krok podle t něco
    překreslí – např. prodlouží pruh v tabulce výsledků.
    Ease-out = pohyb začne rychle a na konci zpomalí, působí přirozeněji.
    """
    start = time.perf_counter()

    def tik():
        if not widget.winfo_exists():       # widget mezitím zmizel -> konec
            return
        t = min(1.0, (time.perf_counter() - start) * 1000 / trvani_ms)
        krok(1 - (1 - t) ** 3)           # ease-out cubic
        if t < 1:
            widget.after(16, tik)           # naplánuje další snímek
    tik()


def stitek(rodic, text, ton, pismo="tiny"):
    """Barevný štítek (O(n²), stabilní, Ověřeno …).

    ton je klíč ze slovníku TONY a určuje barvu pozadí i textu.
    """
    bg, fg = TONY[ton]
    return tk.Label(rodic, text=text, bg=BARVY[bg], fg=BARVY[fg],
                    font=PISMO[pismo], padx=7, pady=1)


def cip(rodic, text):
    """Neutrální informační čip (počet hodnot, typ, zdroj …)."""
    return tk.Label(rodic, text=text, bg=BARVY["sunken"], fg=BARVY["text2"],
                    font=PISMO["small"], padx=9, pady=3)


class Tlacitko(tk.Frame):
    """Vlastní tlačítko – macOS nedovolí obarvit klasický tk.Button.

    varianta: "primary" (černé), "secondary" (bílé s rámečkem), "ghost" (bez rámečku)
    Rámeček tvoří vnější Frame (1 px kolem popisku). Ovládá se myší
    i klávesnicí (Tab + mezerník/Enter), fokus je vidět jako modrý rámeček.

    Jak to funguje: tlačítko je Frame (rámeček) a uvnitř Label (text).
    Label je o 1 px menší, takže z Framu kolem něj zbude proužek –
    to je viditelný rámeček. Barvu Framu i Labelu měníme podle stavu
    (pod myší, má fokus, vypnuté).
    """

    def __init__(self, rodic, text, prikaz, varianta="secondary", padx=16, pady=7):
        super().__init__(rodic, takefocus=1)     # takefocus=1 -> jde na něj skočit Tabem
        self.prikaz = prikaz          # funkce, která se zavolá po kliknutí
        self.varianta = varianta
        self.povoleno = True          # vypnuté tlačítko na klik nereaguje
        self.pod_mysi = False         # je nad tlačítkem kurzor? (hover)
        self.fokus = False            # má tlačítko fokus klávesnice?
        pozadi = rodic.cget("bg")     # barva rodiče – pro "ghost" tlačítko bez rámečku
        # Sada barev pro každou variantu:
        #   bg/fg = pozadí/text, hover = pozadí pod myší, ram = barva rámečku,
        #   off_… = barvy vypnutého tlačítka.
        # Na konci [varianta] vybere jen tu sadu, kterou tlačítko potřebuje.
        self.barvy = {
            "primary": dict(bg=BARVY["ink"], fg="#FFFFFF", hover=BARVY["ink_hover"],
                            ram=BARVY["ink"], off_bg=BARVY["ink_disabled"], off_fg="#FFFFFF",
                            off_ram=BARVY["ink_disabled"]),
            "secondary": dict(bg=BARVY["surface"], fg=BARVY["text"], hover=BARVY["sunken"],
                              ram=BARVY["border_strong"], off_bg=BARVY["surface"],
                              off_fg=BARVY["text3"], off_ram=BARVY["border"]),
            "ghost": dict(bg=pozadi, fg=BARVY["text2"], hover=BARVY["sunken"], ram=pozadi,
                          off_bg=pozadi, off_fg=BARVY["border_strong"], off_ram=pozadi),
        }[varianta]
        self.lbl = tk.Label(self, text=text, padx=padx, pady=pady,
                            font=PISMO["bold" if varianta == "primary" else "body"])
        self.lbl.pack(padx=1, pady=1)          # 1 px okolo = rámeček
        # Události myši navážeme na Frame i na Label, protože kurzor může
        # být nad kterýmkoli z nich.
        for w in (self, self.lbl):
            w.bind("<Enter>", lambda e: self._mys(True))      # kurzor vjel dovnitř
            w.bind("<Leave>", lambda e: self._mys(False))     # kurzor odjel
            w.bind("<ButtonRelease-1>", self._klik)           # puštění levého tlačítka myši
        self.bind("<Return>", self._klavesa)                  # Enter
        self.bind("<space>", self._klavesa)                   # mezerník
        self.bind("<FocusIn>", lambda e: self._zmena_fokusu(True))
        self.bind("<FocusOut>", lambda e: self._zmena_fokusu(False))
        self._prekresli()

    def _prekresli(self):
        """Nastaví barvy podle aktuálního stavu (povoleno, pod myší, fokus)."""
        b = self.barvy
        if self.povoleno:
            bg = b["hover"] if self.pod_mysi else b["bg"]
            ram = BARVY["focus"] if self.fokus else b["ram"]   # modrý rámeček při fokusu
            self.lbl.config(bg=bg, fg=b["fg"], cursor="pointinghand")
        else:
            ram = b["off_ram"]
            self.lbl.config(bg=b["off_bg"], fg=b["off_fg"], cursor="arrow")
        self.config(bg=ram)          # barva Framu = barva rámečku

    def _mys(self, uvnitr):
        self.pod_mysi = uvnitr
        self._prekresli()

    def _zmena_fokusu(self, ma_fokus):
        self.fokus = ma_fokus
        self._prekresli()

    def _klik(self, e):
        # akce jen když uživatel tlačítko pustí nad ním (jako u nativních tlačítek)
        # e.x_root/e.y_root = poloha myši na obrazovce; odečteme polohu
        # tlačítka a zjistíme, jestli je myš pořád uvnitř jeho obdélníku.
        x = e.x_root - self.winfo_rootx()
        y = e.y_root - self.winfo_rooty()
        if self.povoleno and 0 <= x < self.winfo_width() and 0 <= y < self.winfo_height():
            self.prikaz()

    def _klavesa(self, e):
        if self.povoleno:
            self.prikaz()
        return "break"          # mezerník už nepropadne do zkratek okna

    def nastav(self, povoleno=None, text=None):
        """Zapne/vypne tlačítko nebo změní jeho text (None = neměnit)."""
        if povoleno is not None:
            self.povoleno = povoleno
            self.config(takefocus=1 if povoleno else 0)   # vypnuté se Tabem přeskočí
        if text is not None:
            self.lbl.config(text=text)
        self._prekresli()


class Karta(tk.Frame):
    """Bílá karta s číslem kroku, nadpisem a popisem (01 Data, 02 Algoritmy …).

    Obsah karty se vkládá do self.obsah (vnitřní Frame s okraji),
    hlavička je v self.hlavicka – tam se dají přidat další prvky vpravo
    (např. záložky u karty Výsledky).
    """

    def __init__(self, rodic, cislo, nadpis, popis):
        # highlightthickness=1 + highlightbackground = tenký šedý rámeček karty
        super().__init__(rodic, bg=BARVY["surface"], highlightthickness=1,
                         highlightbackground=BARVY["border"])
        self.obsah = tk.Frame(self, bg=BARVY["surface"])
        self.obsah.pack(fill="both", expand=True, padx=24, pady=22)
        self.hlavicka = tk.Frame(self.obsah, bg=BARVY["surface"])
        self.hlavicka.pack(fill="x")
        tk.Label(self.hlavicka, text=cislo, font=PISMO["mono_small"], fg=BARVY["text3"],
                 bg=BARVY["surface"]).pack(side="left", padx=(0, 10))
        tk.Label(self.hlavicka, text=nadpis, font=PISMO["card_title"], fg=BARVY["text"],
                 bg=BARVY["surface"]).pack(side="left")
        self.popis = tk.Label(self.obsah, text=popis, font=PISMO["body"], fg=BARVY["text2"],
                              bg=BARVY["surface"], anchor="w", justify="left")
        self.popis.pack(fill="x", pady=(4, 16))


class AlgoKarta(tk.Frame):
    """Zaškrtávací karta jednoho algoritmu.

    Kliknutím kamkoli na kartu se algoritmus vybere / zruší. Vybraná karta
    má černý rámeček a zaškrtnuté políčko vpravo nahoře.
    pri_zmene je funkce hlavního okna, která po změně výběru zapne
    nebo vypne tlačítka Porovnat a Animovat.
    """

    def __init__(self, rodic, info, pri_zmene):
        super().__init__(rodic, bg=BARVY["surface"], highlightthickness=1,
                         highlightbackground=BARVY["border"], cursor="pointinghand",
                         takefocus=1, highlightcolor=BARVY["focus"])
        self.klic = info["klic"]      # např. "bubble" – podle něj se volá sort.ALGORITMY
        self.vybrano = False
        self.pri_zmene = pri_zmene
        vnitrek = tk.Frame(self, bg=BARVY["surface"])
        vnitrek.pack(fill="both", expand=True, padx=14, pady=12)

        # Horní řádek: název vlevo, zaškrtávací políčko vpravo
        horni = tk.Frame(vnitrek, bg=BARVY["surface"])
        horni.pack(fill="x")
        tk.Label(horni, text=info["nazev"], font=PISMO["bold"], fg=BARVY["text"],
                 bg=BARVY["surface"]).pack(side="left")
        # Zaškrtávací políčko kreslíme sami na malé plátno 18×18 px
        self.check = tk.Canvas(horni, width=18, height=18, bg=BARVY["surface"],
                               highlightthickness=0)
        self.check.pack(side="right")

        self.popis = tk.Label(vnitrek, text=info["kratce"], font=PISMO["small"],
                              fg=BARVY["text2"], bg=BARVY["surface"], justify="left",
                              anchor="w", wraplength=220)
        self.popis.pack(fill="x", pady=(4, 8))
        # Spodní řádek: štítky se složitostí a stabilitou
        radek = tk.Frame(vnitrek, bg=BARVY["surface"])
        radek.pack(fill="x")
        for text, ton in info["stitky"]:
            stitek(radek, text, ton).pack(side="left", padx=(0, 6))

        # kliknout jde kamkoli na kartu, i na její popisky
        # (proto se události navážou na kartu i na všechny vnořené widgety)
        for w in self._vsechny(self):
            w.bind("<Button-1>", lambda e: self.prepni())
            w.bind("<Enter>", lambda e: self._hover(True))
            w.bind("<Leave>", lambda e: self._hover(False))
        # Mezerník přepne výběr; "break" zastaví další zpracování klávesy.
        # Zápis (akce, "break")[1] provede akci a vrátí "break" v jednom výrazu.
        self.bind("<space>", lambda e: (self.prepni(), "break")[1])
        # Když se změní šířka karty, popis se zalomí podle nové šířky
        self.bind("<Configure>", lambda e: self.popis.config(wraplength=max(120, e.width - 32)))
        self._prekresli()

    def _vsechny(self, w):
        """Projde widget a rekurzivně všechny jeho potomky (generátor)."""
        yield w
        for dite in w.winfo_children():
            yield from self._vsechny(dite)

    def _hover(self, uvnitr):
        # Nevybraná karta pod myší dostane o něco tmavší rámeček
        if not self.vybrano:
            self.config(highlightbackground=BARVY["border_strong" if uvnitr else "border"])

    def prepni(self):
        """Obrátí výběr karty a dá vědět hlavnímu oknu."""
        self.nastav(not self.vybrano)
        self.focus_set()
        self.pri_zmene()

    def nastav(self, vybrano):
        """Nastaví výběr bez volání pri_zmene (používá „Vybrat vše“)."""
        self.vybrano = vybrano
        self._prekresli()

    def _prekresli(self):
        """Překreslí zaškrtávací políčko a rámeček podle self.vybrano."""
        c = self.check
        c.delete("all")               # smaže vše, co bylo na plátně dřív
        if self.vybrano:
            self.config(highlightbackground=BARVY["ink"])
            zaobleny_obdelnik(c, 1, 1, 17, 17, 5, fill=BARVY["ink"], outline=BARVY["ink"])
            # fajfka = lomená čára přes tři body
            c.create_line(5, 9.5, 8, 12.5, 13.5, 6, fill="#FFFFFF", width=2,
                          capstyle="round", joinstyle="round")
        else:
            self.config(highlightbackground=BARVY["border"])
            zaobleny_obdelnik(c, 1, 1, 17, 17, 5, fill=BARVY["surface"],
                              outline=BARVY["border_strong"])


class Zalozky(tk.Frame):
    """Segmentový přepínač záložek (Časy / Vstup / Seřazeno).

    Každá záložka je Label. Vybraná má bílé pozadí, ostatní šedé.
    pri_zmene(index) přepne v hlavním okně zobrazený panel.
    """

    def __init__(self, rodic, nazvy, pri_zmene):
        super().__init__(rodic, bg=BARVY["sunken"], padx=3, pady=3)
        self.pri_zmene = pri_zmene
        self.polozky = []
        for i, nazev in enumerate(nazvy):
            lbl = tk.Label(self, text=nazev, font=PISMO["small"], padx=14, pady=4,
                           cursor="pointinghand", takefocus=1,
                           highlightthickness=1, highlightcolor=BARVY["focus"])
            lbl.pack(side="left")
            # i=i „zamrazí“ aktuální hodnotu i do lambdy – bez toho by
            # všechny záložky po kliknutí poslaly poslední hodnotu i.
            lbl.bind("<Button-1>", lambda e, i=i: self.vyber(i))
            lbl.bind("<space>", lambda e, i=i: (self.vyber(i), "break")[1])
            self.polozky.append(lbl)
        self.vyber(0)

    def vyber(self, index):
        """Zvýrazní záložku s daným indexem a přepne panel."""
        self.aktivni = index
        for i, lbl in enumerate(self.polozky):
            vybrana = i == index
            bg = BARVY["surface"] if vybrana else BARVY["sunken"]
            lbl.config(bg=bg, highlightbackground=bg,
                       fg=BARVY["text"] if vybrana else BARVY["text2"])
        self.pri_zmene(index)


class SeznamHodnot(tk.Frame):
    """Všechny hodnoty v mřížce; malé šedé číslo vlevo je pozice v poli.

    Používá se dvakrát: v záložce Vstup (původní data) a v záložce
    Seřazeno (výstup ze sort.py). Hodnoty se vypisují do tk.Text
    v pevně širokém písmu, takže sloupce jsou zarovnané. Počet sloupců
    se dopočítá podle šířky okna.
    """

    def __init__(self, rodic, vyska=12):
        super().__init__(rodic, bg=BARVY["surface2"], highlightthickness=1,
                         highlightbackground=BARVY["border"])
        self.text = tk.Text(self, height=vyska, bg=BARVY["surface2"], fg=BARVY["text"],
                            font=PISMO["mono"], relief="flat", wrap="none", padx=14, pady=10,
                            highlightthickness=0, cursor="arrow", spacing1=2, spacing3=2)
        # Posuvník a Text se propojí oběma směry:
        #   posuvník -> text: command=self.text.yview (tažení posouvá text)
        #   text -> posuvník: yscrollcommand=posuvnik.set (posun textu hýbe jezdcem)
        posuvnik = ttk.Scrollbar(self, orient="vertical", command=self.text.yview,
                                 style="Tenky.Vertical.TScrollbar")
        self.text.config(yscrollcommand=posuvnik.set, state="disabled")  # disabled = jen pro čtení
        # Značka (tag) "pos" = šedé menší písmo pro čísla pozic
        self.text.tag_config("pos", foreground=BARVY["text3"], font=PISMO["mono_small"])
        posuvnik.pack(side="right", fill="y", padx=(0, 3), pady=3)
        self.text.pack(side="left", fill="both", expand=True)
        self.hodnoty, self.typ, self.sloupcu = [], "integer", 0
        # Při změně velikosti se může změnit počet sloupců -> překreslit
        self.text.bind("<Configure>", lambda e: self._vykresli())

    def zobraz(self, hodnoty, typ):
        """Zobrazí nový seznam hodnot (sloupcu = 0 vynutí překreslení)."""
        self.hodnoty, self.typ, self.sloupcu = hodnoty, typ, 0
        self._vykresli()

    def _vykresli(self):
        """Vypíše hodnoty do řádků po `sloupcu` buňkách."""
        sirka_znaku = tkfont.Font(font=PISMO["mono"]).measure("0")   # šířka 1 znaku v px
        texty = [formatuj_hodnotu(v, self.typ) for v in self.hodnoty]
        sirka_hod = max((len(t) for t in texty), default=1)   # nejdelší hodnota ve znacích
        sirka_pos = len(str(len(texty)))                      # počet číslic nejvyšší pozice
        # šířka jedné buňky v pixelech: pozice + mezera + hodnota + 4 mezery odstup
        bunka = (sirka_pos + 1 + sirka_hod + 4) * sirka_znaku
        sloupcu = max(1, (self.text.winfo_width() - 28) // bunka)
        if sloupcu == self.sloupcu:
            return                      # počet sloupců se nezměnil – není co dělat
        self.sloupcu = sloupcu

        self.text.config(state="normal")        # dočasně povolit zápis
        self.text.delete("1.0", "end")          # "1.0" = 1. řádek, 0. znak = začátek
        for start in range(0, len(texty), sloupcu):
            casti = []
            for i in range(start, min(start + sloupcu, len(texty))):
                # insert() bere dvojice (text, značka): číslo pozice se značkou
                # "pos" (šedě), hodnota bez značky "". :>{n} = zarovnat doprava
                # na n znaků, :<{n} = doleva.
                casti += [f"{i + 1:>{sirka_pos}} ", "pos", f"{texty[i]:<{sirka_hod}}    ", ""]
            casti += ["\n", ""]
            self.text.insert("end", *casti)
        self.text.config(state="disabled")      # zase jen pro čtení


class Posuvnik(tk.Canvas):
    """Tenký posuvník (tažení myší i kliknutí do dráhy).
    prikaz(hodnota) se volá jen při změně uživatelem, ne při nastav().

    Používá se v okně animace dvakrát: pro výběr kroku a pro rychlost.
    Je nakreslený na plátně: šedá dráha, černá vyplněná část a kolečko.
    Hodnoty jsou celá čísla od `od` do `do`.
    """

    def __init__(self, rodic, od, do, hodnota, prikaz, sirka=200):
        super().__init__(rodic, width=sirka, height=22, bg=rodic.cget("bg"),
                         highlightthickness=0, cursor="pointinghand")
        self.od, self.do, self.hodnota, self.prikaz = od, do, hodnota, prikaz
        self.bind("<Configure>", lambda e: self._vykresli())   # změna velikosti
        self.bind("<Button-1>", self._tah)                     # kliknutí
        self.bind("<B1-Motion>", self._tah)                    # tažení se stisknutým tlačítkem

    def nastav(self, hodnota):
        """Posune jezdec programem (bez volání prikaz)."""
        self.hodnota = hodnota
        self._vykresli()

    def _x(self, hodnota):
        """Převede hodnotu na vodorovnou souřadnici v pixelech.
        9 px je okraj na každé straně, aby se kolečko vešlo celé."""
        rozsah = max(1, self.do - self.od)
        return 9 + (hodnota - self.od) / rozsah * (self.winfo_width() - 18)

    def _tah(self, e):
        """Opačný převod: poloha myši -> hodnota (zaokrouhlená na celé číslo)."""
        rozsah = max(1, self.do - self.od)
        # podíl 0–1 = jak daleko je myš na dráze; min/max ho udrží v mezích
        podil = min(max((e.x - 9) / max(1, self.winfo_width() - 18), 0), 1)
        hodnota = self.od + round(podil * rozsah)
        if hodnota != self.hodnota:
            self.nastav(hodnota)
            self.prikaz(hodnota)

    def _vykresli(self):
        self.delete("all")
        w, stred = self.winfo_width(), 11
        x = self._x(self.hodnota)
        self.create_line(9, stred, w - 9, stred, width=4, capstyle="round", fill=BARVY["sunken"])
        self.create_line(9, stred, x, stred, width=4, capstyle="round", fill=BARVY["ink"])
        self.create_oval(x - 8, stred - 8, x + 8, stred + 8, fill=BARVY["surface"],
                         outline=BARVY["ink"], width=2)


# ---------------------------------------------------------------------------
# 5) Modální okna: společný základ, kontrola souboru, animace
# ---------------------------------------------------------------------------

class Dialog(tk.Toplevel):
    """Společný základ modálních oken (OknoKontroly, OknoAnimace).

    tk.Toplevel = samostatné okno nad hlavním oknem.
    Modální = dokud je okno otevřené, hlavní okno nejde ovládat.
    Okno se otevře uprostřed hlavního okna, Esc i křížek ho zavřou.
    Podtřída do self.fokus uloží prvek, který má po otevření dostat fokus.
    """

    def __init__(self, app, titulek, sirka, vyska):
        super().__init__(app.root, bg=BARVY["surface"])
        self.app = app
        self.fokus = None
        self.title(titulek)
        self.transient(app.root)                  # okno patří k hlavnímu oknu (je nad ním)
        self.geometry(self._stred(sirka, vyska))  # velikost a poloha uprostřed hlavního okna
        self.bind("<Escape>", lambda e: self.zavri())
        # Křížek v liště okna má zavolat naši funkci zavri
        self.protocol("WM_DELETE_WINDOW", self.zavri)
        self.after(100, self._modalni)

    def _modalni(self):
        # grab_set() pošle všechny kliky jen do tohoto okna -> hlavní okno počká
        try:
            self.grab_set()
        except tk.TclError:             # okno ještě není zobrazené – zkusit znovu
            self.after(100, self._modalni)
            return
        if self.fokus:
            self.fokus.focus_set()

    def _stred(self, w, h):
        """Vrátí geometrii "ŠxV+X+Y", aby okno leželo uprostřed hlavního okna."""
        r = self.app.root
        x = r.winfo_rootx() + max(0, (r.winfo_width() - w) // 2)
        y = r.winfo_rooty() + max(0, (r.winfo_height() - h) // 2)
        return f"{w}x{h}+{x}+{y}"

    def zavri(self):
        """Zavře okno, uvolní modalitu a vrátí fokus hlavnímu oknu."""
        self.grab_release()
        self.destroy()
        self.app.root.focus_set()


class OknoKontroly(Dialog):
    """Kontrola načteného souboru: ukáže rozpoznaný typ dat a všechny
    hodnoty a zeptá se, jestli je chce uživatel takto třídit.

      Ano, třídit         -> data se předají hlavnímu oknu (_nastav_data)
      Vybrat jiný soubor  -> znovu se otevře výběr souboru
      Zrušit / Esc        -> okno se zavře, původní data zůstanou
    """

    def __init__(self, app, soubor, typ, hodnoty, upozorneni):
        super().__init__(app, "Kontrola načtených dat", 720, 580)
        self.soubor, self.typ, self.hodnoty = soubor, typ, hodnoty
        self.minsize(600, 520)
        obal = tk.Frame(self, bg=BARVY["surface"])
        obal.pack(fill="both", expand=True, padx=36, pady=28)

        # --- hlavička: odkud data jsou, jaký typ jsme poznali a proč ---
        tk.Label(obal, text=f"Rozpoznaný typ dat · {soubor}", font=PISMO["small"],
                 fg=BARVY["text3"], bg=BARVY["surface"], anchor="w").pack(fill="x")
        tk.Label(obal, text=popis_typu(typ).capitalize(), font=PISMO["dialog_title"],
                 fg=BARVY["text"], bg=BARVY["surface"], anchor="w").pack(fill="x")
        tk.Label(obal, text=PROC_TYP[typ], font=PISMO["body"], fg=BARVY["text2"],
                 bg=BARVY["surface"], anchor="w", justify="left",
                 wraplength=640).pack(fill="x", pady=(2, 12))

        # --- čipy: počet hodnot a rozsah (u textu jen počet) ---
        cipy = tk.Frame(obal, bg=BARVY["surface"])
        cipy.pack(fill="x")
        cip(cipy, f"{cesky_pocet(len(hodnoty))} hodnot").pack(side="left", padx=(0, 6))
        if typ != "text":
            # min()/max() jen pro informaci v okně – netřídí se tím
            cip(cipy, f"od {formatuj_hodnotu(min(hodnoty), typ)} "
                      f"do {formatuj_hodnotu(max(hodnoty), typ)}").pack(side="left")

        # --- žluté upozornění, když data míchají čísla a text ---
        if upozorneni:
            tk.Label(obal, text=upozorneni, font=PISMO["small"], fg=BARVY["yellow"],
                     bg=BARVY["yellow_bg"], anchor="w", justify="left", wraplength=620,
                     padx=14, pady=10).pack(fill="x", pady=(14, 0))

        # --- všechny načtené hodnoty v pořadí ze souboru ---
        tk.Label(obal, text="Načtené hodnoty", font=PISMO["bold"], fg=BARVY["text"],
                 bg=BARVY["surface"], anchor="w").pack(fill="x", pady=(18, 6))
        # Tlačítka balíme dřív než seznam se side="bottom": když se okno
        # zmenší, zmenší se seznam a tlačítka zůstanou vidět.
        tlacitka = tk.Frame(obal, bg=BARVY["surface"])
        tlacitka.pack(side="bottom", fill="x")
        tk.Label(obal, text=f"Chcete třídit tyto hodnoty jako {popis_typu(typ)}?",
                 font=PISMO["bold"], fg=BARVY["text"], bg=BARVY["surface"],
                 anchor="w").pack(side="bottom", fill="x", pady=(18, 12))
        seznam = SeznamHodnot(obal, vyska=8)
        seznam.pack(fill="both", expand=True)
        seznam.zobraz(hodnoty, typ)

        # Tlačítka vytvoříme v pořadí zleva doprava (tak mezi nimi skáče Tab),
        # ale „Ano“ zabalíme jako první se side="right", aby bylo úplně vpravo.
        zrusit = Tlacitko(tlacitka, "Zrušit", self.zavri, "ghost")
        jiny = Tlacitko(tlacitka, "Vybrat jiný soubor", self.jiny_soubor)
        ano = Tlacitko(tlacitka, "Ano, třídit", self.potvrd, "primary")
        zrusit.pack(side="left")
        ano.pack(side="right")
        jiny.pack(side="right", padx=8)
        self.bind("<Return>", lambda e: self.potvrd())   # Enter = Ano
        self.fokus = ano

    def potvrd(self):
        """Ano – data se použijí v hlavním okně."""
        self.zavri()
        self.app._nastav_data(self.hodnoty, self.typ, self.soubor)

    def jiny_soubor(self):
        """Uživatel načetl něco jiného, než chtěl – znovu výběr souboru."""
        self.zavri()
        self.app.nacti_soubor()


# Animace nic netřídí sama. Algoritmus ze sort.py při třídění zapisuje každý
# krok do seznamu `kroky` (= self.snimky). Jeden snímek je slovník:
#   "pole"    – stav pole v tom okamžiku
#   "aktivni" – indexy prvků, se kterými algoritmus právě pracuje (oranžově)
#   "hotovo"  – indexy prvků na konečném místě (zeleně)
#   "zprava"  – česky popsaný krok („Porovnávám prvek s pivotem.“)
# Okno jen tyto snímky postupně kreslí jako sloupcový graf.

class OknoAnimace(Dialog):
    """Přehrává kroky, které zaznamenal algoritmus v sort.py (parametr `kroky`)."""

    def __init__(self, app, info, snimky, typ, poznamka):
        super().__init__(app, info["nazev"], 1040, 820)
        self.snimky, self.typ = snimky, typ
        # index = číslo právě zobrazeného snímku, hraje = běží přehrávání,
        # casovac = identifikátor naplánovaného after() (kvůli zrušení)
        self.index, self.hraje, self.casovac = 0, False, None
        self.minsize(820, 760)

        obal = tk.Frame(self, bg=BARVY["surface"])
        obal.pack(fill="both", expand=True, padx=36, pady=28)

        # --- hlavička: název algoritmu + tlačítko Zavřít ---
        hlava = tk.Frame(obal, bg=BARVY["surface"])
        hlava.pack(fill="x")
        tk.Label(hlava, text=info["nazev"], font=PISMO["dialog_title"], fg=BARVY["text"],
                 bg=BARVY["surface"]).pack(side="left")
        Tlacitko(hlava, "Zavřít", self.zavri, "secondary", padx=12, pady=4).pack(side="right")
        tk.Label(obal, text=f"{poznamka} · {cesky_pocet(len(snimky))} kroků zaznamenaných v sort.py",
                 font=PISMO["small"], fg=BARVY["text3"], bg=BARVY["surface"],
                 anchor="w").pack(fill="x", pady=(2, 10))
        tk.Label(obal, text=info["vysvetleni"], font=PISMO["body"], fg=BARVY["text2"],
                 bg=BARVY["surface"], justify="left", anchor="w",
                 wraplength=860).pack(fill="x", pady=(0, 14))

        # --- legenda barev ---
        legenda = tk.Frame(obal, bg=BARVY["surface"])
        legenda.pack(fill="x", pady=(0, 8))
        for barva, text in (("bar_active", "právě porovnávané"), ("bar", "ostatní"),
                            ("bar_done", "na konečném místě")):
            ctverec = tk.Canvas(legenda, width=10, height=10, bg=BARVY["surface"],
                                highlightthickness=0)
            zaobleny_obdelnik(ctverec, 0, 0, 10, 10, 3, fill=BARVY[barva], outline="")
            ctverec.pack(side="left", padx=(0, 6))
            tk.Label(legenda, text=text, font=PISMO["small"], fg=BARVY["text2"],
                     bg=BARVY["surface"]).pack(side="left", padx=(0, 18))

        # --- plátno se sloupcovým grafem ---
        self.platno = tk.Canvas(obal, height=250, bg=BARVY["surface2"], highlightthickness=1,
                                highlightbackground=BARVY["border"])
        self.platno.pack(fill="x")
        # Šířku plátna známe až po zobrazení okna -> kreslíme při každé změně velikosti
        self.platno.bind("<Configure>", lambda e: self._vykresli())
        n = len(snimky[0]["pole"])                 # počet prvků v animaci
        tk.Label(obal, font=PISMO["tiny"], fg=BARVY["text3"], bg=BARVY["surface"], anchor="w",
                 text="Výška sloupce odpovídá pořadí hodnoty; pod sloupcem je pozice."
                 if n <= 40 else "Výška sloupce odpovídá pořadí hodnoty. Popisky se u tolika "
                                 "prvků kvůli přehlednosti nezobrazují.").pack(fill="x", pady=(6, 12))

        # --- šedý box s číslem kroku, popisem kroku a aktivními pozicemi ---
        krok_box = tk.Frame(obal, bg=BARVY["sunken"])
        krok_box.pack(fill="x")
        vnitrek = tk.Frame(krok_box, bg=BARVY["sunken"])
        vnitrek.pack(fill="x", padx=18, pady=12)
        self.lbl_pocet = tk.Label(vnitrek, font=PISMO["mono"], fg=BARVY["text3"],
                                  bg=BARVY["sunken"], width=13, anchor="nw")
        self.lbl_pocet.pack(side="left", anchor="n")
        texty = tk.Frame(vnitrek, bg=BARVY["sunken"])
        texty.pack(side="left", fill="x", expand=True)
        self.lbl_zprava = tk.Label(texty, font=PISMO["body"], fg=BARVY["text"],
                                   bg=BARVY["sunken"], anchor="w", justify="left")
        self.lbl_zprava.pack(fill="x")
        self.lbl_pozice = tk.Label(texty, font=PISMO["mono_small"], fg=BARVY["text2"],
                                   bg=BARVY["sunken"], anchor="w")
        self.lbl_pozice.pack(fill="x", pady=(3, 0))

        # --- posuvník kroků: přetažením se dá skočit na libovolný krok ---
        self.posuvnik = Posuvnik(obal, 0, len(snimky) - 1, 0, self._posun)
        self.posuvnik.pack(fill="x", pady=(14, 12))

        # --- ovládací tlačítka a rychlost ---
        ovladani = tk.Frame(obal, bg=BARVY["surface"])
        ovladani.pack(fill="x")
        self.btn_play = Tlacitko(ovladani, "Přehrát", self.prepni_prehravani, "primary")
        self.btn_play.lbl.config(width=10)   # pevná šířka – nepřeskakuje mezi Přehrát/Pozastavit
        self.btn_play.pack(side="left")
        self.btn_krok = Tlacitko(ovladani, "Krok", lambda: (self.zastav(), self.krok(1)))
        self.btn_krok.pack(side="left", padx=8)
        Tlacitko(ovladani, "Od začátku", self.od_zacatku, "ghost").pack(side="left")

        # Prvky s side="right" se skládají zprava doleva, proto je pořadí
        # v kódu obrácené: nejdřív text „5 kroků/s“, pak posuvník, pak popisek.
        self.lbl_rychlost = tk.Label(ovladani, text="5 kroků/s", font=PISMO["mono_small"],
                                     fg=BARVY["text2"], bg=BARVY["surface"], width=11, anchor="e")
        self.lbl_rychlost.pack(side="right")
        self.rychlost = 5               # kroků za sekundu
        Posuvnik(ovladani, 1, 300, self.rychlost, self._zmena_rychlosti,
                 sirka=150).pack(side="right", padx=8)
        tk.Label(ovladani, text="Rychlost", font=PISMO["small"], fg=BARVY["text2"],
                 bg=BARVY["surface"]).pack(side="right")

        # --- nápověda klávesových zkratek ---
        napoveda = tk.Frame(obal, bg=BARVY["surface"])
        napoveda.pack(fill="x", pady=(16, 0))
        for klavesa, popis in (("Mezerník", "přehrát / pozastavit"), ("→", "další krok"),
                               ("←", "předchozí"), ("Esc", "zavřít")):
            tk.Label(napoveda, text=klavesa, font=PISMO["mono_small"], fg=BARVY["text2"],
                     bg=BARVY["sunken"], padx=6).pack(side="left", padx=(0, 5))
            tk.Label(napoveda, text=popis, font=PISMO["tiny"], fg=BARVY["text3"],
                     bg=BARVY["surface"]).pack(side="left", padx=(0, 14))

        # Klávesové zkratky okna
        self.bind("<space>", lambda e: self.prepni_prehravani())
        self.bind("<Right>", lambda e: (self.zastav(), self.krok(1)))
        self.bind("<Left>", lambda e: (self.zastav(), self.krok(-1)))
        self.fokus = self.btn_play       # po otevření (Dialog._modalni) dostane fokus Přehrát

        self._vykresli()

    # --- vykreslení jednoho snímku -------------------------------------------------
    def _vykresli(self):
        """Nakreslí snímek self.index: sloupce, popisky a texty pod grafem."""
        snimek = self.snimky[self.index]
        # set() kvůli rychlému testu „i in aktivni“
        pole, aktivni, hotovo = snimek["pole"], set(snimek["aktivni"]), set(snimek["hotovo"])
        c = self.platno
        c.delete("all")
        W, H = c.winfo_width(), c.winfo_height()
        if W > 10:                       # plátno už má skutečnou velikost
            n = len(pole)
            popisky = n <= 40            # čísla pozic jen u menšího počtu sloupců
            okraj, dole = 14, (22 if popisky else 0)   # místo pod grafem na popisky
            # výška sloupce podle pořadí hodnoty, ne podle hodnoty samotné
            # (aby byly vidět i rozdíly u dat s velkým rozptylem)
            # poradi: hodnota -> její pořadí mezi různými hodnotami (1 = nejmenší)
            poradi = {v: i + 1 for i, v in enumerate(sorted(set(pole)))}
            max_poradi = max(1, len(poradi))
            sirka = (W - 2 * okraj) / n               # šířka místa na jeden sloupec
            mezera = min(4, sirka * 0.18)             # mezera mezi sloupci
            spodek = H - okraj - dole                 # y-souřadnice spodní hrany sloupců
            for i, v in enumerate(pole):
                h = max(3, poradi[v] / max_poradi * (spodek - okraj))   # výška aspoň 3 px
                x1 = okraj + i * sirka + mezera / 2
                x2 = x1 + max(sirka - mezera, 1)
                # Oranžová má přednost před zelenou: aktivní prvek je vidět,
                # i když už je na konečném místě.
                barva = BARVY["bar_active"] if i in aktivni else \
                    BARVY["bar_done"] if i in hotovo else BARVY["bar"]
                # Na plátně roste y směrem DOLŮ, proto sloupec začíná nahoře
                # v (spodek - h) a končí dole ve `spodek`.
                c.create_rectangle(x1, spodek - h, x2, spodek, fill=barva, outline="")
                if popisky:
                    c.create_text((x1 + x2) / 2, spodek + 12, text=str(i + 1),
                                  fill=BARVY["text3"], font=PISMO["mono_small"])

        self.lbl_pocet.config(text=f"{self.index} / {len(self.snimky) - 1}")
        self.lbl_zprava.config(text=snimek["zprava"])
        # Pozice se v okně počítají od 1 (pro lidi), indexy v Pythonu od 0
        self.lbl_pozice.config(text="Pozice: –" if not snimek["aktivni"] else "Pozice " + " · ".join(
            f"{i + 1} → {formatuj_hodnotu(pole[i], self.typ)}" for i in snimek["aktivni"]))
        self.posuvnik.nastav(self.index)
        na_konci = self.index >= len(self.snimky) - 1
        self.btn_krok.nastav(povoleno=not na_konci)   # na posledním kroku už „Krok“ nejde
        if na_konci:
            self.zastav()

    # --- ovládání ------------------------------------------------------------------
    def krok(self, smer):
        """Posun o jeden snímek: smer = +1 dopředu, -1 dozadu."""
        novy = min(max(self.index + smer, 0), len(self.snimky) - 1)   # nepřekročit okraje
        if novy == self.index:          # jsme na začátku/konci, není kam jít
            self.zastav()
            return
        self.index = novy
        self._vykresli()

    def _tik(self):
        # Jeden „tik“ přehrávání: krok dopředu a naplánování dalšího tiku.
        # Interval 1000 / rychlost ms -> např. 5 kroků/s = každých 200 ms.
        self.krok(1)
        if self.hraje:
            self.casovac = self.after(int(1000 / self.rychlost), self._tik)

    def prepni_prehravani(self):
        """Tlačítko Přehrát / Pozastavit (a mezerník)."""
        if self.hraje:
            self.zastav()
            return
        if self.index >= len(self.snimky) - 1:   # na konci -> přehrát znovu od začátku
            self.index = 0
        self.hraje = True
        self.btn_play.nastav(text="Pozastavit")
        self.casovac = self.after(int(1000 / self.rychlost), self._tik)

    def zastav(self):
        """Zastaví přehrávání a zruší naplánovaný tik."""
        self.hraje = False
        if self.casovac:
            self.after_cancel(self.casovac)
            self.casovac = None
        self.btn_play.nastav(text="Přehrát")

    def od_zacatku(self):
        self.zastav()
        self.index = 0
        self._vykresli()

    def _posun(self, index):
        # volá posuvník kroků, když ho uživatel přetáhne
        self.zastav()
        self.index = index
        self._vykresli()

    def _zmena_rychlosti(self, hodnota):
        # volá posuvník rychlosti; nová rychlost platí od dalšího tiku
        self.rychlost = hodnota
        self.lbl_rychlost.config(text=f"{hodnota} kroků/s")

    def zavri(self):
        """Zavře okno: zastaví časovač a pak zavře okno jako každý Dialog."""
        self.zastav()
        super().zavri()


# ---------------------------------------------------------------------------
# 6) Hlavní okno
# ---------------------------------------------------------------------------

class SortApp:
    """Hlavní okno aplikace – drží data, výsledky a obsluhuje všechna tlačítka.

    Průběh práce uživatele = tři karty:
      01 Data       -> generuj() / nacti_soubor() / pouzij_rucne()
      02 Algoritmy  -> porovnej() (měření) nebo animuj() (okno animace)
      03 Výsledky   -> tabulka časů, vstupní data, seřazená čísla, export CSV

    MĚŘENÍ A VLÁKNA:
    Pomalé algoritmy třídí 3 000 čísel i několik sekund. Kdyby běžely
    v hlavním vlákně, okno by po tu dobu zamrzlo (nešlo by kliknout ani na
    Zastavit). Proto měření běží ve VEDLEJŠÍM vlákně (threading.Thread).
    Tkinter ale dovoluje měnit okno jen z hlavního vlákna. Vedlejší vlákno
    tedy okno nemění – jen vkládá zprávy do fronty (queue.Queue) a hlavní
    vlákno je každých 40 ms vybírá v _zpracuj_frontu() a teprve to
    překresluje tabulku.
    """

    def __init__(self, root):
        self.root = root
        self.hodnoty, self.typ = [], "integer"   # aktuální data a jejich typ
        self.vysledky = {}              # klíč -> {"median", "min", "max", "ok"}
        self.serazeno = None            # {"klic", "pole", "ok"} pro záložku Seřazeno
        self.bezi = False               # probíhá právě měření?
        self.stop = threading.Event()   # „vlajka“ pro zastavení měření (vidí ji i vlákno)
        self.fronta = queue.Queue()     # zprávy z vlákna s měřením
        self.radky = {}                 # klíč -> widgety jednoho řádku tabulky výsledků

        root.title("SortApp · Laboratoř třídění")
        root.configure(bg=BARVY["bg"])
        root.geometry("1240x880")       # výchozí velikost okna
        root.minsize(980, 640)          # menší okno už by se nevešlo
        self._styly()
        self._postav_okno()
        self._obnov_tlacitka()
        root.after(40, self._zpracuj_frontu)    # spustí pravidelné čtení fronty

    # --- styly ttk (rozbalovací seznamy, posuvníky) --------------------------------
    def _styly(self):
        """Obarví widgety ttk (Combobox, Scrollbar) do stejné palety.

        Widgety ttk se nestylují parametry bg/fg, ale přes ttk.Style:
        configure() nastaví vzhled a map() vzhled v určitém stavu
        (např. "focus" = prvek má fokus, "readonly" = jen výběr ze seznamu).
        """
        s = ttk.Style(self.root)
        s.theme_use("clam")      # téma „clam“ jde na rozdíl od macOS tématu obarvit
        s.configure("TCombobox", fieldbackground=BARVY["surface"], background=BARVY["surface"],
                    foreground=BARVY["text"], bordercolor=BARVY["border_strong"],
                    lightcolor=BARVY["surface"], darkcolor=BARVY["surface"],
                    arrowcolor=BARVY["text2"], padding=(8, 5), arrowsize=12)
        s.map("TCombobox", fieldbackground=[("readonly", BARVY["surface"])],
              selectbackground=[("readonly", BARVY["surface"])],
              selectforeground=[("readonly", BARVY["text"])],
              bordercolor=[("focus", BARVY["focus"])],
              background=[("active", BARVY["sunken"])])
        # Rozbalený seznam Comboboxu je obyčejný Listbox – nastavuje se přes option_add
        self.root.option_add("*TCombobox*Listbox.font", PISMO["body"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", BARVY["sunken"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", BARVY["text"])

        # Vlastní rozložení posuvníku: jen dráha (trough) a jezdec (thumb),
        # bez šipek nahoru/dolů -> tenký moderní posuvník.
        tenky = [("Vertical.Scrollbar.trough", {
            "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})],
            "sticky": "ns"})]
        # Dva styly: jeden pro seznamy hodnot (světlé pozadí), druhý pro celé okno
        for styl, pozadi in (("Tenky.Vertical.TScrollbar", BARVY["surface2"]),
                             ("Okno.Vertical.TScrollbar", BARVY["bg"])):
            s.layout(styl, tenky)
            s.configure(styl, troughcolor=pozadi, background=BARVY["bar"], bordercolor=pozadi,
                        lightcolor=BARVY["bar"], darkcolor=BARVY["bar"], arrowsize=8, gripcount=0)
            s.map(styl, background=[("active", BARVY["text3"])])

    # --- rozvržení -----------------------------------------------------------------
    def _postav_okno(self):
        """Postaví celé hlavní okno: posuvnou stránku a v ní všechny části."""
        r = self.root
        # Obsah je na posuvném plátně, aby se vešel i do menšího okna.
        # Frame se v Tkinteru posouvat nedá, Canvas ano. Proto vložíme celou
        # stránku (Frame) do plátna přes create_window a posouváme plátnem.
        self.platno = tk.Canvas(r, bg=BARVY["bg"], highlightthickness=0, yscrollincrement=24)
        posuvnik = ttk.Scrollbar(r, orient="vertical", command=self.platno.yview,
                                 style="Okno.Vertical.TScrollbar")
        self.platno.configure(yscrollcommand=posuvnik.set)
        posuvnik.pack(side="right", fill="y", padx=2, pady=2)
        self.platno.pack(side="left", fill="both", expand=True)
        self.stranka = tk.Frame(self.platno, bg=BARVY["bg"])
        # anchor="n" = stránka je ukotvená horním středem -> dá se vycentrovat
        self.okno_id = self.platno.create_window(0, 0, window=self.stranka, anchor="n")
        self.stranka.bind("<Configure>", lambda e: self._oblast_posunu())   # změnila se výška obsahu
        self.platno.bind("<Configure>", self._zmena_velikosti)              # změnila se velikost okna
        r.bind_all("<MouseWheel>", self._kolecko)                           # kolečko myši kdekoli v okně

        self._hlavicka()
        self._hero()
        # Mřížka se dvěma sloupci: vlevo karta Data, vpravo Algoritmy,
        # pod nimi přes oba sloupce karta Výsledky.
        # weight 5 : 6 = poměr šířek sloupců; uniform="k" drží poměr přesně.
        mrizka = tk.Frame(self.stranka, bg=BARVY["bg"])
        mrizka.pack(fill="x")
        mrizka.columnconfigure(0, weight=5, uniform="k")
        mrizka.columnconfigure(1, weight=6, uniform="k")
        self._karta_data(mrizka).grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 16))
        self._karta_algoritmy(mrizka).grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 16))
        self._karta_vysledky(mrizka).grid(row=1, column=0, columnspan=2, sticky="nsew")
        self._paticka()

    def _zmena_velikosti(self, e):
        # obsah max. 1180 px široký a vycentrovaný
        # (48 px = okraje vlevo a vpravo; stránka leží ve středu e.width / 2)
        self.platno.itemconfigure(self.okno_id, width=min(e.width - 48, 1180))
        self.platno.coords(self.okno_id, e.width / 2, 0)
        self._oblast_posunu()

    def _oblast_posunu(self):
        # posouvá se jen svisle; vodorovně oblast začíná na 0, jinak by se
        # vycentrovaný obsah „přilepil“ k levému okraji
        # scrollregion = obdélník, po kterém se dá posouvat (výška = výška obsahu)
        self.platno.configure(scrollregion=(0, 0, self.platno.winfo_width(),
                                            self.stranka.winfo_reqheight()))

    def _kolecko(self, e):
        # seznamy hodnot (tk.Text) se posouvají samy, stránka jen mimo ně
        # str(e.widget) je cesta widgetu ve stromu (".!canvas.!frame…");
        # když nezačíná cestou plátna, je událost z jiného okna (animace).
        if isinstance(e.widget, tk.Text) or not str(e.widget).startswith(str(self.platno)):
            return
        # (0.0, 1.0) = je vidět celá stránka, není co posouvat
        if self.platno.yview() != (0.0, 1.0):
            # e.delta > 0 = kolečko nahoru -> posun nahoru (-1)
            self.platno.yview_scroll(-1 if e.delta > 0 else 1, "units")

    def _hlavicka(self):
        """Horní lišta: logo, název aplikace a vpravo stav (kolik algoritmů je v sort.py)."""
        h = tk.Frame(self.stranka, bg=BARVY["bg"])
        h.pack(fill="x", pady=(20, 0))
        logo = tk.Canvas(h, width=26, height=26, bg=BARVY["bg"], highlightthickness=0)
        zaobleny_obdelnik(logo, 0, 0, 26, 26, 7, fill=BARVY["ink"], outline="")
        for i, vyska in enumerate((7, 11, 15)):          # tři sloupce = seřazená data
            logo.create_rectangle(7 + i * 5, 20 - vyska, 10 + i * 5, 20, fill="#FFFFFF", outline="")
        logo.pack(side="left")
        tk.Label(h, text="SortApp", font=PISMO["brand"], fg=BARVY["text"],
                 bg=BARVY["bg"]).pack(side="left", padx=(10, 6))
        tk.Label(h, text="laboratoř třídění", font=PISMO["small"], fg=BARVY["text3"],
                 bg=BARVY["bg"]).pack(side="left")

        stav = tk.Frame(h, bg=BARVY["surface"], highlightthickness=1,
                        highlightbackground=BARVY["border"])
        stav.pack(side="right")
        tecka = tk.Canvas(stav, width=8, height=8, bg=BARVY["surface"], highlightthickness=0)
        tecka.create_oval(0, 0, 8, 8, fill=BARVY["bar_done"], outline="")   # zelená tečka
        tecka.pack(side="left", padx=(12, 6))
        # počet algoritmů se bere přímo ze sort.py – přidaný algoritmus se tu projeví sám
        tk.Label(stav, text=f"sort.py · {len(sort.ALGORITMY)} algoritmů", font=PISMO["small"],
                 fg=BARVY["text2"], bg=BARVY["surface"]).pack(side="left", padx=(0, 12), pady=4)

    def _hero(self):
        """Úvodní blok: seznam algoritmů, velký nadpis a krátký popis aplikace."""
        h = tk.Frame(self.stranka, bg=BARVY["bg"])
        h.pack(fill="x", pady=(44, 32))
        tk.Label(h, text=" · ".join(a["klic"] for a in ALGORITMY_INFO), font=PISMO["mono_small"],
                 fg=BARVY["text3"], bg=BARVY["bg"]).pack(anchor="w")
        # Label umí jen jedno písmo, proto je nadpis složený ze tří Labelů
        # vedle sebe – prostřední slovo „seřadí“ je kurzívou.
        nadpis = tk.Frame(h, bg=BARVY["bg"])
        nadpis.pack(anchor="w", pady=(10, 10))
        for text, pismo in (("Jak rychle se ", "hero"), ("seřadí", "hero_italic"),
                            (" stejná data?", "hero")):
            tk.Label(nadpis, text=text, font=PISMO[pismo], fg=BARVY["ink"], bg=BARVY["bg"],
                     padx=0).pack(side="left", anchor="s")
        tk.Label(h, text="Připravte data, vyberte algoritmy a změřte je. Třídí přímo funkce "
                         "ze souboru sort.py – každý krok si můžete přehrát v animaci.",
                 font=PISMO["body"], fg=BARVY["text2"], bg=BARVY["bg"], justify="left",
                 wraplength=620).pack(anchor="w")

    def _pole(self, rodic, popisek, widget_fn, radek, sloupec):
        """Políčko formuláře s popiskem nad sebou.

        widget_fn je funkce, která vytvoří samotný vstup (Combobox nebo
        Spinbox) uvnitř připraveného rámečku. Políčko se umístí do mřížky
        na (radek, sloupec) a vrátí se vstupní widget, aby z něj šlo číst.
        """
        f = tk.Frame(rodic, bg=BARVY["surface"])
        f.grid(row=radek, column=sloupec, sticky="ew", pady=(0, 12),
               padx=(0, 6) if sloupec == 0 else (6, 0))
        tk.Label(f, text=popisek, font=PISMO["small"], fg=BARVY["text2"],
                 bg=BARVY["surface"]).pack(anchor="w", pady=(0, 4))
        w = widget_fn(f)
        w.pack(fill="x")
        return w

    def _vstup_cislo(self, rodic, hodnota, od, do):
        """Číselné políčko se šipkami (Spinbox) s výchozí hodnotou."""
        spin = tk.Spinbox(rodic, from_=od, to=do, font=PISMO["body"], relief="flat",
                          bg=BARVY["surface"], fg=BARVY["text"], buttonbackground=BARVY["surface"],
                          highlightthickness=1, highlightbackground=BARVY["border_strong"],
                          highlightcolor=BARVY["focus"], insertbackground=BARVY["text"], width=8)
        spin.delete(0, "end")            # Spinbox začíná hodnotou `od` – přepíšeme ji
        spin.insert(0, str(hodnota))
        return spin

    def _vyber(self, rodic, moznosti):
        """Rozbalovací seznam (jen výběr, nedá se do něj psát)."""
        cb = ttk.Combobox(rodic, values=[t for _, t in moznosti], state="readonly",
                          font=PISMO["body"])
        cb.current(0)                    # vybrat první možnost
        return cb

    def _karta_data(self, rodic):
        """Karta 01 Data: generátor, načtení souboru, ruční vstup a souhrn."""
        k = Karta(rodic, "01", "Data", "Vygenerujte je, načtěte ze souboru, nebo zadejte ručně.")
        o = k.obsah
        # Čtyři políčka ve dvou sloupcích (uniform="p" = stejně široké sloupce)
        pole = tk.Frame(o, bg=BARVY["surface"])
        pole.pack(fill="x")
        pole.columnconfigure((0, 1), weight=1, uniform="p")
        self.cb_typ = self._pole(pole, "Typ hodnot", lambda f: self._vyber(f, TYPY), 0, 0)
        self.cb_rozlozeni = self._pole(pole, "Rozložení", lambda f: self._vyber(f, ROZLOZENI), 0, 1)
        self.sp_pocet = self._pole(pole, "Počet prvků",
                                   lambda f: self._vstup_cislo(f, 1000, 2, MAX_PRVKU), 1, 0)
        self.sp_seed = self._pole(pole, "Seed", lambda f: self._vstup_cislo(f, 42, 0, 999999), 1, 1)

        tlacitka = tk.Frame(o, bg=BARVY["surface"])
        tlacitka.pack(fill="x", pady=(4, 18))
        Tlacitko(tlacitka, "Generovat data", self.generuj, "primary").pack(side="left")
        Tlacitko(tlacitka, "Načíst .txt", self.nacti_soubor).pack(side="left", padx=8)

        # Oddělovač „—— nebo ručně ——“: čára, text, čára
        oddelovac = tk.Frame(o, bg=BARVY["surface"])
        oddelovac.pack(fill="x", pady=(0, 10))
        tk.Frame(oddelovac, bg=BARVY["border"], height=1).pack(side="left", fill="x", expand=True)
        tk.Label(oddelovac, text="nebo ručně", font=PISMO["tiny"], fg=BARVY["text3"],
                 bg=BARVY["surface"], padx=10).pack(side="left")
        tk.Frame(oddelovac, bg=BARVY["border"], height=1).pack(side="left", fill="x", expand=True)

        # Víceřádkové pole pro ruční zadání čísel
        self.txt_rucne = tk.Text(o, height=3, font=PISMO["mono"], relief="flat", wrap="word",
                                 bg=BARVY["surface"], fg=BARVY["text"], padx=10, pady=8,
                                 highlightthickness=1, highlightbackground=BARVY["border_strong"],
                                 highlightcolor=BARVY["focus"], insertbackground=BARVY["text"])
        self.txt_rucne.pack(fill="x")
        radek = tk.Frame(o, bg=BARVY["surface"])
        radek.pack(fill="x", pady=(8, 14))
        tk.Label(radek, text="Oddělte středníkem nebo novým řádkem (čísla i mezerou).",
                 font=PISMO["tiny"], fg=BARVY["text3"], bg=BARVY["surface"]).pack(side="left")
        Tlacitko(radek, "Použít", self.pouzij_rucne, padx=14, pady=4).pack(side="right")

        # Souhrn načtených dat (čipy „1 000 hodnot · celá čísla · …“) – plní _nastav_data
        self.souhrn = tk.Frame(o, bg=BARVY["surface"])
        self.souhrn.pack(fill="x")
        tk.Label(self.souhrn, text="Zatím žádná data.", font=PISMO["small"], fg=BARVY["text3"],
                 bg=BARVY["surface"]).pack(side="left")
        return k

    def _karta_algoritmy(self, rodic):
        """Karta 02 Algoritmy: karty k výběru, opakování a tlačítka akcí."""
        k = Karta(rodic, "02", "Algoritmy", "Pro porovnání vyberte libovolné, pro animaci právě jeden.")
        o = k.obsah
        mrizka = tk.Frame(o, bg=BARVY["surface"])
        mrizka.pack(fill="x")
        mrizka.columnconfigure((0, 1), weight=1, uniform="a")
        self.karty_algo = []
        for i, info in enumerate(ALGORITMY_INFO):
            karta = AlgoKarta(mrizka, info, self._obnov_tlacitka)
            # i // 2 = řádek, i % 2 = sloupec -> karty po dvou vedle sebe
            karta.grid(row=i // 2, column=i % 2, sticky="nsew",
                       padx=(0, 5) if i % 2 == 0 else (5, 0), pady=5)
            self.karty_algo.append(karta)

        radek = tk.Frame(o, bg=BARVY["surface"])
        radek.pack(fill="x", pady=(12, 14))
        Tlacitko(radek, "Vybrat vše", lambda: self._vyber_vse(True), "ghost",
                 padx=10, pady=4).pack(side="left")
        Tlacitko(radek, "Zrušit výběr", lambda: self._vyber_vse(False), "ghost",
                 padx=10, pady=4).pack(side="left", padx=4)
        # Kolikrát se každý algoritmus změří (z více měření se počítá medián)
        self.sp_opakovani = self._vstup_cislo(radek, 3, 1, 10)
        self.sp_opakovani.config(width=4)
        self.sp_opakovani.pack(side="right")
        tk.Label(radek, text="Opakování", font=PISMO["small"], fg=BARVY["text2"],
                 bg=BARVY["surface"]).pack(side="right", padx=8)

        akce = tk.Frame(o, bg=BARVY["surface"])
        akce.pack(fill="x")
        self.btn_porovnat = Tlacitko(akce, "Porovnat", self.porovnej, "primary", padx=22, pady=9)
        self.btn_porovnat.pack(side="left")
        # Tlačítko Zastavit se vytvoří, ale zobrazí se jen během měření
        # (pack/pack_forget v _obnov_tlacitka)
        self.btn_stop = Tlacitko(akce, "Zastavit", self.zastav_mereni, pady=9)
        self.btn_animovat = Tlacitko(akce, "Animovat", self.animuj, pady=9)
        self.btn_animovat.pack(side="left", padx=8)
        # Nápověda pod tlačítky: proč je nějaké tlačítko vypnuté
        self.lbl_napoveda = tk.Label(o, font=PISMO["small"], fg=BARVY["text3"],
                                     bg=BARVY["surface"], anchor="w")
        self.lbl_napoveda.pack(fill="x", pady=(10, 0))
        return k

    def _karta_vysledky(self, rodic):
        """Karta 03 Výsledky se třemi panely přepínanými záložkami."""
        k = Karta(rodic, "03", "Výsledky",
                  "Medián, minimum a maximum z opakovaných měření v milisekundách.")

        # Všechny tři panely leží v JEDNÉ buňce mřížky přes sebe (row=0,
        # column=0). Záložka pak jen vytáhne vybraný panel nahoru (tkraise),
        # ostatní zůstanou schované pod ním.
        self.panely = tk.Frame(k.obsah, bg=BARVY["surface"])
        self.panely.pack(fill="both", expand=True)
        self.panely.columnconfigure(0, weight=1)
        self.panely.rowconfigure(0, weight=1, minsize=300)

        # Panel 1: tabulka časů
        # Dokud se nic neměřilo, ukazuje „prázdný stav“ s nápovědou;
        # po spuštění porovnání ho nahradí tabulka (_postav_tabulku).
        self.panel_casy = tk.Frame(self.panely, bg=BARVY["surface"])
        self.prazdno = tk.Frame(self.panel_casy, bg=BARVY["surface2"], highlightthickness=1,
                                highlightbackground=BARVY["border"])
        tk.Label(self.prazdno, text="Zatím nic nebylo změřeno", font=PISMO["bold"],
                 fg=BARVY["text"], bg=BARVY["surface2"]).pack(pady=(100, 4))
        tk.Label(self.prazdno, text="Připravte data, vyberte algoritmy a spusťte porovnání. "
                                    "Výsledky se ověří proti vestavěné funkci sorted().",
                 font=PISMO["small"], fg=BARVY["text2"], bg=BARVY["surface2"]).pack(pady=(0, 100))
        self.tabulka = tk.Frame(self.panel_casy, bg=BARVY["surface"])
        self.prazdno.pack(fill="both", expand=True)

        # Panel 2: vstupní data
        self.panel_vstup = tk.Frame(self.panely, bg=BARVY["surface"])
        self.seznam_vstup = SeznamHodnot(self.panel_vstup)
        self.seznam_vstup.pack(fill="both", expand=True)

        # Panel 3: seřazená čísla (výstup z sort.py)
        self.panel_serazeno = tk.Frame(self.panely, bg=BARVY["surface"])
        ovl = tk.Frame(self.panel_serazeno, bg=BARVY["surface"])
        ovl.pack(fill="x", pady=(0, 10))
        tk.Label(ovl, text="Seřadit algoritmem", font=PISMO["small"], fg=BARVY["text2"],
                 bg=BARVY["surface"]).pack(side="left", padx=(0, 8))
        self.cb_serad = ttk.Combobox(ovl, values=[a["nazev"] for a in ALGORITMY_INFO],
                                     state="readonly", font=PISMO["body"], width=16)
        self.cb_serad.current(0)
        self.cb_serad.pack(side="left")
        # current() vrátí pořadí vybrané položky -> podle něj najdeme klíč algoritmu
        self.btn_serad = Tlacitko(ovl, "Seřadit", lambda: self.zobraz_serazeno(
            ALGORITMY_INFO[self.cb_serad.current()]["klic"]), padx=14, pady=4)
        self.btn_serad.pack(side="left", padx=8)
        self.btn_kopirovat = Tlacitko(ovl, "Kopírovat", self.kopiruj_serazeno, "ghost",
                                      padx=12, pady=4)
        self.btn_kopirovat.pack(side="right")
        self.info_serazeno = tk.Frame(self.panel_serazeno, bg=BARVY["surface"])
        self.info_serazeno.pack(fill="x", pady=(0, 10))
        self.seznam_serazeno = SeznamHodnot(self.panel_serazeno, vyska=10)
        self.seznam_serazeno.pack(fill="both", expand=True)

        for p in (self.panel_casy, self.panel_vstup, self.panel_serazeno):
            p.grid(row=0, column=0, sticky="nsew")      # všechny do stejné buňky

        # Spodní řádek karty: věta o nejrychlejším algoritmu a tlačítka
        spodek = tk.Frame(k.obsah, bg=BARVY["surface"])
        spodek.pack(fill="x", pady=(14, 0))
        self.lbl_nejrychlejsi = tk.Label(spodek, font=PISMO["small"], fg=BARVY["text2"],
                                         bg=BARVY["surface"], anchor="w")
        self.lbl_nejrychlejsi.pack(side="left")
        self.btn_export = Tlacitko(spodek, "Export CSV", self.export_csv, padx=12, pady=4)
        self.btn_export.pack(side="right")
        # zobrazí se až po dokončeném měření (_konec_mereni)
        self.btn_jdi_serazeno = Tlacitko(spodek, "Zobrazit seřazené hodnoty",
                                         lambda: self.zalozky.vyber(2), "ghost", padx=12, pady=4)

        # záložky až nakonec – při vytvoření hned přepnou na první panel
        # (kdyby vznikly dřív, _prepni_panel by sahal na panely, které ještě neexistují)
        self.zalozky = Zalozky(k.hlavicka, ["Časy", "Vstup", "Seřazeno"], self._prepni_panel)
        self.zalozky.pack(side="right")
        return k

    def _paticka(self):
        """Patička: stavový řádek vlevo (co se právě stalo) a limity vpravo."""
        p = tk.Frame(self.stranka, bg=BARVY["bg"])
        p.pack(fill="x", pady=(18, 28))
        self.lbl_stav = tk.Label(p, text="Připraveno. Vygenerujte data a vyberte algoritmy.",
                                 font=PISMO["small"], fg=BARVY["text2"], bg=BARVY["bg"], anchor="w")
        self.lbl_stav.pack(side="left")
        tk.Label(p, text="Max. 3 000 prvků · animace max. 100 hodnot · třídí sort.py",
                 font=PISMO["tiny"], fg=BARVY["text3"], bg=BARVY["bg"]).pack(side="right")

    # --- stav tlačítek a zprávy ----------------------------------------------------
    def stav(self, text):
        """Zobrazí zprávu ve stavovém řádku dole (chyby, „Hotovo“ …)."""
        self.lbl_stav.config(text=text)

    def _vybrane(self):
        """Seznam klíčů vybraných algoritmů, např. ["bubble", "quick"]."""
        return [k.klic for k in self.karty_algo if k.vybrano]

    def _vyber_vse(self, vybrat):
        """Tlačítka „Vybrat vše“ (True) a „Zrušit výběr“ (False)."""
        for k in self.karty_algo:
            k.nastav(vybrat)
        self._obnov_tlacitka()

    def _obnov_tlacitka(self):
        """Zapne/vypne tlačítka podle aktuálního stavu aplikace.

        Volá se po každé změně (nová data, změna výběru, začátek a konec
        měření), takže tlačítka nikdy nedovolí nesmyslnou akci – např.
        porovnat bez dat nebo animovat dva algoritmy najednou.
        """
        vybrane = len(self._vybrane())
        ma_data = bool(self.hodnoty)
        self.btn_porovnat.nastav(povoleno=not self.bezi and ma_data and vybrane > 0)
        self.btn_animovat.nastav(povoleno=not self.bezi and ma_data and vybrane == 1)
        self.btn_serad.nastav(povoleno=not self.bezi and ma_data)
        self.btn_kopirovat.nastav(povoleno=self.serazeno is not None)
        self.btn_export.nastav(povoleno=bool(self.vysledky) and not self.bezi)
        if self.bezi:
            # během měření se ukáže Zastavit hned za tlačítkem Porovnat
            self.btn_stop.nastav(povoleno=True)
            self.btn_stop.pack(side="left", padx=(8, 0), after=self.btn_porovnat)
        else:
            self.btn_stop.pack_forget()       # pack_forget = schovat (widget dál existuje)
        # nápověda, proč tlačítka nejsou aktivní
        if self.bezi:
            napoveda = "Měření probíhá…"
        elif not ma_data:
            napoveda = "Nejdřív připravte data v kroku 01."
        elif vybrane == 0:
            napoveda = "Vyberte alespoň jeden algoritmus."
        elif vybrane > 1:
            napoveda = "Animace je dostupná pro právě jeden vybraný algoritmus."
        else:
            napoveda = ""
        self.lbl_napoveda.config(text=napoveda)

    def _prepni_panel(self, index):
        """Zobrazí panel podle záložky: 0 = Časy, 1 = Vstup, 2 = Seřazeno."""
        (self.panel_casy, self.panel_vstup, self.panel_serazeno)[index].tkraise()

    # --- příprava dat --------------------------------------------------------------
    def _cislo(self, spin, vychozi, od, do):
        """Přečte číslo ze Spinboxu a ohlídá ho.

        Neplatný text (např. „abc“) nahradí výchozí hodnotou, číslo mimo
        rozsah posune na nejbližší povolenou hodnotu a opravenou hodnotu
        zapíše zpět do políčka, aby uživatel viděl, s čím se počítá.
        """
        try:
            hodnota = int(spin.get())
        except ValueError:
            hodnota = vychozi
        hodnota = min(max(hodnota, od), do)
        spin.delete(0, "end")
        spin.insert(0, str(hodnota))
        return hodnota

    def generuj(self):
        """Tlačítko „Generovat data“."""
        pocet = self._cislo(self.sp_pocet, 1000, 2, MAX_PRVKU)
        seed = self._cislo(self.sp_seed, 0, 0, 999999)
        typ = TYPY[self.cb_typ.current()][0]           # klíč vybraného typu, např. "float"
        typ = "integer" if typ == "auto" else typ      # u generování znamená „auto“ celá čísla
        klic, nazev = ROZLOZENI[self.cb_rozlozeni.current()]
        # zdroj pro čip souhrnu: „náhodně, seed 42“ (text před pomlčkou, malými písmeny)
        self._nastav_data(generuj_hodnoty(typ, pocet, seed, klic), typ,
                          f"{nazev.split(' – ')[0].lower()}, seed {seed}")

    def nacti_soubor(self):
        """Tlačítko „Načíst .txt“ – uživatel vybere textový soubor.

        Aplikace rozpozná typ dat (rozpoznej_hodnoty) a v okně kontroly
        (OknoKontroly) se zeptá, jestli je chce uživatel takto třídit.
        Data se použijí až po kliknutí na „Ano, třídit“.
        """
        # Systémové okno pro výběr souboru. Vrátí cestu k souboru, nebo
        # prázdný řetězec, když ho uživatel zavře. filetypes = jen soubory .txt
        cesta = filedialog.askopenfilename(
            title="Načíst data ze souboru", filetypes=[("Textový soubor", "*.txt")])
        if not cesta:                    # uživatel dialog zavřel bez výběru
            return
        try:
            # utf-8-sig zvládne i soubory s neviditelnou značkou BOM na začátku
            # (ukládá ji např. Poznámkový blok ve Windows)
            with open(cesta, encoding="utf-8-sig") as f:
                typ, hodnoty, upozorneni = rozpoznej_hodnoty(f.read())
        # UnicodeDecodeError je podtřída ValueError, proto musí být zachycena dřív
        except (OSError, UnicodeDecodeError):
            chyba = "Soubor se nepodařilo přečíst (není to textový soubor?)."
        except ValueError as e:          # chybná data – zpráva z rozpoznej_hodnoty
            chyba = str(e)
        else:
            OknoKontroly(self, cesta.rsplit("/", 1)[-1], typ, hodnoty, upozorneni)  # jen název souboru
            return
        # Stavový řádek je až dole pod výsledky, chybu proto ukážeme v okně
        messagebox.showerror("Soubor nejde načíst", chyba, parent=self.root)

    def pouzij_rucne(self):
        """Tlačítko „Použít“ u ručního vstupu."""
        try:
            # "1.0" až "end" = celý obsah textového pole
            typ, hodnoty, upozorneni = rozpoznej_hodnoty(self.txt_rucne.get("1.0", "end"))
        except ValueError as chyba:
            self.stav(str(chyba))
            self.txt_rucne.focus_set()   # kurzor zpět do pole, ať jde chyba hned opravit
            return
        # Rozpoznaný typ uvidí uživatel v čipu pod polem (např. „celá čísla“)
        self._nastav_data(hodnoty, typ, "ruční vstup")
        if upozorneni:
            self.stav(upozorneni)

    def _nastav_data(self, hodnoty, typ, zdroj):
        """Společný konec všech tří způsobů přípravy dat.

        Uloží data, smaže staré výsledky (patřily k jiným datům),
        vypíše souhrn a vstupní hodnoty a obnoví tlačítka.
        """
        self.hodnoty, self.typ = hodnoty, typ
        self.vysledky, self.serazeno = {}, None
        for w in self.souhrn.winfo_children():    # smazat staré čipy
            w.destroy()
        for text in (f"{cesky_pocet(len(hodnoty))} hodnot", popis_typu(typ), zdroj):
            cip(self.souhrn, text).pack(side="left", padx=(0, 6))
        self.seznam_vstup.zobraz(hodnoty, typ)
        self._vycisti_vysledky()
        self._vycisti_serazeno()
        self._obnov_tlacitka()
        self.stav("Data jsou připravena. Vyberte algoritmy a spusťte porovnání, nebo animaci.")

    # --- tabulka výsledků ----------------------------------------------------------
    def _vycisti_vysledky(self):
        """Schová tabulku a ukáže znovu prázdný stav."""
        self.tabulka.pack_forget()
        self.prazdno.pack(fill="both", expand=True)
        self.lbl_nejrychlejsi.config(text="")
        self.btn_jdi_serazeno.pack_forget()

    def _postav_tabulku(self, klice):
        """Vytvoří tabulku s řádkem pro každý měřený algoritmus.

        Tabulka je mřížka (grid): řádek 0 = záhlaví, pak pro každý algoritmus
        dva řádky – tenká čára (oddělovač) a řádek s daty. Proto r = 2 * i + 1.
        Hodnoty jsou zatím „–“ a stav „Čeká“; vyplní je _vypln_radek.
        """
        for w in self.tabulka.winfo_children():   # smazat tabulku z minulého měření
            w.destroy()
        self.radky = {}
        t = self.tabulka
        t.columnconfigure(0, weight=1)            # sloupec s názvem zabere volné místo
        # záhlaví: (text, zarovnání) – "w" = vlevo (west), "e" = vpravo (east)
        for sl, (text, zarovnani) in enumerate((("Algoritmus", "w"), ("Medián", "e"),
                                                ("Minimum", "e"), ("Maximum", "e"), ("Stav", "w"))):
            tk.Label(t, text=text, font=PISMO["tiny"], fg=BARVY["text3"], bg=BARVY["surface"],
                     anchor=zarovnani).grid(row=0, column=sl, sticky="ew", padx=12, pady=(0, 8))
        for i, klic in enumerate(klice):
            r = 2 * i + 1
            tk.Frame(t, bg=BARVY["border"], height=1).grid(row=r, column=0, columnspan=5, sticky="ew")
            # Buňka s názvem: název, (skrytý) štítek „nejrychlejší“ a pruh relativní rychlosti
            jmeno = tk.Frame(t, bg=BARVY["surface"])
            jmeno.grid(row=r + 1, column=0, sticky="ew", padx=12, pady=10)
            horni = tk.Frame(jmeno, bg=BARVY["surface"])
            horni.pack(fill="x")
            tk.Label(horni, text=INFO[klic]["nazev"], font=PISMO["bold"], fg=BARVY["text"],
                     bg=BARVY["surface"]).pack(side="left")
            odznak_best = stitek(horni, "nejrychlejší", "best")   # zobrazí se jen u vítěze
            pruh = tk.Canvas(jmeno, width=160, height=4, bg=BARVY["surface"], highlightthickness=0)
            pruh.pack(anchor="w", pady=(6, 0))
            pruh.create_rectangle(0, 0, 160, 4, fill=BARVY["sunken"], outline="")   # šedá dráha
            bar = pruh.create_rectangle(0, 0, 0, 4, fill=BARVY["bar"], outline="")  # pruh, zatím 0 px
            bunky = []
            for sl in (1, 2, 3):          # medián, minimum, maximum
                lbl = tk.Label(t, text="–", font=PISMO["mono"], bg=BARVY["surface"], anchor="e",
                               fg=BARVY["text"] if sl == 1 else BARVY["text2"], width=10)
                lbl.grid(row=r + 1, column=sl, sticky="e", padx=12)
                bunky.append(lbl)
            odznak = stitek(t, "Čeká", "wait", "small")
            odznak.grid(row=r + 1, column=4, sticky="w", padx=12)
            # Uložíme si widgety řádku, abychom je později mohli měnit podle klíče
            self.radky[klic] = dict(bunky=bunky, odznak=odznak, pruh=pruh, bar=bar,
                                    best=odznak_best, delka=0.0)
        self.prazdno.pack_forget()
        self.tabulka.pack(fill="x")

    def _stav_radku(self, klic, text, ton):
        """Změní stavový štítek řádku (Čeká / Běží… / Ověřeno / Chyba / Zastaveno)."""
        bg, fg = TONY[ton]
        self.radky[klic]["odznak"].config(text=text, bg=BARVY[bg], fg=BARVY[fg])

    def _vypln_radek(self, klic, v):
        """Doplní do řádku naměřené časy a výsledek kontroly."""
        radek = self.radky[klic]
        for lbl, hodnota in zip(radek["bunky"], (v["median"], v["min"], v["max"])):
            lbl.config(text=formatuj_ms(hodnota))
        self._stav_radku(klic, "Ověřeno" if v["ok"] else "Chyba", "ok" if v["ok"] else "err")
        self._relativni_pruhy()

    def _relativni_pruhy(self):
        # délka = log(medián) / log(nejpomalejší medián), aby byly vidět i rychlé
        # Bez logaritmu by u 1500 ms vs. 5 ms byl rychlý pruh téměř neviditelný.
        # +1 zajistí, že log10 nedostane číslo menší než 1 (výsledek by byl záporný).
        maximum = max(math.log10(v["median"] + 1) for v in self.vysledky.values())
        for klic, v in self.vysledky.items():
            radek = self.radky[klic]
            cil = max(0.02, math.log10(v["median"] + 1) / maximum) if maximum > 0 else 1
            od = radek["delka"]               # dosavadní délka (0–1)
            radek["delka"] = cil

            # Pruh se plynule protáhne z délky `od` na `cil`.
            # Výchozí parametry (radek=radek, …) zamrazí hodnoty pro tento
            # průchod cyklem – jinak by všechny animace použily poslední řádek.
            def krok(t, radek=radek, od=od, cil=cil):
                radek["pruh"].coords(radek["bar"], 0, 0, 160 * (od + (cil - od) * t), 4)
            animuj(radek["pruh"], 450, krok)

    def _nejrychlejsi(self):
        """Najde nejrychlejší správně třídící algoritmus a vrátí jeho klíč.

        Zvýrazní ho v tabulce (štítek „nejrychlejší“, zelený pruh) a dole
        vypíše, kolikrát je rychlejší než nejpomalejší.
        """
        # seřazené dvojice (medián, klíč) – první je nejrychlejší, poslední nejpomalejší
        platne = sorted((v["median"], k) for k, v in self.vysledky.items() if v["ok"])
        for radek in self.radky.values():    # nejdřív zrušit staré zvýraznění
            radek["best"].pack_forget()
            radek["pruh"].itemconfig(radek["bar"], fill=BARVY["bar"])
        if not platne:
            self.lbl_nejrychlejsi.config(text="")
            return None
        median, klic = platne[0]
        text = f"Nejrychlejší: {INFO[klic]['nazev']} · medián {formatuj_ms(median)}"
        if len(platne) > 1:                  # zvýrazňovat má smysl jen při porovnání více algoritmů
            radek = self.radky[klic]
            radek["best"].pack(side="left", padx=(8, 0))
            radek["pruh"].itemconfig(radek["bar"], fill=BARVY["bar_done"])
            nejpomalejsi_med, nejpomalejsi = platne[-1]
            text += f" · {round(nejpomalejsi_med / median)}× rychlejší než {INFO[nejpomalejsi]['nazev']}"
        self.lbl_nejrychlejsi.config(text=text)
        return klic

    # --- měření (běží ve vlákně, aby okno nezamrzlo) -------------------------------
    def porovnej(self):
        """Tlačítko „Porovnat“ – připraví tabulku a spustí měřicí vlákno."""
        klice = self._vybrane()
        if self.bezi or not klice or not self.hodnoty:
            return
        opakovani = self._cislo(self.sp_opakovani, 3, 1, 10)
        self.bezi = True
        self.stop.clear()                # shodit vlajku z případného minulého zastavení
        self.vysledky = {}
        self._postav_tabulku(klice)
        self.lbl_nejrychlejsi.config(text="")
        self.btn_jdi_serazeno.pack_forget()
        self.zalozky.vyber(0)            # přepnout na záložku Časy
        self._obnov_tlacitka()
        self.stav("Porovnávám algoritmy v Pythonu…")
        # daemon=True = vlákno se ukončí samo, když uživatel zavře aplikaci.
        # list(self.hodnoty) = vlákno dostane vlastní kopii dat.
        threading.Thread(target=self._vlakno_mereni, daemon=True,
                         args=(klice, list(self.hodnoty), opakovani)).start()

    def _vlakno_mereni(self, klice, data, opakovani):
        """Pro každý algoritmus změří `opakovani` běhů na KOPII dat.
        Okno se z vlákna nesmí měnit přímo – výsledky jdou přes frontu.

        Zprávy do fronty jsou n-tice, první prvek říká druh zprávy:
          ("stav", klic, text, ton)  – změna stavového štítku řádku
          ("vysledek", klic, {...})  – naměřené časy jednoho algoritmu
          ("konec", zastaveno)       – měření skončilo (True = zastavil uživatel)
        """
        ocekavane = sorted(data)          # správný výsledek pro kontrolu
        for klic in klice:
            if self.stop.is_set():        # uživatel klikl na Zastavit
                self.fronta.put(("stav", klic, "Zastaveno", "wait"))
                continue
            self.fronta.put(("stav", klic, "Běží…", "run"))
            casy, ok = [], True
            for _ in range(opakovani):
                if self.stop.is_set():
                    break
                kopie = list(data)        # každý běh dostane neseřazenou kopii
                start = time.perf_counter()
                sort.ALGORITMY[klic](kopie)        # SAMOTNÉ TŘÍDĚNÍ – funkce ze sort.py
                casy.append((time.perf_counter() - start) * 1000)   # sekundy -> ms
                ok = ok and kopie == ocekavane     # stačí jedna chyba a výsledek je „Chyba“
            if not casy:                  # zastaveno dřív, než doběhl první běh
                self.fronta.put(("stav", klic, "Zastaveno", "wait"))
                continue
            # Medián je odolnější než průměr: jeden zpomalený běh (např. když
            # počítač zrovna dělá něco jiného) výsledek nezkreslí.
            self.fronta.put(("vysledek", klic, {"median": statistics.median(casy),
                                                "min": min(casy), "max": max(casy), "ok": ok}))
        self.fronta.put(("konec", self.stop.is_set()))

    def _vlakno_serazeni(self, klic, data):
        """Ve vlákně seřadí kopii dat a výsledek pošle do fronty (záložka Seřazeno)."""
        kopie = list(data)
        sort.ALGORITMY[klic](kopie)
        self.fronta.put(("serazeno", klic, kopie, kopie == sorted(data)))

    def _zpracuj_frontu(self):
        """Každých 40 ms vybere z fronty všechny zprávy a promítne je do okna.

        Běží v hlavním vlákně (spouští ho root.after), takže smí měnit widgety.
        get_nowait() vrátí zprávu hned, nebo vyhodí queue.Empty, když je
        fronta prázdná – tím cyklus while skončí.
        """
        try:
            while True:
                zprava = self.fronta.get_nowait()
                druh = zprava[0]
                if druh == "stav":
                    self._stav_radku(*zprava[1:])          # *zprava[1:] = rozbalí zbytek n-tice do parametrů
                elif druh == "vysledek":
                    self.vysledky[zprava[1]] = zprava[2]
                    self._vypln_radek(zprava[1], zprava[2])
                elif druh == "konec":
                    self._konec_mereni(zprava[1])
                elif druh == "serazeno":
                    self._zobraz_serazeno(*zprava[1:])
        except queue.Empty:
            pass
        self.root.after(40, self._zpracuj_frontu)          # naplánovat další kontrolu

    def _konec_mereni(self, zastaveno):
        """Úklid po skončení měření (přišla zpráva „konec“)."""
        self.bezi = False
        nejrychlejsi = self._nejrychlejsi()
        self._obnov_tlacitka()
        self.stav("Porovnání bylo zastaveno." if zastaveno
                  else "Hotovo. Výsledky jsou ověřené proti funkci sorted().")
        if nejrychlejsi and not zastaveno:
            # seřazená čísla od nejrychlejšího algoritmu rovnou do záložky Seřazeno
            self.zobraz_serazeno(nejrychlejsi)
            self.btn_jdi_serazeno.pack(side="right", padx=(0, 8))

    def zastav_mereni(self):
        """Tlačítko „Zastavit“ – nastaví vlajku, vlákno ji zkontroluje
        před dalším během a skončí. Právě běžící třídění se dokončí."""
        self.stop.set()
        self.btn_stop.nastav(povoleno=False)

    # --- záložka Seřazeno ----------------------------------------------------------
    def _vycisti_serazeno(self):
        """Vrátí záložku Seřazeno do výchozího stavu s nápovědou."""
        for w in self.info_serazeno.winfo_children():
            w.destroy()
        tk.Label(self.info_serazeno, text="Zvolte algoritmus a klikněte na Seřadit – nebo spusťte "
                                          "porovnání, výsledek nejrychlejšího se zobrazí sám.",
                 font=PISMO["small"], fg=BARVY["text3"], bg=BARVY["surface"]).pack(side="left")
        self.seznam_serazeno.zobraz([], self.typ)

    def zobraz_serazeno(self, klic):
        """Spustí seřazení dat algoritmem `klic` (tlačítko Seřadit nebo konec měření)."""
        if not self.hodnoty:
            self.stav("Nejdřív připravte data v kroku 01.")
            return
        # nastavit rozbalovací seznam na použitý algoritmus
        self.cb_serad.current([a["klic"] for a in ALGORITMY_INFO].index(klic))
        self.btn_serad.nastav(povoleno=False)    # znovu se zapne v _obnov_tlacitka
        # i jedno seřazení pomalým algoritmem může trvat – proto také vlákno
        threading.Thread(target=self._vlakno_serazeni, args=(klic, list(self.hodnoty)),
                         daemon=True).start()

    def _zobraz_serazeno(self, klic, pole, ok):
        """Vypíše seřazené hodnoty (zpráva „serazeno“ z fronty)."""
        self.serazeno = {"klic": klic, "pole": pole, "ok": ok}
        for w in self.info_serazeno.winfo_children():
            w.destroy()
        stitek(self.info_serazeno, "Ověřeno proti sorted()" if ok else "Chyba – neodpovídá sorted()",
               "ok" if ok else "err", "small").pack(side="left", padx=(0, 6))
        # pole je seřazené, takže nejmenší hodnota je první a největší poslední
        for text in (f"{INFO[klic]['nazev']} · {cesky_pocet(len(pole))} hodnot",
                     f"nejmenší {formatuj_hodnotu(pole[0], self.typ)}",
                     f"největší {formatuj_hodnotu(pole[-1], self.typ)}"):
            cip(self.info_serazeno, text).pack(side="left", padx=(0, 6))
        self.seznam_serazeno.zobraz(pole, self.typ)
        self._obnov_tlacitka()
        self.stav(f"Seřazené hodnoty ({INFO[klic]['nazev']}) jsou v záložce „Seřazeno“.")

    def kopiruj_serazeno(self):
        """Tlačítko „Kopírovat“ – seřazené hodnoty do schránky.
        Čísla a data oddělí mezerou, text novým řádkem (text může mít mezery)."""
        if not self.serazeno:
            return
        oddelovac = "\n" if self.typ == "text" else " "
        self.root.clipboard_clear()
        self.root.clipboard_append(oddelovac.join(formatuj_hodnotu(v, self.typ)
                                                  for v in self.serazeno["pole"]))
        self.stav("Seřazené hodnoty jsou zkopírované do schránky.")

    # --- export a animace ----------------------------------------------------------
    def export_csv(self):
        """Tlačítko „Export CSV“ – uloží tabulku výsledků do souboru."""
        if not self.vysledky:
            return
        cesta = filedialog.asksaveasfilename(title="Uložit výsledky", defaultextension=".csv",
                                             initialfile="porovnani-razeni.csv",
                                             filetypes=[("CSV", "*.csv")])
        if not cesta:                    # uživatel ukládání zrušil
            return
        try:
            # utf-8-sig + středník = Excel otevře soubor správně i s diakritikou
            # newline="" = modul csv si konce řádků řídí sám (jinak prázdné řádky)
            with open(cesta, "w", newline="", encoding="utf-8-sig") as f:
                zapis = csv.writer(f, delimiter=";")
                zapis.writerow(["Algoritmus", "Medián (ms)", "Minimum (ms)", "Maximum (ms)", "Stav"])
                for info in ALGORITMY_INFO:          # pořadí řádků jako v rozhraní
                    v = self.vysledky.get(info["klic"])
                    if v:                            # jen algoritmy, které se měřily
                        zapis.writerow([info["nazev"], f"{v['median']:.4f}", f"{v['min']:.4f}",
                                        f"{v['max']:.4f}", "Ověřeno" if v["ok"] else "Chyba"])
        except OSError:
            self.stav("CSV soubor se nepodařilo uložit.")
            return
        self.stav("CSV soubor byl uložen.")

    def animuj(self):
        """Tlačítko „Animovat“ – nechá sort.py zaznamenat kroky a otevře okno animace."""
        klice = self._vybrane()
        if len(klice) != 1 or not self.hodnoty:
            return
        vzorek, poznamka = self.hodnoty, f"{len(self.hodnoty)} hodnot"
        if len(vzorek) > MAX_ANIMACE:
            # rovnoměrná ukázka 100 hodnot z celých dat
            # (každá krok-tá hodnota, např. u 1000 hodnot každá desátá)
            krok = len(vzorek) / MAX_ANIMACE
            vzorek = [self.hodnoty[int(i * krok)] for i in range(MAX_ANIMACE)]
            poznamka = f"ukázka {MAX_ANIMACE} z {cesky_pocet(len(self.hodnoty))} hodnot"
        snimky = []
        # Předáním seznamu `snimky` jako parametru `kroky` zapneme v sort.py
        # záznam: algoritmus do něj při třídění připíše každý krok.
        sort.ALGORITMY[klice[0]](list(vzorek), snimky)     # sort.py zaznamená každý krok
        self.stav(f"Animace připravena: {cesky_pocet(len(snimky))} kroků.")
        OknoAnimace(self, INFO[klice[0]], snimky, self.typ, poznamka)


# ---------------------------------------------------------------------------
# 7) Spuštění
# ---------------------------------------------------------------------------

def main():
    """Vytvoří okno, připraví písma, postaví aplikaci a spustí hlavní smyčku."""
    root = tk.Tk()           # hlavní okno Tkinteru
    priprav_pisma(root)      # písma až po vytvoření okna (dřív je Tk nezná)
    SortApp(root)
    root.mainloop()          # smyčka událostí – běží, dokud uživatel okno nezavře


# Blok se provede jen při spuštění `python3 app.py`, ne při importu souboru.
if __name__ == "__main__":
    main()
