STIN - 2025

2 Moduly - 2 Tymy (komunikuji mezi sebou)

1) Modul Burza (finanční zdroje dat akcie)
https://support.microsoft.com/cs-cz/office/o-finan%C4%8Dn%C3%ADch-zdroj%C3%ADch-dat-akcie-98a03e23-37f6-4776-beea-c5a6c8e787e6
Faze 1
	a. Modul definuje interval nebo na rucni start zaskavat aktualni nebo historicka data pro definovane polozky
		(napr Microsoft) na burze (umoznit uzivateli definovat svuj seznam oblibenych polozek)
	b. Umoznit uzivateli definovat zakladni filtr na vyvoj polozky v case
		1. odfiltrovat ty co posledni 3 dny klesaly
		2. odfiltrovat takove, ktere maji za posledni 5 dni vice nez dva poklesy
	c. Poslat pozadavek na ziskani doporuceni do modulu zpravy
	
Faze 2
	a. Vezme vysledek hodnoceni modulu zpravy a k tem polozkam, ktere maji raiting vetsi
		nez uzivatelem definovanou hodnotu doplni o doporuceni prodat
	b. Vysledek posle modulu zpravy	 		



2) Modul Zpravy (napr ČTK)
napr: https://newsapi.ai/?gad_source=1&gclid=CjwKCAiAn9a9BhBtEiwAbKg6fo2hdQYX3GSA4jZxKktEbjhSeG_jaTtXDTdXQSwTI2K8eze5kVHGQhoC5W8QAvD_BwE
Faze 1
	a. Z libovolneho API stahovat zpravy, ktere se tykaji polozek ziskanych modulem burza za dane obdobi
	b. Vyhodnotit, zda-li se jedna o pozitivni nebo negativni zpravy (dle definovanych pravidel
		nebo je mozne tady zapojit genAI pro hodnoceni zprav) - pripojit raiting.
	c. Umoznit definovat filtry, ktere odfiltruji polozky, ktere: 
		1. Maji malo zprav k dispozici
		2. Ktera maji negativni hodnoceni
	d. Pridat kvalitu hodnoceni/raiting k neodfiltrovanych polozkam a tyto predat vcetne hodnoceni zpet modulu burza
	
Faze 2
	a. Vezme doporuceni modulu Burza a
		1. Pokud mam uzivatel v portfoliu polozku s doporucenim prodat, tak se vsechny prodaji
		2. Pokd nema polozku s doporucenim koupit, tak se nakoupi
	
	
Pozadavky: 
	1. Obe UI musi bezet na pc i na mobilu (Webovka)
	2. Moduly musi bezet mimo localhost

Obecne: 	
	1. Libovolny jazyk 
	2. Splnit test coverage > 80%  (nesmi byt na lokalu) (ma byt na serveru nebo na git)
	3. Vyuzit CD/CI - git	
