#!/usr/bin/env python3
"""
HomeOps — Odoo Maintenance module seed data (idempotent).

Creates realistic home maintenance data via XML-RPC.
Safe to run multiple times: existing records are matched by name/serial
and skipped. New records from the script are added.

Waits for Odoo to be ready before seeding (useful in docker-compose).

Environment variables (or CLI args):
    ODOO_URL      (default: http://localhost:8069)
    ODOO_DB       (default: homeops)
    ODOO_USER     (default: admin)
    ODOO_PASSWORD (default: admin)
"""

import os
import sys
import time
import xmlrpc.client
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------

URL = os.environ.get("ODOO_URL", "http://localhost:8069")
DB = os.environ.get("ODOO_DB", "homeops")
USER = os.environ.get("ODOO_USER", "admin")
PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")

MAX_RETRIES = int(os.environ.get("ODOO_INIT_RETRIES", "30"))
RETRY_DELAY = int(os.environ.get("ODOO_INIT_DELAY", "5"))


# ---------------------------------------------------------------------------
# Odoo XML-RPC client
# ---------------------------------------------------------------------------

class OdooRPC:
    def __init__(self, url: str, db: str, user: str, password: str):
        self.db = db
        self.password = password
        self.models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        self.uid = common.authenticate(db, user, password, {})
        if not self.uid:
            raise ConnectionError(f"Authentication failed for {user}@{db}")
        print(f"Connected as uid={self.uid}")

    def search(self, model: str, domain: list) -> list[int]:
        return self.models.execute_kw(
            self.db, self.uid, self.password, model, "search", [domain]
        )

    def create(self, model: str, vals: dict) -> int:
        return self.models.execute_kw(
            self.db, self.uid, self.password, model, "create", [vals]
        )

    def search_read(self, model: str, domain: list, fields: list) -> list[dict]:
        return self.models.execute_kw(
            self.db, self.uid, self.password, model, "search_read",
            [domain], {"fields": fields}
        )

    def find_or_create(self, model: str, match_field: str, match_value: str, vals: dict) -> tuple[int, bool]:
        """Return (id, created). Finds by match_field or creates with vals."""
        existing = self.search(model, [(match_field, "=", match_value)])
        if existing:
            return existing[0], False
        record_id = self.create(model, vals)
        return record_id, True


# ---------------------------------------------------------------------------
# Wait for Odoo readiness
# ---------------------------------------------------------------------------

def wait_for_odoo(url: str, db: str, user: str, password: str) -> OdooRPC:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            rpc = OdooRPC(url, db, user, password)
            return rpc
        except Exception as e:
            print(f"[{attempt}/{MAX_RETRIES}] Odoo not ready: {e}")
            if attempt == MAX_RETRIES:
                print("ERROR: Odoo did not become ready in time.")
                sys.exit(1)
            time.sleep(RETRY_DELAY)


# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

CATEGORIES = [
    ("Électroménager", "Lave-linge, sèche-linge, lave-vaisselle, réfrigérateur, four, etc."),
    ("Chauffage / Climatisation", "Chaudière, pompe à chaleur, radiateurs, climatiseur, VMC."),
    ("Plomberie", "Robinetterie, chauffe-eau, canalisations, WC, siphons."),
    ("Électricité", "Tableau électrique, prises, interrupteurs, éclairage."),
    ("Menuiserie / Ouvrants", "Portes, fenêtres, volets roulants, serrures."),
    ("Extérieur / Jardin", "Tondeuse, portail, arrosage, piscine."),
]

TEAMS = ["Occupant", "Artisan / Pro"]

