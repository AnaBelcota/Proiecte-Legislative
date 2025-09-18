# Task primit in cadrul practicii de vara

Functionalitate:
-Acceseaza site ul CDEP/Senat
-Extrage titlul si numarul fiecarui proiect, iar apoi acceseaza fiecare proiect in parte si extrage datele necesare
-La final toate datele sunt salvate intr-un JSON (initial facusem cu salvarea lor intr-un tabel in postgreSQL, dar ni s a cerut sa modificam in JSON pentru a fi mai usor de accesat)
-Partea cu site ul Senatului este facuta cu selenium, caci altfel nu am reusit sa accesam fiecare proiect, pe cand la CDEP am reusit cu BeautifulSoup.
