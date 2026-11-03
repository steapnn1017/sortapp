"""
sort.py – logika třídění pro aplikaci SortApp
=============================================

Soubor obsahuje šest třídících algoritmů implementovaných jako funkce:

    1. bubble_sort     – bublinkové třídění       O(n²)
    2. selection_sort  – třídění výběrem          O(n²)
    3. insertion_sort  – třídění vkládáním        O(n²), nejlépe O(n)
    4. merge_sort      – třídění sléváním         O(n log n)
    5. quick_sort      – rychlé třídění           O(n log n) v průměru
    6. heap_sort       – třídění haldou           O(n log n)

Všechny funkce mají stejné rozhraní:

    funkce(pole, kroky=None) -> pole

  * `pole`  – Python seznam (list) čísel, který se seřadí VZESTUPNĚ
              přímo na místě (in-place), tzn. mění se původní seznam.
              Funkce ho pro pohodlí zároveň vrací.
  * `kroky` – nepovinný seznam. Když ho předáme, algoritmus do něj
              zapisuje jednotlivé kroky (co právě porovnává / prohazuje).
              Z těchto záznamů webové rozhraní (index.html) kreslí animaci.
              Při měření času se `kroky` nepředávají (jsou None), takže
              záznam nic nezdržuje.

Jak soubor spustit:

    python3 app.py           -> desktopová aplikace (Tkinter), která volá
                                funkce z tohoto souboru
    python3 sort.py          -> ukázka a test všech algoritmů v terminálu
    python3 sort.py --web    -> spustí lokální server a otevře index.html,
                                které tento soubor načte a volá jeho funkce
                                (v prohlížeči běží Python přes Pyodide)
"""

import json
import random
import sys
import time

# Merge sort i quick sort jsou rekurzivní (funkce volá sama sebe).
# Python má výchozí limit hloubky rekurze 1000 – pro jistotu ho zvýšíme,
# i když při rozumné volbě pivota hloubka roste jen jako log2(n).
sys.setrecursionlimit(10_000)


# ---------------------------------------------------------------------------
# Pomocná funkce pro záznam kroků (používá ji jen animace)
# ---------------------------------------------------------------------------

def _krok(kroky, pole, aktivni, hotovo, zprava):
    """Uloží jeden snímek průběhu třídění.

    kroky   – seznam, do kterého se ukládá (když je None, nic se neděje)
    pole    – aktuální stav tříděného pole (uloží se jeho KOPIE, protože
              algoritmus pole dál mění a my chceme zachytit tento okamžik)
    aktivni – indexy prvků, se kterými algoritmus právě pracuje (oranžově)
    hotovo  – indexy prvků, které už jsou na svém konečném místě (zeleně)
    zprava  – lidsky čitelný popis, co se v tomto kroku děje
    """
    if kroky is None:
        return
    kroky.append({
        "pole": list(pole),
        "aktivni": list(aktivni),
        "hotovo": sorted(hotovo),
        "zprava": zprava,
    })


# ===========================================================================
# 1) BUBBLE SORT – bublinkové třídění
# ===========================================================================
#
# PRINCIP:
#   Algoritmus opakovaně prochází pole zleva doprava a porovnává vždy dva
#   SOUSEDNÍ prvky. Pokud je levý větší než pravý, prohodí je.
#   Díky tomu se největší prvek při každém průchodu "probublá" (jako bublina
#   ve vodě) až na konec pole. Po 1. průchodu je tedy největší prvek na
#   posledním místě, po 2. průchodu druhý největší na předposledním atd.
#
#   Konec pole se tak postupně zaplňuje seřazenými prvky, a proto každý
#   další průchod může skončit o jeden prvek dříve.
#
#   Optimalizace: pokud během celého průchodu nedošlo k žádnému prohození,
#   pole už je seřazené a můžeme skončit dřív (u seřazeného vstupu stačí
#   jediný průchod -> nejlepší případ O(n)).
#
# PŘÍKLAD (1. průchod pole [5, 1, 4, 2]):
#   [5, 1, 4, 2]  5 > 1 -> prohodit -> [1, 5, 4, 2]
#   [1, 5, 4, 2]  5 > 4 -> prohodit -> [1, 4, 5, 2]
#   [1, 4, 5, 2]  5 > 2 -> prohodit -> [1, 4, 2, 5]   <- 5 je na svém místě
#
# SLOŽITOST:  nejhorší i průměrná O(n²), nejlepší O(n)
# PAMĚŤ:      O(1) – třídí na místě, nepotřebuje další pole
# STABILITA:  stabilní (stejné hodnoty si zachovají původní pořadí,
#             protože prohazujeme jen při ostrém ">" )
# ---------------------------------------------------------------------------

