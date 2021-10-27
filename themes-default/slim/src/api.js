import axios from 'axios';

// This should be more dynamic. As now when we change the apiKey in config-general.vue. This won't work anymore.
// Because of this, a page reload is required.

export default function() {
    this.apiKey = null;
    this.getToken = () => {
        return axios.get('/token')
            .then(response => {
                this.apiKey = response.data.token;
                this.apiRoute = axios.create({
                    baseURL: '/',
                    timeout: 60000,
                    headers: {
                        Accept: 'application/json',
                        'Content-Type': 'application/json'
                    }
                });

                this.apiv1 = axios.create({
                    baseURL: `/api/v1/${this.apiKey}/`,
                    timeout: 30000,
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
                        'X-Api-Key': this.apiKey
                    }
                });
            });
    };
}
