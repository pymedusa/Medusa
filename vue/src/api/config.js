import api from './api';

const getConfig = () => {
    return new Promise((resolve, reject) => {
        api.get('config').then(({data}) => {
            // Change this to use config: data.config once we fix the API
            resolve({config: data});
        }).catch(reject);
    });
};

export default {
    getConfig
};