# (name, model, serial_no, category, location, cost, warranty_months, note)
EQUIPMENT = [
    ("Lave-linge", "Samsung WW90T554DAW", "SN-WM-2022-4851", "Électroménager",
     "Buanderie", 649.0, 24, "Capacité 9kg, programme vapeur. Filtre à nettoyer tous les mois."),
    ("Sèche-linge", "Bosch WTH85V02FF", "SN-DR-2022-7723", "Électroménager",
     "Buanderie", 529.0, 24, "Condensation, pompe à chaleur. Vider le bac après chaque cycle."),
    ("Lave-vaisselle", "Bosch SMS4HVW33E", "SN-DW-2021-3390", "Électroménager",
     "Cuisine", 499.0, 24, "14 couverts, 44dB. Nettoyer le filtre chaque semaine."),
    ("Réfrigérateur", "LG GBB72PZVCN1", "SN-FR-2023-1102", "Électroménager",
     "Cuisine", 879.0, 36, "Combiné 384L, No Frost. Nettoyer le condenseur tous les 6 mois."),
    ("Four encastrable", "Whirlpool W7 OM4 4S1 P", "SN-OV-2020-8845", "Électroménager",
     "Cuisine", 399.0, 24, "Pyrolyse, 73L, classe A+."),
    ("Chaudière gaz", "Saunier Duval ThemaPlus F25E", "SN-BL-2019-5567",
     "Chauffage / Climatisation", "Garage", 1850.0, 24,
     "Entretien annuel obligatoire. Dernier entretien : sept. 2025."),
    ("Pompe à chaleur", "Daikin Altherma 3 ERGA06DV", "SN-HP-2023-9012",
     "Chauffage / Climatisation", "Extérieur", 8500.0, 60,
     "Air/eau, 6kW. Contrôle fluide frigorigène tous les 2 ans."),
    ("VMC double flux", "Atlantic Duolix Max", "SN-VM-2021-6644",
     "Chauffage / Climatisation", "Combles", 1200.0, 24,
     "Filtres à changer tous les 6 mois."),
    ("Chauffe-eau thermodynamique", "Atlantic Calypso 250L", "SN-WH-2022-3321",
     "Plomberie", "Garage", 1650.0, 36,
     "250L, COP 3.4. Vérifier l'anode tous les 2 ans."),
    ("Adoucisseur d'eau", "BWT Perla Silk M", "SN-WS-2023-7788",
     "Plomberie", "Garage", 1100.0, 24,
     "Régénération automatique. Sel à recharger mensuellement."),
    ("Tableau électrique", "Legrand Drivia 4R", "SN-EP-2018-1100",
     "Électricité", "Entrée", 350.0, 0,
     "4 rangées, 52 modules. Différentiels 30mA type A+AC."),
    ("Volet roulant cuisine", "Somfy IO", "SN-VR-2021-4455",
     "Menuiserie / Ouvrants", "Cuisine", 380.0, 24, "Moteur IO, télécommande Situo."),
    ("Volet roulant salon", "Somfy IO", "SN-VR-2021-4456",
     "Menuiserie / Ouvrants", "Salon", 380.0, 24, "Moteur IO, télécommande Situo."),
    ("Portail coulissant", "CAME BXV-400", "SN-GT-2020-2233",
     "Extérieur / Jardin", "Entrée extérieure", 1200.0, 24,
     "Moteur 400kg max. Graissage rail tous les 6 mois."),
    ("Tondeuse robot", "Husqvarna Automower 305", "SN-MW-2023-5566",
     "Extérieur / Jardin", "Jardin", 999.0, 24,
     "600m², fil périphérique. Hiverner d'octobre à mars."),
]

# (name, equipment_serial, type, priority, stage, team, description, schedule_days_offset)
REQUESTS = [
    ("Lave-linge : code erreur UE", "SN-WM-2022-4851", "corrective", "1",
     "New Request", "Occupant",
     "Le lave-linge affiche le code UE en milieu de cycle. "
     "L'essorage ne se lance pas. Vérifier l'équilibrage du tambour et les amortisseurs.",
     None),
    ("Fuite sous le lave-vaisselle", "SN-DW-2021-3390", "corrective", "2",
     "In Progress", "Occupant",
     "Flaque d'eau constatée après chaque cycle. "
     "Probablement le joint de porte ou le tuyau de vidange.", -2),
    ("Volet roulant salon bloqué", "SN-VR-2021-4456", "corrective", "1",
     "New Request", "Artisan / Pro",
     "Le volet ne descend plus. Le moteur tourne dans le vide. "
     "Possiblement une lame décrochée ou un axe cassé.", None),
    ("Chaudière : pression basse", "SN-BL-2019-5567", "corrective", "2",
     "In Progress", "Artisan / Pro",
     "Pression tombée à 0.5 bar, voyant rouge. "
     "Rechercher fuite sur le circuit de chauffage, vérifier le vase d'expansion.", -5),
    ("Portail ne se ferme plus", "SN-GT-2020-2233", "corrective", "1",
     "New Request", "Artisan / Pro",
     "Le portail s'ouvre mais refuse de se fermer. "
     "Vérifier les cellules photoélectriques et le fin de course.", None),
    ("Entretien annuel chaudière", "SN-BL-2019-5567", "preventive", "0",
     "New Request", "Artisan / Pro",
     "Entretien annuel obligatoire. Vérification brûleur, analyse combustion, "
     "contrôle étanchéité, nettoyage corps de chauffe.", 30),
    ("Nettoyage filtres VMC", "SN-VM-2021-6644", "preventive", "0",
     "New Request", "Occupant",
     "Remplacement des filtres G4/F7. Vérifier l'encrassement des bouches d'extraction.", 14),
    ("Détartrage chauffe-eau", "SN-WH-2022-3321", "preventive", "0",
     "New Request", "Artisan / Pro",
     "Vérification de l'anode magnésium, détartrage de la résistance, "
     "contrôle du groupe de sécurité.", 60),
    ("Rechargement sel adoucisseur", "SN-WS-2023-7788", "preventive", "0",
     "New Request", "Occupant",
     "Vérifier le niveau de sel et recharger si nécessaire. "
     "Contrôler la dureté en sortie avec bandelette test.", 3),
    ("Graissage rail portail", "SN-GT-2020-2233", "preventive", "0",
     "New Request", "Occupant",
     "Graisser le rail de guidage et la crémaillère. "
     "Vérifier le serrage des fixations et l'état des galets.", 45),
    ("Hivernage tondeuse robot", "SN-MW-2023-5566", "preventive", "0",
     "New Request", "Occupant",
     "Nettoyer les lames, charger la batterie à 100%, "
     "stocker à l'intérieur. Vérifier le fil périphérique au printemps.", 90),
]


