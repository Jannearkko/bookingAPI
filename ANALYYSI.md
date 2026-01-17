# ANALYYSI

### 1. Mitä tekoäly teki hyvin?

Olen ollut jo vuosia ChatGPT:n käyttäjä ja oppinut tavan jolla kehotteista/prompteista saisi parhaimman tuloksen irti. Siispä lähdin vaiheessa 1 liikkeelle siitä, että annan tekoälylle tehtävän, jonka tavoitteet on eritelty mahdollisimman hyvin ja strukturoidusti.

Aloitin kertomalla sovellukselta vaadittavan teknologian, jossa päädyin Python kieleen ja FastAPI-kirjastoon. Nämä siitä syystä, että olen toiminut aiemminkin FastAPI:n ja sen Swagger UI:n kanssa, joka käytännössä avaa automaattisesti OpenAPI-dokumentoinnin kautta valmiin /docs-rajapinnan, jonka kautta kykenen testaamaan kehitettyjä rajapintoja.

Seuraavaksi kerroin tekoälylle mitä ominaisuuksia rajapinnalla tulee olla sekä logiikka, jota tulee noudattaa. Nämä olivat käytännössä suoria kopioita tehtävänannosta.

Koska tehtävä oli yksinkertainen, ChatGPT:ltä tuli heti ensimmäisen promptin jälkeen toimiva kokonaisuus jo ulos. Testasin ominaisuudet ja logiikan pääpiirteittäin jonka jälkeen kehotin tekoälyä pienentämään kokoushuone-avaruutta 100:sta huoneesta viiteen ja lisäämään Swagger UI:n /docs-rajapinnalle informatiivisemmat kuvaukset sekä raja-arvot, joita käyttäjän tulee noudattaa (Toimintalogiikka)

Tässäkin ChatGPT onnistui hyvin ja antoi viidelle kokoushuoneelle nimet: "alpha", "bravo", "charlie", "delta" ja "echo". Myöskin kuvaukset ja toimintalogiikan raja-arvot olivat nyt paljon ymmärrettävämmät Swagger UI:ssa.

Seuraavaksi kehotin lisäämään nimi- tai id-arvon varauksiin, jotta varauksen tekijät voidaan tunnistaa ja kohdentaa. Tällainenhan on tekoälylle hyvin yksinkertainen tehtävä.

Lopuksi kerroin, että rajapinta sekä sen kaikki ominaisuudet ja logiikka toimii kuten on pyydetty. Pyysin vielä kirjoittamaan testit rajapinnan endpointeille testaamaan niiden virhelogiikka sekä statuskoodit. Tätä varten ChatGPT valitsi 'pytest'-kirjaston, joka on nimenomaan se oikea valinta Pythoniin ja kirjoitti kerrasta juuri oikeanlaiset testit jokaiselle eri endpointille. 

Lopulta ajoin testit läpi, jokainen testi onnistui ja mielestäni se merkkasi vaiheen 1 loppua. 

Kaiken kaikkiaan ChatGPT onnistui erittäin hyvin yksinkertaisen rajapinnan luonnissa vain neljällä kehotteella. Tässä yhteydessä pitää mainita, että maksan palvelusta, joten saan käyttööni aina uusimman mallin, jolloin eroa tietysti ilmaiseen malliin voi tulla melko paljonkin.

### 2. Mitä tekoäly teki huonosti?

Varsinaisesti malli ei tehnyt mitään 'huonosti', mutta tekoälyn kanssa työskentelyyn liittyy aina koodin toimivuuden varmentaminen sekä laatikon ulkopuolelta tarkastelu. Hyvänä esimerkkinä pidän varaajan tietojen poisjättöä alkuperäisestä iteraatiosta. Aina jos jotain varataan jonkinlaiseen käyttöön niin varaajan tietojen pitäisi kulkea myös varauksen mukana. Tämän jouduinkin kehottamaan, eikä malli itsekseen sellaista ehdottanut.

Toisekseen tässä tehtävässä tekoäly ei moduloinut koodia sen kummemmin vaan kirjoitti kaiken yhteen ja samaan scriptiin. Varsinkin jos projekti kasvaa niin erilaiset moduulit ovat välttämättömiä ja tätä lähdinkin itse heti vaiheessa 2 korjaamaan. Moduulit ei vain paranna luettavuutta, mutta myös helpottaa jatkossa uusien ominaisuuksien lisäämistä rajapintaan. Tämä ei tosin tullut itselleni yllätyksenä, sillä varsinkin ChatGPT:n kanssa työskennellessä, joudut jatkuvasti itse siirtämään toimintoja moduuleihin kun jostain syystä malli ei sitä itse halua oikein tehdä.

### 3. Mitkä olivat tärkeimmät parannukset, jotka teit tekoälyn tuottamaan koodiin ja miksi?

Kuten edellä mainitsin, heti ensimmäisenä siirsin kaikki luokat omiin moduuleihin, jotta main skripti sekä moduulit säilyvät luettavana ja puhtaana. Mielestäni tämä on de-facto tapa ja pyrin siihen itse kaikessa ohjelmoinnissa.

Toiseksi, pidän erityisen tärkeänä, että koodipohjaan ja logiikkaan lisätään mahdollisimman vähän hard-koodattuja stringejä tai ylipäänsä mitään tekstiä, jota mahdollisesti joku joskus haluaisi muokata. On erittäin aikaa vievää etsiä lähdekoodista juuri se 'oikea' teksti, jossa on esimerkiksi kirjoitusvirhe, varsinkin isoissa projekteissa. Tästä syystä siirsin kaiken virheviestinnän omaan errors-moduuliin sekä tein luokkarakenteen virheille, jotta jos jatkossa rajapinnalle kehitetään esimerkiksi käyttöliittymä niin silloin voi nojata jo valmiiseen virhekäsittelyyn ja tietää 100% varmuudella minkälainen virheviesti palvelimelta käyttöliittymälle matkaa. Alkuun epäilin hetken kannattaako tätä lähteä suorittamaan tekstien vähyyden vuoksi, jota kysyin myös tekoälyltä ja sekin päätyi samaan, että se on ihan ok tehdä myös pienissä projekteissa.

Kolmanneksi muutin kirjoitetut testit huomioimaan tämän uuden ApiError-luokan tarjoaman dictionary-tietorakenteen. Tästä pyysin ChatGPT:ltä suoraan bulkkina uudet testit, koska tiesin itse jo ratkaisun ja miten se tehdään, mutta ajan säästämiseksi tekoäly kirjoittaa saman asian huomattavasti nopeammin ja tarkemmin.

Vaiheessa 2 olin epävarma oliko FastAPI:n rajapinnat jo valmiiksi parametrisoituja ja päädyin kysymään sitä tekoälyltä. Olivathan ne. Tämä siitä syystä, että oikeastaan ainoa pelko, jota kannan ohjelmoinnissa mukanani on se, että onko ohjelmani tietoturvallinen. 

Viimeisenä muutoksena lisäsin ns. fallback-reitin /docs-endpointtiin kaikille muille reiteille, joita ei määritetty rajapinnassa sekä tekoälyn avustamana lisäsin myös poikkeuksen hallinnan kaikille näille reiteille. Tämäkin vähentää muun muassa hyökkäyspinta-alaa kun API uudelleenohjaa automaattisesti kaikki väärät reitit.