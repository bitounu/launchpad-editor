*Przeczytaj w: [English](README.md) | [Polski](README.pl.md)*

# Launchpad Mini MK3 – Edytor Pixel Art

Webowy edytor pixel art dla Novation Launchpad Mini MK3 z podglądem na żywo na sprzęcie i zestawem narzędzi CLI do animacji i konwersji obrazów.

## Funkcje

- **Edytor webowy** (`index.html`) – rysuj pixel art na siatce 8×8 z pełną 128-kolorową paletą Launchpada
- **Podgląd na żywo** – obserwuj swoją grafikę na fizycznym Launchpadzie w czasie rzeczywistym
- **Odtwarzacz CLI** (`launchpad_grid.py`) – odtwarzaj animacje i sceny na sprzęcie
- **Konwerter PNG** (`png2launchpad.py`) – konwertuj dowolny obraz PNG do formatu Launchpada

## Szybki start

1. Otwórz `index.html` w przeglądarce
2. Wybierz kolor z palety i rysuj na siatce
3. Zapisz pracę przyciskiem "Zapisz plik" (pobiera plik `.txt`)

### Podgląd na żywo na sprzęcie

Podłącz Launchpad Mini MK3 przez USB, następnie:

```bash
# Zainstaluj zależność
pip install pyyaml

# Uruchom serwer podglądu na żywo (automatycznie wykrywa port MIDI)
./launchpad_grid.py --serve

# Lub podaj port ręcznie
./launchpad_grid.py --serve -p hw:1,0,0
```

W edytorze kliknij **"Live Preview"** – przycisk zmieni kolor na zielony, a każda zmiana zostanie natychmiast wysłana na Launchpada.

### Odtwarzanie animacji

```bash
# Odtwórz plik animacji
./launchpad_grid.py sciezka/do/animacji.txt

# Zapętl z własnym FPS
./launchpad_grid.py -l --fps 12 animacja.txt

# Pokaż pojedynczą klatkę
./launchpad_grid.py -f 3 animacja.txt

# Wyczyść wyświetlacz
./launchpad_grid.py --clear
```

### Odtwarzanie scen (YAML)

```bash
./launchpad_grid.py --scene scena.yaml --loop
```

### Konwersja PNG do formatu Launchpada

```bash
python3 png2launchpad.py wejscie.png wyjscie.txt
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
./launchpad_grid.py [opcje] [animacja.txt]

Opcje:
  -p, --port PORT       Port MIDI (np. hw:1,0,0). Wykrywany automatycznie.
  -l, --loop            Zapętl odtwarzanie
  -n, --repeats N       Liczba powtórzeń (domyślnie: 1)
  -f, --frame N         Wyświetl tylko klatkę N
  --fps FPS             Nadpisz prędkość odtwarzania
  --clear               Wyczyść wyświetlacz Launchpada
  --list-ports          Wyświetl dostępne porty MIDI
  --scene PLIK          Wczytaj plik sceny YAML
  --serve               Uruchom serwer HTTP do podglądu na żywo
  --http-port PORT      Port HTTP dla --serve (domyślnie: 9321)
```

```
python3 png2launchpad.py [opcje] <wejscie.png> [wyjscie.txt]

Opcje:
  -h, --help            Wyświetl pomoc
```

## Wymagania

- Python 3.9+
- `pyyaml` (`pip install pyyaml`)
- `amidi` (część `alsa-utils` na Linuxie)
- Novation Launchpad Mini MK3
