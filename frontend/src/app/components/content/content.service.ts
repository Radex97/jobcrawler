import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { API_URL } from 'src/app/env';
import { Job } from './job-card/job';

// Schnittstelle für die API-Antwort
interface ApiResponse {
  jobs: Job[];
  databaseAvailable: boolean;
  timeoutOccurred: boolean;
  error?: string;
}

@Injectable({
  providedIn: 'root',
})
export class ContentService {
  constructor(private http: HttpClient) {
    console.log('ContentService initialisiert');
    console.log('API_URL ist:', API_URL);
  }

  getJobs(source: string, title: string, city: string): Observable<Job[]> {
    const url = API_URL + source;
    console.log(`ContentService.getJobs() - Anfrage an ${url} mit Parametern:`, { title, city });
    
    return this.http.get<ApiResponse>(url, {
      params: { title, city },
    }).pipe(
      tap((response: ApiResponse) => {
        console.log('API-Antwort:', response);
        if (response.timeoutOccurred) {
          console.warn('Zeitüberschreitung bei der API-Anfrage!');
        }
        if (!response.databaseAvailable) {
          console.warn('Datenbank nicht verfügbar!');
        }
      }),
      map((response: ApiResponse) => {
        // Extrahiere nur das jobs-Array aus der Antwort
        if (!response.jobs || !Array.isArray(response.jobs)) {
          console.error('Unerwartetes Format der API-Antwort:', response);
          return []; // Leeres Array zurückgeben, wenn keine Jobs vorhanden sind
        }
        return response.jobs;
      }),
      catchError((error: any) => {
        console.error('API-Fehler:', error);
        throw error;
      })
    );
  }
}
