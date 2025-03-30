import urllib3
from bs4 import BeautifulSoup
import logging

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_stepstone_jobs(title: str, city: str):
    """ BeautifulSoup4 web scraping for Stepstone """
    try:
        http = urllib3.PoolManager()
        
        # Deutsche URL verwenden statt schwedischer
        url = f"https://www.stepstone.de/jobs/{title}/in-{city}"
        logger.info(f"Stepstone-Scraping mit URL: {url}")
        
        page = http.request("GET", url)
        logger.info(f"Stepstone-Antwort-Status: {page.status}")
        
        soup = BeautifulSoup(page.data, "lxml")
        
        # Selektoren für deutsche Stepstone-Webseite anpassen
        job_listings = soup.find_all("article", class_="ResultsListEntry")
        logger.info(f"Gefundene Job-Listings: {len(job_listings)}")
        
        jobs = []
        for item in job_listings[:9]:  # Begrenze auf 9 Ergebnisse
            try:
                title_elem = item.find("h2", class_="ResultsListEntry-title")
                company_elem = item.find("span", class_="ResultsListEntry-company")
                location_elem = item.find("span", class_="ResultsListEntry-location")
                url_elem = item.find("a", class_="ResultsListEntry-link")
                
                if title_elem and company_elem and location_elem and url_elem:
                    job = {
                        "title": title_elem.text.strip(),
                        "company": company_elem.text.strip(),
                        "location": location_elem.text.strip(),
                        "url": url_elem.get("href", "")
                    }
                    jobs.append(job)
            except Exception as e:
                logger.error(f"Fehler beim Parsen eines Stepstone-Job-Eintrags: {e}")
        
        logger.info(f"Erfolgreich {len(jobs)} Jobs von Stepstone extrahiert")
        return jobs
    except Exception as e:
        logger.error(f"Fehler beim Scraping von Stepstone: {e}")
        # Leere Liste zurückgeben, damit die Anwendung nicht abstürzt
        return []


def find_monster_jobs(title: str or None, city: str or None):
    """ BeautifulSoup4 web scraping for Monster """
    try:
        http = urllib3.PoolManager()

        # Deutsche URL verwenden
        url = ""
        if not title and not city:
            url = "https://www.monster.de/jobs/suche/"
        else:
            url = f"https://www.monster.de/jobs/suche/?q={title}&where={city}"
        
        logger.info(f"Monster-Scraping mit URL: {url}")
        
        page = http.request("GET", url)
        logger.info(f"Monster-Antwort-Status: {page.status}")
        
        soup = BeautifulSoup(page.data, "lxml")
        
        # Selektoren für deutsche Monster-Webseite anpassen
        job_listings = soup.find_all("div", class_="card-content")
        logger.info(f"Gefundene Job-Listings: {len(job_listings)}")
        
        jobs = []
        for item in job_listings[:9]:  # Begrenze auf 9 Ergebnisse
            try:
                title_elem = item.find("h2", class_="title")
                company_elem = item.find("div", class_="company")
                location_elem = item.find("div", class_="location")
                url_elem = item.find("a", class_="card-title-link")
                
                if title_elem and company_elem and location_elem and url_elem:
                    job = {
                        "title": title_elem.text.strip(),
                        "company": company_elem.text.strip(),
                        "location": location_elem.text.strip(),
                        "url": url_elem.get("href", "")
                    }
                    jobs.append(job)
            except Exception as e:
                logger.error(f"Fehler beim Parsen eines Monster-Job-Eintrags: {e}")
        
        logger.info(f"Erfolgreich {len(jobs)} Jobs von Monster extrahiert")
        return jobs
    except Exception as e:
        logger.error(f"Fehler beim Scraping von Monster: {e}")
        # Leere Liste zurückgeben, damit die Anwendung nicht abstürzt
        return []