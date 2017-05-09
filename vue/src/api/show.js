export default {
    getShows(next) {
        next();
    },
    addShow(show, next) {
        next(null, show);
    }
};
