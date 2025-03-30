import urllib3
from bs4 import BeautifulSoup
import logging
import time
import random
import requests

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HTTP-Client mit Timeout konfigurieren
http = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=3.0, read=5.0),
    retries=urllib3.Retry(connect=1, read=1, redirect=1)
)

# Erhöhte Timeouts für HTTP-Anfragen
HTTP_TIMEOUT = 10  # Erhöht von 3/5 auf 10 Sekunden

# Beispieldaten für Elektriker in verschiedenen Städten
EXAMPLE_ELEKTRIKER_JOBS = [
    {
        "title": "Elektroniker / Elektriker (m/w/d)",
        "company": "WISAG Elektrotechnik GmbH",
        "location": "Köln",
        "url": "https://www.stepstone.de/stellenangebote--Elektroniker-Elektriker-m-w-d-Koeln-WISAG-Elektrotechnik-GmbH--8925825-inline.html",
        "source": "stepstone (example)"
    },
    {
        "title": "Elektroniker / Elektriker für Betriebstechnik (m/w/d)",
        "company": "Bayer AG",
        "location": "Köln",
        "url": "https://www.stepstone.de/stellenangebote--Elektroniker-Elektriker-fuer-Betriebstechnik-m-w-d-Koeln-Bayer--8433960-inline.html",
        "source": "stepstone (example)"
    },
    {
        "title": "Elektroinstallateur / Elektriker (m/w/d)",
        "company": "Dussmann Service Deutschland GmbH",
        "location": "Köln",
        "url": "https://www.stepstone.de/stelleangebote--Elektroinstallateur-Elektriker-m-w-d-Koeln-Dussmann-Service-Deutschland-GmbH--9013752-inline.html",
        "source": "stepstone (example)"
    }
]

# Beispieldaten für Monster
EXAMPLE_MONSTER_JOBS = [
    {
        "title": "Elektriker / Elektroniker (m/w/d)",
        "company": "Personalberatung Schulten",
        "location": "Köln",
        "url": "https://www.monster.de/job-suche/elektriker-elektroniker-m-w-d_köln",
        "source": "monster (example)"
    },
    {
        "title": "Elektriker / Elektroniker für Energietechnik (m/w/d)",
        "company": "AXA Konzern AG",
        "location": "Köln",
        "url": "https://www.monster.de/job-suche/elektriker-elektroniker-für-energietechnik-m-w-d_köln",
        "source": "monster (example)"
    },
    {
        "title": "Industrieelektriker (m/w/d)",
        "company": "Randstad Deutschland GmbH",
        "location": "Köln",
        "url": "https://www.monster.de/job-suche/industrieelektriker-m-w-d_köln",
        "source": "monster (example)"
    }
]

