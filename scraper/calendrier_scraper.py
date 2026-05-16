from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import json
import os
import re

print("📅 Démarrage du Scraper de Calendrier...")

chrome_options = Options()
chrome_options.add_argument("--window-size=1280,800")
# chrome_options.add_argument("--headless") # Décommente pour le mode invisible
driver = webdriver.Chrome(options=chrome_options)
url_accueil = "https://www.abssa.be/Abssabe-01"

db_calendrier = {"saison": "2025-2026", "division": "Division 1", "journees": {}}

try:
    # 1. Navigation Initiale
    print("🌍 Ouverture de la page d'accueil...")
    driver.get(url_accueil)
    time.sleep(3)

    print("🖱️ Clic sur 'Menu'...")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "M7"))).click()
    time.sleep(2)

    print("🖱️ Clic sur 'Calendrier - Résultats'...")
    bouton_cal = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//*[contains(text(), 'Calendrier') or contains(text(), 'CALENDRIER')]",
            )
        )
    )
    bouton_cal.click()
    time.sleep(4)

    # 2. Boucle sur les 26 journées
    print("⏳ Démarrage de l'aspiration des 26 journées...")

    # On identifie la liste déroulante des journées (ID: A3)
    select_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "A3"))
    )
    select = Select(select_element)

    # On récupère le nombre total d'options (journées)
    nombre_journees = len(select.options)
    print(f"📊 {nombre_journees} journées détectées.")

    for index in range(nombre_journees):
        journee_num = index + 1
        print(f"   -> Extraction de la Journée {journee_num}...")

        # Sélection de la journée par son index
        select.select_by_index(index)
        time.sleep(3)  # TEMPS DE PAUSE CRUCIAL POUR AJAX

        journee_data = []

        # On aspire le tableau de la journée (ID: ctzA8 d'après ton code)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table", id="ctzA8")

        if table:
            # On cherche toutes les lignes dont l'ID commence par A8_
            rows = table.find_all("tr", id=lambda x: x and x.startswith("A8_"))
            for row in rows:
                cols = row.find_all("td")

                # Vérification : il faut au moins les colonnes EquipeDomicile, ScoreDom, Tiret, ScoreExt, EquipeExt
                # Dans ton HTML, ça semble correspondre à certains index.
                # Ajustement basé sur ton code source (colonnes cX-A13, cX-A17, cX-A18, cX-A16)
                if len(cols) >= 7:
                    try:
                        # Extraire le texte de chaque colonne.
                        # On prend les colonnes paires (les impaires sont les séparateurs comme "-")
                        domicile = cols[0].text.strip()
                        score_dom = cols[4].text.strip()
                        score_ext = cols[6].text.strip()
                        exterieur = cols[2].text.strip()

                        # Si les scores sont vides, le match n'est pas encore joué
                        status = "Joue" if score_dom and score_ext else "A Venir"

                        match = {
                            "equipe_domicile": domicile,
                            "score_domicile": int(score_dom) if score_dom else None,
                            "score_exterieur": int(score_ext) if score_ext else None,
                            "equipe_exterieure": exterieur,
                            "statut": status,
                        }
                        journee_data.append(match)
                    except Exception as e:
                        # On ignore les lignes mal formatées (parfois des espaces vides)
                        continue

        db_calendrier["journees"][f"Journee_{journee_num}"] = journee_data

    # 3. Sauvegarde
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # On remonte de 1 seul niveau ("..") depuis 'scraper' pour trouver 'data'
    file_path = os.path.abspath(
        os.path.join(script_dir, "..", "data", "calendrier.json")
    )

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(db_calendrier, f, indent=4, ensure_ascii=False)

    print(f"\n🎉 EXCELLENT ! Le calendrier a été sauvegardé dans : {file_path}")

except Exception as e:
    print(f"\n❌ ERREUR LORS DU SCRAPING DU CALENDRIER : {e}")

finally:
    driver.quit()
    print("🔌 Navigateur fermé.")
