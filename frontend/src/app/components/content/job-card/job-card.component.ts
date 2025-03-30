import { Component, Input, OnInit } from '@angular/core';
import { Job } from './job';

@Component({
  selector: 'app-job-card',
  templateUrl: './job-card.component.html',
})
export class JobCardComponent implements OnInit {
  @Input() job: Job;

  constructor() {}

  ngOnInit(): void {}
}
