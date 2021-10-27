import axios from 'axios';

// This should be more dynamic. As now when we change the apiKey in config-general.vue. This won't work anymore.
// Because of this, a page reload is required.

export default function() {
    this.token = null;
    this.getToken = () => {
        return axios.get('/token')
            .then(response => {
                this.token = response.data;
                this.apiRoute = axios.create({
                    baseURL: '/',
                    timeout: 60000,
                    headers: {
                        Accept: 'application/json',
                        'Content-Type': 'application/json'
                    }
                });

                this.api = axios.create({
                    baseURL: '/api/v2/',
                    timeout: 30000,
                    headers: {
                        Accept: 'application/json',
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${this.token}`
                    }
                });
            });
    };
}
