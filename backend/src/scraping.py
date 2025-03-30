import urllib3
from bs4 import BeautifulSoup
import logging
import time

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HTTP-Client mit Timeout konfigurieren
http = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=5.0, read=10.0),
    retries=urllib3.Retry(connect=1, read=1, redirect=1)
)

def find_stepstone_jobs(title: str, city: str):
    """ BeautifulSoup4 web scraping for Stepstone """
    start_time = time.time()
    logger.info(f"Starte Stepstone-Scraping für Titel: {title}, Stadt: {city}")
    
    try:
        # Deutsche URL verwenden statt schwedischer
        url = f"https://www.stepstone.de/jobs/{title}/in-{city}"
        logger.info(f"Stepstone-Scraping mit URL: {url}")
        
        # Request mit Timeout
        page = http.request("GET", url)
        logger.info(f"Stepstone-Antwort-Status: {page.status}, Zeit: {time.time() - start_time:.2f}s")
        
        if page.status != 200:
            logger.warning(f"Stepstone-Antwort nicht erfolgreich: Status {page.status}")
            return []
        
        # HTML parsen
        soup = BeautifulSoup(page.data, "lxml")
        
        # Kurze Meldung für Debugging
        logger.info(f"HTML-Parsing abgeschlossen, Zeit: {time.time() - start_time:.2f}s")
        
        # Einfachere Selektoren für bessere Performance
        job_listings = []
        
        # Versuch 1: Nach typischen Stepstone Artikeln suchen
        articles = soup.find_all("article", limit=10)
        if articles:
            logger.info(f"Gefunden {len(articles)} Artikel")
            job_listings = articles
        else:
            # Versuch 2: Allgemeinere Suche nach Job-Listings
            divs = soup.find_all("div", class_=lambda c: c and "job" in c.lower(), limit=10)
            if divs:
                logger.info(f"Gefunden {len(divs)} Job-Divs")
                job_listings = divs
        
        logger.info(f"Gefundene Job-Listings: {len(job_listings)}, Zeit: {time.time() - start_time:.2f}s")
        
        if not job_listings:
            # Fallback: Mock-Daten zurückgeben für Test
            logger.warning("Keine Job-Listings gefunden, verwende Beispieldaten")
            return [
                {
                    "title": f"{title} Stelle in {city}",
                    "company": "Beispiel GmbH",
                    "location": city,
                    "url": "https://www.stepstone.de/",
                    "source": "stepstone (mock)"
                },
                {
                    "title": f"Senior {title} in {city}",
                    "company": "Test AG",
                    "location": city,
                    "url": "https://www.stepstone.de/",
                    "source": "stepstone (mock)"
                }
            ]
        
        jobs = []
        for item in job_listings[:5]:  # Begrenze auf 5 Ergebnisse für bessere Performance
            try:
                # Flexibles Extrahieren von Informationen
                # Titel
                title_elem = (
                    item.find("h2") or 
                    item.find("h3") or 
                    item.find(class_=lambda c: c and "title" in c.lower())
                )
                # Firma
                company_elem = (
                    item.find(class_=lambda c: c and "company" in c.lower()) or
                    item.find("span", class_=lambda c: c and ("company" in c.lower() or "employer" in c.lower()))
                )
                # Ort
                location_elem = (
                    item.find(class_=lambda c: c and ("location" in c.lower() or "place" in c.lower())) or
                    item.find("span", class_=lambda c: c and "location" in c.lower())
                )
                # URL
                url_elem = item.find("a", href=True)
                
                # Stelle ein job-Objekt zusammen, wenn wir die wesentlichen Informationen haben
                if title_elem:
                    job_title = title_elem.get_text().strip() if hasattr(title_elem, "get_text") else "Unbekannter Titel"
                    job_company = company_elem.get_text().strip() if company_elem and hasattr(company_elem, "get_text") else "Unbekannte Firma"
                    job_location = location_elem.get_text().strip() if location_elem and hasattr(location_elem, "get_text") else city
                    job_url = url_elem['href'] if url_elem and url_elem.has_attr('href') else "https://www.stepstone.de/"
                    
                    job = {
                        "title": job_title,
                        "company": job_company,
                        "location": job_location,
                        "url": job_url,
                        "source": "stepstone"
                    }
                    jobs.append(job)
            except Exception as e:
                logger.error(f"Fehler beim Parsen eines Stepstone-Job-Eintrags: {e}")
        
        # Wenn wir keine Jobs extrahieren konnten, Beispiel-Jobs zurückgeben
        if not jobs:
            logger.warning("Keine Jobs extrahiert, verwende Beispieldaten")
            jobs = [
                {
                    "title": f"{title} Stelle in {city}",
                    "company": "Beispiel GmbH",
                    "location": city,
                    "url": "https://www.stepstone.de/",
                    "source": "stepstone (mock)"
                }
            ]
        
        logger.info(f"Erfolgreich {len(jobs)} Jobs von Stepstone extrahiert, Zeit: {time.time() - start_time:.2f}s")
        return jobs
    except Exception as e:
        logger.error(f"Fehler beim Scraping von Stepstone: {e}")
        # Bei einem Fehler geben wir Beispieldaten zurück
        return [
            {
                "title": f"{title} (Fehler beim Scraping)",
                "company": "Fehler beim Laden",
                "location": city,
                "url": "https://www.stepstone.de/",
                "source": "stepstone (error)"
            }
        ]


