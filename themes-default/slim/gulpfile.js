const path = require('path');
const gulp = require('gulp');
const imagemin = require('gulp-imagemin');
const pngquant = require('imagemin-pngquant');
const changed = require('gulp-changed');

const pkg = require('./package.json');

const { config } = pkg;
let buildDest = '';

/**
 * Attempt to get the cssTheme config object from the package.json.
 * @param {string} theme theme to try and get
 */
const setCsstheme = theme => {
    const cssTheme = config.cssThemes[theme];
    if (cssTheme) {
        buildDest = path.normalize(cssTheme.dest);
    }
};

/**
 * Compressing and copying images to their destinations.
 * Should save up to 50% of total filesize.
 *
 * @returns {NodeJS.ReadWriteStream} stream
 */
const moveImages = () => {
    const dest = `${buildDest}/assets/img`;
    return gulp
        .src('static/images/**/*', {
            base: 'static/images/'
        })
        .pipe(changed(dest))
        .pipe(imagemin({
            progressive: true,
            svgoPlugins: [{ removeViewBox: false }, { cleanupIDs: false }],
            use: [pngquant()]
        }))
        .pipe(gulp.dest(dest));
};

/** Gulp tasks */

const generateSyncTasks = () => {
    const tasks = Object.keys(config.cssThemes).map(theme => {
        const setTheme = callback => {
            console.log(`Starting syncing for theme: ${theme}`);
            setCsstheme(theme);
            callback();
        };
        return gulp.series(setTheme, moveImages);
    });
    return gulp.series(...tasks);
};

exports.sync = generateSyncTasks();

/**
 * Sync by default.
 */
exports.default = exports.sync;
