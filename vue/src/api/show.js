import {apiError} from '../errors';
import api from './api';

export default {
    getShows(next) {
        // The {} around data grabs it from the response param
        api.get('show').then(({data}) => next(data)).catch(apiError);
    },
    addShow(show, next) {
        next(null, show);
    }
};
