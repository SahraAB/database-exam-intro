# Importerer sqlite3 – et built-in Python-bibliotek til at arbejde med SQLite-databaser.
# SQLite er en letvægts-database der gemmer alt i én enkelt fil (ingen server nødvendig).
import sqlite3
# Importerer Path fra pathlib – gør det nemt at arbejde med filstier
# på tværs af operativsystemer (Windows bruger \, Mac/Linux bruger /).
from pathlib import Path 

# Opretter stien til mappen 'databases/' i den nuværende arbejdsmappe.
# Path.cwd() returnerer den mappe, hvorfra scriptet køres.
files_path = Path(str(Path.cwd()) + '/databases/')
# Printer stien så man kan se præcis hvor databasefilen ligger på disken.
print(files_path)

# --- FORBINDELSE TIL DATABASEN ---
# sqlite3.connect() åbner en forbindelse til databasefilen 'enterprise.db'.
# Hvis filen ikke findes, opretter SQLite den automatisk.
# 'conn' (connection) er selve forbindelsen – tænk på det som en åben telefonlinje til databasen.
conn = sqlite3.connect(files_path / 'enterprise.db')

# --- HVAD ER EN CURSOR? ---
# En cursor er et objekt der fungerer som en "fjernbetjening" til databasen.
# Den bruges til at:
#   1. Sende SQL-kommandoer til databasen (via cursor.execute())
#   2. Hente resultater tilbage (via cursor.fetchall() / cursor.fetchone())
# Tænk på det sådan: conn er forbindelsen (telefonlinjen), og cursor er den
# du taler igennem (mundstykket). Du kan have flere cursors på samme forbindelse.
cursor = conn.cursor()

# --- SETUP: Nulstiller og opretter tabeller med testdata ---

# cursor.execute() sender en SQL-kommando til databasen og udfører den.
# Her sender vi 'DROP TABLE IF EXISTS inventory' – som sletter tabellen 'inventory'
# hvis den allerede eksisterer. Det sikrer at vi starter fra scratch hver gang.
cursor.execute('DROP TABLE IF EXISTS inventory')
cursor.execute('DROP TABLE IF EXISTS employees')

# CREATE TABLE opretter en ny tabel. Her laver vi 'inventory' med 3 kolonner:
#   - asset_id (INT): et heltal der identificerer udstyret
#   - item_name (TEXT): navnet på udstyret (tekst)
#   - status (TEXT): status som f.eks. 'In Use' eller 'Available'
# Dette er den "harmløse" tabel som brugeren normalt skal søge i.
cursor.execute('CREATE TABLE inventory (asset_id INT, item_name TEXT, status TEXT)')

# INSERT INTO tilføjer nye rækker (data) til tabellen.
# VALUES (1, 'MacBook Pro', 'In Use') angiver værdierne for hver kolonne i rækkefølge.
cursor.execute("INSERT INTO inventory VALUES (1, 'MacBook Pro', 'In Use')")
cursor.execute("INSERT INTO inventory VALUES (2, 'Dell Monitor', 'Available')")

# Opretter employees-tabellen – dette er den FØLSOMME tabel med brugernavne og passwords.
# En angriber vil forsøge at tilgå denne tabel via SQL injection.
cursor.execute('CREATE TABLE employees (id INT, username TEXT, password TEXT)')
# Indsætter to brugere med passwords i employees-tabellen.
cursor.execute("INSERT INTO employees VALUES (01, 'admin', 'SuperSecret123')")
cursor.execute("INSERT INTO employees VALUES (02, 'employee1', 'Password456')")

# conn.commit() gemmer ALLE ændringer permanent i databasefilen.
# Uden commit() ville ændringerne kun eksistere midlertidigt i hukommelsen
# og gå tabt når programmet lukker. Tænk på det som at trykke "Gem".
conn.commit()

# Printer en overskrift for programmet.
print("\n--- CORPORATE ASSET TRACKER ---")
# input() viser en besked og venter på at brugeren skriver noget.
# Det brugeren skriver gemmes i variablen 'asset_id' som en tekststreng.
asset_id = input("Enter Asset ID: ")

# ============================================================
# ⚠️  SÅRBARHED: STRING CONCATENATION (Streng-sammensætning)
# ============================================================
# Her sættes brugerens input DIREKTE ind i SQL-strengen med en f-string.
# f"...WHERE asset_id = {asset_id}" betyder at Python erstatter {asset_id}
# med præcis det brugeren skrev – UDEN nogen form for kontrol eller rensning.
#
# HVORFOR ER DETTE FARLIGT? (SQL Injection)
# Hvis brugeren skriver "1" bliver forespørgslen:
#   SELECT asset_id, item_name, status FROM inventory WHERE asset_id = 1
#   → Helt normalt og fint.
#
# Men hvis brugeren skriver: 1 UNION SELECT id, username, password FROM employees
# Så bliver den fulde SQL-forespørgsel:
#   SELECT asset_id, item_name, status FROM inventory WHERE asset_id = 1
#   UNION SELECT id, username, password FROM employees
#   → UNION kombinerer to SELECT-forespørgsler, så angriberen får ALT fra employees-tabellen!
#   → Brugernavn og passwords bliver lækket.
#
# INGEN af disse tre sikkerhedstrin bruges her (modsat safe_enterprise.py):
#   1. Ingen invariant-check (vi tjekker ikke om input er et tal)
#   2. Ingen sanitering (vi fjerner ikke farlige tegn)
#   3. Ingen parameterisering (vi bruger ikke '?' pladsholderen)
query = f"SELECT asset_id, item_name, status FROM inventory WHERE asset_id = {asset_id}"

# Printer den fulde SQL-forespørgsel. Her kan man tydeligt se at brugerens
# ondsindede input er blevet en del af selve SQL-kommandoen.
print(f"Executing SQL: {query}\n")

try:
    # cursor.execute(query) sender SQL-kommandoen til databasen og udfører den.
    # PROBLEMET: Hele query-strengen (inkl. brugerens input) køres som SQL-kode.
    # Databasen kan IKKE se forskel på den originale forespørgsel og angriberens kode,
    # fordi det hele er blandet sammen i én streng.
    # I safe_enterprise.py bruger vi i stedet: cursor.execute(query, (data,))
    # hvor data sendes SEPARAT og aldrig fortolkes som SQL.
    cursor.execute(query)

    # cursor.fetchall() henter ALLE rækker der matcher forespørgslen.
    # Returnerer en liste af tuples, f.eks.: [(1, 'MacBook Pro', 'In Use')]
    # Ved en UNION-injection returneres også rækker fra employees-tabellen!
    results = cursor.fetchall()

    # Tjekker om der er resultater (en tom liste er False i Python).
    if results:
        # Looper igennem hver række og printer den formateret.
        # row er en tuple, så row[0] = første kolonne, row[1] = anden, row[2] = tredje.
        # Ved injection vil row[0]=id, row[1]=username, row[2]=password fra employees.
        for row in results:
            print(f"RESULT: ID: {row[0]} | Item: {row[1]} | Status: {row[2]}")
    else:
        # Ingen resultater fundet for det givne Asset ID.
        print("No asset found.")
except Exception as e:
    # try/except fanger fejl der kan ske under kørsel (f.eks. ugyldig SQL-syntaks).
    # 'e' indeholder selve fejlbeskeden som vi printer.
    print(f"SQL Error: {e}")

# conn.close() lukker forbindelsen til databasen.
# Det er vigtigt at lukke forbindelsen for at frigøre ressourcer (hukommelse, fillåse).
# Ligesom man lukker en fil efter man har læst den.
conn.close()