def bubble_sort(pole, kroky=None):
    """Seřadí `pole` vzestupně bublinkovým tříděním (na místě)."""
    n = len(pole)                 # počet prvků v poli
    hotovo = set()                # indexy, které jsou už na konečném místě
    _krok(kroky, pole, [], hotovo, "Start: pole je připraveno k třídění.")

    # Vnější cyklus = jeden PRŮCHOD polem. Stačí n-1 průchodů, protože
    # když je n-1 největších prvků na místě, zbývající nejmenší je taky.
    for i in range(n - 1):
        prohozeno = False         # zaznamenáme, zda v průchodu došlo k výměně

        # Vnitřní cyklus porovnává sousedy pole[j] a pole[j+1].
        # Posledních `i` prvků už je seřazených (probublaly tam v minulých
        # průchodech), proto jdeme jen do n-1-i.
        for j in range(n - 1 - i):
            _krok(kroky, pole, [j, j + 1], hotovo,
                  f"Porovnávám sousední prvky na pozicích {j + 1} a {j + 2}.")

            if pole[j] > pole[j + 1]:
                # Prvky jsou ve špatném pořadí -> prohodíme je.
                # Python umí prohodit dvě hodnoty jedním přiřazením (tuple).
                pole[j], pole[j + 1] = pole[j + 1], pole[j]
                prohozeno = True
                _krok(kroky, pole, [j, j + 1], hotovo,
                      "Levý prvek je větší – prohazuji je.")

        # Po průchodu je největší prvek z nesetříděné části na pozici n-1-i.
        hotovo.add(n - 1 - i)
        _krok(kroky, pole, [], hotovo,
              f"Konec průchodu: pozice {n - i} obsahuje svou konečnou hodnotu.")

        # Žádná výměna = všechny sousední dvojice jsou v pořádku = hotovo.
        if not prohozeno:
            break

    hotovo.update(range(n))
    _krok(kroky, pole, [], hotovo, "Hotovo, pole je seřazené.")
    return pole


# ===========================================================================
# 2) SELECTION SORT – třídění výběrem
# ===========================================================================
#
# PRINCIP:
#   Pole si myšleně rozdělíme na dvě části:
#       [ seřazená část | neseřazená část ]
#   Na začátku je seřazená část prázdná. V každém kroku v NESEŘAZENÉ části
#   najdeme nejmenší prvek (minimum) a prohodíme ho s prvním prvkem
#   neseřazené části. Tím se seřazená část prodlouží o jeden prvek.
#   Opakujeme, dokud neseřazená část nezmizí.
#
#   Na rozdíl od bubble sortu dělá selection sort v každém průchodu nejvýše
#   JEDNU výměnu (celkem max. n-1 výměn), porovnání je ale vždy stejně
#   mnoho – i když je pole už seřazené.
#
# PŘÍKLAD pole [29, 10, 14, 37, 13]:
#   minimum z [29,10,14,37,13] je 10  -> prohodit s 29 -> [10 | 29,14,37,13]
#   minimum z [29,14,37,13]    je 13  -> prohodit s 29 -> [10,13 | 14,37,29]
#   minimum z [14,37,29]       je 14  -> už je na místě -> [10,13,14 | 37,29]
#   minimum z [37,29]          je 29  -> prohodit s 37 -> [10,13,14,29 | 37]
#
# SLOŽITOST:  O(n²) ve všech případech (vždy n(n-1)/2 porovnání)
# PAMĚŤ:      O(1) – třídí na místě
# STABILITA:  nestabilní (dlouhý skok při výměně může přeskočit stejnou
#             hodnotu a změnit pořadí shodných prvků)
# ---------------------------------------------------------------------------

