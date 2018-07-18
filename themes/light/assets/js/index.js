import Vue from 'vue';
import Vuex from 'vuex';
import VueMeta from 'vue-meta';
import VueRouter from 'vue-router';
import VueNativeSock from 'vue-native-websocket';
import VueInViewportMixin from 'vue-in-viewport-mixin';
import httpVueLoader from 'http-vue-loader';
import store from './store';
import router from './router';
import { apiRoute, apiv1, api } from './api';

// vue-async-computed@3.3.0.js
// vue-snotify.min.js
// vue-js-toggle-button.js

if (window) {
    // Adding libs to window so mako files can use them
    window.Vue = Vue;
    window.Vuex = Vuex;
    window.VueMeta = VueMeta;
    window.VueRouter = VueRouter;
    window.VueNativeSock = VueNativeSock;
    window.vueInViewportMixin = VueInViewportMixin;
    window.httpVueLoader = httpVueLoader;
    window.store = store;
    window.router = router;
    window.apiRoute = apiRoute;
    window.apiv1 = apiv1;
    window.api = api;
}
