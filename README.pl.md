*Przeczytaj w: [English](README.md) | [Polski](README.pl.md)*

# Launchpad Mini MK3 – Edytor Pixel Art

Webowy edytor pixel art dla Novation Launchpad Mini MK3 z podglądem na żywo na sprzęcie i zestawem narzędzi CLI do animacji i konwersji obrazów.

## Funkcje

- **Edytor webowy** (`index.html`) – rysuj pixel art na siatce 8×8 z pełną 128-kolorową paletą Launchpada
- **Podgląd na żywo** – obserwuj swoją grafikę na fizycznym Launchpadzie w czasie rzeczywistym
- **Odtwarzacz CLI** (`launchpad_midi.py`) – odtwarzaj animacje i sceny na sprzęcie (czysty Python, bez `amidi`)
- **Starszy odtwarzacz CLI** (`launchpad_grid.py`) – te same funkcje z użyciem `amidi` (tylko Linux/ALSA)
- **Konwerter PNG** (`png2launchpad.py`) – konwertuj dowolny obraz PNG do formatu Launchpada

## Szybki start

1. Otwórz `index.html` w przeglądarce
2. Wybierz kolor z palety i rysuj na siatce
3. Zapisz pracę przyciskiem "Zapisz plik" (pobiera plik `.txt`)

### Konfiguracja środowiska

Zainstaluj [uv](https://docs.astral.sh/uv/), a następnie skonfiguruj projekt:

```bash
# Utwórz środowisko wirtualne i zainstaluj wszystkie zależności
uv sync
```

### Podgląd na żywo na sprzęcie

Podłącz Launchpad Mini MK3 przez USB, następnie:

```bash
# Uruchom serwer podglądu na żywo (automatycznie wykrywa port MIDI)
uv run python launchpad_midi.py --serve

# Lub podaj port ręcznie
uv run python launchpad_midi.py --serve -p "Launchpad Mini MK3:Launchpad Mini MK3 MIDI 1 20:0"
```

W edytorze kliknij **"Live Preview"** – przycisk zmieni kolor na zielony, a każda zmiana zostanie natychmiast wysłana na Launchpada.

### Odtwarzanie animacji

```bash
# Odtwórz plik animacji
uv run python launchpad_midi.py sciezka/do/animacji.txt

# Zapętl z własnym FPS
uv run python launchpad_midi.py -l --fps 12 animacja.txt

# Pokaż pojedynczą klatkę
uv run python launchpad_midi.py -f 3 animacja.txt

# Wyczyść wyświetlacz
uv run python launchpad_midi.py --clear
```

### Odtwarzanie scen (YAML)

```bash
uv run python launchpad_midi.py --scene scena.yaml --loop
```

### Przewijany tekst

```bash
# Przewiń tekst raz (biały)
uv run python launchpad_midi.py --text "Hello World"

# Zapętl czerwony tekst z prędkością 15
uv run python launchpad_midi.py --text "Uwaga!" -l --speed 15 --color 5

# Własny kolor RGB
uv run python launchpad_midi.py --text "RGB" --color 0,127,0

# Zatrzymaj przewijanie
uv run python launchpad_midi.py --text-stop
```

### Konwersja PNG do formatu Launchpada

```bash
uv run python png2launchpad.py wejscie.png wyjscie.txt
```

Obraz musi być kwadratowy (max 400×400 px). Zostanie przeskalowany do 8×8, a każdy piksel zostanie dopasowany do najbliższego koloru z palety Launchpada.

## Narzędzia edytora

| Narzędzie | Opis |
|-----------|------|
| Pędzel | Rysuj wybranym kolorem |
| Zaznaczenie | Zaznacz komórki (prostokąt, elipsa, linia pionowa/pozioma) |
| Odznacz | Usuń zaznaczenie |
| Wiaderko | Wypełnij zaznaczony obszar lub flood-fill |
| Próbnik koloru | Pobierz kolor z siatki |
| Gumka | Ustaw komórki na kolor 0 (wyłączony) |
| Wyczyść zaznaczenie | Wymaż tylko zaznaczone komórki |
| Nowy obrazek | Wyczyść całą siatkę |

## Format pliku

Format `.txt` to prosta siatka tekstowa – 8 wierszy po 8 indeksów kolorów (0–127) rozdzielonych spacjami:

```
# Launchpad Mini MK3 pixel art
delay 100
0 0 0 5 5 0 0 0
0 0 5 5 5 5 0 0
0 5 5 5 5 5 5 0
5 5 5 5 5 5 5 5
5 5 5 5 5 5 5 5
0 5 5 5 5 5 5 0
0 0 5 5 5 5 0 0
0 0 0 5 5 0 0 0
```

Wiele klatek można rozdzielić za pomocą `---`, a różne opóźnienia ustawić przez `delay <ms>`.

## Opis narzędzi CLI

```
uv run python launchpad_midi.py [opcje] [animacja.txt]

Opcje:
  -p, --port PORT       Nazwa portu MIDI. Wykrywany automatycznie.
  -l, --loop            Zapętl odtwarzanie
  -n, --repeats N       Liczba powtórzeń (domyślnie: 1)
  -f, --frame N         Wyświetl tylko klatkę N
  --fps FPS             Nadpisz prędkość odtwarzania
  --clear               Wyczyść wyświetlacz Launchpada
  --list-ports          Wyświetl dostępne porty MIDI
  --scene PLIK          Wczytaj plik sceny YAML
  --serve               Uruchom serwer HTTP do podglądu na żywo
  --http-port PORT      Port HTTP dla --serve (domyślnie: 9321)
  --text TEKST          Przewiń tekst na wyświetlaczu Launchpada
  --text-stop           Zatrzymaj aktywne przewijanie tekstu
  --speed N             Prędkość przewijania w padach/s (domyślnie: 10; ujemna = odwrotnie)
  --color KOLOR         Kolor tekstu: indeks palety 0-127 lub r,g,b (np. 127,0,0)
```

```
uv run python png2launchpad.py [opcje] <wejscie.png> [wyjscie.txt]

Opcje:
  -h, --help            Wyświetl pomoc
```

## Wymagania

- [uv](https://docs.astral.sh/uv/) (zalecane) lub `pip`
- Python 3.9+
- Novation Launchpad Mini MK3

Wszystkie zależności Pythona (`pyyaml`, `mido`, `python-rtmidi`) są zadeklarowane w `pyproject.toml` i instalowane automatycznie przez `uv sync`.

### Starszy CLI (`launchpad_grid.py`)

Oryginalny `launchpad_grid.py` korzysta z polecenia `amidi` (część `alsa-utils` na Linuxie) zamiast bibliotek MIDI Pythona. Pozostaje dostępny dla środowisk, w których instalacja `python-rtmidi` nie jest możliwa.
