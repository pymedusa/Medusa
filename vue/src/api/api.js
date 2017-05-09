import axios from 'axios';

const idToken = localStorage.getItem('idToken');

const api = axios.create({
    timeout: 10000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${idToken}`
    }
});

export default api;
