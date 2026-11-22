# SATEL VERSA Bridge — integracja Home Assistant

Lokalny odczyt stanów wejść VERSY przez ETHM-1 Plus. Wersja **0.1.0-beta.2**,
sprawdzona z VERSA 15; inne modele i firmware pozostają niezweryfikowane.

Wymaga Home Assistant 2026.10.1 lub nowszego. Nie potrzebuje osobnego dodatku,
kontenera, MQTT ani uruchomionego DLOADX. Przed użyciem rozłącz DLOADX.

## Instalacja

### HACS — repozytorium niestandardowe

1. Otwórz HACS → menu → Repozytoria niestandardowe.
2. Dodaj `https://github.com/mic-hall/SATEL-VERSA-Connector-for-HomeAssistant`, typ Integracja.
3. Pobierz SATEL VERSA i uruchom Home Assistant ponownie.
4. Dodaj integrację w Ustawienia → Urządzenia i usługi.

Projekt nie znajduje się w domyślnym katalogu HACS; dla wersji beta włącz
wyświetlanie wydań testowych.

### Instalacja ręczna

Rozpakuj paczkę `satel_versa-<wersja>.zip` do katalogu konfiguracji HA.
Musi powstać `custom_components/satel_versa/manifest.json`. Uruchom HA ponownie,
a następnie wybierz Ustawienia → Urządzenia i usługi → Dodaj integrację → SATEL VERSA.

## Konfiguracja

Wpisz adres, port (zwykle 7090), klucz DLOADX modułu ETHM oraz identyfikatory
DLOADX i VERSA z okna konfiguracji komunikacji. PIN otwierania programu DLOADX
nie jest potrzebny. Identyfikatory mają po 8 znaków hex; obsługujemy klucz ETHM
od 1 do 12 drukowalnych znaków ASCII.

Wybierz numery faktycznie używanych wejść, np. `1-8,10`. Zakres obsługiwanych
pozycji to 1–30, co nie oznacza automatycznego wykrycia obecności wejść.
Każde wejście tworzy encję `binary_sensor`: `on` oznacza bieżące naruszenie,
a nie pamięć alarmu. Nazwy i pomieszczenia przypisz w HA. Nie zgadujemy,
czy dana czujka oznacza ruch, drzwi lub inny stan.

Domyślny odczyt co 1 sekundę jest wspólny dla wszystkich wejść. Po utracie
połączenia encje mają stan niedostępny; integracja ponawia połączenie z odstępem
rosnącym do 60 sekund. Wyłączenie integracji zamyka sesję. Przed użyciem DLOADX
wyłącz integrację, po jego rozłączeniu ponownie ją włącz.

„Konfiguruj” zmienia wejścia i odstęp odczytu. „Zmień konfigurację” pozwala
zmienić parametry połączenia; podaj ponownie oba identyfikatory i klucz.
Podczas sprawdzania ustawień połączenie zostaje na chwilę zatrzymane.

Integracja nie uzbraja/rozbraja, nie steruje wyjściami i nie zapisuje konfiguracji
centrali. Diagnostyka nie zawiera kluczy, adresu, identyfikatorów ani stanów wejść.
Zabezpiecz konfigurację HA i jej kopie zapasowe — HA przechowuje tam parametry
połączenia. Nie załączaj plików DCX ani nagrań sieciowych do publicznych zgłoszeń.

Pełna dokumentacja, ograniczenia i testy: [README.md](README.md),
[TESTING.md](TESTING.md). Projekt jest niezależny od SATEL. Licencja MIT.

## Eksperymentalna obsługa VERSA Plus LTE

Wariant wbudowanego Ethernetu jest rozpoznawany po powitaniu `VERSA`.
Klient czeka 2,5 s przed START, używa alternatywnego formatu odpowiedzi,
timeoutu 15 s i pomija odczyt wyświetlacza. ETHM zachowuje swoje ustawienia.
Nie wymaga to zmiany konfiguracji HA. Nie oznacza obsługi połączenia przez sieć LTE.
Zmiana opiera się na dostarczonym opisie działającej instalacji; ta implementacja
przeszła testy symulowane, ale wymaga potwierdzenia na fizycznej centrali.

## Eksperymentalne wskaźniki wyjść ETHM

W opcjach **Konfiguruj** wpisz numery w polu **Numery wyjść ETHM**, np.
`1-4,12`. Puste pole wyłącza dodatkowy odczyt; jest to ustawienie domyślne
również dla istniejących instalacji. Pole jest też dostępne przy dodawaniu
integracji i zmianie konfiguracji połączenia. Wybieraj tylko faktycznie
skonfigurowane pozycje1–12. Nie wykrywamy obecności ani nazw wyjść.
Obsługa wyjść dotyczy obecnie wyłącznie ETHM-1 Plus.

Powstaną encje `sensor` **Wskaźnik wyjścia N**, przypisane do urządzenia VERSA.
Pokazują **Zielony**, **Czerwony**, **Migający zielony/czerwony**, zgodnie z
podglądem DLOADX. Nie są przełącznikami ani potwierdzonym fizycznym ON/OFF.
Numerację i kolory odtworzono z kodu DLOADX, format potwierdzono na18 odpowiedziach
ze stałymi danymi. Fizyczne zmiany wyjść oraz znaczenie migania wymagają walidacji.

