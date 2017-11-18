const Medusa = require('medusa-lib');

const medusa = new Medusa({
    url: document.getElementsByTagName('base')[0].href
});

(async function() {
    const apiKey = document.getElementsByTagName('body')[0].getAttribute('api-key');
    if (apiKey) {
        await medusa.auth({ apiKey });
    }
})();

module.exports = medusa;
