import * as types from './mutation-types';

const addSeries = ({ commit }, series) => {
    commit(types.ADD_SERIES, {
        id: series.id
    });
};

export default addSeries;