def selection_sort(pole, kroky=None):
    """Seřadí `pole` vzestupně tříděním výběrem (na místě)."""
    n = len(pole)
    hotovo = set()
    _krok(kroky, pole, [], hotovo, "Start: pole je připraveno k třídění.")

    # i = index, kde začíná neseřazená část (a kam patří další minimum).
    for i in range(n - 1):
        # Předpokládáme, že minimum je první prvek neseřazené části...
        index_min = i
        _krok(kroky, pole, [i], hotovo,
              f"Hledám nejmenší prvek od pozice {i + 1} dál.")

        # ...a projdeme zbytek pole, jestli nenajdeme menší.
        for j in range(i + 1, n):
            _krok(kroky, pole, [index_min, j], hotovo,
                  "Porovnávám dosavadní minimum s dalším prvkem.")
            if pole[j] < pole[index_min]:
                index_min = j     # našli jsme nové, menší minimum

        # Minimum přesuneme na začátek neseřazené části (pokud už tam není).
        if index_min != i:
            pole[i], pole[index_min] = pole[index_min], pole[i]
            _krok(kroky, pole, [i, index_min], hotovo,
                  f"Prohazuji minimum na pozici {i + 1}.")

        # Pozice i teď obsahuje svou konečnou hodnotu – seřazená část roste.
        hotovo.add(i)

    hotovo.update(range(n))
    _krok(kroky, pole, [], hotovo, "Hotovo, pole je seřazené.")
    return pole


# ===========================================================================
# 3) INSERTION SORT – třídění vkládáním
# ===========================================================================
#
# PRINCIP:
#   Funguje jako řazení karet v ruce. Pole má opět dvě části:
#       [ seřazená část | neseřazená část ]
#   Na začátku tvoří seřazenou část jen první prvek. V každém kroku vezmeme
#   první prvek neseřazené části (tzv. KLÍČ) a VLOŽÍME ho na správné místo
#   do seřazené části: větší prvky posuneme o jednu pozici doprava, aby
#   pro klíč vzniklo volné místo.
#
#   Na rozdíl od selection sortu prvky seřazené části ještě nejsou na
#   KONEČNÝCH pozicích – pozdější menší klíč je může posunout doprava.
#   Velkou výhodou je rychlost na téměř seřazených datech: když je klíč
#   už na správném místě, stačí jediné porovnání.
#
# PŘÍKLAD pole [12, 11, 13, 5]:
#   klíč 11: 12 > 11 -> posunout 12 -> [11, 12 | 13, 5]
#   klíč 13: 12 < 13 -> zůstává     -> [11, 12, 13 | 5]
#   klíč 5:  posunout 13, 12, 11    -> [5, 11, 12, 13]
#
# SLOŽITOST:  nejhorší i průměrná O(n²), nejlepší O(n) (seřazený vstup)
# PAMĚŤ:      O(1) – třídí na místě
# STABILITA:  stabilní (posouváme jen prvky OSTŘE větší než klíč)
# ---------------------------------------------------------------------------

def insertion_sort(pole, kroky=None):
    """Seřadí `pole` vzestupně tříděním vkládáním (na místě)."""
    n = len(pole)
    hotovo = set()     # zeleně až na konci – pozice se ještě mohou posouvat
    _krok(kroky, pole, [], hotovo, "Start: pole je připraveno k třídění.")

    # i = index klíče, který právě vkládáme. Prvek na indexu 0 tvoří
    # na začátku seřazenou část sám, proto začínáme od 1.
    for i in range(1, n):
        klic = pole[i]
        j = i - 1          # ukazatel do seřazené části (jdeme zprava doleva)
        _krok(kroky, pole, [i], hotovo,
              f"Beru klíč {klic} z pozice {i + 1} a hledám mu místo vlevo.")

        # Dokud je prvek vlevo větší než klíč, posuneme ho o jedno doprava.
        while j >= 0 and pole[j] > klic:
            _krok(kroky, pole, [j, j + 1], hotovo,
                  f"{pole[j]} je větší než klíč – posouvám ho doprava.")
            pole[j + 1] = pole[j]
            j -= 1

        # Volné místo je na j+1 – sem klíč vložíme.
        pole[j + 1] = klic
        _krok(kroky, pole, [j + 1], hotovo,
              f"Vkládám klíč na pozici {j + 2}.")

    hotovo.update(range(n))
    _krok(kroky, pole, [], hotovo, "Hotovo, pole je seřazené.")
    return pole


