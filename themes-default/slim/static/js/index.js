import Vue from 'vue';
import Vuex from 'vuex';
import VueMeta from 'vue-meta';
import VueRouter from 'vue-router';
import VueNativeSock from 'vue-native-websocket';
import VueInViewportMixin from 'vue-in-viewport-mixin';
import VueToggleButton from 'vue-js-toggle-button';
import axios from 'axios';
import httpVueLoader from 'http-vue-loader';
import store from './store';
import router from './router';
import { apiRoute, apiv1, api } from './api';

//
// vue-async-computed@3.3.0.js
// vue-snotify.min.js

if (window) {
    // Adding libs to window so mako files can use them
    window.Vue = Vue;
    window.Vuex = Vuex;
    window.VueMeta = VueMeta;
    window.VueRouter = VueRouter;
    window.VueNativeSock = VueNativeSock;
    window.VueInViewportMixin = VueInViewportMixin;
    window.VueToggleButton = VueToggleButton;
    window.axios = axios;
    window.httpVueLoader = httpVueLoader;
    window.store = store;
    window.router = router;
    window.apiRoute = apiRoute;
    window.apiv1 = apiv1;
    window.api = api;
}
