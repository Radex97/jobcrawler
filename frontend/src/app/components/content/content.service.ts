import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from 'src/app/env';
import { Job } from './job-card/job';

@Injectable({
  providedIn: 'root',
})
export class ContentService {
  constructor(private http: HttpClient) {}

  getJobs(source: string, title: string, city: string): Observable<Job[]> {
    return this.http.get<Job[]>(API_URL + source, {
      params: { title, city },
    });
  }
}