# ===========================================================================
# 4) MERGE SORT – třídění sléváním
# ===========================================================================
#
# PRINCIP – metoda "ROZDĚL A PANUJ" (divide and conquer):
#   1. ROZDĚL:  pole rozdělíme na dvě poloviny.
#   2. PANUJ:   každou polovinu seřadíme – rekurzivně stejným algoritmem.
#               Rekurze končí u úseku s 0 nebo 1 prvkem, ten je seřazený
#               sám od sebe.
#   3. SLEJ:    dvě seřazené poloviny SLOUČÍME (merge) do jednoho
#               seřazeného celku.
#
#   Slévání je klíčová operace: máme dvě seřazené posloupnosti a v každém
#   kroku porovnáme jejich PRVNÍ (nejmenší) dosud nepoužité prvky. Menší
#   z nich zapíšeme do výsledku a posuneme se v jeho posloupnosti o jedno
#   dál. Když jedna posloupnost dojde, zbytek druhé jen opíšeme.
#
# PŘÍKLAD pole [38, 27, 43, 3]:
#   rozdělení:   [38, 27]        [43, 3]
#                [38] [27]       [43] [3]
#   slévání:     [27, 38]        [3, 43]
#                    [3, 27, 38, 43]
#
#   Pole se půlí, takže úrovní rekurze je log2(n); na každé úrovni se
#   dohromady slévá všech n prvků -> celkem n * log2(n) operací.
#
# SLOŽITOST:  O(n log n) ve všech případech
# PAMĚŤ:      O(n) – při slévání potřebuje pomocné kopie polovin
# STABILITA:  stabilní (při rovnosti bereme prvek z LEVÉ poloviny: "<=")
# ---------------------------------------------------------------------------

def merge_sort(pole, kroky=None):
    """Seřadí `pole` vzestupně tříděním sléváním (výsledek zapíše do `pole`)."""
    n = len(pole)
    hotovo = set()
    _krok(kroky, pole, [], hotovo, "Start: pole je připraveno k třídění.")

    def serad_usek(zacatek, konec):
        """Rekurzivně seřadí úsek pole[zacatek:konec] (konec se nepočítá)."""
        # Základní případ rekurze: úsek s 0 nebo 1 prvkem je už seřazený.
        if konec - zacatek <= 1:
            return

        # ROZDĚL: najdeme střed úseku (// je celočíselné dělení).
        stred = (zacatek + konec) // 2

        # PANUJ: seřadíme levou a pravou polovinu (rekurzivní volání).
        serad_usek(zacatek, stred)
        serad_usek(stred, konec)

        # SLEJ: obě seřazené poloviny sloučíme dohromady.
        slej(zacatek, stred, konec)

    def slej(zacatek, stred, konec):
        """Sloučí dvě seřazené poloviny pole[zacatek:stred] a pole[stred:konec]."""
        # Zkopírujeme obě poloviny, protože do `pole` budeme přepisovat.
        leva = pole[zacatek:stred]
        prava = pole[stred:konec]

        i = 0             # ukazatel do levé poloviny
        j = 0             # ukazatel do pravé poloviny
        k = zacatek       # kam v `pole` zapisujeme další (nejmenší) prvek

        # Dokud mají obě poloviny nepoužité prvky, bereme vždy ten menší.
        while i < len(leva) and j < len(prava):
            _krok(kroky, pole, [zacatek + i, stred + j], hotovo,
                  "Slévám: porovnávám první prvky obou seřazených polovin.")
            if leva[i] <= prava[j]:       # "<=" zajišťuje stabilitu
                pole[k] = leva[i]
                i += 1
            else:
                pole[k] = prava[j]
                j += 1
            _krok(kroky, pole, [k], hotovo,
                  f"Na pozici {k + 1} zapisuji menší z obou prvků.")
            k += 1

        # Jedna polovina došla – zbytek druhé je už seřazený, jen ho opíšeme.
        while i < len(leva):
            pole[k] = leva[i]
            _krok(kroky, pole, [k], hotovo, "Doplňuji zbytek levé poloviny.")
            i += 1
            k += 1
        while j < len(prava):
            pole[k] = prava[j]
            _krok(kroky, pole, [k], hotovo, "Doplňuji zbytek pravé poloviny.")
            j += 1
            k += 1

    serad_usek(0, n)

    hotovo.update(range(n))
    _krok(kroky, pole, [], hotovo, "Hotovo, pole je seřazené.")
    return pole


