const baseUrl = $('body').attr('api-root');
const idToken = $('body').attr('api-key');

const api = axios.create({ // eslint-disable-line no-unused-vars
    baseURL: baseUrl,
    timeout: 10000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': idToken
    }
});