def find_monster_jobs(title: str or None, city: str or None):
    """ BeautifulSoup4 web scraping for Monster """
    start_time = time.time()
    logger.info(f"Starte Monster-Scraping für Titel: {title}, Stadt: {city}")
    
    try:
        # Deutsche URL verwenden
        url = ""
        if not title and not city:
            url = "https://www.monster.de/jobs/suche/"
        else:
            url = f"https://www.monster.de/jobs/suche/?q={title}&where={city}"
        
        logger.info(f"Monster-Scraping mit URL: {url}")
        
        # Request mit Timeout
        page = http.request("GET", url)
        logger.info(f"Monster-Antwort-Status: {page.status}, Zeit: {time.time() - start_time:.2f}s")
        
        if page.status != 200:
            logger.warning(f"Monster-Antwort nicht erfolgreich: Status {page.status}")
            return []
        
        # HTML parsen
        soup = BeautifulSoup(page.data, "lxml")
        logger.info(f"HTML-Parsing abgeschlossen, Zeit: {time.time() - start_time:.2f}s")
        
        # Verschiedene Selektoren ausprobieren
        job_listings = []
        
        # Versuch 1: typisches Monster-Layout
        cards = soup.find_all("div", class_=lambda c: c and "card" in c.lower(), limit=10)
        if cards:
            logger.info(f"Gefunden {len(cards)} Karten")
            job_listings = cards
        else:
            # Versuch 2: Allgemeinere Suche
            divs = soup.find_all("div", class_=lambda c: c and "job" in c.lower(), limit=10)
            if divs:
                logger.info(f"Gefunden {len(divs)} Job-Divs")
                job_listings = divs
        
        logger.info(f"Gefundene Job-Listings: {len(job_listings)}, Zeit: {time.time() - start_time:.2f}s")
        
        if not job_listings:
            # Fallback: Mock-Daten zurückgeben für Test
            logger.warning("Keine Job-Listings gefunden, verwende Beispieldaten")
            return [
                {
                    "title": f"{title} Stelle in {city}",
                    "company": "Beispiel GmbH",
                    "location": city,
                    "url": "https://www.monster.de/",
                    "source": "monster (mock)"
                },
                {
                    "title": f"Senior {title} in {city}",
                    "company": "Test AG",
                    "location": city,
                    "url": "https://www.monster.de/",
                    "source": "monster (mock)"
                }
            ]
        
        jobs = []
        for item in job_listings[:5]:  # Begrenze auf 5 Ergebnisse für bessere Performance
            try:
                # Flexibles Extrahieren von Informationen
                # Titel
                title_elem = (
                    item.find("h2") or 
                    item.find("h3") or 
                    item.find(class_=lambda c: c and "title" in c.lower())
                )
                # Firma
                company_elem = (
                    item.find(class_=lambda c: c and "company" in c.lower()) or
                    item.find("div", class_=lambda c: c and "company" in c.lower())
                )
                # Ort
                location_elem = (
                    item.find(class_=lambda c: c and ("location" in c.lower() or "place" in c.lower())) or
                    item.find("div", class_=lambda c: c and "location" in c.lower())
                )
                # URL
                url_elem = item.find("a", href=True)
                
                # Stelle ein job-Objekt zusammen, wenn wir die wesentlichen Informationen haben
                if title_elem:
                    job_title = title_elem.get_text().strip() if hasattr(title_elem, "get_text") else "Unbekannter Titel"
                    job_company = company_elem.get_text().strip() if company_elem and hasattr(company_elem, "get_text") else "Unbekannte Firma"
                    job_location = location_elem.get_text().strip() if location_elem and hasattr(location_elem, "get_text") else city
                    job_url = url_elem['href'] if url_elem and url_elem.has_attr('href') else "https://www.monster.de/"
                    
                    job = {
                        "title": job_title,
                        "company": job_company,
                        "location": job_location,
                        "url": job_url,
                        "source": "monster"
                    }
                    jobs.append(job)
            except Exception as e:
                logger.error(f"Fehler beim Parsen eines Monster-Job-Eintrags: {e}")
        
        # Wenn wir keine Jobs extrahieren konnten, Beispiel-Jobs zurückgeben
        if not jobs:
            logger.warning("Keine Jobs extrahiert, verwende Beispieldaten")
            jobs = [
                {
                    "title": f"{title} Stelle in {city}",
                    "company": "Beispiel GmbH",
                    "location": city,
                    "url": "https://www.monster.de/",
                    "source": "monster (mock)"
                }
            ]
        
        logger.info(f"Erfolgreich {len(jobs)} Jobs von Monster extrahiert, Zeit: {time.time() - start_time:.2f}s")
        return jobs
    except Exception as e:
        logger.error(f"Fehler beim Scraping von Monster: {e}")
        # Bei einem Fehler geben wir Beispieldaten zurück
        return [
            {
                "title": f"{title} (Fehler beim Scraping)",
                "company": "Fehler beim Laden",
                "location": city,
                "url": "https://www.monster.de/",
                "source": "monster (error)"
            }
        ]