def find_stepstone_jobs(title, city, max_jobs=3):
    """
    Findet Stepstone Jobs für den angegebenen Titel und die Stadt.
    
    max_jobs: Maximale Anzahl der zurückzugebenden Jobs (zum Vermeiden von Timeouts)
    """
    start_time = time.time()
    if not title or not city:
        example_jobs = [
            {
                "title": "Beispiel Job Stepstone 1",
                "company": "Muster Firma",
                "location": city or "Berlin",
                "url": "https://www.stepstone.de/jobs/example/in-berlin",
                "source": "stepstone (example)"
            },
            {
                "title": f"{title or 'Developer'} Position",
                "company": "ABC GmbH",
                "location": city or "Berlin",
                "url": f"https://www.stepstone.de/jobs/{title or 'developer'}/in-{city or 'berlin'}",
                "source": "stepstone (example)"
            },
            {
                "title": f"Senior {title or 'Developer'}",
                "company": "Muster Firma",
                "location": city or "Berlin",
                "url": f"https://www.stepstone.de/jobs/{title or 'developer'}/in-{city or 'berlin'}",
                "source": "stepstone (example)"
            }
        ]
        logger.info("Stepstone-Beispieldaten zurückgegeben, da Titel oder Stadt fehlen")
        return example_jobs[:max_jobs]

    logger.info(f"Stepstone-Suche gestartet für Titel='{title}', Stadt='{city}'")
    
    url = f"https://www.stepstone.de/jobs/{title}/in-{city}"
    logger.info(f"Stepstone-URL: {url}")
    
    try:
        # Timeouts erhöht, um unerwartete Verbindungsabbrüche zu vermeiden
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }, timeout=HTTP_TIMEOUT)
        
        if response.status_code != 200:
            logger.warning(f"Fehler beim Abrufen von Stepstone: {response.status_code}")
            # Fallback auf Beispieldaten
            return get_example_jobs(title, city, "stepstone", max_jobs)
        
        soup = BeautifulSoup(response.text, "html.parser")
        job_listings = soup.select("article.resultlist-qlsxrl")
        
        if not job_listings:
            logger.warning("Keine Stepstone-Jobangebote gefunden, versuche alternative Selektor")
            # Versuche alternative Selektoren, falls die Seitenstruktur sich geändert hat
            job_listings = soup.select(".Wrapper-sc-09qggu-0") or soup.select(".ResultsListContainer") or soup.select("article")
        
        if not job_listings:
            logger.warning("Keine Stepstone-Jobangebote gefunden mit alternativen Selektoren")
            return get_example_jobs(title, city, "stepstone", max_jobs)
        
        logger.info(f"Gefundene Stepstone-Jobangebote: {len(job_listings)}")
        
        jobs = []
        for job in job_listings[:max_jobs]:  # Limitieren auf max_jobs
            try:
                # Verschiedene Selektoren für unterschiedliche Seitenversionen/Layouts
                job_title = get_text(job, ["a.resultlist-8job4e", "h2", ".listing-title", ".job-title"])
                company = get_text(job, [".resultlist-1ektyc4", ".listing-company", ".company-name"])
                location = get_text(job, [".resultlist-d0ezlk", ".location", ".listing-location"])
                url_element = job.select_one("a.resultlist-8job4e") or job.select_one("a") or job.select_one("h2 a")
                
                if not job_title or not url_element:
                    logger.warning(f"Unvollständige Job-Informationen, überspringe")
                    continue
                
                url = url_element.get("href", "")
                if not url.startswith("http"):
                    url = "https://www.stepstone.de" + url
                
                if not company:
                    company = "Unbekanntes Unternehmen"
                
                if not location:
                    location = city
                
                jobs.append({
                    "title": job_title,
                    "company": company,
                    "location": location,
                    "url": url,
                    "source": "stepstone"
                })
                
            except Exception as e:
                logger.error(f"Fehler beim Parsen eines Stepstone-Jobs: {e}")
                continue
                
            # Prüfe, ob wir bereits genug Jobs haben
            if len(jobs) >= max_jobs:
                logger.info(f"Max. Anzahl Jobs ({max_jobs}) erreicht, stoppe Suche")
                break
        
        if not jobs:
            logger.warning("Keine gültigen Stepstone-Jobs gefunden, verwende Beispieldaten")
            jobs = get_example_jobs(title, city, "stepstone", max_jobs)
        
        logger.info(f"Stepstone-Suche abgeschlossen in {time.time() - start_time:.2f}s, {len(jobs)} Jobs gefunden")
        return jobs
        
    except Exception as e:
        logger.error(f"Fehler bei Stepstone-Scraping: {e}")
        # Fallback auf Beispieldaten
        return get_example_jobs(title, city, "stepstone", max_jobs)