Wybranie wyjść dodaje jeden wspólny odczyt na cykl, w tej samej sesji co wejścia.
Błąd odczytu powoduje niedostępność encji do czasu poprawnego pełnego cyklu.
Usunięcie numeru z listy usuwa encję po przeładowaniu. Surowe bajty statusu
nie trafiają do atrybutów encji ani diagnostyki. Sterowanie wyjściami nie jest
zaimplementowane.

## Opcjonalne encje stref ETHM

W **Konfiguruj → Strefy ETHM** wpisz `1` (A), `2` (B) lub `1,2` (obie).
Pole jest też w konfiguratorze dodawania integracji i zmiany połączenia. Puste
pole wyłącza dodatkowy odczyt i jest domyślne dla istniejących instalacji.
Obsługa dotyczy ETHM-1 Plus; wariant LTE odrzuca tę opcję przed START.

Każda wybrana strefa ma encję **Strefa N — czuwanie**: Rozbrojona, Pełne,
Nocne, Dzienne. Osobne czujniki pokazują czas na wejście, czas na wyjście,
alarm, alarm pożarowy, sabotażowy i ostrzegawczy (cichy). Podczas czasu na
wyjście tryb pokazuje wybrany tryb uzbrojenia, dlatego sprawdzaj też osobną
flagę odliczania przed uznaniem strefy za w pełni uzbrojoną.

Pamięci alarmów i flagi ACPO są osobnymi encjami, domyślnie wyłączonymi
w rejestrze encji; można je włączyć indywidualnie. Pamięć pożaru nie włącza
czujnika bieżącego alarmu pożarowego. Nazwa zwykłej flagi to **Alarm**, zgodnie
z DLOADX; nie przypisujemy jej jeszcze jednoznacznie do alarmu włamaniowego.
Dodano encje alarm_control_panel tylko do odczytu; akcje sterujące są blokowane.

Wszystkie wybrane strefy korzystają z jednego odczytu na cykl. Błąd dowolnego
skonfigurowanego odczytu powoduje niedostępność encji do czasu poprawnego pełnego
cyklu. Usunięte z listy strefy tracą encje po przeładowaniu. Informacje o użytkowniku
uzbrajającym nie są udostępniane w HA.

Uzbrojenie i rozbrojenie obu stref skorelowano z działaniami użytkownika na jednej
instalacji VERSA + ETHM. Czuwanie pełne i czas na wyjście odczytano w tym samym
nagraniu. Tryby nocny/dzienny, czas na wejście, alarmy i ich pamięci rozpoznano
z kodu DLOADX, ale nie potwierdzono aktywnymi przykładami sprzętowymi. Nowy kod
klienta i encje HA przeszły testy automatyczne; nie wdrażano ich jeszcze do HA.

## Panele alarmowe tylko do odczytu

Dla każdej wybranej strefy ETHM powstaje też encja `alarm_control_panel`
**Strefa N — alarm**, przypisana do obecnego urządzenia VERSA. Korzysta
z dotychczasowego pola **Strefy ETHM** (`1`, `2` lub `1,2`) i tych samych
odczytów. Nie wymaga nowego ustawienia ani dodatkowych danych dostępowych.
Istniejące encje czuwania i flag pozostają dostępne pod swoimi identyfikatorami.

| Odczytany stan | Stan alarmu HA |
|---|---|
| Bieżący alarm, pożarowy, sabotażowy lub ostrzegawczy (cichy) | Wyzwolony (`triggered`) |
| Czas na wejście, bez aktywnego alarmu | Oczekiwanie (`pending`) |
| Czas na wyjście, bez aktywnego alarmu i czasu na wejście | Uzbrajanie (`arming`) |
| Czuwanie pełne | Uzbrojony poza domem (`armed_away`) |
| Czuwanie nocne | Uzbrojony na noc (`armed_night`) |
| Czuwanie dzienne | Uzbrojony w domu (`armed_home`) |
| Rozbrojona | Rozbrojony (`disarmed`) |
| Błąd odczytu, brak danych strefy lub wyłączenie integracji | Niedostępny |

Kolejność tabeli ustala priorytet. Pożar/sabotaż może pokazać alarm także
w rozbrojonej strefie. Sama pamięć alarmu lub flaga ACPO nie wyzwala panelu.
Mapowanie czuwania dziennego na „w domu” jest konwencją tej integracji.
Osobne czujniki nadal wskazują rodzaj alarmu i jego pamięć.

Wszystkie metody uzbrajania, rozbrajania i wyzwalania są jawnie blokowane.
HA może mimo to pokazywać przycisk Rozbrój, ponieważ domena alarmu zawsze
udostępnia tę akcję. Jej wywołanie zwraca komunikat „tylko do odczytu”,
bez wysyłania komendy i bez zmiany prezentowanego stanu. Integracja nie prosi
o PIN alarmu. Encje można wykorzystać do podglądu, historii i automatyzacji.

Testy HA potwierdzają mapowanie i odzyskiwanie dostępności. Zakres dowodów
sprzętowych pozostaje taki jak dla opisanych wyżej stref; nowa warstwa HA
nie stanowi dodatkowej walidacji aktywnych alarmów.
