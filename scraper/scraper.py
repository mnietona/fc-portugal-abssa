from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
import re  # <-- L'outil de nettoyage de texte

print("🚀 Démarrage du Robot Navigateur (Phase 1 & 2)...")

chrome_options = Options()
chrome_options.add_argument("--window-size=1280,800")
driver = webdriver.Chrome(options=chrome_options)
url_accueil = "https://www.abssa.be/Abssabe-01"

try:
    # --- PHASE 1 : RECUPERER LE CLASSEMENT ---
    print("🌍 1. Ouverture de la page d'accueil...")
    driver.get(url_accueil)
    time.sleep(3)

    print("🖱️ 2. Clic sur 'Menu'...")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "M7"))).click()
    time.sleep(2)

    print("🖱️ 3. Clic sur 'Classement'...")
    bouton_classement = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//*[contains(text(), 'Classement') or contains(text(), 'CLASSEMENT')]",
            )
        )
    )
    bouton_classement.click()
    time.sleep(3)

    print("⏳ 4. Aspiration du classement...")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ctzA4")))
    soup = BeautifulSoup(driver.page_source, "html.parser")
    table = soup.find("table", id="ctzA4")

    db = {"saison": "2025-2026", "division": "Division 1", "classement": []}

    if table:
        rows = table.find_all("tr", id=lambda x: x and x.startswith("A4_"))
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 9:
                try:
                    equipe_data = {
                        "position": int(cols[0].text.strip()),
                        "equipe": cols[1].text.strip(),
                        "joues": int(cols[2].text.strip()),
                        "gagnes": int(cols[3].text.strip()),
                        "perdus": int(cols[4].text.strip()),
                        "nuls": int(cols[5].text.strip()),
                        "points": int(cols[8].text.strip()),
                        # On prépare nos nouvelles colonnes
                        "couleur_maillot": "",
                        "terrain_nom": "",
                        "terrain_adresse": "",
                    }
                    db["classement"].append(equipe_data)
                except ValueError:
                    continue
        print(f"✅ Classement extrait ! {len(db['classement'])} équipes prêtes.")

    # --- PHASE 2 : RECUPERER LES INFOS DES CLUBS ---
    print("\n🔄 Passage à la Phase 2 : Infos des Clubs...")

    print("🖱️ 5. Clic sur 'Menu'...")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "M7"))).click()
    time.sleep(2)

    print("🖱️ 6. Clic sur 'CLUBS - EQUIPES'...")
    bouton_clubs = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(text(), 'CLUBS') and contains(text(), 'EQUIPES')]")
        )
    )
    bouton_clubs.click()
    time.sleep(3)

    # On passe en revue nos équipes du classement
    for equipe in db["classement"]:
        # La Regex magique : Retire les espaces et les chiffres à la fin
        nom_club_propre = re.sub(r"\s+\d+$", "", equipe["equipe"]).strip()
        print(f"🔍 Recherche du club : {nom_club_propre}...")

        try:
            # On cherche le club dans la liste de gauche
            club_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//*[normalize-space(text())='{nom_club_propre}']")
                )
            )
            # On force le clic sur le club (astuce vitale sur WebDev)
            driver.execute_script("arguments[0].click();", club_element)
            time.sleep(
                3
            )  # On laisse le temps au panneau de droite de charger les infos

            # =======================================================
            # 🚀 EXTRACTION DES DONNÉES AVEC LES IDs TROUVÉS
            # =======================================================
            try:
                # 1. Couleur du maillot (tzA11)
                equipe["couleur_maillot"] = driver.find_element(
                    By.ID, "tzA11"
                ).text.strip()
            except:
                equipe["couleur_maillot"] = "Non trouvé"

            try:
                # 2. Infos terrains (Heures, Synthétique/Gazon...) -> c'est l'ID tzA19
                info_terrain = driver.find_element(By.ID, "tzA19").text.strip()
                # On remplace les sauts de ligne moches par des tirets/barres pour faire propre
                equipe["terrain_nom"] = re.sub(r"\n+", " | ", info_terrain)
            except:
                equipe["terrain_nom"] = "Non trouvé"

            try:
                # 3. Adresse physique du terrain et directions -> c'est l'ID tzA14
                adresse = driver.find_element(By.ID, "tzA14").text.strip()
                # On remplace les sauts de ligne par des virgules
                equipe["terrain_adresse"] = re.sub(r"\n+", ", ", adresse)
            except:
                equipe["terrain_adresse"] = "Non trouvé"

            print(f"   ✅ Fiche extraite ! (Maillot: {equipe['couleur_maillot']})")

        except Exception as e:
            print(f"   ⚠️ Impossible de cliquer sur {nom_club_propre}")

    # Sauvegarde finale
    os.makedirs("../data", exist_ok=True)
    with open("../data/abssa_data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

    print(f"\n🎉 TOUTES LES ÉQUIPES ONT ÉTÉ TRAITÉES ET SAUVEGARDÉES !")

except Exception as e:
    print(f"\n❌ ERREUR GLOBALE : {e}")

finally:
    driver.quit()
    print("🔌 Navigateur fermé.")
