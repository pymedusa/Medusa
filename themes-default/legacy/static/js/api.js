var baseUrl = $('body').attr('api-root');
var idToken = $('body').attr('api-key');

var api = axios.create({ // eslint-disable-line no-unused-vars
    baseURL: baseUrl,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': idToken
    }
});
