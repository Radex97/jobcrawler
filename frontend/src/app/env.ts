const API_URL = process.env.NODE_ENV === 'production' 
  ? 'https://jobcrawler-production.up.railway.app/'
  : 'http://localhost:5000/';

export { API_URL };
