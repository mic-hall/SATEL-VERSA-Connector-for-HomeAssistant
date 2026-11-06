# SATEL VERSA Bridge — integracja Home Assistant

Lokalny odczyt stanów wejść VERSY przez ETHM-1 Plus. Wersja **0.1.0-beta.2**,
sprawdzona z VERSA 15; inne modele i firmware pozostają niezweryfikowane.

Wymaga Home Assistant 2026.10.1 lub nowszego. Nie potrzebuje osobnego dodatku,
kontenera, MQTT ani uruchomionego DLOADX. Przed użyciem rozłącz DLOADX.

## Instalacja

Rozpakuj paczkę `satel_versa-<wersja>.zip` do katalogu konfiguracji HA.
Musi powstać `custom_components/satel_versa/manifest.json`. Uruchom HA ponownie,
a następnie wybierz Ustawienia → Urządzenia i usługi → Dodaj integrację → SATEL VERSA.

Po publikacji repozytorium można dodać w HACS:
`https://github.com/mic-hall/SATEL-VERSA-Connector-for-HomeAssistant`, typ Integracja.
Projekt nie jest domyślnie umieszczony w katalogu HACS; dla wersji beta włącz
wyświetlanie wydań testowych.

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
