import * as types from './mutation-types'

const addShow = ({commit}, show) => {
    commit(types.ADD_SHOW, {
        id: show.id
    });
};

export default addShow;
