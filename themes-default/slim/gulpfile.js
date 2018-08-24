const path = require('path');
const runSequence = require('run-sequence');
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

/**
 * By default build.
 */
gulp.task('default', ['sync']);

const syncTheme = (theme, sequence) => {
    return new Promise(resolve => {
        console.log(`Starting syncing for theme: ${theme}`);
        setCsstheme(theme);
        runSequence(sequence, resolve);
    });
};

/**
 * Build the current theme and copy all files to the location configured in the package.json config attribute.
 */
gulp.task('sync', async () => { // eslint-disable-line space-before-function-paren
    // Whe're building the light and dark theme. For this we need to run two sequences.
    // If we need a yargs parameter name csstheme.
    for (const theme of Object.keys(config.cssThemes)) {
        await syncTheme(theme, ['img']); // eslint-disable-line no-await-in-loop
    }
});

/**
 * Task for compressing and copying images to it's destination.
 * Should save up to 50% of total filesize.
 */
gulp.task('img', moveImages);
