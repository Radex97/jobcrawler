import logging
import os
from datetime import datetime
import time

# Logging konfigurieren
logger = logging.getLogger(__name__)

def get_database():
    """
    Stellt eine Verbindung zur PostgreSQL-Datenbank her
    """
    # Prüfe alle möglichen Umgebungsvariablen für die Datenbankverbindung
    database_url = None
    env_vars_tried = []
    
    for var_name in ["DATABASE_URL", "DATABASE_PUBLIC_URL", "POSTGRES_URL", "PGDATABASE"]:
        if os.environ.get(var_name):
            env_vars_tried.append(var_name)
            if database_url is None:  # Verwende die erste gefundene Variable
                database_url = os.environ.get(var_name)
                logger.info(f"Verwende {var_name} für Datenbankverbindung")
    
    # Fallback auf lokale Datenbank, wenn keine Umgebungsvariable gefunden wurde
    if database_url is None:
        database_url = "postgres:///jobbig"
        logger.warning(f"Keine Datenbank-Umgebungsvariable gefunden. Geprüfte Variablen: {', '.join(env_vars_tried) or 'keine'}. Verwende Fallback: {database_url}")
    else:
        # Obfuskiere das Passwort für das Logging
        url_parts = database_url.split('@')
        if len(url_parts) > 1:
            # Es gibt ein @ in der URL, also vermutlich ein Passwort
            masked_url = f"{url_parts[0].split(':')[0]}:***@{url_parts[1]}"
            logger.info(f"Verwende Datenbankverbindung (maskiert): {masked_url}")
        else:
            logger.info(f"Verwende Datenbankverbindung (ohne Credentials)")
    
    # Railway verwendet 'postgres://' anstatt 'postgresql://'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        logger.info("Datenbankstring von postgres:// auf postgresql:// korrigiert")
    
    # Logge einige Umgebungsinformationen für Debugging
    logger.info(f"Aktuelle Umgebungsvariablen (nur Namen): {', '.join(sorted(os.environ.keys()))}")    
        
    # Erhöhter Timeout für Railway-Verbindungen (30 statt 10 Sekunden)
    connect_timeout = 30
    logger.info(f"Verwende Verbindungs-Timeout von {connect_timeout} Sekunden")
        
    # Versuche zuerst mit psycopg
    try:
        import psycopg
        # Erhöhe das Connection-Timeout für langsame Netzwerke
        logger.info(f"Versuche Verbindungsaufbau mit psycopg...")
        conn = psycopg.connect(
            database_url, 
            connect_timeout=connect_timeout,
            application_name="jobbig-app"  # Hilft bei der Identifikation in DB-Logs
        )
        logger.info("Datenbankverbindung erfolgreich mit psycopg hergestellt")
        return conn
    except ImportError as e:
        logger.warning(f"psycopg nicht verfügbar: {e}")
    except Exception as e:
        logger.error(f"Fehler beim Herstellen der Datenbankverbindung mit psycopg: {type(e).__name__}: {e}")
        logger.error(f"Connection string verwendet (maskiert): {database_url.split('@')[0].split(':')[0]}:***@{database_url.split('@')[1] if '@' in database_url else 'keine-auth'}")
    
    # Versuche mit psycopg2, wenn psycopg nicht funktioniert
    try:
        import psycopg2
        # Erhöhe das Connection-Timeout für langsame Netzwerke
        logger.info(f"Versuche Verbindungsaufbau mit psycopg2...")
        conn = psycopg2.connect(
            database_url, 
            connect_timeout=connect_timeout,
            application_name="jobbig-app"  # Hilft bei der Identifikation in DB-Logs
        )
        logger.info("Datenbankverbindung erfolgreich mit psycopg2 hergestellt")
        return conn
    except ImportError as e:
        logger.warning(f"psycopg2 nicht verfügbar: {e}")
    except Exception as e:
        logger.error(f"Fehler beim Herstellen der Datenbankverbindung mit psycopg2: {type(e).__name__}: {e}")
        logger.error(f"Connection string verwendet (maskiert): {database_url.split('@')[0].split(':')[0]}:***@{database_url.split('@')[1] if '@' in database_url else 'keine-auth'}")
    
    # Wenn keine Methode funktioniert hat
    logger.error("Keine Datenbankverbindung konnte hergestellt werden")
    return None

