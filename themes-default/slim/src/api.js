import axios from 'axios';

// This should be more dynamic. As now when we change the apiKey in config-general.vue. This won't work anymore.
// Because of this, a page reload is required.

export default function() {
    this.webRoot = document.body.getAttribute('web-root');
    this.token = null;
    this.getToken = () => {
        return axios.get(`${this.webRoot}/token`)
            .then(response => {
                this.token = response.data;
                this.apiRoute = axios.create({
                    baseURL: `${this.webRoot}/`,
                    timeout: 60000,
                    headers: {
                        Accept: 'application/json',
                        'Content-Type': 'application/json'
                    }
                });

                this.api = axios.create({
                    baseURL: `${this.webRoot}/api/v2/`,
                    timeout: 30000,
                    headers: {
                        Accept: 'application/json',
                        'Content-Type': 'application/json',
                        'x-auth': `Bearer ${this.token}`
                    }
                });
            });
    };
}
