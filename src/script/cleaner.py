import json
import re
import os


def get_team_number(equipe_full_name):
    """Extrait le numéro de l'équipe (ex: 'AZUR RCS 1' -> '1'). Renvoie vide si aucun."""
    match_numero = re.search(r"\s+(\d+)$", equipe_full_name)
    return match_numero.group(1) if match_numero else ""


def clean_couleur(numero, couleur_raw):
    """Garde uniquement la couleur de l'équipe concernée."""
    if not couleur_raw or couleur_raw == "Non trouvé":
        return "Non défini"

    # Si c'est détaillé par équipes
    if "Equipe" in couleur_raw and numero:
        lignes = couleur_raw.replace("\n", "|").split("|")
        for ligne in lignes:
            partie_gauche = ligne.split(":")[0] if ":" in ligne else ligne
            # Si le numéro de notre équipe est dans la partie gauche
            if "Equipe" in partie_gauche and str(numero) in re.findall(
                r"\d+", partie_gauche
            ):
                return ligne.split(":")[-1].strip()

        return lignes[0].split(":")[-1].strip()

    # Si on n'a pas de numéro, on prend la première ligne valide
    if "\n" in couleur_raw:
        return couleur_raw.split("\n")[0].split(":")[-1].strip()

    return couleur_raw.strip()


def clean_terrain_nom(numero, terrain_nom_raw):
    """Isole les infos du terrain (Heure et surface) spécifiques à l'équipe."""
    if not terrain_nom_raw or terrain_nom_raw == "Non trouvé":
        return "Non défini"

    # Ordre de priorité pour la recherche
    prefixes = [f"Equipe {numero} :", f"Equipe {numero}:"] if numero else []
    prefixes.extend(["Equipe :", "Equipe:"])

    segments = [segment.strip() for segment in terrain_nom_raw.split("|")]

    for prefix in prefixes:
        for s in segments:
            if s.startswith(prefix):
                return s

    return "Info terrain non trouvée"


def get_terrain_code(numero, terrain_nom_raw):
    """Trouve le code du terrain (ex: O 01) assigné à l'équipe dans les infos générales."""
    # On cherche tous les codes de terrains présents (Format Lettre + 2 chiffres, ex: "L 09")
    lignes_codes = re.findall(r"([A-Z]\s\d{2})\s*-", terrain_nom_raw)

    if not lignes_codes:
        return None

    # Si le club n'a qu'un seul terrain, c'est facile
    if len(lignes_codes) == 1:
        return lignes_codes[0]

    # S'il y a plusieurs terrains, on cherche celui de NOTRE équipe
    if numero:
        segments = [segment.strip() for segment in terrain_nom_raw.split("|")]
        for s in segments:
            match_code = re.match(r"^([A-Z]\s\d{2})\s*-", s)
            if match_code:
                # Cherche les numéros d'équipes assignés à ce terrain (ex: "Equipes : 1-2-4")
                match_eq = re.search(
                    r"Equipes?\s*(?::)?\s*([0-9\-\&\s,]+)", s, re.IGNORECASE
                )
                if match_eq:
                    numeros_assignes = re.findall(r"\d+", match_eq.group(1))
                    if str(numero) in numeros_assignes:
                        return match_code.group(1)

    # Par défaut, on renvoie le premier
    return lignes_codes[0]


def clean_terrain_adresse(terrain_code, terrain_adresse_raw):
    """Nettoie l'adresse et isole le bon bloc grâce au code terrain."""
    if not terrain_adresse_raw or terrain_adresse_raw == "Non trouvé":
        return "Adresse non définie"

    # 1. On sépare les adresses si le club a plusieurs terrains (en utilisant le pattern des codes)
    blocs = re.split(r"(?=[A-Z]\s\d{2}\s-)", terrain_adresse_raw)

    bloc_cible = blocs[0]

    # 2. On sélectionne le bloc qui correspond à notre code terrain secret
    if terrain_code:
        for bloc in blocs:
            if bloc.startswith(terrain_code):
                bloc_cible = bloc
                break

    # 3. Maintenant on nettoie ce bloc précis
    parts = [p.strip() for p in bloc_cible.split(",")]

    cp_index = -1
    for i, part in enumerate(parts):
        # L'ancre : 4 chiffres suivis d'un espace et d'une lettre
        if re.match(r"^\d{4}\s+[A-Za-z]", part):
            cp_index = i
            break

    if cp_index != -1:
        rue_parts = []
        for i in range(1, cp_index):
            part = parts[i]
            # On ignore les mentions "Equipe" dans l'adresse
            if part and not part.lower().startswith("equipe"):
                rue_parts.append(part)

        rue_complete = ", ".join(rue_parts)
        if not rue_complete:
            rue_complete = "Rue non trouvée"

        code_postal_ville = parts[cp_index]

        complexe = ""
        if cp_index + 1 < len(parts):
            potential_complex = parts[cp_index + 1]

            direction_words = [
                "au départ",
                "a partir",
                "à partir",
                "en venant",
                "venant",
                "autoroute",
                "ring",
                "via",
                "prendre",
                "sortie",
                "passer",
                "tourner",
                "au rond",
                "rond-point",
                "chaussée",
                "place",
                "par l'autoroute",
                "aux quatre-bras",
                "ou :",
            ]

            is_direction = any(
                potential_complex.lower().startswith(w) for w in direction_words
            )

            if not is_direction and len(potential_complex) < 55:
                complexe = f" | {potential_complex}"

        return f"{rue_complete} - {code_postal_ville}{complexe}"

    # S'il y a un souci, on renvoie le bloc mais on enlève les mots "Equipe"
    bloc_clean = [p for p in parts if not p.lower().startswith("equipe")]
    return ", ".join(bloc_clean)


def process_json_file():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.abspath(
        os.path.join(script_dir, "..", "..", "data", "abssa_data.json")
    )

    print(f"🧹 Démarrage du nettoyage (Niveau Expert)...")

    if not os.path.exists(file_path):
        print(f"❌ Erreur : Le fichier n'existe pas ({file_path}).")
        return

    with open(file_path, "r", encoding="utf-8") as file:
        db = json.load(file)

    for equipe in db.get("classement", []):
        nom_complet = equipe.get("equipe", "")

        # 1. Extraction du numéro (ex: "1" ou "")
        numero = get_team_number(nom_complet)

        # 2. Nettoyage Maillot & Nom Terrain
        equipe["couleur_maillot"] = clean_couleur(
            numero, equipe.get("couleur_maillot", "")
        )
        raw_nom = equipe.get("terrain_nom", "")
        equipe["terrain_nom"] = clean_terrain_nom(numero, raw_nom)

        # 3. Le lien secret : On trouve le code (ex: O 01) dans le texte brut
        code_terrain = get_terrain_code(numero, raw_nom)

        # 4. Nettoyage Adresse avec le bon code
        raw_addr = equipe.get("terrain_adresse", "")
        equipe["terrain_adresse"] = clean_terrain_adresse(code_terrain, raw_addr)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(db, file, indent=4, ensure_ascii=False)

    print(f"✅ Nettoyage terminé ! Les adresses multiples sont domptées.")


if __name__ == "__main__":
    process_json_file()
