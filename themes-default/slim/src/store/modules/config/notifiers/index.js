import { ADD_CONFIG } from '../../../mutation-types';
import boxcar2 from './boxcar2';
import discord from './discord';
import email from './email';
import emby from './emby';
import freemobile from './freemobile';
import growl from './growl';
import kodi from './kodi';
import libnotify from './libnotify';
import nmj from './nmj';
import nmjv2 from './nmjv2';
import plex from './plex';
import prowl from './prowl';
import pushalot from './pushalot';
import pushbullet from './pushbullet';
import join from './join';
import pushover from './pushover';
import pyTivo from './py-tivo';
import slack from './slack';
import synology from './synology';
import synologyIndex from './synology-index';
import telegram from './telegram';
import trakt from './trakt';
import twitter from './twitter';

const state = {};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'notifiers') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {};

const actions = {};

const modules = {
    boxcar2,
    discord,
    email,
    emby,
    freemobile,
    growl,
    kodi,
    libnotify,
    nmj,
    nmjv2,
    plex,
    prowl,
    pushalot,
    pushbullet,
    join,
    pushover,
    pyTivo,
    slack,
    synology,
    synologyIndex,
    telegram,
    trakt,
    twitter
};

export default {
    state,
    mutations,
    getters,
    actions,
    modules
};
