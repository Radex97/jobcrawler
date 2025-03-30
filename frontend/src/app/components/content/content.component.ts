import { Component, OnInit } from '@angular/core';
import { ContentService } from './content.service';
import { Job } from './job-card/job';
import { Search } from './job-search-form/search';

@Component({
  selector: 'app-content',
  templateUrl: './content.component.html',
})
export class ContentComponent implements OnInit {
  jobs: Job[];

  constructor(private contentService: ContentService) {
    console.log('ContentComponent initialisiert');
  }

  ngOnInit(): void {
    console.log('ContentComponent ngOnInit');
  }

  getJobs({ source, title, city }: Search) {
    console.log('ContentComponent.getJobs() aufgerufen mit:', { source, title, city });
    
    this.contentService
      .getJobs(source, title, city)
      .subscribe(
        (jobs) => {
          console.log('Jobs erfolgreich geladen:', jobs);
          this.jobs = jobs;
        },
        (error) => {
          console.error('Fehler beim Laden der Jobs:', error);
          alert('Fehler beim Laden der Jobs. Bitte überprüfen Sie die Konsole für Details.');
        }
      );
  }
}