# ===========================================================================
# 5) QUICK SORT – rychlé třídění
# ===========================================================================
#
# PRINCIP – také "ROZDĚL A PANUJ", ale práce se dělá PŘED rekurzí:
#   1. Vybereme jeden prvek pole – tzv. PIVOT.
#   2. ROZDĚLENÍ (partition): přeskládáme pole tak, aby
#          vlevo od pivota byly prvky MENŠÍ než pivot,
#          vpravo od pivota prvky VĚTŠÍ nebo ROVNÉ.
#      Pivot tím stojí na své KONEČNÉ pozici a už se nikdy nepohne.
#   3. Rekurzivně stejně seřadíme levou a pravou část.
#   Na rozdíl od merge sortu se části nemusí slévat – jakmile jsou obě
#   seřazené, je seřazené celé pole.
#
#   Rozdělení (Lomutovo schéma):
#     - pivot přesuneme na konec úseku,
#     - `i` ukazuje na hranici "menších" prvků (vše před `i` je < pivot),
#     - procházíme úsek indexem `j`; když je pole[j] < pivot, prohodíme
#       ho na pozici `i` a hranici `i` posuneme o jedno doprava,
#     - nakonec pivot prohodíme na pozici `i` – mezi menší a větší prvky.
#
#   Volba pivota: bereme NÁHODNÝ prvek. Kdybychom brali vždy poslední
#   prvek, u již seřazeného pole by se pole dělilo nejhůř možně (0 : n-1)
#   a algoritmus by spadl na O(n²). Náhodný pivot tomu prakticky zabrání.
#
# PŘÍKLAD pole [7, 2, 9, 4, 5], pivot = 5:
#   po rozdělení: [2, 4] 5 [9, 7]  -> 5 je na konečné pozici
#   rekurze:      [2, 4]   a   [7, 9]  -> výsledek [2, 4, 5, 7, 9]
#
# SLOŽITOST:  průměrně O(n log n), nejhorší O(n²) (velmi nepravděpodobné
#             při náhodném pivotu)
# PAMĚŤ:      O(log n) – zásobník rekurze, jinak třídí na místě
# STABILITA:  nestabilní (výměny na velké vzdálenosti)
# ---------------------------------------------------------------------------

def quick_sort(pole, kroky=None):
    """Seřadí `pole` vzestupně rychlým tříděním (na místě)."""
    n = len(pole)
    hotovo = set()
    _krok(kroky, pole, [], hotovo, "Start: pole je připraveno k třídění.")

    def rozdel(zacatek, konec):
        """Rozdělí úsek pole[zacatek..konec] (včetně) kolem náhodného pivota.
        Vrátí konečný index pivota."""
        # Náhodně vybraný pivot přesuneme na konec úseku, ať nám nepřekáží.
        p = random.randint(zacatek, konec)
        pole[p], pole[konec] = pole[konec], pole[p]
        pivot = pole[konec]
        _krok(kroky, pole, [konec], hotovo,
              f"Pivot = {pivot} (náhodně vybraný, přesunut na konec úseku).")

        i = zacatek       # hranice: vše na indexech < i je menší než pivot
        for j in range(zacatek, konec):
            _krok(kroky, pole, [j, konec], hotovo,
                  "Porovnávám prvek s pivotem.")
            if pole[j] < pivot:
                # Menší prvek patří doleva – prohodíme ho na hranici
                # a hranici posuneme.
                pole[i], pole[j] = pole[j], pole[i]
                _krok(kroky, pole, [i, j], hotovo,
                      "Prvek je menší než pivot – přesouvám ho doleva.")
                i += 1

        # Pivot vložíme mezi menší (vlevo) a větší/rovné (vpravo) prvky.
        pole[i], pole[konec] = pole[konec], pole[i]
        hotovo.add(i)
        _krok(kroky, pole, [i], hotovo,
              f"Pivot je na své konečné pozici {i + 1}.")
        return i

    def serad_usek(zacatek, konec):
        """Rekurzivně seřadí úsek pole[zacatek..konec] (včetně)."""
        # Úsek s 0 nebo 1 prvkem je seřazený – konec rekurze.
        if zacatek >= konec:
            if zacatek == konec:
                hotovo.add(zacatek)
            return
        index_pivota = rozdel(zacatek, konec)
        serad_usek(zacatek, index_pivota - 1)    # levá část (menší prvky)
        serad_usek(index_pivota + 1, konec)      # pravá část (větší prvky)

    serad_usek(0, n - 1)

    hotovo.update(range(n))
    _krok(kroky, pole, [], hotovo, "Hotovo, pole je seřazené.")
    return pole