def verify_database_connection():
    """
    Überprüft, ob eine Verbindung zur Datenbank hergestellt werden kann
    """
    # Erweitere das Timeout für die Verbindungsüberprüfung
    max_retries = 3
    retry_delay = 2  # Sekunden
    
    for attempt in range(1, max_retries + 1):
        logger.info(f"Überprüfe Datenbankverbindung (Versuch {attempt}/{max_retries})...")
        
        try:
            conn = get_database()
            if conn:
                try:
                    with conn.cursor() as cur:
                        start_time = datetime.now()
                        cur.execute("SELECT version(), current_timestamp, pg_backend_pid()")
                        result = cur.fetchone()
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        
                        if result:
                            logger.info(f"Datenbankverbindung erfolgreich verifiziert in {duration:.2f}s: PostgreSQL {result[0].split(' ')[1] if result[0] else 'unbekannt'}")
                            logger.info(f"Datenbank-Zeit: {result[1]}, Backend-PID: {result[2]}")
                    conn.close()
                    return True
                except Exception as e:
                    logger.error(f"Fehler bei der Datenbankabfrage: {type(e).__name__}: {e}")
                    try:
                        conn.close()
                    except:
                        pass
            else:
                logger.warning("get_database() hat keine Verbindung zurückgegeben")
            
            # Bei Fehlschlag: Warte und versuche es erneut, außer beim letzten Versuch
            if attempt < max_retries:
                logger.info(f"Warte {retry_delay} Sekunden vor dem nächsten Verbindungsversuch...")
                time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei der Überprüfung der Datenbankverbindung: {type(e).__name__}: {e}")
            if attempt < max_retries:
                logger.info(f"Warte {retry_delay} Sekunden vor dem nächsten Verbindungsversuch...")
                time.sleep(retry_delay)
    
    logger.error(f"Datenbankverbindung konnte nach {max_retries} Versuchen nicht hergestellt werden")
    return False

