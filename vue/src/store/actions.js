import * as types from './mutation-types';

const addSeries = ({commit}, series) => {
    commit(types.SERIES_CREATE_SINGULAR, {
        id: series.id
    });
};

export default addSeries;
