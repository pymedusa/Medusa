// Imported from vender.js
import log from 'loglevel'; // eslint-disable-line import/no-unresolved

// Please only use testLogger when testing
const testLogger = log.getLogger('test').setLevel(log.levels.TRACE);
const generalLogger = log.getLogger('general');

// Each component of our app should have it's own logger
const apiLogger = log.getLogger('api');
const seriesLogger = log.getLogger('series');

export default generalLogger;

export {
    testLogger,
    generalLogger,
    apiLogger,
    seriesLogger
};
