const Medusa = require('medusa-lib');

const medusa = new Medusa({
    url: document.getElementsByTagName('base')[0].href
});

(async function() {
    await medusa.auth({ apiKey: document.getElementsByTagName('body')[0].getAttribute('api-key') });
})();

module.exports = medusa;
