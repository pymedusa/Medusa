import axios from 'axios';

const api = axios.create({
    baseURL: '/api/v2/',
    timeout: 10000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json'
    }
});

api.interceptors.request.use(request => {
    const token = localStorage.getItem('token');
    const headers = request.headers || (request.headers = {});

    if (token !== null && token !== 'undefined') {
        // @TODO: Switch back to Bearer once we have jwt added properly
        // headers.Authorization = `Bearer ${token}`;
        headers['X-Api-Key'] = token;
    }

    return request;
}, err => Promise.reject(err));

api.interceptors.response.use(response => {
    if (response.status && response.status.code === 401) {
        localStorage.removeItem('token');
    }

    // @TODO: Add a way to save token when passed back in response
    // if (response.headers && response.headers.Authorization) {
    //     localStorage.setItem('token', response.headers.Authorization);
    // }
    //
    // if (response.entity && response.entity.token && response.entity.token.length > 10) {
    //     localStorage.setItem('token', response.entity.token);
    // }

    return response;
}, err => Promise.reject(err));

export default api;
