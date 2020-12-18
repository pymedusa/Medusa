import browserEnv from 'browser-env';
import $ from 'jquery';

// Setup browser environment
browserEnv({
    // This needs to be set otherwise we get errors from vue-router
    url: 'http://localhost:8081/'
});

// Setup document variables
const baseElement = document.createElement('base');
baseElement.setAttribute('href', 'http://localhost:8081');
document.head.append(baseElement);

document.body.setAttribute('web-root', '');
document.body.setAttribute('api-key', '1234567890ABCDEF1234567890ABCDEF');

// Setup jQuery
global.$ = $;
global.jQuery = $;
