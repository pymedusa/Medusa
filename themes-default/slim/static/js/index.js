import Vue from 'vue';
import Vuex from 'vuex';
import VueMeta from 'vue-meta';
import VueRouter from 'vue-router';
import VueNativeSock from 'vue-native-websocket';
import VueInViewportMixin from 'vue-in-viewport-mixin';
import AsyncComputed from 'vue-async-computed';
import ToggleButton from 'vue-js-toggle-button';
import Snotify from 'vue-snotify';
import axios from 'axios';
import httpVueLoader from 'http-vue-loader';
import store from './store';
import router from './router';
import { apiRoute, apiv1, api } from './api';

if (window) {
    // Adding libs to window so mako files can use them
    window.Vue = Vue;
    window.Vuex = Vuex;
    window.VueMeta = VueMeta;
    window.VueRouter = VueRouter;
    window.VueNativeSock = VueNativeSock;
    window.VueInViewportMixin = VueInViewportMixin;
    window.AsyncComputed = AsyncComputed;
    window.ToggleButton = ToggleButton;
    window.Snotify = Snotify;
    window.axios = axios;
    window.httpVueLoader = httpVueLoader;
    window.store = store;
    window.router = router;
    window.apiRoute = apiRoute;
    window.apiv1 = apiv1;
    window.api = api;
}
