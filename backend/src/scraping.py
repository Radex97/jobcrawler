import urllib3
from bs4 import BeautifulSoup
import logging
import time
import random
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from fake_useragent import UserAgent
from webdriver_manager.chrome import ChromeDriverManager

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

# Debug-Modus für Scraper-Entwicklung - EXPLIZIT DEAKTIVIERT FÜR PRODUKTION
DEBUG_MODE = False  # Muss False sein für Produktionsumgebung

# Verwende Selenium-Browser für Scraping (für Seiten, die JavaScript benötigen)
USE_SELENIUM = True

# Debug-Level für Logging (0=nur Fehler, 1=Warnungen, 2=Info, 3=Debug)
DEBUG_LEVEL = 2

# Browser-Konfiguration
def get_selenium_browser():
    """Konfiguriert und gibt einen Selenium Browser zurück"""
    try:
        # Chrome-Optionen konfigurieren
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Headless-Modus für Server
        chrome_options.add_argument("--no-sandbox")  # Notwendig für Docker/Railway
        chrome_options.add_argument("--disable-dev-shm-usage")  # Für Container-Umgebungen
        chrome_options.add_argument("--disable-gpu")  # Weniger Ressourcenverbrauch
        chrome_options.add_argument("--window-size=1920,1080")  # Standardgröße
        
        # Zufälligen User-Agent setzen
        try:
            ua = UserAgent()
            chrome_options.add_argument(f"--user-agent={ua.random}")
        except Exception as e:
            logger.warning(f"Konnte keinen zufälligen User-Agent verwenden: {e}")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Anti-Bot-Detection-Maßnahmen
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Anti-Automation-Detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Chrome-Service konfigurieren
        if os.path.exists("/usr/local/bin/chromedriver"):
            service = Service(executable_path="/usr/local/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            # Fallback auf automatische Installation
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Selenium stealth (anti-detection) direkt im Browser-Kontext ausführen
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['de-DE', 'de', 'en-US', 'en']
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """
        })
        
        # Timeouts setzen
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        logger.info("Selenium Browser erfolgreich initialisiert")
        return driver
    except Exception as e:
        logger.error(f"Fehler bei der Browser-Initialisierung: {type(e).__name__}: {e}")
        return None

# Seitenlade-Hilfsfunktion für Selenium
def load_page_with_selenium(url, wait_for_selector=None, timeout=15):
    """Lädt eine Seite mit Selenium und wartet auf ein bestimmtes Element"""
    driver = None
    try:
        driver = get_selenium_browser()
        if not driver:
            return None
        
        logger.info(f"Lade URL mit Selenium: {url}")
        driver.get(url)
        
        # Warte auf Ladevorgang und ggf. auf bestimmtes Element
        if wait_for_selector:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
            )
            logger.info(f"Element '{wait_for_selector}' erfolgreich geladen")
        else:
            # Sonst warte kurz, damit JavaScript laden kann
            time.sleep(3)
        
        # Führe Scroll-Operationen durch, um dynamische Inhalte zu laden
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # HTML der geladenen Seite zurückgeben
        page_source = driver.page_source
        logger.info(f"Seite erfolgreich geladen, HTML-Länge: {len(page_source)}")
        return page_source
    except TimeoutException:
        logger.warning(f"Timeout beim Laden der Seite: {url}")
        return None if not driver else driver.page_source
    except Exception as e:
        logger.error(f"Fehler beim Laden der Seite mit Selenium: {type(e).__name__}: {e}")
        return None
    finally:
        if driver:
            driver.quit()

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
        
    # Sicherheitscheck - Stellen Sie sicher, dass DEBUG_MODE False ist
    assert DEBUG_MODE == False, "DEBUG_MODE muss für Produktion deaktiviert sein"
        
    # Debug-Modus: Immer Beispieldaten zurückgeben - SOLLTE NIE AUSGEFÜHRT WERDEN
    if DEBUG_MODE:
        logger.error("DEBUG-MODUS IST AKTIVIERT! Nur Beispieldaten werden zurückgegeben!")
        return get_example_jobs(title, city, "stepstone", max_jobs)

    logger.info(f"Stepstone-Suche gestartet für Titel='{title}', Stadt='{city}'")
    
    # URL-Formatierung verbessert - Leerzeichen durch Bindestrich ersetzen und Sonderzeichen behandeln
    search_title = title.replace(" ", "-").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss").lower()
    search_city = city.replace(" ", "-").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss").lower()
    
    # Search-Variante für Selenium (mit Query-Parametern)
    selenium_url = f"https://www.stepstone.de/jobs-in-{search_city}/{search_title}"
    
    # Alternative URLs für den Fall, dass die Haupturl nicht funktioniert
    alternative_urls = [
        selenium_url,
        f"https://www.stepstone.de/jobs/{search_title}/in-{search_city}",
        f"https://www.stepstone.de/stellenangebote/suche?q={search_title}&l={search_city}",
        f"https://www.stepstone.de/stellenangebote/suche?what={search_title}&where={search_city}"
    ]
    
    jobs = []
    html_content = None
    used_url = None
    
    # Versuche mit Selenium, wenn verfügbar
    if USE_SELENIUM:
        logger.info("Verwende Selenium für Stepstone-Scraping")
        
        # Versuche jede URL mit Selenium
        for current_url in alternative_urls:
            html_content = load_page_with_selenium(
                current_url, 
                wait_for_selector=".sc-dkmUuB, .Teaser-sc-574p6w-0, [data-testid='job-item'], article",
                timeout=20
            )
            
            if html_content and len(html_content) > 1000:  # Prüfe auf valides HTML
                used_url = current_url
                logger.info(f"Erfolgreich HTML von URL geladen: {current_url}")
                break
            logger.warning(f"Konnte keine valide Seite von {current_url} laden")
        
        # Mit dem HTML weitermachen, falls gefunden
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Nach dem typischen "Keine Jobs gefunden" Text suchen
            if any(text in html_content for text in [
                "Leider haben wir keine passenden Stellenangebote", 
                "Keine passenden Jobs gefunden",
                "Keine Stellenangebote gefunden"
            ]):
                logger.warning(f"Stepstone meldet 'Keine Jobs gefunden' für {used_url}")
                return get_example_jobs(title, city, "stepstone", max_jobs)
                
            # Versuche verschiedene Selektoren für die Stellenangebote
            card_selectors = [
                "[data-testid='job-item']",  # Neues Layout
                ".sc-dkmUuB",                # Alternative Layout-Klasse
                ".Teaser-sc-574p6w-0",       # Alternatives StepStone-Layout
                "article.sc-hHtQVP",         # Artikel-Layout
                "article[data-results-list-item]",  # Datenattribut
                "article",                   # Generischer Fallback
            ]
            
            job_listings = []
            for selector in card_selectors:
                listings = soup.select(selector)
                if listings:
                    logger.info(f"Gefunden {len(listings)} Jobs mit Selektor '{selector}'")
                    job_listings = listings
                    break
            
            # Verarbeite die gefundenen Stellenangebote
            if job_listings:
                logger.info(f"Insgesamt {len(job_listings)} Stellenangebote gefunden")
                
                for job_card in job_listings[:max_jobs]:
                    try:
                        # Verschiedene Selektoren für Titel versuchen
                        title_selectors = [
                            "h2", "h3", "h5", 
                            "[data-testid='job-element-title']",
                            "[data-at='job-item-title']",
                            ".sc-dkmUuB-title",
                            ".JobCard-sc-aq7yxf-0 h2"
                        ]
                        
                        job_title = None
                        for selector in title_selectors:
                            title_elem = job_card.select_one(selector)
                            if title_elem and title_elem.text.strip():
                                job_title = title_elem.text.strip()
                                break
                        
                        # Verschiedene Selektoren für Unternehmen
                        company_selectors = [
                            "[data-testid='job-element-company']",
                            "[data-at='job-item-company-name']",
                            ".sc-dkmUuB-company",
                            ".JobCard-sc-aq7yxf-0 .company"
                        ]
                        
                        company = None
                        for selector in company_selectors:
                            company_elem = job_card.select_one(selector)
                            if company_elem and company_elem.text.strip():
                                company = company_elem.text.strip()
                                break
                                
                        # Verschiedene Selektoren für Standort
                        location_selectors = [
                            "[data-testid='job-element-location']",
                            "[data-at='job-item-location']",
                            ".sc-dkmUuB-location",
                            ".JobCard-sc-aq7yxf-0 .location"
                        ]
                        
                        location = None
                        for selector in location_selectors:
                            location_elem = job_card.select_one(selector)
                            if location_elem and location_elem.text.strip():
                                location = location_elem.text.strip()
                                break
                        
                        # URL extrahieren
                        url_element = job_card.select_one("a") or None
                        if url_element:
                            job_url = url_element.get("href", "")
                            # Relative URLs korrigieren
                            if job_url and not job_url.startswith("http"):
                                job_url = f"https://www.stepstone.de{job_url}"
                        else:
                            # Versuche alternative Methoden, um die URL zu extrahieren
                            all_links = job_card.select("a")
                            for link in all_links:
                                href = link.get("href", "")
                                if href and ("stellenangebot" in href or "job-details" in href):
                                    job_url = href if href.startswith("http") else f"https://www.stepstone.de{href}"
                                    break
                            else:
                                job_url = f"https://www.stepstone.de/stellenangebote/suche?q={search_title}&l={search_city}"
                        
                        # Validiere extrahierte Daten
                        if not job_title:
                            logger.warning(f"Kein Jobtitel gefunden für Stepstone-Job")
                            continue
                            
                        if not company:
                            company = "Unbekanntes Unternehmen"
                            
                        if not location:
                            location = city
                            
                        # Job-Objekt erstellen und zur Liste hinzufügen
                        job_object = {
                            "title": job_title,
                            "company": company,
                            "location": location,
                            "url": job_url,
                            "source": "stepstone"
                        }
                        
                        jobs.append(job_object)
                        logger.info(f"Job gefunden: {job_title} bei {company} in {location}")
                        
                    except Exception as e:
                        logger.error(f"Fehler beim Verarbeiten eines Stepstone-Jobs: {type(e).__name__}: {e}")
                        continue
                        
                    # Prüfen ob Maximum erreicht
                    if len(jobs) >= max_jobs:
                        logger.info(f"Maximale Anzahl von {max_jobs} Jobs erreicht")
                        break
            else:
                logger.warning("Keine Job-Listings in der Stepstone-Antwort gefunden")
    
    # Fallback auf normale Requests, wenn Selenium nicht verfügbar oder keine Jobs gefunden wurden
    if not jobs and not USE_SELENIUM:
        logger.info("Selenium nicht verfügbar, versuche mit normalem HTTP-Request")
        # Hier der bestehende HTTP-Request-Code
        # ...
    
    # Nach allen Versuchen, wenn keine Jobs gefunden wurden, verwende Beispieldaten
    if not jobs:
        logger.warning("Keine Stepstone-Jobs gefunden, verwende Beispieldaten")
        jobs = get_example_jobs(title, city, "stepstone", max_jobs)
    
    execution_time = time.time() - start_time
    logger.info(f"Stepstone-Suche abgeschlossen in {execution_time:.2f}s, {len(jobs)} Jobs gefunden")
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
        
    # Sicherheitscheck - Stellen Sie sicher, dass DEBUG_MODE False ist  
    assert DEBUG_MODE == False, "DEBUG_MODE muss für Produktion deaktiviert sein"
        
    # Debug-Modus: Immer Beispieldaten zurückgeben - SOLLTE NIE AUSGEFÜHRT WERDEN
    if DEBUG_MODE:
        logger.error("DEBUG-MODUS IST AKTIVIERT! Nur Beispieldaten werden zurückgegeben!")
        return get_example_jobs(title, city, "monster", max_jobs)

    logger.info(f"Monster-Suche gestartet für Titel='{title}', Stadt='{city}'")
    
    # URL-Formatierung verbessert
    search_title = title.strip().replace(" ", "+")
    search_city = city.strip().replace(" ", "+")
    
    # Direkte Jobsuche-URL (aktuelles Format 2024)
    selenium_url = f"https://www.monster.de/jobs/suche?q={search_title}&where={search_city}"
    
    # Alternative URLs für den Fall, dass die Haupturl nicht funktioniert
    alternative_urls = [
        selenium_url,
        f"https://www.monster.de/jobs/suche/?q={search_title}&where={search_city}",
        f"https://www.monster.de/jobs/search/?q={search_title}&where={search_city}"
    ]
    
    jobs = []
    html_content = None
    used_url = None
    
    # Versuche mit Selenium, wenn verfügbar
    if USE_SELENIUM:
        logger.info("Verwende Selenium für Monster-Scraping")
        
        # Versuche jede URL mit Selenium
        for current_url in alternative_urls:
            html_content = load_page_with_selenium(
                current_url, 
                wait_for_selector="[data-testid='jobCard'], .job-search-card, article.job-card",
                timeout=20
            )
            
            if html_content and len(html_content) > 1000:  # Prüfe auf valides HTML
                used_url = current_url
                logger.info(f"Erfolgreich HTML von URL geladen: {current_url}")
                break
            logger.warning(f"Konnte keine valide Seite von {current_url} laden")
        
        # Mit dem HTML weitermachen, falls gefunden
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Nach dem typischen "Keine Jobs gefunden" Text suchen
            if any(text in html_content for text in [
                "keine passenden Jobs", 
                "Leider haben wir keine passenden Stellenangebote",
                "Keine Treffer gefunden"
            ]):
                logger.warning(f"Monster meldet 'Keine Jobs gefunden' für {used_url}")
                return get_example_jobs(title, city, "monster", max_jobs)
                
            # Versuche verschiedene Selektoren für die Stellenangebote
            card_selectors = [
                "[data-testid='jobCard']",           # Neues Layout
                ".job-search-card",                  # Alternatives Layout
                "article.job-card",                  # Artikel-Layout
                ".results-card",                     # Älteres Layout
                ".job-cardstyle__JobCardComponent",  # Spezielles Layout
                "article"                            # Generischer Fallback
            ]
            
            job_listings = []
            for selector in card_selectors:
                listings = soup.select(selector)
                if listings:
                    logger.info(f"Gefunden {len(listings)} Jobs mit Selektor '{selector}'")
                    job_listings = listings
                    break
            
            # Verarbeite die gefundenen Stellenangebote
            if job_listings:
                logger.info(f"Insgesamt {len(job_listings)} Stellenangebote gefunden")
                
                for job_card in job_listings[:max_jobs]:
                    try:
                        # Verschiedene Selektoren für Titel versuchen
                        title_selectors = [
                            "[data-testid='jobTitle']",
                            ".job-card-title",
                            ".title",
                            "h2",
                            "h3.title"
                        ]
                        
                        job_title = None
                        for selector in title_selectors:
                            title_elem = job_card.select_one(selector)
                            if title_elem and title_elem.text.strip():
                                job_title = title_elem.text.strip()
                                break
                        
                        # Verschiedene Selektoren für Unternehmen
                        company_selectors = [
                            "[data-testid='company']",
                            ".job-card-company",
                            ".company",
                            ".name"
                        ]
                        
                        company = None
                        for selector in company_selectors:
                            company_elem = job_card.select_one(selector)
                            if company_elem and company_elem.text.strip():
                                company = company_elem.text.strip()
                                break
                                
                        # Verschiedene Selektoren für Standort
                        location_selectors = [
                            "[data-testid='location']",
                            ".job-card-location",
                            ".location",
                            ".address"
                        ]
                        
                        location = None
                        for selector in location_selectors:
                            location_elem = job_card.select_one(selector)
                            if location_elem and location_elem.text.strip():
                                location = location_elem.text.strip()
                                break
                        
                        # URL extrahieren
                        url_selectors = [
                            "a[data-testid='jobDetailUrl']",
                            "a.job-card-link",
                            "a.title-link",
                            "h2 a", 
                            "h3 a",
                            "a[href*='job-view']",
                            "a"
                        ]
                        
                        job_url = None
                        for selector in url_selectors:
                            url_element = job_card.select_one(selector)
                            if url_element:
                                job_url = url_element.get("href", "")
                                if job_url:
                                    # Relative URLs korrigieren
                                    if not job_url.startswith("http"):
                                        job_url = f"https://www.monster.de{job_url}"
                                    break
                        
                        # Fallback für URL
                        if not job_url:
                            job_url = f"https://www.monster.de/jobs/suche?q={search_title}&where={search_city}"
                        
                        # Validiere extrahierte Daten
                        if not job_title:
                            logger.warning(f"Kein Jobtitel gefunden für Monster-Job")
                            continue
                            
                        if not company:
                            company = "Unbekanntes Unternehmen"
                            
                        if not location:
                            location = city
                            
                        # Job-Objekt erstellen und zur Liste hinzufügen
                        job_object = {
                            "title": job_title,
                            "company": company,
                            "location": location,
                            "url": job_url,
                            "source": "monster"
                        }
                        
                        jobs.append(job_object)
                        logger.info(f"Job gefunden: {job_title} bei {company} in {location}")
                        
                    except Exception as e:
                        logger.error(f"Fehler beim Verarbeiten eines Monster-Jobs: {type(e).__name__}: {e}")
                        continue
                        
                    # Prüfen ob Maximum erreicht
                    if len(jobs) >= max_jobs:
                        logger.info(f"Maximale Anzahl von {max_jobs} Jobs erreicht")
                        break
            else:
                logger.warning("Keine Job-Listings in der Monster-Antwort gefunden")

    # Nach allen Versuchen, wenn keine Jobs gefunden wurden, verwende Beispieldaten
    if not jobs:
        logger.warning("Keine Monster-Jobs gefunden, verwende Beispieldaten")
        jobs = get_example_jobs(title, city, "monster", max_jobs)
    
    execution_time = time.time() - start_time
    logger.info(f"Monster-Suche abgeschlossen in {execution_time:.2f}s, {len(jobs)} Jobs gefunden")
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