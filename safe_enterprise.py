# Importerer sqlite3 – et built-in Python-bibliotek til at arbejde med SQLite-databaser.
# SQLite er en letvægts-database der gemmer alt i én enkelt fil (ingen server nødvendig).
import sqlite3

# Importerer re (regular expressions) – bruges til mønstergenkendelse og filtrering af tekst.
# Her bruger vi det til at fjerne farlige tegn fra brugerinput (sanitering).
import re

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

# --- SETUP: Opretter tabeller med testdata ---

# cursor.execute() sender en SQL-kommando til databasen og udfører den.
# Her sender vi 'DROP TABLE IF EXISTS inventory' – som sletter tabellen 'inventory'
# hvis den allerede eksisterer. Det sikrer at vi starter fra scratch hver gang.
cursor.execute('DROP TABLE IF EXISTS inventory')
cursor.execute('DROP TABLE IF EXISTS employees')

# CREATE TABLE opretter en ny tabel. Her laver vi 'inventory' med 3 kolonner:
#   - asset_id (INT): et heltal der identificerer udstyret
#   - item_name (TEXT): navnet på udstyret (tekst)
#   - status (TEXT): status som f.eks. 'In Use' eller 'Available'
cursor.execute('CREATE TABLE inventory (asset_id INT, item_name TEXT, status TEXT)')

# INSERT INTO tilføjer nye rækker (data) til tabellen.
# VALUES (1, 'MacBook Pro', 'In Use') angiver værdierne for hver kolonne i rækkefølge.
cursor.execute("INSERT INTO inventory VALUES (1, 'MacBook Pro', 'In Use')")
cursor.execute("INSERT INTO inventory VALUES (2, 'Dell Monitor', 'Available')")

# Opretter employees-tabellen med kolonner: id, username, password
cursor.execute('CREATE TABLE employees (id INT, username TEXT, password TEXT)')
# Indsætter en admin-bruger – dette er testdata til at demonstrere SQL injection-risiko.
cursor.execute("INSERT INTO employees VALUES (1, 'admin', 'SuperSecret123')")

# conn.commit() gemmer ALLE ændringer permanent i databasefilen.
# Uden commit() ville ændringerne kun eksistere midlertidigt i hukommelsen
# og gå tabt når programmet lukker. Tænk på det som at trykke "Gem".
conn.commit()

# Printer en overskrift for programmet
print("\n--- SAFE CORPORATE ASSET TRACKER ---")
# input() viser en besked og venter på at brugeren skriver noget.
# Det brugeren skriver gemmes i variablen 'user_input' som en tekststreng.
user_input = input("Enter Asset ID: ")

# --- 1. ENFORCEMENT OF INVARIANTS (Håndhævning af regler/begrænsninger) ---
# En "invariant" er en regel der ALTID skal gælde. Her er reglen:
# "Asset ID skal altid være et tal". .isnumeric() returnerer True hvis
# strengen KUN indeholder cifre (0-9), og False ellers.
if not user_input.isnumeric():
    # Hvis input indeholder bogstaver, symboler, eller SQL-kode → afvis det straks.
    # Dette er første forsvarslinje mod SQL injection.
    print("SECURITY ALERT: Invariant violated! Asset ID must be a numeric value.")
else:
    # --- 2. SANITIZATION (Sanitering/rensning af input) ---
    # Selvom vi allerede ved at input er numerisk, tilføjer vi et ekstra sikkerhedslag.
    # re.sub(r"[^0-9]", "", user_input) fjerner ALT der ikke er et ciffer.
    # r"[^0-9]" er et regex-mønster: ^ betyder "IKKE", og 0-9 er cifre.
    # Så det matcher alt der IKKE er et ciffer og erstatter det med "" (ingenting).
    sanitized_input = re.sub(r"[^0-9]", "", user_input)

    # --- 3. PARAMETERIZED QUERY (Parametriseret forespørgsel) ---
    # I stedet for at sætte brugerens data direkte ind i SQL-strengen (farligt!),
    # bruger vi '?' som en pladsholder. Databasen ved så at alt der sendes
    # via parameteren er REN DATA – ikke SQL-kode. Dette er den vigtigste
    # beskyttelse mod SQL injection.
    #
    # USIKKERT eksempel:  f"SELECT * FROM inventory WHERE asset_id = {user_input}"
    # SIKKERT eksempel:   "SELECT * FROM inventory WHERE asset_id = ?"
    query = "SELECT asset_id, item_name, status FROM inventory WHERE asset_id = ?"

    # Printer forespørgslen og den data der sendes med, så man kan se hvad der sker.
    print(f"Executing Safe SQL: {query} (with data: {sanitized_input})\n")

    try:
        # cursor.execute(query, (sanitized_input,)) – HER SKER DET VIGTIGE:
        # Første argument er SQL-strengen med '?' pladsholder.
        # Andet argument er en TUPLE med data: (sanitized_input,)
        #   - Kommaet efter sanitized_input gør det til en tuple (påkrævet af SQLite).
        # SQLite erstatter '?' med værdien, men behandler den ALTID som data,
        # ALDRIG som SQL-kode. Selv hvis nogen skrev "1 OR 1=1" ville det blive
        # behandlet som en tekst-streng, ikke som SQL-logik.
        cursor.execute(query, (sanitized_input,))

        # cursor.fetchall() henter ALLE rækker der matcher forespørgslen.
        # Returnerer en liste af tuples, f.eks.: [(1, 'MacBook Pro', 'In Use')]
        # Hvis ingen rækker matcher, returneres en tom liste: []
        results = cursor.fetchall()
        
        # Tjekker om der er resultater (en tom liste er False i Python)
        if results:
            # Looper igennem hver række og printer den formateret.
            # row er en tuple, så row[0] = asset_id, row[1] = item_name, row[2] = status.
            for row in results:
                print(f"RESULT: ID: {row[0]} | Item: {row[1]} | Status: {row[2]}")
        else:
            # Ingen resultater fundet for det givne Asset ID
            print("No asset found.")
            
    except Exception as e:
        # try/except fanger fejl der kan ske under kørsel (f.eks. databasefejl).
        # 'e' indeholder selve fejlbeskeden som vi printer.
        print(f"An error occurred: {e}")

# conn.close() lukker forbindelsen til databasen.
# Det er vigtigt at lukke forbindelsen for at frigøre ressourcer (hukommelse, fillåse).
# Ligesom man lukker en fil efter man har læst den.