import api from './api';

const getUser = () => {
    return new Promise((resolve, reject) => {
        api.get('user').then(({data}) => {
            // Change this to use user: data.user once we fix the API
            resolve({user: data});
        }).catch(reject);
    });
};

export default {
    getUser
};