# ===========================================================================
# 6) HEAP SORT – třídění haldou
# ===========================================================================
#
# PRINCIP:
#   Využívá datovou strukturu MAX-HALDA (max-heap). Je to binární strom
#   uložený přímo v poli: prvek na indexu i má děti na indexech 2i+1
#   a 2i+2. Platí pravidlo haldy: každý rodič je >= svým dětem, takže
#   NEJVĚTŠÍ prvek je vždy v kořeni, tedy na indexu 0.
#
#   Algoritmus má dvě fáze:
#   1. STAVBA HALDY: z neseřazeného pole uděláme max-haldu. Procházíme
#      rodiče odspodu (od posledního rodiče n//2-1 až ke kořeni) a každého
#      "probubláme dolů" (sift down) – dokud je menší než větší z dětí,
#      prohodíme ho s ním.
#   2. TŘÍDĚNÍ: kořen (maximum) prohodíme s posledním prvkem haldy –
#      maximum je tím na své konečné pozici na konci pole. Halda se
#      zmenší o jeden prvek, nový kořen probubláme dolů a opakujeme.
#
#   Je to vlastně selection sort, který minimum/maximum nehledá lineárně,
#   ale díky haldě ho najde v čase O(log n).
#
# PŘÍKLAD pole [4, 10, 3, 5, 1]:
#   stavba haldy:  [10, 5, 3, 4, 1]          (10 je v kořeni)
#   10 <-> 1:      [1, 5, 3, 4 | 10] -> probublat 1 -> [5, 4, 3, 1 | 10]
#   5 <-> 1:       [1, 4, 3 | 5, 10] -> probublat 1 -> [4, 1, 3 | 5, 10]
#   ... až          [1, 3, 4, 5, 10]
#
# SLOŽITOST:  O(n log n) ve všech případech
# PAMĚŤ:      O(1) – třídí na místě (halda je přímo v poli)
# STABILITA:  nestabilní (prohazování kořene s koncem mění pořadí shodných)
# ---------------------------------------------------------------------------

