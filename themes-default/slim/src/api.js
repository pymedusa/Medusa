import axios from 'axios';

// This should be more dynamic. As now when we change the apiKey in config-general.vue. This won't work anymore.
// Because of this, a page reload is required.
export const webRoot = document.body.getAttribute('web-root');
export const apiKey = document.body.getAttribute('api-key');

/**
 * Api client based on the axios client, to communicate with medusa's web routes, which return json data.
 */
export const apiRoute = axios.create({
    baseURL: webRoot + '/',
    timeout: 60000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json'
    }
});

/**
 * Api client based on the axios client, to communicate with medusa's api v1.
 */
export const apiv1 = axios.create({
    baseURL: webRoot + '/api/v1/' + apiKey + '/',
    timeout: 30000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json'
    }
});

/**
 * Api client based on the axios client, to communicate with medusa's api v2.
 */
export const api = axios.create({
    baseURL: webRoot + '/api/v2/',
    timeout: 30000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': apiKey
    }
});
