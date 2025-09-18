import requests
from bs4 import BeautifulSoup
import re
import json
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        ctx.check_hostname = False
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


session = requests.Session()
session.mount("https://", TLSAdapter())


def normalize_initiator(text):
    text = text.lower()
    if "guvern" in text:
        return "guvern"
    elif "cetățean" in text or "cetateni" in text:
        return "cetateni"
    elif "senatori și deputați" in text or "senatori si deputati" in text:
        return "senatori si deputati"
    elif "senatori sau deputați" in text or "senatori sau deputati" in text:
        return "senatori sau deputati"
    elif "senatori" in text and "deputați" not in text:
        return "senatori"
    elif "deputați" in text and "senatori" not in text:
        return "deputati"
    return text


def normalize_prima_camera(text):
    text_original = text  # păstrăm versiunea originală pentru return dacă e necunoscută
    text = text.lower().replace("ș", "s").replace("ț", "t").replace("ţ", "t").replace("ă", "a").replace("â", "a").replace("î", "i")
    text = text.replace(" ", "").replace("\xa0", "")  # elimină spații și caractere invizibile

    # Cazuri compuse
    if "cameradeputatilor+senat" in text:
        return "Camera Deputaților + Senatul României"
    if "guvern+senat" in text:
        return "Guvern + Senatul României"
    if "guvern+cameradeputatilor" in text:
        return "Guvern + Camera Deputaților"
    if "sedintacomuna" in text:
        return "Ședință comună"

    # Cazuri simple
    if "cameradeputatilor" in text:
        return "Camera Deputaților"
    if "senat" in text:
        return "Senatul României"

    return text_original.strip()


def get_text_flexibil(label, soup):
    rows = soup.select("table tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2:
            if label.lower() in cols[0].get_text(strip=True).lower():
                bold_tag = cols[1].find("b")
                return bold_tag.get_text(strip=True) if bold_tag else cols[1].get_text(strip=True)
    return ""


def get_stadiu_link_only(soup):
    rows = soup.select("table tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2 and "Stadiu:" in cols[0].get_text(strip=True):
            a_tag = cols[1].find("a")
            return a_tag.get_text(strip=True) if a_tag else ""
    return ""


def get_proiecte_camera_deputatilor():
    an_curent = "2025"
    url_lista = f"https://www.cdep.ro/pls/proiecte/upl_pck2015.lista?cam=2&anp={an_curent}"

    try:
        resp = session.get(url_lista, verify=False, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Eroare la descărcarea listei: {e}")
        return

    soup = BeautifulSoup(resp.content, "html.parser")
    rows = soup.select("table tr")[1:]

    if not rows:
        print("⚠ Nu s-au găsit rânduri în tabelul HTML.")
        return

    proiecte = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        link_tag = cols[1].find("a", href=True)
        if not link_tag:
            continue
        numar_raw = link_tag.get_text(strip=True)
        match_numar = re.search(r"(\d+)/(\d{2})\.(\d{2})\.(\d{4})", numar_raw)

        if match_numar:
            numar = f"{match_numar.group(1)}/{match_numar.group(4)}"
            data = f"{match_numar.group(2)}.{match_numar.group(3)}.{match_numar.group(4)}"
        else:
            numar = numar_raw
            data = ""  # fallback dacă nu e găsită data

        titlu_tag = cols[1].find_next_sibling("td")
        titlu = titlu_tag.get_text(strip=True) if titlu_tag else ""

        stadiu = ""
        if len(cols) >= 3:
            a_elements = cols[2].select("a")
            if a_elements:
                stadiu = a_elements[0].get_text(strip=True)

        href = link_tag["href"]
        match = re.search(r"idp=(\d+)", href)
        if not match:
            continue
        idproiect = int(match.group(1))
        url_detalii = f"https://www.cdep.ro{href}"

        try:
            detalii_resp = session.get(url_detalii, verify=False, timeout=30)
            detalii_resp.raise_for_status()
            soup_detalii = BeautifulSoup(detalii_resp.content, "html.parser")
        except requests.RequestException as e:
            print(f"❌ Eroare la proiectul {idproiect}: {e}")
            continue

        numar_an = ""
        for a_tag in soup_detalii.find_all("a", href=True):
            text = a_tag.get_text(strip=True)
            if re.match(r"^[LB]\d+/\d{4}$", text):
                numar_an = text
                break

        tip = get_text_flexibil("Tip initiativa", soup_detalii)
        initiator = normalize_initiator(get_text_flexibil("Initiator", soup_detalii)).capitalize()

        prima_camera_raw = get_text_flexibil("Camera decizionala", soup_detalii)
        prima_camera = normalize_prima_camera(prima_camera_raw).capitalize()

        an = an_curent

        stadiu_table = soup_detalii.find("table", class_="stadiu")
        if stadiu_table:
            stadiu = stadiu_table.get_text(separator=" ", strip=True)
        else:
            stadiu = get_text_flexibil("Stadiu", soup_detalii)

        pdf_links = []
        for a_tag in soup_detalii.find_all("a", href=True):
            href = a_tag['href']
            if href.lower().endswith(".pdf"):
                if href.startswith("http"):
                    pdf_links.append(href)
                else:
                    pdf_links.append("https://www.cdep.ro" + href)
        documente = ";".join(pdf_links)

        proiect = {
            "idproiect": idproiect,
            "titlu": titlu,
            "numar": numar,
            "data": data,  # <-- adăugat aici
            "an": an,
            "numar_an": numar_an,
            "stadiu": stadiu,
            "tip": tip,
            "initiator": initiator,
            "prima_camera": prima_camera,
            "documente": documente
        }

        proiecte.append(proiect)
        print(f"[{idproiect}] {titlu[:60]}...")

    # Salvăm în fișier JSON
    with open(f"proiecte_{an_curent}.json", "w", encoding="utf-8") as f:
        json.dump(proiecte, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(proiecte)} proiecte din {an_curent} au fost salvate în fișierul JSON.")


if __name__ == "__main__":
    get_proiecte_camera_deputatilor()