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

  constructor(private contentService: ContentService) {}

  ngOnInit(): void {}

  getJobs({ source, title, city }: Search) {
    this.contentService
      .getJobs(source, title, city)
      .subscribe((jobs) => (this.jobs = jobs));
  }
}
