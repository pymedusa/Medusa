import axios from 'axios';

const webRoot = document.body.getAttribute('web-root');
const apiKey = document.body.getAttribute('api-key');

/**
 * Api client based on the axios client, to communicate with medusa's web routes, which return json data.
 */
const apiRoute = axios.create({ // eslint-disable-line no-unused-vars
    baseURL: webRoot + '/',
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
    baseURL: webRoot + '/api/v1/' + apiKey + '/',
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
    baseURL: webRoot + '/api/v2/',
    timeout: 10000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': apiKey
    }
});

export {
    webRoot,
    apiKey,
    apiRoute,
    apiv1,
    api
};
