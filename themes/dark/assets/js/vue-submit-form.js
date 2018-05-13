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
        .then(res => {
            // We can get the redirect url using obj.url.
            if (res.url) {
                window.location.href = res.url;
            } else if (redirect) {
                // This is statically redirecting to "/", or at least for addNewShow.
                // But how are we going to use the redirect offered by tornado?
                window.location.href = base + redirect;
            }
        });
};
