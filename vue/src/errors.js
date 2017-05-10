import {apiLogger} from './log';

// @TODO: Add more stuff in here for HTTP errors and such
const apiError = err => apiLogger.error(err);

export {
    apiError // eslint-disable-line import/prefer-default-export
};
