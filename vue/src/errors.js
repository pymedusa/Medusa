import log from './log';

const apiError = err => log.error(err);

export {
    apiError // eslint-disable-line import/prefer-default-export
};
