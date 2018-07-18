// @ts-check
import axios from 'axios';

const baseUrl = document.body.getAttribute('web-root');
const idToken = document.body.getAttribute('api-key');

/**
 * Api client based on the axios client, to communicate with medusa's web routes, which return json data.
 */
const apiRoute = axios.create({ // eslint-disable-line no-unused-vars
    baseURL: baseUrl + '/',
    timeout: 10000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json'
    }
});

/**
 * Api client based on the axios client, to communicate with medusa's api v1.
 */
const apiv1 = axios.create({ // eslint-disable-line no-unused-vars
    baseURL: baseUrl + '/api/v1/' + idToken + '/',
    timeout: 10000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json'
    }
});

/**
 * Api client based on the axios client, to communicate with medusa's api v2.
 */
const api = axios.create({ // eslint-disable-line no-unused-vars
    baseURL: baseUrl + '/api/v2/',
    timeout: 10000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': idToken
    }
});

export {
    apiRoute,
    apiv1,
    api
}
