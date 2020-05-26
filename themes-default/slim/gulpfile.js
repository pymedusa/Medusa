const path = require('path');
const gulp = require('gulp');
const imagemin = require('gulp-imagemin');
const pngquant = require('imagemin-pngquant');
const changed = require('gulp-changed');

const pkg = require('./package.json');

/**
 * Make an "images" task for the provided theme.
 *
 * @param {string} theme - Theme object.
 * @returns {function} A function (task) that performs as described above.
 */
const makeMoveImagesTask = theme => {
    /**
      * Compressing and copying images to their destinations.
      * Should save up to 50% of total filesize.
      *
      * @returns {NodeJS.ReadWriteStream} stream
      */
    const moveImages = () => {
        const buildDest = path.normalize(theme.dest);
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

    // Rename `moveImages` function so it has a more descriptive name
    Object.defineProperty(moveImages, 'name', { value: `move-images-${theme.name}` });
    return moveImages;
};

/** Gulp tasks */

const generateSyncTasks = () => {
    const tasks = pkg.config.cssThemes.map(theme => makeMoveImagesTask(theme));
    return gulp.series(...tasks);
};

exports.sync = generateSyncTasks();

/**
 * Sync by default.
 */
exports.default = exports.sync;