# ---------------------------------------------------------------------------
# Seed logic (idempotent)
# ---------------------------------------------------------------------------

def seed(rpc: OdooRPC):
    now = datetime.now()
    created_count = {"teams": 0, "categories": 0, "equipment": 0, "requests": 0}
    skipped_count = {"teams": 0, "categories": 0, "equipment": 0, "requests": 0}

    # --- Teams ---
    print("\n--- Teams ---")
    team_map = {}
    for name in TEAMS:
        tid, created = rpc.find_or_create("maintenance.team", "name", name, {"name": name})
        team_map[name] = tid
        if created:
            created_count["teams"] += 1
            print(f"  + {name}")
        else:
            skipped_count["teams"] += 1
            print(f"  = {name} (exists)")

    # --- Categories ---
    print("\n--- Categories ---")
    cat_map = {}
    for name, note in CATEGORIES:
        cid, created = rpc.find_or_create(
            "maintenance.equipment.category", "name", name,
            {"name": name, "note": note},
        )
        cat_map[name] = cid
        if created:
            created_count["categories"] += 1
            print(f"  + {name}")
        else:
            skipped_count["categories"] += 1
            print(f"  = {name} (exists)")

    # --- Equipment (matched by serial_no) ---
    print("\n--- Equipment ---")
    equip_by_serial = {}
    for name, model, serial, cat, location, cost, warranty_mo, note in EQUIPMENT:
        warranty_date = False
        if warranty_mo > 0:
            warranty_date = (now + timedelta(days=warranty_mo * 30)).strftime("%Y-%m-%d")

        eid, created = rpc.find_or_create(
            "maintenance.equipment", "serial_no", serial,
            {
                "name": name,
                "model": model,
                "serial_no": serial,
                "category_id": cat_map[cat],
                "location": location,
                "cost": cost,
                "warranty_date": warranty_date,
                "note": note,
                "owner_user_id": rpc.uid,
                "maintenance_team_id": team_map["Occupant"],
            },
        )
        equip_by_serial[serial] = eid
        if created:
            created_count["equipment"] += 1
            print(f"  + {name} ({serial})")
        else:
            skipped_count["equipment"] += 1
            print(f"  = {name} ({serial}) (exists)")

    # --- Stages ---
    stages = {s["name"]: s["id"] for s in rpc.search_read("maintenance.stage", [], ["id", "name"])}

    # --- Maintenance requests (matched by name) ---
    print("\n--- Maintenance requests ---")
    for name, equip_serial, mtype, priority, stage, team, desc, sched_offset in REQUESTS:
        vals = {
            "name": name,
            "equipment_id": equip_by_serial[equip_serial],
            "maintenance_type": mtype,
            "priority": priority,
            "stage_id": stages[stage],
            "maintenance_team_id": team_map[team],
            "description": desc,
            "owner_user_id": rpc.uid,
            "user_id": rpc.uid,
            "request_date": now.strftime("%Y-%m-%d"),
        }
        if sched_offset is not None:
            vals["schedule_date"] = (now + timedelta(days=sched_offset)).strftime("%Y-%m-%d %H:%M:%S")

        rid, created = rpc.find_or_create("maintenance.request", "name", name, vals)
        tag = "CORRECTIF" if mtype == "corrective" else "PRÉVENTIF"
        if created:
            created_count["requests"] += 1
            print(f"  + [{tag}] {name}")
        else:
            skipped_count["requests"] += 1
            print(f"  = [{tag}] {name} (exists)")

    # --- Summary ---
    total_created = sum(created_count.values())
    total_skipped = sum(skipped_count.values())
    print(f"\nDone. Created {total_created}, skipped {total_skipped} (already existed).")


def main():
    print(f"HomeOps Odoo seed — {URL} db={DB} user={USER}")
    rpc = wait_for_odoo(URL, DB, USER, PASSWORD)
    seed(rpc)


if __name__ == "__main__":
    main()
