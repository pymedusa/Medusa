import Vue from 'vue';
import VueResource from 'vue-resource';
import router from './router';
import store from './store';
import App from './components/app.vue';

Vue.use(VueResource);

new Vue({ // eslint-disable-line no-new
    el: '#app',
    router,
    render: h => h(App),
    store
});