def heap_sort(pole, kroky=None):
    """Seřadí `pole` vzestupně tříděním haldou (na místě)."""
    n = len(pole)
    hotovo = set()
    _krok(kroky, pole, [], hotovo, "Start: pole je připraveno k třídění.")

    def probublej_dolu(rodic, velikost):
        """Posune prvek z indexu `rodic` dolů, aby platilo pravidlo haldy.
        `velikost` = počet prvků, které do haldy ještě patří."""
        while True:
            levy = 2 * rodic + 1
            pravy = 2 * rodic + 2
            nejvetsi = rodic

            # Najdeme největší z trojice rodič – levé dítě – pravé dítě.
            if levy < velikost:
                _krok(kroky, pole, [rodic, levy], hotovo,
                      "Porovnávám rodiče s levým potomkem.")
                if pole[levy] > pole[nejvetsi]:
                    nejvetsi = levy
            if pravy < velikost:
                _krok(kroky, pole, [nejvetsi, pravy], hotovo,
                      "Porovnávám s pravým potomkem.")
                if pole[pravy] > pole[nejvetsi]:
                    nejvetsi = pravy

            # Rodič je největší -> pravidlo haldy platí, končíme.
            if nejvetsi == rodic:
                return

            # Jinak rodiče prohodíme s větším dítětem a pokračujeme níž.
            pole[rodic], pole[nejvetsi] = pole[nejvetsi], pole[rodic]
            _krok(kroky, pole, [rodic, nejvetsi], hotovo,
                  "Potomek je větší – prohazuji ho s rodičem.")
            rodic = nejvetsi

    # 1. fáze: stavba max-haldy. Listy (druhá polovina pole) jsou haldou
    #    samy o sobě, proto začínáme od posledního rodiče.
    for i in range(n // 2 - 1, -1, -1):
        probublej_dolu(i, n)
    _krok(kroky, pole, [0] if n else [], hotovo,
          "Halda je postavená – největší prvek je na první pozici.")

    # 2. fáze: maximum (kořen) přesuneme na konec a haldu zmenšíme.
    for konec in range(n - 1, 0, -1):
        pole[0], pole[konec] = pole[konec], pole[0]
        hotovo.add(konec)
        _krok(kroky, pole, [0, konec], hotovo,
              f"Přesouvám maximum z kořene na pozici {konec + 1}.")
        probublej_dolu(0, konec)

    hotovo.update(range(n))
    _krok(kroky, pole, [], hotovo, "Hotovo, pole je seřazené.")
    return pole


# ===========================================================================
# Rozhraní pro webovou aplikaci (index.html)
# ===========================================================================
# index.html načte tento soubor do Pyodide (Python v prohlížeči) a volá
# následující funkce. Samotné třídění tedy vždy provádí kód výše.

# Registr algoritmů: klíč z webového rozhraní -> Python funkce.
ALGORITMY = {
    "bubble": bubble_sort,
    "selection": selection_sort,
    "insertion": insertion_sort,
    "merge": merge_sort,
    "quick": quick_sort,
    "heap": heap_sort,
}

# Data, nad kterými se měří (nastaví je webové rozhraní).
_data = []


def nastav_data(data_json):
    """Uloží vstupní data (JSON seznam čísel) pro následná měření."""
    global _data
    _data = json.loads(data_json)
    return len(_data)


def zmer_jednou(klic):
    """Jednou seřadí KOPII dat zvoleným algoritmem a změří čas.

    Vrací JSON: {"ms": doba v milisekundách, "ok": True/False}
    `ok` říká, zda výsledek odpovídá vestavěné funkci sorted() – tím
    ověřujeme, že algoritmus třídí správně.
    """
    kopie = list(_data)                   # originál necháme netknutý
    start = time.perf_counter()           # přesné měření času
    ALGORITMY[klic](kopie)
    konec = time.perf_counter()
    return json.dumps({
        "ms": (konec - start) * 1000,
        "ok": kopie == sorted(_data),
    })


def serad_data(klic):
    """Seřadí KOPII dat zvoleným algoritmem a vrátí výsledek.

    Vrací JSON: {"pole": seřazený seznam, "ok": True/False}
    Webové rozhraní z něj zobrazí seřazená čísla v záložce „Seřazeno“.
    """
    kopie = list(_data)
    ALGORITMY[klic](kopie)
    return json.dumps({"pole": kopie, "ok": kopie == sorted(_data)})


def kroky_json(klic, data_json):
    """Seřadí malou ukázku dat a vrátí JSON se všemi kroky pro animaci."""
    kroky = []
    ALGORITMY[klic](json.loads(data_json), kroky)
    return json.dumps(kroky)


# ===========================================================================
# Spuštění z terminálu
# ===========================================================================

def _ukazka():
    """Předvede a otestuje všechny algoritmy v terminálu."""
    ukazka = [38, 27, 43, 3, 9, 82, 10]
    print("Vstup:", ukazka)
    for funkce in ALGORITMY.values():
        print(f"  {funkce.__name__:15} -> {funkce(list(ukazka))}")

    # Automatický test: náhodná data, seřazená, obrácená a s duplicitami.
    testy = [
        [],
        [1],
        [random.randint(-1000, 1000) for _ in range(500)],
        list(range(300)),
        list(range(300, 0, -1)),
        [random.choice([1, 2, 3]) for _ in range(300)],
        [random.uniform(-1, 1) for _ in range(300)],
    ]
    for klic, funkce in ALGORITMY.items():
        for data in testy:
            assert funkce(list(data)) == sorted(data), klic
    print("Test: všechny algoritmy třídí správně.")

    # Orientační porovnání rychlosti na 2000 náhodných číslech.
    data = [random.randint(0, 1_000_000) for _ in range(2000)]
    nastav_data(json.dumps(data))
    print("\nČas pro 2000 náhodných čísel:")
    for klic, funkce in ALGORITMY.items():
        vysledek = json.loads(zmer_jednou(klic))
        print(f"  {funkce.__name__:15} {vysledek['ms']:9.2f} ms")


def _spust_web():
    """Spustí lokální HTTP server ve složce projektu a otevře index.html.

    Prohlížeč smí načíst sort.py jen přes http://, ne přes file://,
    proto je potřeba malý server.
    """
    import functools
    import http.server
    import os
    import webbrowser

    slozka = os.path.dirname(os.path.abspath(__file__))
    port = 8000
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=slozka)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        url = f"http://127.0.0.1:{port}/index.html"
        print(f"SortApp běží na {url}  (ukončení: Ctrl+C)")
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer ukončen.")


if __name__ == "__main__":
    if "--web" in sys.argv:
        _spust_web()
    else:
        _ukazka()
