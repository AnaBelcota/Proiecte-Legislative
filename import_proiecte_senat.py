from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import json


class MergedSenateScraper:
    def __init__(self, headless=False):
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=self.options)
        self.wait = WebDriverWait(self.driver, 15)
        self.proiecte = []
        self.pagina_curenta = 1
        self.numar_pagini_parcurse = 0

    def setup_initial_page(self):
        url = "https://www.senat.ro/legis/lista.aspx?AllowPaging=1"
        self.driver.get(url)
        try:
            select = Select(self.wait.until(EC.presence_of_element_located((By.ID, "ctl00_B_Center_Lista_ddAni"))))
            select.select_by_visible_text("2025")
            search_btn = self.driver.find_element(By.ID, "ctl00_B_Center_Lista_btnCauta2")
            search_btn.click()
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "lista-legis-table-title-container")))
            time.sleep(2)
            return True
        except Exception:
            return False

    def get_projects_on_current_page(self):
        try:
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "lista-legis-table-title-container")))
            containers = self.driver.find_elements(By.CLASS_NAME, "lista-legis-table-title-container")
            randuri = self.driver.find_elements(By.CSS_SELECTOR, "#ctl00_B_Center_Lista_grdLista > tbody > tr")
            projects_data = []
            for i, container in enumerate(containers):
                try:
                    titlu = container.find_element(By.TAG_NAME, "p").text.strip()
                    try:
                        initiatori = container.find_element(
                            By.CSS_SELECTOR, ".lista-legis-table-initiatori-container div[style]"
                        ).text.strip()
                    except:
                        initiatori = ""
                    try:
                        link_elem = randuri[i + 1].find_element(By.CSS_SELECTOR, "td a")
                        link_javascript = link_elem.get_attribute("href").strip()
                        link_id = link_elem.get_attribute("id")
                    except:
                        continue
                    project_data = {
                        "index": i,
                        "titlu": titlu,
                        "initiatori": initiatori,
                        "link_javascript": link_javascript,
                        "link_element_id": link_id
                    }
                    projects_data.append(project_data)
                except:
                    continue
            print(f"[Debug] Nr. proiecte găsite pe pagina {self.pagina_curenta}: {len(projects_data)}")
            return projects_data
        except:
            return []

    def click_project_and_extract_details(self, project_data):
        try:
            link_elem = self.driver.find_element(By.ID, project_data["link_element_id"])
            self.driver.execute_script("arguments[0].scrollIntoView(true);", link_elem)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", link_elem)
            self.wait_for_ajax_complete()
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, "ctl00_B_Center_Lista_pnlContents")))
                details = self.extract_project_details()
                if details:
                    complete_project = {
                        "titlu": project_data["titlu"],
                        "initiatori": project_data["initiatori"],
                        **details
                    }
                    self.proiecte.append(complete_project)
                    return True
            except TimeoutException:
                return False
        except:
            return False

    def extract_project_details(self):
        try:
            panel = self.driver.find_element(By.ID, "ctl00_B_Center_Lista_pnlContents")

            def extract_row(label_text):
                try:
                    row = panel.find_element(By.XPATH, f".//tr[td[contains(text(), '{label_text}')]]")
                    return row.find_elements(By.TAG_NAME, "td")[1].text.strip()
                except:
                    return ""

            return {
                "titlu_detaliat": panel.find_element(By.TAG_NAME, "p").text.strip(),
                "nr_inregistrare": extract_row("Număr de înregistrare Senat"),
                "tip_initiativa": extract_row("Tip inițiativă"),
                "data_inregistrare": extract_row("Data"),
                "stadiu": extract_row("Stadiu"),
                "caracter": extract_row("Caracterul legii"),
                "procedura_urgenta": extract_row("Procedura de urgență"),
                "aviz_cons_leg": extract_row("Avizul Consiliului Legislativ")
            }
        except:
            return None

    def wait_for_ajax_complete(self):
        try:
            time.sleep(1)
            self.wait.until(
                lambda driver: driver.execute_script("""
                    try {
                        var prm = Sys.WebForms.PageRequestManager.getInstance();
                        return !prm.get_isInAsyncPostBack();
                    } catch (e) {
                        return true;
                    }
                """)
            )
            time.sleep(0.5)
        except:
            time.sleep(2)

    def return_to_list(self):
        try:
            self.driver.get("https://www.senat.ro/legis/lista.aspx?AllowPaging=1")
            self.wait.until(EC.presence_of_element_located((By.ID, "ctl00_B_Center_Lista_ddAni")))
            select = Select(self.driver.find_element(By.ID, "ctl00_B_Center_Lista_ddAni"))
            select.select_by_visible_text("2025")
            search_btn = self.driver.find_element(By.ID, "ctl00_B_Center_Lista_btnCauta2")
            search_btn.click()
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "lista-legis-table-title-container")))
            if self.pagina_curenta > 1:
                self.navigate_to_specific_page(self.pagina_curenta)
            time.sleep(1)
            return True
        except:
            return False

    def navigate_to_specific_page(self, pagina_dorita):
        try:
            paginare = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, '//td/a | //td/span')))
            for link in paginare:
                if link.text.strip() == str(pagina_dorita) and link.is_displayed() and link.is_enabled():
                    if link.tag_name.lower() == 'span':
                        return True
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(0.5)
                        link.click()
                        self.wait.until(EC.staleness_of(link))
                        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "lista-legis-table-title-container")))
                        return True
                    except:
                        return False

            # Dacă nu găsim pagina direct, încearcă să mergi mai departe cu "..."
            puncte = [l for l in paginare if l.text.strip() == "..."]
            if puncte:
                self.driver.execute_script("arguments[0].click();", puncte[-1])
                self.wait.until(EC.staleness_of(puncte[-1]))
                self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "lista-legis-table-title-container")))
                return self.navigate_to_specific_page(pagina_dorita)
            return False
        except:
            return False

    def process_all_pages(self):
        if not self.setup_initial_page():
            return False

        MAX_PAGINI = 33

        while self.pagina_curenta <= MAX_PAGINI:
            print(f"[Procesare] Pagina {self.pagina_curenta}")
            projects = self.get_projects_on_current_page()
            if not projects:
                print("[Stop] Nu s-au găsit proiecte pe această pagină.")
                break

            for project in projects:
                try:
                    success = self.click_project_and_extract_details(project)
                    if not self.return_to_list():
                        break
                    time.sleep(0.5)
                except:
                    self.return_to_list()
                    continue

            next_page = self.pagina_curenta + 1
            if next_page > MAX_PAGINI:
                print(f"[Final] Am ajuns la pagina {MAX_PAGINI}. Gata.")
                break

            success = self.navigate_to_specific_page(next_page)
            if not success:
                print(f"[Stop] Nu s-a putut naviga la pagina {next_page}. Ieșim.")
                break
            self.pagina_curenta = next_page

        return True

    def save_results(self, filename="proiecte_senat.json"):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.proiecte, f, ensure_ascii=False, indent=2)
            print(f"[Success] Salvate {len(self.proiecte)} proiecte în {filename}")
            return True
        except Exception as e:
            print(f"[Eroare] la salvare: {e}")
            return False

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    scraper = MergedSenateScraper(headless=False)
    try:
        scraper.process_all_pages()
        scraper.save_results()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[Eroare] generală: {e}")
    finally:
        scraper.close()
