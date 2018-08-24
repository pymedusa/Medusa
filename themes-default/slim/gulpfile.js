const fs = require('fs');
const path = require('path');
const runSequence = require('run-sequence');
const livereload = require('gulp-livereload');
const gulpif = require('gulp-if');
const gulp = require('gulp');
const imagemin = require('gulp-imagemin');
const pngquant = require('imagemin-pngquant');
const { argv } = require('yargs');
const rename = require('gulp-rename');
const changed = require('gulp-changed');

const PROD = process.env.NODE_ENV === 'production';
const pkg = require('./package.json');

const { config } = pkg;
let cssTheme = argv.csstheme;
let buildDest = '';

/**
 * Get theme object.
 * @param {*} theme name passed by yargs.
 * @returns {Object} theme object
 */
const getCssTheme = theme => {
    // Using the --csstheme is mandatory.
    if (argv.csstheme === undefined && !theme) {
        throw new Error('You need to pass a csstheme to build with the param --csstheme');
    }

    // Check if the theme provided is available in the package.json config.
    if (!config.cssThemes[theme]) {
        throw new Error(`Please provide a valid theme with the --cssTheme parameter, theme ${theme} is not available in the package.json config section.`);
    }
    return config.cssThemes[theme];
};

/**
 * Attempt to get the cssTheme config object from the package.json.
 * @param {string} theme theme to try and get
 */
const setCsstheme = theme => {
    cssTheme = getCssTheme(theme || cssTheme);
    if (cssTheme) {
        buildDest = path.normalize(cssTheme.dest);
    }
};

const watch = () => {
    livereload.listen({ port: 35729 });
    // Image changes
    gulp.watch([
        'static/images/**/*.gif',
        'static/images/**/*.png',
        'static/images/**/*.jpg'
    ], ['img']);

    // Css changes
    gulp.watch([
        'static/css/**/*.css'
    ], ['css']);
};

/**
 * Files from the source root to copy to destination.
 */
const rootFiles = [
    'index.html'
];

const moveRoot = () => {
    const pkgFilePath = path.join(buildDest, 'package.json');
    console.log(`Writing ${pkgFilePath}`);
    const theme = JSON.stringify({
        name: cssTheme.name,
        version: pkg.version,
        author: pkg.author
    }, undefined, 2);
    fs.writeFileSync(pkgFilePath, theme);

    console.log(`Moving root files to: ${buildDest}`);
    return gulp
        .src(rootFiles)
        .pipe(changed(buildDest))
        .pipe(gulp.dest(buildDest));
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
        .pipe(gulp.dest(dest))
        .pipe(gulpif(!PROD, livereload({ port: 35729 })))
        .pipe(gulpif(PROD, gulp.dest(dest)));
};

/**
 * Move and rename css.
 * @returns {*} gulp stream
 */
const moveCss = () => {
    const dest = `${buildDest}/assets`;
    return gulp
        .src([
            '!static/css/light.css',
            '!static/css/dark.css',
            'static/css/**/*'
        ], {
            base: 'static'
        })
        .pipe(changed(dest))
        .pipe(gulp.dest(dest));
};

/**
 * Move and rename themed css.
 * @returns {*} gulp stream
 */
const moveAndRenameCss = () => {
    const dest = `${buildDest}/assets/css`;
    return gulp
        .src(`static/css/${cssTheme.css}`)
        .pipe(rename(`themed.css`))
        .pipe(gulp.dest(dest));
};

/** Gulp tasks */

/**
 * By default build.
 */
gulp.task('default', ['build']);

/**
 * Build the current theme and copy all files to the location configured in the package.json config attribute.
 * It's required to pass the theme name through the `--csstheme` parameter.
 * For example: gulp build --csstheme light, will build the theme and rename the light.css to themed.css and
 * copy all files to /themes/[theme dest]/. Themes destination is configured in the package.json.
 */
gulp.task('build', done => {
    // Whe're building the light and dark theme. For this we need to run two sequences.
    // If we need a yargs parameter name csstheme.
    setCsstheme();
    runSequence('css', 'cssTheme', 'img', 'root', () => {
        if (!PROD) {
            done();
        }
    });
});

const syncTheme = (theme, sequence) => {
    return new Promise(resolve => {
        console.log(`Starting syncing for theme: ${theme[0]}`);
        setCsstheme(theme[0]);
        runSequence(sequence, resolve);
    });
};

/**
 * Build the current theme and copy all files to the location configured in the package.json config attribute.
 * It's required to pass the theme name through the `--csstheme` parameter.
 * For example: gulp build --csstheme light, will build the theme and rename the light.css to themed.css and
 * copy all files to /themes/[theme dest]/. Themes destination is configured in the package.json.
 */
gulp.task('sync', async () => { // eslint-disable-line space-before-function-paren
    // Whe're building the light and dark theme. For this we need to run two sequences.
    // If we need a yargs parameter name csstheme.
    for (const theme of Object.entries(config.cssThemes)) {
        await syncTheme(theme, ['css', 'cssTheme', 'img', 'root']); // eslint-disable-line no-await-in-loop
    }
});

/**
 * Watch file changes and build.
 */
gulp.task('watch', ['build'], watch);

/**
 * Task for compressing and copying images to it's destination.
 * Should save up to 50% of total filesize.
 */
gulp.task('img', moveImages);

/**
 * Copy all css files to the destination excluding the theme files, as whe're going to rename those.
 */
gulp.task('css', moveCss);

/**
 * Copy and rename the light or dark theme files from the configuration located in the package.json.
 * For example cssThemes.light.css for the `light.css` theme.
 */
gulp.task('cssTheme', moveAndRenameCss);

/**
 * Task for moving the files out of the root folder (index.html and package.json) to the destinations
 * root folder. These are required to let medusa read the themes metadata.
 */
gulp.task('root', moveRoot);