def find_monster_jobs(title, city, max_jobs=3):
    """
    Findet Monster Jobs für den angegebenen Titel und die Stadt.
    
    max_jobs: Maximale Anzahl der zurückzugebenden Jobs (zum Vermeiden von Timeouts)
    """
    start_time = time.time()
    if not title or not city:
        example_jobs = [
            {
                "title": "Beispiel Job Monster 1",
                "company": "Muster Firma",
                "location": city or "Berlin",
                "url": "https://www.monster.de/jobs/example/in-berlin",
                "source": "monster (example)"
            },
            {
                "title": f"{title or 'Developer'}",
                "company": "Muster Firma",
                "location": city or "Berlin",
                "url": f"https://www.monster.de/jobs/{title or 'developer'}/in-{city or 'berlin'}",
                "source": "monster (example)"
            },
            {
                "title": f"Lead {title or 'developer'}",
                "company": "Muster Firma",
                "location": city or "Berlin",
                "url": f"https://www.monster.de/jobs/{title or 'developer'}/in-{city or 'berlin'}",
                "source": "monster (example)"
            }
        ]
        logger.info("Monster-Beispieldaten zurückgegeben, da Titel oder Stadt fehlen")
        return example_jobs[:max_jobs]

    logger.info(f"Monster-Suche gestartet für Titel='{title}', Stadt='{city}'")
    
    url = f"https://www.monster.de/jobs/suche/?q={title}&where={city}"
    logger.info(f"Monster-URL: {url}")
    
    try:
        # Timeouts erhöht, um unerwartete Verbindungsabbrüche zu vermeiden
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }, timeout=HTTP_TIMEOUT)
        
        if response.status_code != 200:
            logger.warning(f"Fehler beim Abrufen von Monster: {response.status_code}")
            # Fallback auf Beispieldaten
            return get_example_jobs(title, city, "monster", max_jobs)
        
        soup = BeautifulSoup(response.text, "html.parser")
        job_listings = soup.select(".results-card")
        
        if not job_listings:
            logger.warning("Keine Monster-Jobangebote gefunden, versuche alternative Selektor")
            # Versuche alternative Selektoren, falls die Seitenstruktur sich geändert hat
            job_listings = soup.select(".job-cardstyle__JobCardComponent") or soup.select(".job-search-resultsstyle__JobCardWrap") or soup.select("article")
        
        if not job_listings:
            logger.warning("Keine Monster-Jobangebote gefunden mit alternativen Selektoren")
            return get_example_jobs(title, city, "monster", max_jobs)
        
        logger.info(f"Gefundene Monster-Jobangebote: {len(job_listings)}")
        
        jobs = []
        for job in job_listings[:max_jobs]:  # Limitieren auf max_jobs
            try:
                # Verschiedene Selektoren für unterschiedliche Seitenversionen/Layouts
                job_title = get_text(job, [".title", "h2", ".job-title"])
                company = get_text(job, [".company", ".name", ".company-name"])
                location = get_text(job, [".location", ".address", ".job-location"])
                url_element = job.select_one(".title a") or job.select_one("h2 a") or job.select_one("a")
                
                if not job_title or not url_element:
                    logger.warning(f"Unvollständige Job-Informationen, überspringe")
                    continue
                
                url = url_element.get("href", "")
                if not url.startswith("http"):
                    url = "https://www.monster.de" + url
                
                if not company:
                    company = "Unbekanntes Unternehmen"
                
                if not location:
                    location = city
                
                jobs.append({
                    "title": job_title,
                    "company": company,
                    "location": location,
                    "url": url,
                    "source": "monster"
                })
                
            except Exception as e:
                logger.error(f"Fehler beim Parsen eines Monster-Jobs: {e}")
                continue
            
            # Prüfe, ob wir bereits genug Jobs haben
            if len(jobs) >= max_jobs:
                logger.info(f"Max. Anzahl Jobs ({max_jobs}) erreicht, stoppe Suche")
                break
        
        if not jobs:
            logger.warning("Keine gültigen Monster-Jobs gefunden, verwende Beispieldaten")
            jobs = get_example_jobs(title, city, "monster", max_jobs)
        
        logger.info(f"Monster-Suche abgeschlossen in {time.time() - start_time:.2f}s, {len(jobs)} Jobs gefunden")
        return jobs
        
    except Exception as e:
        logger.error(f"Fehler bei Monster-Scraping: {e}")
        # Fallback auf Beispieldaten
        return get_example_jobs(title, city, "monster", max_jobs)

def get_text(element, selectors):
    """
    Versucht, Text aus einem Element mit verschiedenen Selektoren zu extrahieren.
    
    Gibt den ersten gefundenen Text zurück oder leeren String, wenn nichts gefunden wurde.
    """
    for selector in selectors:
        selected = element.select_one(selector)
        if selected and selected.text.strip():
            return selected.text.strip()
    return ""

def get_example_jobs(title, city, source, max_jobs=3):
    """
    Generiert Beispiel-Jobs für den Fall, dass das Scraping fehlschlägt
    """
    jobs = [
        {
            "title": f"Erfahrener {title}",
            "company": "ABC GmbH",
            "location": city,
            "url": f"https://www.{source}.de/jobs/{title}/in-{city}",
            "source": f"{source} (example)"
        },
        {
            "title": title,
            "company": "Muster Firma",
            "location": city,
            "url": f"https://www.{source}.de/jobs/{title}/in-{city}",
            "source": f"{source} (example)"
        },
        {
            "title": f"Lead {title}",
            "company": "Muster Firma",
            "location": city,
            "url": f"https://www.{source}.de/jobs/{title}/in-{city}",
            "source": f"{source} (example)"
        }
    ]
    logger.info(f"Beispiel-Jobs für {source} generiert")
    return jobs[:max_jobs]