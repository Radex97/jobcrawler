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
HTTP_TIMEOUT = 15  # Erhöht auf 15 Sekunden

# Debug-Modus für Scraper-Entwicklung
DEBUG_MODE = False  # Auf False setzen für Produktionsumgebung

# Erweiterte User-Agent-Rotation zur Vermeidung von Blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]

def get_random_user_agent():
    """Wählt einen zufälligen User-Agent aus der Liste aus"""
    return random.choice(USER_AGENTS)

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
        logger.info("Stepstone-Beispieldaten zurückgegeben, da Titel oder Stadt fehlen")
        return get_example_jobs(title, city, "stepstone", max_jobs)
        
    # Debug-Modus: Immer Beispieldaten zurückgeben
    if DEBUG_MODE:
        logger.info("DEBUG-MODUS: Stepstone-Beispieldaten werden zurückgegeben")
        return get_example_jobs(title, city, "stepstone", max_jobs)

    logger.info(f"Stepstone-Suche gestartet für Titel='{title}', Stadt='{city}'")
    
    # URL-Formatierung verbessert - Leerzeichen durch Bindestrich ersetzen
    search_title = title.replace(" ", "-").lower()
    search_city = city.replace(" ", "-").lower()
    url = f"https://www.stepstone.de/jobs/{search_title}/in-{search_city}"
    logger.info(f"Stepstone-URL: {url}")
    
    # Alternative URLs für den Fall, dass die Haupturl nicht funktioniert
    alternative_urls = [
        f"https://www.stepstone.de/jobs/{search_title}/in-{search_city}",
        f"https://www.stepstone.de/stellenangebote/{search_title}/{search_city}",
        f"https://www.stepstone.de/stellenangebote/suche/{search_title}-in-{search_city}"
    ]
    
    jobs = []
    
    # Versuche verschiedene URLs
    for current_url in alternative_urls:
        if jobs:
            break  # Wenn wir bereits Jobs gefunden haben, beenden
            
        try:
            logger.info(f"Versuche URL: {current_url}")
            
            # Verwende zufälligen User-Agent und erhöhten Timeout
            response = requests.get(
                current_url, 
                headers={
                    "User-Agent": get_random_user_agent(),
                    "Accept": "text/html,application/xhtml+xml,application/xml",
                    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Connection": "keep-alive"
                }, 
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.warning(f"Fehler beim Abrufen von Stepstone URL {current_url}: {response.status_code}")
                continue
            
            logger.info(f"Stepstone URL {current_url} erfolgreich abgerufen")
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Speichere HTML für Debug-Zwecke
            if "Keine passenden Jobs gefunden" in response.text:
                logger.warning("Stepstone meldet 'Keine passenden Jobs gefunden'")
                continue
                
            # Neuere Stepstone-Layoutselektoren (2024)
            job_listings = soup.select("[data-testid='job-item']") or soup.select(".sc-fzoNJl") or soup.select(".sc-results-item")
            
            # Ältere Stepstone-Layoutselektoren als Fallback
            if not job_listings:
                job_listings = soup.select("article.resultlist-qlsxrl") or soup.select(".Wrapper-sc-09qggu-0") or soup.select(".ResultsListContainer") or soup.select("article")
            
            if not job_listings:
                logger.warning(f"Keine Stepstone-Jobangebote gefunden in URL {current_url}")
                continue
            
            logger.info(f"Gefundene Stepstone-Jobangebote: {len(job_listings)}")
            
            for job in job_listings[:max_jobs]:
                try:
                    # 2024 Selektoren
                    job_title = get_text(job, [
                        "[data-testid='job-element-title']", 
                        "[data-at='job-item-title']",
                        "h5", "h2", 
                        ".listing-title", 
                        ".job-title"
                    ])
                    
                    company = get_text(job, [
                        "[data-testid='job-element-company']", 
                        "[data-at='job-item-company-name']",
                        ".company", 
                        ".listing-company", 
                        ".company-name"
                    ])
                    
                    location = get_text(job, [
                        "[data-testid='job-element-location']", 
                        "[data-at='job-item-location']",
                        ".location", 
                        ".listing-location"
                    ])
                    
                    # Verschiedene Methoden zum Extrahieren des Links
                    url_element = None
                    url_selectors = [
                        "a[data-testid='job-element-link']", 
                        "a[data-at='job-item-title']",
                        "a.resultlist-8job4e", 
                        "h2 a", 
                        "h5 a", 
                        "a"
                    ]
                    
                    for selector in url_selectors:
                        url_element = job.select_one(selector)
                        if url_element:
                            break
                    
                    if not job_title or not url_element:
                        logger.warning("Unvollständige Job-Informationen, überspringe")
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
        
        except Exception as e:
            logger.error(f"Fehler bei Stepstone-URL {current_url}: {type(e).__name__}: {e}")
            continue
    
    # Nur wenn alle URLs fehlgeschlagen sind, verwende Beispieldaten
    if not jobs:
        logger.warning("Keine Stepstone-Jobs gefunden unter allen URLs, verwende Beispieldaten")
        jobs = get_example_jobs(title, city, "stepstone", max_jobs)
    
    logger.info(f"Stepstone-Suche abgeschlossen in {time.time() - start_time:.2f}s, {len(jobs)} Jobs gefunden")
    return jobs

def find_monster_jobs(title, city, max_jobs=3):
    """
    Findet Monster Jobs für den angegebenen Titel und die Stadt.
    
    max_jobs: Maximale Anzahl der zurückzugebenden Jobs (zum Vermeiden von Timeouts)
    """
    start_time = time.time()
    if not title or not city:
        logger.info("Monster-Beispieldaten zurückgegeben, da Titel oder Stadt fehlen")
        return get_example_jobs(title, city, "monster", max_jobs)
        
    # Debug-Modus: Immer Beispieldaten zurückgeben
    if DEBUG_MODE:
        logger.info("DEBUG-MODUS: Monster-Beispieldaten werden zurückgegeben")
        return get_example_jobs(title, city, "monster", max_jobs)

    logger.info(f"Monster-Suche gestartet für Titel='{title}', Stadt='{city}'")
    
    # URL-Formatierung verbessert
    search_title = title.strip().replace(" ", "+")
    search_city = city.strip().replace(" ", "+")
    url = f"https://www.monster.de/jobs/suche/?q={search_title}&where={search_city}"
    
    # Alternative URLs für den Fall, dass die Haupturl nicht funktioniert
    alternative_urls = [
        f"https://www.monster.de/jobs/suche/?q={search_title}&where={search_city}",
        f"https://www.monster.de/jobs/search/?q={search_title}&where={search_city}"
    ]
    
    jobs = []
    
    # Versuche verschiedene URLs
    for current_url in alternative_urls:
        if jobs:
            break  # Wenn wir bereits Jobs gefunden haben, beenden
            
        try:
            logger.info(f"Versuche URL: {current_url}")
            
            # Verwende zufälligen User-Agent und erhöhten Timeout
            response = requests.get(
                current_url, 
                headers={
                    "User-Agent": get_random_user_agent(),
                    "Accept": "text/html,application/xhtml+xml,application/xml",
                    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
                }, 
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.warning(f"Fehler beim Abrufen von Monster URL {current_url}: {response.status_code}")
                continue
            
            logger.info(f"Monster URL {current_url} erfolgreich abgerufen")
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 2024 Monster Layout-Selektoren
            job_listings = soup.select("[data-testid='jobCard']") or soup.select(".job-search-card") or soup.select("#SearchResults .card-content")
            
            # Fallback auf ältere Selektoren
            if not job_listings:
                job_listings = soup.select(".results-card") or soup.select(".job-cardstyle__JobCardComponent") or soup.select(".job-search-resultsstyle__JobCardWrap") or soup.select("article")
            
            if not job_listings:
                logger.warning(f"Keine Monster-Jobangebote gefunden in URL {current_url}")
                continue
            
            logger.info(f"Gefundene Monster-Jobangebote: {len(job_listings)}")
            
            for job in job_listings[:max_jobs]:
                try:
                    # 2024 Selektoren und Fallbacks
                    job_title = get_text(job, [
                        "[data-testid='jobTitle']", 
                        ".job-card-title", 
                        ".title", 
                        "h2", 
                        ".job-title"
                    ])
                    
                    company = get_text(job, [
                        "[data-testid='company']", 
                        ".job-card-company", 
                        ".company", 
                        ".name", 
                        ".company-name"
                    ])
                    
                    location = get_text(job, [
                        "[data-testid='location']", 
                        ".job-card-location", 
                        ".location", 
                        ".address", 
                        ".job-location"
                    ])
                    
                    # Verschiedene Methoden zum Extrahieren des Links
                    url_element = None
                    url_selectors = [
                        "a[data-testid='jobDetailUrl']", 
                        "a.job-card-link", 
                        ".title a", 
                        "h2 a", 
                        "a"
                    ]
                    
                    for selector in url_selectors:
                        url_element = job.select_one(selector)
                        if url_element:
                            break
                    
                    if not job_title or not url_element:
                        logger.warning("Unvollständige Monster-Job-Informationen, überspringe")
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
        
        except Exception as e:
            logger.error(f"Fehler bei Monster-URL {current_url}: {type(e).__name__}: {e}")
            continue
    
    # Nur wenn alle URLs fehlgeschlagen sind, verwende Beispieldaten
    if not jobs:
        logger.warning("Keine Monster-Jobs gefunden unter allen URLs, verwende Beispieldaten")
        jobs = get_example_jobs(title, city, "monster", max_jobs)
    
    logger.info(f"Monster-Suche abgeschlossen in {time.time() - start_time:.2f}s, {len(jobs)} Jobs gefunden")
    return jobs

def get_text(element, selectors):
    """
    Versucht, Text aus einem Element mit verschiedenen Selektoren zu extrahieren.
    
    Gibt den ersten gefundenen Text zurück oder leeren String, wenn nichts gefunden wurde.
    """
    for selector in selectors:
        try:
            selected = element.select_one(selector)
            if selected and selected.text.strip():
                return selected.text.strip()
        except Exception:
            continue
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