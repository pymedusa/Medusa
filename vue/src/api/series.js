import api from './api';

const getAllSeries = () => {
    return new Promise((resolve, reject) => {
        api.get('series').then(({data}) => {
            // Change this to use series: data.series once we fix the API
            resolve({series: data});
        }).catch(reject);
    });
};

const getSeries = ({seriesIndexer, seriesId}) => {
    return new Promise((resolve, reject) => {
        api.get(`series/${seriesIndexer}${seriesId}`).then(({data}) => {
            // Change this to use series: data.series once we fix the API
            resolve({series: data});
        }).catch(reject);
    });
};

export default {
    getSeries,
    getAllSeries
};
