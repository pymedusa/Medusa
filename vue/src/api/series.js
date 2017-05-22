import api from './api';

const getAllSeries = () => {
    return new Promise((resolve, reject) => {
        api.get('series').then(({data}) => {
            resolve({series: data.series});
        }).catch(reject);
    });
};

const getSeries = ({seriesIndexer, seriesId}) => {
    return new Promise((resolve, reject) => {
        api.get(`series/${seriesIndexer}${seriesId}`).then(({data}) => {
            resolve({series: data.series});
        }).catch(reject);
    });
};

export default {
    getSeries,
    getAllSeries
};
