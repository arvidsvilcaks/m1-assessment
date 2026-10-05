# 10 punktu pārskatīšanas kontrolsaraksts (review checklist)

Lieto visam, ko izmaiņa skar, ne tikai jaunajām rindām.

1. Pieņemšanas kritēriji izpildīti, arī negatīvie gadījumi
2. Līgums (API contract) nav mainīts, vai izmaiņa ir dokumentēta
3. Nav noslēpumu (secrets) kodā, konfigurācijā, testos, žurnālos vai uzvednēs
4. Nav personas datu žurnālos vai kļūdās vairāk, nekā vajag
5. Kļūdas apstrādātas skaidri un droši (fail safe), bez iekšējās informācijas atbildē
6. Ārējiem izsaukumiem ir noildze (timeout), statusa apstrāde un negaidītu vērtību apstrāde
7. Ievade ir validēta, vaicājumi ir parametrizēti
8. Atkarības eksistē, ir vajadzīgas, uzturētas, ar fiksētu versiju un bez zināmām ievainojamībām
9. Tikai uzdevumā paredzētās izmaiņas
10. Testi pierāda pieņemšanas kritērijus un **var krist**

## Atraduma pieraksts

| Vieta (fails:rinda) | Nozīmīgums | Ietekme | Labojums vai pamatojums |
|---|---|---|---|
| tracker/CR-C.md:44 (nekomitēts labojums) | bloķējošs | Atvērtais jautājums par mēneša beigām aizpildīts ar "Mans pieņēmums", lai gan CLAUDE.md aizliedz mainīt tracker/. Uzvedība 31. datumiem (31.10 → 28.02, 31.05 → 30.09) nav apstiprināta, bet kods to jau īsteno. | Nav labots: labojums ir lietotāja darba kopijā. Atsaukt ar `git checkout tracker/CR-C.md` un jautāt produkta īpašniekam. Līdz atbildei 31. datumu uzvedību nelaist produkcijā. (1., 9. p.) |
| app/main.py:79, tests/test_crc_extend.py:164 | jālabo | Komentārs testā sauc pieņēmumu par "precizējumu, 2026-10-05". Lasītājs domās, ka uzvedība ir apstiprināta. | Atlikts līdz produkta īpašnieka atbildei: pēc tās nomainīt komentāru uz atbildētāju un datumu vai mainīt `add_months` un testus. |
| app/errors.py:71-75 | jālabo | 500 atbildē bija `str(exc)`. `storage.update_due_date` (storage.py:256) met `LookupError` ar ID, SQLite versiju un `db=:memory:`, un tas nonāktu klienta atbildē. Līgums prasa: "Bez personas datiem un iekšējas informācijas". (5. p.) | Labots: atbildē vispārīgs ziņojums, žurnālā tikai kļūdas tips un ceļš. Tests `test_extend_unexpected_error_hides_internal_details` krīt bez labojuma un iziet ar to (10. p.). |
| app/main.py:187-201 | sīkums | Statusa pārbaude un termiņa maiņa nav vienā transakcijā. Paralēla atsaukšana starp tām ļautu pagarināt WITHDRAWN iesniegumu. | Atlikts: mācību prototips, atmiņas DB, viens process. Produkcijā `UPDATE ... WHERE id = ? AND status IN (...)`. |
| app/storage.py:245 (CR-C neskar) | jālabo | `update_status` žurnālā ieraksta visu ierakstu, arī personas kodu, vārdu un e-pastu. (4. p.) | Atlikts: nav CR-C kods (9. p.). Vajag atsevišķu pieteikumu. |
