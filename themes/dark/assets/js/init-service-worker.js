if ('serviceWorker' in navigator) {
    const base = $('base').attr('href');
    navigator.serviceWorker.register(base + 'sw.js').then(serviceWorker => {
        console.debug('Yay, service worker is live!', serviceWorker);
    }).catch(error => {
        console.debug('Error adding service worker', error);
    });
}
