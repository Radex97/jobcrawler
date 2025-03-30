import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { API_URL } from 'src/app/env';
import { Job } from './job-card/job';

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
    
    return this.http.get<Job[]>(url, {
      params: { title, city },
    }).pipe(
      tap((response: Job[]) => console.log('API-Antwort:', response)),
      catchError((error: any) => {
        console.error('API-Fehler:', error);
        throw error;
      })
    );
  }
}
