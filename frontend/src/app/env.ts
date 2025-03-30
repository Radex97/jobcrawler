declare const process: any;

const API_URL = (window as any).NODE_ENV === 'production' 
  ? 'https://jobcrawler-production.up.railway.app/api/'
  : 'http://localhost:5000/api/';

export { API_URL };
