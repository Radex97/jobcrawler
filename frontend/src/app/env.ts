declare const process: any;

// Die API-URL sollte die tatsächliche Produktions-Domain verwenden
const API_URL = window.location.hostname.includes('jobcrawler') 
  ? window.location.origin + '/api/'  // Verwende die aktuelle Domain + /api/
  : 'http://localhost:5000/api/';     // Im lokalen Entwicklungsmodus

console.log('API_URL konfiguriert als:', API_URL);
console.log('Current hostname:', window.location.hostname);

export { API_URL };
