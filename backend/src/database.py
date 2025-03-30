import psycopg
import logging
import os
from datetime import datetime

# Logging konfigurieren
logger = logging.getLogger(__name__)

def get_database():
    """
    Stellt eine Verbindung zur PostgreSQL-Datenbank her
    """
    try:
        database_url = os.environ.get("DATABASE_URL", "postgres:///jobbig")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        conn = psycopg.connect(database_url)
        logger.info("Datenbankverbindung erfolgreich hergestellt")
        return conn
    except Exception as e:
        logger.error(f"Fehler beim Herstellen der Datenbankverbindung: {e}")
        return None

def verify_database_connection():
    """
    Überprüft, ob eine Verbindung zur Datenbank hergestellt werden kann
    """
    try:
        conn = get_database()
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                conn.close()
                return True
        return False
    except Exception as e:
        logger.error(f"Fehler bei der Überprüfung der Datenbankverbindung: {e}")
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
            # Zuerst alle bestehenden Jobs löschen
            cur.execute("DELETE FROM jobs")
            logger.info("Bestehende Jobs in der Datenbank gelöscht")
            
            # Jetzt neue Jobs einfügen
            for job in jobs:
                if not isinstance(job, dict):
                    logger.warning(f"Ungültiger Job, überspringe: {job}")
                    continue
                
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
            
            conn.commit()
            logger.info(f"{len(jobs)} Jobs in der Datenbank gespeichert")
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