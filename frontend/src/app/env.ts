declare const process: any;

const API_URL = (window as any).NODE_ENV === 'production' 
  ? 'https://jobcrawler-production.up.railway.app/'
  : 'http://localhost:5000/';

export { API_URL };
