window.vueSubmitForm = async function(formId) {
    const element = document.getElementById(formId);
    const formData = new FormData(element);
    const method = element.getAttribute('method');
    const base = document.getElementsByTagName('base')[0].getAttribute('href');
    const path = element.getAttribute('action');
    const redirect = element.getAttribute('redirect');

    // @TODO: Add this back when we're JSON only
    //        This converts formData to JSON
    // const body = Array.from(formData.entries()).reduce((memo, pair) => ({
    // ...memo,
    // [pair[0]]: pair[1]
    // }), {});
    this.$http[method](path, { body: formData, redirect: 'follow' })
        .then(() => {
            if (redirect) {
                window.location.href = base + redirect;
            }
        });
};