def save_new_jobs(jobs):
    """
    Speichert neue Jobs in der Datenbank
    """
    if not jobs:
        logger.info("Keine Jobs zum Speichern vorhanden")
        return
    
    conn = get_database()
    if not conn:
        logger.error("Keine Datenbankverbindung vorhanden, Jobs können nicht gespeichert werden")
        return
    
    try:
        with conn.cursor() as cur:
            # Prüfe ob die Tabelle existiert
            try:
                cur.execute("SELECT COUNT(*) FROM jobs")
                count = cur.fetchone()[0]
                logger.info(f"Jobs-Tabelle existiert mit {count} Einträgen")
            except Exception as e:
                logger.warning(f"Jobs-Tabelle existiert möglicherweise nicht: {e}")
                logger.info("Versuche Tabelle zu erstellen...")
                create_tables_if_not_exist()
                conn = get_database()  # Neue Verbindung nach Tabellenerstellung
                if not conn:
                    return
            
            # Zuerst alle bestehenden Jobs löschen
            try:
                cur.execute("DELETE FROM jobs")
                logger.info("Bestehende Jobs in der Datenbank gelöscht")
            except Exception as e:
                logger.error(f"Fehler beim Löschen bestehender Jobs: {e}")
                return
            
            # Jetzt neue Jobs einfügen
            inserted = 0
            for job in jobs:
                if not isinstance(job, dict):
                    logger.warning(f"Ungültiger Job, überspringe: {job}")
                    continue
                
                try:
                    cur.execute(
                        "INSERT INTO jobs (title, company, location, url, source) VALUES (%s, %s, %s, %s, %s)",
                        (
                            job.get("title", "Unbekannter Titel"),
                            job.get("company", "Unbekanntes Unternehmen"),
                            job.get("location", "Unbekannter Ort"),
                            job.get("url", "https://example.com"),
                            job.get("source", "unbekannt"),
                        )
                    )
                    inserted += 1
                except Exception as e:
                    logger.error(f"Fehler beim Einfügen eines Jobs: {e}")
            
            conn.commit()
            logger.info(f"{inserted} von {len(jobs)} Jobs in der Datenbank gespeichert")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Jobs in der Datenbank: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_jobs_by_criteria(title="", city="", source=""):
    """
    Ruft Jobs aus der Datenbank ab, die den angegebenen Kriterien entsprechen
    """
    conn = get_database()
    if not conn:
        logger.error("Keine Datenbankverbindung vorhanden, Jobs können nicht abgerufen werden")
        return []
    
    jobs = []
    try:
        with conn.cursor() as cur:
            # Prüfe ob die Tabelle existiert
            try:
                cur.execute("SELECT COUNT(*) FROM jobs")
                count = cur.fetchone()[0]
                logger.info(f"Jobs-Tabelle existiert mit {count} Einträgen")
            except Exception as e:
                logger.warning(f"Jobs-Tabelle existiert möglicherweise nicht: {e}")
                return []
                
            query = "SELECT id, title, company, location, url, source FROM jobs WHERE 1=1"
            params = []
            
            if title:
                query += " AND title ILIKE %s"
                params.append(f"%{title}%")
            
            if city:
                query += " AND location ILIKE %s"
                params.append(f"%{city}%")
            
            if source:
                query += " AND source = %s"
                params.append(source)
            
            cur.execute(query, params)
            
            for row in cur:
                jobs.append({
                    "id": row[0],
                    "title": row[1],
                    "company": row[2],
                    "location": row[3],
                    "url": row[4],
                    "source": row[5]
                })
            
            logger.info(f"{len(jobs)} Jobs aus der Datenbank abgerufen")
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Jobs aus der Datenbank: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
    
    return jobs

def create_tables_if_not_exist():
    """
    Erstellt die benötigten Tabellen, falls sie noch nicht existieren
    """
    conn = get_database()
    if not conn:
        logger.error("Keine Datenbankverbindung vorhanden, Tabellen können nicht erstellt werden")
        return False
    
    try:
        with conn.cursor() as cur:
            # Prüfe, ob die jobs-Tabelle existiert
            try:
                cur.execute("""
                    SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'jobs'
                    );
                """)
                table_exists = cur.fetchone()[0]
                
                if not table_exists:
                    logger.info("Jobs-Tabelle existiert nicht, erstelle sie")
                    cur.execute("""
                        CREATE TABLE jobs (
                            id SERIAL PRIMARY KEY,
                            title VARCHAR(200) NOT NULL,
                            company VARCHAR(200) NOT NULL,
                            location VARCHAR(200) NOT NULL,
                            url VARCHAR(200) NOT NULL,
                            source VARCHAR(200) NOT NULL
                        );
                    """)
                    conn.commit()
                    logger.info("Jobs-Tabelle erfolgreich erstellt")
                else:
                    logger.info("Jobs-Tabelle existiert bereits")
                    
                return True
            except Exception as e:
                logger.error(f"Fehler bei der Tabellenprüfung oder -erstellung: {e}")
                # Versuche es einfach direkt mit der CREATE TABLE-Anweisung
                try:
                    logger.info("Versuche Tabelle direkt zu erstellen...")
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS jobs (
                            id SERIAL PRIMARY KEY,
                            title VARCHAR(200) NOT NULL,
                            company VARCHAR(200) NOT NULL,
                            location VARCHAR(200) NOT NULL,
                            url VARCHAR(200) NOT NULL,
                            source VARCHAR(200) NOT NULL
                        );
                    """)
                    conn.commit()
                    logger.info("Jobs-Tabelle mit IF NOT EXISTS erfolgreich erstellt")
                    return True
                except Exception as e2:
                    logger.error(f"Fehler beim direkten Erstellen der Tabelle: {e2}")
                    return False
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Tabellen: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass 