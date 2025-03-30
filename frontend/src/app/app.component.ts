import { Component, OnInit, OnDestroy } from '@angular/core';
import { AppService } from './app.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
})
export class AppComponent implements OnInit, OnDestroy {
  constructor(private appService: AppService) {}

  ngOnInit() {
    this.appService.wakeUpServer();
  }

  ngOnDestroy() {}
}
