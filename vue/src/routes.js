import HomeComponent from './components/home.vue';
import NotFoundComponent from './components/not-found.vue';

export default [{
    name: 'Home',
    path: '/',
    component: HomeComponent
}, {
    name: 'NotFound',
    path: '*',
    component: NotFoundComponent
}];
