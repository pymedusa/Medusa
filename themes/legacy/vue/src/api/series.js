import { seriesLogger as log } from '../log';
import { apiError } from '../errors';
import api from './api';

export default {
    getSeries(next) {
        // The {} around data grabs it from the response param
        api.get('series').then(({ data }) => {
            log.info(data);
            next(data.response);
        }).catch(err => {
            apiError(err);
            next(err);
        });
    },
    addSeries(series, next) {
        next(null, series);
    }
};
