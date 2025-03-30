import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { Search } from './search';

@Component({
  selector: 'app-job-search-form',
  templateUrl: './job-search-form.component.html',
})
export class JobSearchFormComponent implements OnInit {
  @Output() getJobs: EventEmitter<any> = new EventEmitter();

  sources = [
    { name: 'Monster', value: 'monster' },
    { name: 'Stepstone', value: 'stepstone' },
  ];

  jobSearch = new FormGroup({
    title: new FormControl(''),
    city: new FormControl(''),
    source: new FormControl(this.sources[0]),
  });

  constructor() {}

  ngOnInit(): void {}

  onSubmit() {
    const search: Search = {
      source: this.jobSearch.controls['source'].value.value,
      title: this.jobSearch.controls['title'].value,
      city: this.jobSearch.controls['city'].value,
    };

    this.getJobs.emit(search);
  }
}
