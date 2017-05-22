import axios from 'axios';

const api = axios.create({
    baseURL: '/api/v2/',
    timeout: 5000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json'
    }
});

api.interceptors.request.use(async request => {
    const response = await axios.get('/token');
    const apiKey = response.data.token;
    const token = localStorage.getItem('token');
    const headers = request.headers || (request.headers = {});

    if (token !== null && token !== 'undefined') {
        headers.Authorization = `Bearer ${token}`;
    }

    if (apiKey !== null && apiKey !== 'undefined') {
        headers['X-Api-Key'] = apiKey;
        localStorage.setItem('token', apiKey);
    }

    return request;
}, err => Promise.reject(err));

api.interceptors.response.use(response => {
    if (response.status && (response.status.code === 401 || response.status.code === 403)) {
        localStorage.removeItem('token');
    }

    return response;
}, err => Promise.reject(err));

export default api;
